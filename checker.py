#!/usr/bin/env python3
"""Conservative, dependency-free stock monitor. Python 3.12+."""
import argparse
import datetime as dt
import hashlib
import json
import os
import random
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

UA = 'StockWatch/1.0 (personal low-frequency product availability monitor)'
HOSTS = {'www.apple.com', 'www.mediamarkt.es', 'www.fnac.es'}

class StopSource(Exception):
    def __init__(self, reason, delay=3600, permanent=False):
        self.reason, self.delay, self.permanent = reason, delay, permanent

class SafeRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if urllib.parse.urlsplit(newurl).netloc != urllib.parse.urlsplit(req.full_url).netloc:
            raise StopSource('Cross-host redirect; manual review required', permanent=True)
        return super().redirect_request(req, fp, code, msg, headers, newurl)

OPENER = urllib.request.build_opener(SafeRedirect)

def retry_delay(value, now):
    from email.utils import parsedate_to_datetime
    try:
        return max(3600, int(value))
    except (ValueError, TypeError):
        try:
            return max(3600, int(parsedate_to_datetime(value).timestamp() - now))
        except (ValueError, TypeError, OverflowError):
            return 3600

def fetch(url):
    parts = urllib.parse.urlsplit(url)
    if parts.scheme != 'https' or parts.netloc not in HOSTS:
        raise StopSource('URL outside retailer allowlist', permanent=True)
    req = urllib.request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/json,text/plain'})
    try:
        with OPENER.open(req, timeout=25) as response:
            body = response.read(3_000_001)
            if len(body) > 3_000_000:
                raise StopSource('Response exceeds 3MB safety limit')
            text = body.decode('utf-8', errors='strict')
            if re.search(r'<title[^>]*>[^<]*(?:access denied|captcha|just a moment)|cf-chl-|verify you are human', text, re.I):
                raise StopSource('Access challenge detected; manual review required', permanent=True)
            return text
    except urllib.error.HTTPError as exc:
        exc.close()
        if exc.code in (401, 403, 407, 451, 541):
            raise StopSource(f'HTTP {exc.code}; paused for manual review', permanent=True) from None
        if exc.code == 429:
            raise StopSource('HTTP 429; retailer cooldown', retry_delay(exc.headers.get('Retry-After'), time.time())) from None
        raise StopSource(f'HTTP {exc.code}; no stock conclusion') from None
    except (urllib.error.URLError, TimeoutError, UnicodeError, OSError):
        raise StopSource('Network/decoding failure; no stock conclusion') from None

def robots_rules(text, path):
    """Apply longest matching Allow/Disallow, with * and $ support, plus Crawl-delay."""
    groups, agents, rules = [], [], []
    for raw in text.splitlines() + ['User-agent: __end__']:
        line = raw.split('#', 1)[0].strip()
        if ':' not in line:
            continue
        key, value = (x.strip() for x in line.split(':', 1))
        key = key.lower()
        if key == 'user-agent':
            if rules:
                groups.append((agents, rules)); agents, rules = [], []
            agents.append(value.lower())
        elif agents and key in ('allow', 'disallow', 'crawl-delay'):
            rules.append((key, value))
    specific = [(a, r) for a, r in groups if any(x != '*' and x in UA.lower() for x in a)]
    selected = specific or [(a, r) for a, r in groups if '*' in a]
    matches, delay = [], 0
    for _, rs in selected:
        for key, value in rs:
            if key == 'crawl-delay':
                try: delay = max(delay, float(value))
                except ValueError: pass
            elif value:
                end = value.endswith('$')
                pattern = re.escape(value[:-1] if end else value).replace(r'\*', '.*')
                if re.match('^' + pattern + ('$' if end else ''), path):
                    matches.append((len(value.replace('*', '').rstrip('$')), key == 'allow'))
    return (max(matches)[1] if matches else True), delay

def extract_mm(html):
    marker = '"apolloState":'
    if marker not in html:
        raise StopSource('MediaMarkt page format changed; no stock conclusion')
    try:
        data, _ = json.JSONDecoder().raw_decode(html.split(marker, 1)[1].lstrip())
        return data
    except (ValueError, TypeError):
        raise StopSource('MediaMarkt stock data could not be decoded') from None

