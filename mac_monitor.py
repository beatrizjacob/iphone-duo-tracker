#!/usr/bin/env python3
"""Apple Spain Mac Studio monitor: only explicit offer stock counts."""
import argparse, datetime, json, os, re, time, urllib.parse, urllib.request
from html import unescape
from pathlib import Path
from zoneinfo import ZoneInfo
from checker import robots_rules, StopSource
URL = "https://www.apple.com/es/shop/buy-mac/mac-studio/chip-m5-max-cpu-de-18-n%C3%BAcleos-gpu-de-40-n%C3%BAcleos-128-gb-de-memoria-1tb-de-capacidad"
STATE = Path("state.json")

def classify(html, today=None):
    """Only exact product-linked, explicit delivery dates qualify; no inferred stock."""
    today = today or datetime.datetime.now(ZoneInfo("Europe/Madrid")).date()
    scripts = re.findall(
        r'<script[^>]*type=["\']application/ld\\+json["\'][^>]*>(.*?)</script>',
        html, re.I | re.S)
    for script in scripts:
        try:
            root = json.loads(unescape(script))
        except (ValueError, TypeError):
            continue
        def walk(obj):
            if isinstance(obj, list):
                for item in obj: yield from walk(item)
            elif isinstance(obj, dict):
                yield obj
                for value in obj.values(): yield from walk(value)
        for obj in walk(root):
            kind = str(obj.get("@type", "")).lower()
            name = " ".join(str(obj.get("name", "")).lower().split())
            if ("product" not in kind or "mac studio" not in name
                    or "m5 max" not in name or not re.search(r"128\\s*gb", name)
                    or not re.search(r"1\\s*tb", name)):
                continue
            # The ship date must belong to this exact product's offer.
            offers = obj.get("offers") or []
            if isinstance(offers, dict): offers = [offers]
            for offer in offers:
                if not isinstance(offer, dict): continue
                availability = str(offer.get("availability", "")).rsplit("/", 1)[-1].lower()
                if availability not in ("instock", "preorder", "backorder"):
                    continue
                # Only explicit final delivery dates are usable. shipDate is NOT delivery.
                date_string = offer.get("deliveryDate") or offer.get("estimatedDeliveryDate")
                if not isinstance(date_string, str): continue
                try:
                    delivered = datetime.date.fromisoformat(date_string[:10])
                except ValueError:
                    continue
                days = (delivered - today).days
                if 0 <= days <= 14:
                    return "available", f"Apple explicitly estimates delivery {delivered.isoformat()} ({days} days)"
                if days > 14:
                    return "unavailable", f"Apple explicitly estimates delivery {delivered.isoformat()} ({days} days)"
    return "unknown", "Apple has not exposed an exact-config, explicit delivery date"

def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "StockWatch/1.0 (personal stock checking)"})
    with urllib.request.urlopen(req, timeout=25) as r:
        if urllib.parse.urlsplit(r.geturl()).hostname != "www.apple.com":
            raise ValueError("Unexpected host")
        data = r.read(3000001)
        if len(data) > 3000000: raise ValueError("Response too large")
        return data.decode("utf-8")

def send(message):
    token, chat = os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not token or not chat: raise RuntimeError("Telegram secrets unavailable")
    body = urllib.parse.urlencode({"chat_id":chat, "text":message,
                                   "disable_web_page_preview":"true"}).encode()
    try:
        with urllib.request.urlopen(urllib.request.Request(
            "https://api.telegram.org/bot" + token + "/sendMessage", data=body), timeout=25) as r:
            if not json.load(r).get("ok"): raise ValueError()
    except Exception: raise RuntimeError("Telegram delivery failed; secrets suppressed") from None

def main():
    p = argparse.ArgumentParser()
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--test-telegram", action="store_true")
    args = p.parse_args()
    if args.test_telegram:
        send("Mac Studio Apple-only monitor test. No stock claim.")
        return
    state = json.loads(STATE.read_text()) if STATE.exists() else {"version":1}
    prev = state.get("mac_studio_128gb", {})
    try:
        robots = fetch("https://www.apple.com/robots.txt")
        if "user-agent:" not in robots.lower(): raise ValueError("Invalid robots policy")
        allowed, delay = robots_rules(robots, urllib.parse.urlsplit(URL).path)
        if not allowed or delay > 600: raise ValueError("Robots disallows scheduled checks")
        time.sleep(max(10, delay))
        status, reason = classify(fetch(URL))
    except Exception:
        status, reason = "unknown", "Apple response or access could not be verified"
    print(json.dumps({"product":"Mac Studio M5 Max 128 GB 1 TB", "status":status, "reason":reason}))
    if args.dry_run: return
    if status == "available" and prev.get("status") != "available":
        now = datetime.datetime.now(ZoneInfo("Europe/Madrid")).strftime("%d %b %H:%M")
        send("Mac Studio M5 Max / 128 GB / 1 TB: Apple Spain estimates delivery WITHIN 14 DAYS. Confirm at checkout.\n" + URL + "\nBarcelona " + now)
    elif not prev.get("initialized"):
        send("Mac Studio Apple-only monitoring enabled (M5 Max, 128 GB, 1 TB). 14-day delivery criterion. Current status: " + status + ". " + reason + ".\n" + URL)
    elif status == "unknown" and prev.get("status") != "unknown":
        send("Mac Studio check cannot confirm availability. No stock claim. " + reason)
    state["mac_studio_128gb"] = {"initialized":True, "status":status, "reason":reason}
    STATE.write_text(json.dumps(state, indent=2) + "\n")

if __name__ == "__main__":
    main()