def mm_observations(data, products):
    results = []
    for product in products:
        pid = product['id']
        identity = data.get(f'GraphqlProduct:Media:es-ES:{pid}', {})
        title = identity.get('title', '').lower()
        expected = f"{product['capacity_gb']} gb"
        if identity.get('id') != pid or not all(x in title for x in ('iphone duo', 'blanco estrella', expected)):
            raise StopSource(f'Product identity mismatch for {pid}; no stock conclusion')
        feature = data.get(f'CofrDeliveryFeature:Media:es:{pid}', {})
        delivery = feature.get('delivery') or {}
        status = delivery.get('deliveryStatus')
        # Only the two statuses observed in the real response are classified.
        # New status values require review; never infer InStock from an enum name.
        kind = {'AVAILABLE_OUTSIDE_REASONABLE_TIME_FRAME': 'unavailable', 'NOT_AVAILABLE': 'unavailable'}.get(status, 'unknown')
        if feature.get('isProductOfTypeMarketplace') is not False:
            kind = 'unknown'
        dates = delivery.get('fulfillmentTime') or {}
        expiry = dates.get('validUntil')
        if expiry and dt.datetime.fromisoformat(expiry.replace('Z', '+00:00')).timestamp() < time.time():
            kind = 'unknown'
        results.append({'key': f'mediamarkt:{pid}:online_stock', 'retailer': 'MediaMarkt Spain',
                        'capacity_gb': product['capacity_gb'], 'channel': 'online_stock', 'status': kind,
                        'raw_status': status,
                        'scope': 'Spain-wide page; Barcelona postcode eligibility unverified',
                        'url': 'https://www.mediamarkt.es' + identity['url']})
        results.append({'key': f'mediamarkt:{pid}:pickup', 'retailer': 'MediaMarkt Spain',
                        'capacity_gb': product['capacity_gb'], 'channel': 'pickup', 'status': 'unknown',
                        'scope': 'Barcelona store inventory endpoint not verified',
                        'url': 'https://www.mediamarkt.es' + identity['url']})
    return results

def apple_observations(payload, source, postal_code):
    """Read only exact configured Spain parts and explicitly selected Barcelona stores."""
    if str(payload.get('head', {}).get('status')) != '200':
        raise StopSource('Apple returned a non-success payload; no stock conclusion')
    body = payload.get('body') or {}
    if body.get('location') != postal_code or not isinstance(body.get('stores'), list):
        raise StopSource('Apple location/store schema mismatch; no stock conclusion')
    stores = {store.get('storeNumber'): store for store in body['stores'] if isinstance(store, dict)}
    results = []
    for store_id, store_name in source['stores'].items():
        store = stores.get(store_id)
        if not store or store.get('country') != 'ES' or store.get('city') != 'Barcelona':
            raise StopSource(f'Apple expected Barcelona store {store_id} missing; no stock conclusion')
        if store.get('storeName') != store_name:
            raise StopSource(f'Apple store identity changed for {store_id}; manual review required')
        for product in source['products']:
            part = product['part']
            entry = (store.get('partsAvailability') or {}).get(part, {})
            if entry.get('partNumber') != part:
                raise StopSource(f'Apple part {part} missing or mismatched; no stock conclusion')
            regular = (entry.get('messageTypes') or {}).get('regular') or {}
            title = ' '.join(regular.get('storePickupProductTitle', '').lower().split())
            if not all(text in title for text in ('iphone duo', f"{product['capacity_gb']} gb", 'blanco estelar')):
                raise StopSource(f'Apple product identity mismatch for {part}; no stock conclusion')
            raw = entry.get('pickupDisplay')
            quote = ' '.join(str(entry.get('pickupSearchQuote') or '').split())
            status = {'available': 'available', 'unavailable': 'unavailable'}.get(raw, 'unknown')
            if status == 'available' and (entry.get('storePickEligible') is not True or not quote or
                                         re.search(r'no disponible|unavailable', quote, re.I)):
                status = 'unknown'
            results.append({'key': f'apple:{part}:pickup:{store_id}', 'retailer': 'Apple Spain',
                'capacity_gb': product['capacity_gb'], 'channel': 'pickup', 'status': status,
                'raw_status': raw, 'quote': quote, 'store_id': store_id, 'store_name': store_name,
                'scope': f'Apple {store_name}, Barcelona ({store_id})', 'url': product['url']})
    return results

def checked_fetch(url, interval):
    """One robots check, then one public data request, with no protection bypass."""
    parts = urllib.parse.urlsplit(url)
    rules = fetch(f'https://{parts.netloc}/robots.txt')
    if '<html' in rules.lower() or 'user-agent:' not in rules.lower():
        raise StopSource('robots.txt was not a verifiable robots policy', permanent=True)
    allowed, delay = robots_rules(rules, parts.path + ('?' + parts.query if parts.query else ''))
    if not allowed:
        raise StopSource('robots.txt disallows this path', permanent=True)
    if delay > interval:
        raise StopSource('Crawl-delay exceeds configured interval', delay)
    time.sleep(max(10, delay) + random.uniform(0, 3))
    return fetch(url)


def fingerprint(item):
    meaningful = {k: item.get(k) for k in ('status', 'scope')}
    return hashlib.sha256(json.dumps(meaningful, sort_keys=True).encode()).hexdigest()

def should_alert(item, previous):
    eligible = item['status'] == 'available'
    return eligible and previous.get('last_alert') != fingerprint(item)

def record_observation(item, previous):
    previous['observed'] = item
    # Unknown/error does not re-arm an alert. A confirmed stock loss does.
    if item['status'] == 'unavailable':
        previous.pop('last_alert', None)

def telegram(method, payload, token):
    body = json.dumps(payload).encode()
    req = urllib.request.Request(f'https://api.telegram.org/bot{token}/{method}', data=body,
                                 headers={'Content-Type': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=25) as response:
            data = json.load(response)
        if not data.get('ok'):
            raise RuntimeError('Telegram rejected the request')
        return data['result']
    except Exception:
        # Never print the request URL, response, token or exception chain.
        raise RuntimeError('Telegram delivery failed; check credentials/network in private') from None

def save(path, state):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2, ensure_ascii=False) + '\n')
    temp.replace(path)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', default='config.json')
    parser.add_argument('--state', default='state.json')
    parser.add_argument('--dry-run', action='store_true', help='No Telegram or state writes; still performs retailer requests')
    parser.add_argument('--fixture', help='Offline MediaMarkt JSON, no network or Telegram')
    parser.add_argument('--apple-fixture', help='Offline Apple pickup JSON, no network or Telegram')
    parser.add_argument('--test-telegram', action='store_true')
    parser.add_argument('--reset-source', choices=['apple', 'mediamarkt', 'fnac'])
    args = parser.parse_args()
    token, chat = os.getenv('TELEGRAM_BOT_TOKEN'), os.getenv('TELEGRAM_CHAT_ID')
    if args.test_telegram:
        if not token or not chat: raise SystemExit('Set TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID')
        telegram('sendMessage', {'chat_id': chat, 'text': 'StockWatch setup test. No stock claim.'}, token)
        print('Telegram test delivered'); return 0
    config = json.loads(Path(args.config).read_text())
    state_path = Path(args.state)
    state = json.loads(state_path.read_text()) if state_path.exists() else {'version': 1, 'sources': {}, 'items': {}}
    if state.get('version') != 1: raise SystemExit('Unsupported state format; refusing to reset deduplication')
    for previous in state['items'].values():
        item = previous.get('observed', {})
        legacy = {key: item.get(key) for key in ('status', 'earliest', 'latest', 'scope', 'quote')}
        if previous.get('last_alert') == hashlib.sha256(json.dumps(legacy, sort_keys=True).encode()).hexdigest():
            previous['last_alert'] = fingerprint(item)
    state['items'] = {key: value for key, value in state['items'].items()
                      if value.get('observed', {}).get('channel') != 'shipping'}
    if args.reset_source:
        state['sources'].pop(args.reset_source, None)
        if not args.dry_run: save(state_path, state)
        print('Source circuit breaker reset; config enabled flag still applies'); return 0
    offline = bool(args.fixture or args.apple_fixture)
    if not args.dry_run and not offline and (not token or not chat):
        raise SystemExit('Telegram secrets missing; use --dry-run for verification')
    observations, failures = [], []
    now = time.time()
    for name, source in config['sources'].items():
        slot = state['sources'].setdefault(name, {})
        if not source['enabled']:
            failures.append(f"{name}: disabled — {source['reason']}"); continue
        if not offline and (slot.get('paused') or slot.get('next_check', 0) > now):
            failures.append(f'{name}: paused/cooling down; see state branch'); continue
        try:
            if name == 'apple':
                if offline:
                    if not args.apple_fixture:
                        failures.append('apple: skipped in MediaMarkt-only offline fixture run'); continue
                    payload = json.loads(Path(args.apple_fixture).read_text())
                else:
                    params = {'pl': 'true', 'location': config['postal_code']}
                    params.update({f'parts.{i}': product['part'] for i, product in enumerate(source['products'])})
                    url = source['url'] + '?' + urllib.parse.urlencode(params)
                    payload = json.loads(checked_fetch(url, config['interval_seconds']))
                observations.extend(apple_observations(payload, source, config['postal_code']))
            elif name == 'mediamarkt':
                if offline:
                    if not args.fixture:
                        failures.append('mediamarkt: skipped in Apple-only offline fixture run'); continue
                    data = json.loads(Path(args.fixture).read_text())
                else:
                    data = extract_mm(checked_fetch(source['url'], config['interval_seconds']))
                observations.extend(mm_observations(data, source['products']))
            else:
                raise StopSource('No verified working inventory adapter', permanent=True)
            slot.update(failures=0, next_check=now + config['interval_seconds'])
        except (StopSource, ValueError, KeyError, TypeError, AttributeError) as exc:
            if isinstance(exc, StopSource):
                reason, pause, delay = exc.reason, exc.permanent, exc.delay
            else: reason, pause, delay = 'Unexpected response schema; manual review required', True, 3600
            count = slot.get('failures', 0) + 1
            slot.update(failures=count, paused=pause, reason=reason,
                        next_check=now + max(delay, min(86400, 3600 * 2 ** min(count - 1, 5))))
            failures.append(f'{name}: {reason}')
    delivery_failure = False
    for item in observations:
        previous = state['items'].setdefault(item['key'], {})
        record_observation(item, previous)
        print(json.dumps(item, ensure_ascii=False))
        if should_alert(item, previous):
            if args.dry_run or offline: print('Would notify (offline/dry run)'); continue
            label = 'In stock'
            message = (f"{label}\n{item['retailer']} • White {item['capacity_gb']}GB • {item['channel']}\n"
                       f"{item['scope']}\n"
                       f"Checked: {dt.datetime.now(dt.timezone.utc).isoformat()}\n{item['url']}\nConfirm at checkout.")
            try:
                telegram('sendMessage', {'chat_id': chat, 'text': message, 'link_preview_options': {'is_disabled': True}}, token)
                previous['last_alert'] = fingerprint(item)
                save(state_path, state)
            except RuntimeError as exc:
                print(str(exc)); delivery_failure = True
    for failure in failures: print(failure)
    state['last_run_utc'] = dt.datetime.now(dt.timezone.utc).isoformat()
    if not args.dry_run and not offline: save(state_path, state)
    summary = ['# StockWatch coverage', '', 'Stock alerts are only as complete as the coverage below.', '']
    summary += [f'- {x}' for x in failures]
    summary += [f"- {x['key']}: {x['status']} ({x['scope']}; raw status: {x.get('raw_status', 'unverified')})" for x in observations]
    if os.getenv('GITHUB_STEP_SUMMARY'):
        with open(os.environ['GITHUB_STEP_SUMMARY'], 'a') as file: file.write('\n'.join(summary) + '\n')
    if not offline and not args.dry_run:
        status = 'degraded' if failures or any(x['status'] == 'unknown' for x in observations) else 'healthy'
        health_issues = [(name, src['reason'] if not src['enabled'] else
            state['sources'].get(name, {}).get('reason') if state['sources'].get(name, {}).get('failures', 0) else None)
            for name, src in config['sources'].items()]
        health_unknown = [(key, value['observed'].get('raw_status')) for key, value in state['items'].items()
                          if value.get('observed', {}).get('status') == 'unknown']
        health_key = hashlib.sha256(json.dumps({'issues': health_issues,
            'unknown': sorted(health_unknown)}, sort_keys=True).encode()).hexdigest()
        if health_key != state.get('last_health'):
            try:
                telegram('sendMessage', {'chat_id': chat, 'text': '\n'.join(summary)[:3900]}, token)
                state['last_health'] = health_key
                save(state_path, state)
            except RuntimeError as exc:
                print(str(exc)); delivery_failure = True
    active_slots = [state['sources'].get(name, {}) for name, source in config['sources'].items() if source['enabled']]
    no_result_failure = not observations and not offline and (not active_slots or any(
        slot.get('paused') or slot.get('failures', 0) for slot in active_slots))
    return 1 if delivery_failure or no_result_failure else 0

if __name__ == '__main__':
    try: raise SystemExit(main())
    except RuntimeError as exc: raise SystemExit(str(exc)) from None
