"""One-shot MediaMarkt browser feasibility test. No alerts, credentials or state.

Uses ordinary Playwright Chromium, without stealth, proxy, custom user agent,
saved cookies, challenge interaction or direct inventory API calls.
"""
import asyncio
import json
from playwright.async_api import async_playwright
import checker

URL = ('https://www.mediamarkt.es/es/product/_apple-iphone-duo-blanco-estrella-256-gb-'
       '76-oled-super-retina-xdr-plegable-5g-chip-a20-pro-siri-ai-ios-1674375.html')


async def main():
    # Inspect the site's current policy before opening a normal public page.
    rules = checker.fetch('https://www.mediamarkt.es/robots.txt')
    if 'user-agent:' not in rules.lower() or '<html' in rules.lower():
        raise SystemExit('No verifiable robots policy; stopping browser research')
    allowed, delay = checker.robots_rules(rules, URL.split('.es', 1)[1])
    if not allowed:
        raise SystemExit('Product page disallowed; stopping browser research')
    await asyncio.sleep(max(10, delay))
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page(locale='es-ES')
        page.set_default_timeout(15000)
        inventories, blocks = [], []

        async def inspect(response):
            if '/api/v1/graphql' not in response.url:
                return
            if response.status in (401, 403, 429, 451, 541):
                blocks.append(response.status)
                return
            try:
                data = await response.json()
                for item in data if isinstance(data, list) else [data]:
                    result = (item.get('data') or {}).get('closestStoresWithFoundLocation')
                    if result:
                        inventories.append(result)
            except (ValueError, AttributeError):
                pass

        page.on('response', inspect)
        try:
            response = await page.goto(URL, wait_until='domcontentloaded', timeout=45000)
            if response.status in (401, 403, 429, 451, 541):
                print(json.dumps({'result':'blocked', 'http_status':response.status}))
                return
            title = (await page.title()).lower()
            body = (await page.locator('body').inner_text()).lower()
            if any(term in title + body[:1200] for term in
                   ('captcha', 'verify you are human', 'access denied', 'just a moment')):
                print(json.dumps({'result':'challenge; stopping'}))
                return
            deny = page.get_by_role('button', name='Denegar', exact=True)
            if await deny.count():
                await deny.click()
            await page.get_by_role('button', name='Seleccionar tienda', exact=True).click()
            search = page.get_by_role('searchbox', name='Buscar por código postal o ciudad')
            await search.fill('Barcelona')
            await search.press('Enter')
            # Bounded wait for the normal UI's own stock request; no API replay.
            for _ in range(20):
                if inventories or blocks:
                    break
                await asyncio.sleep(1)
            if blocks:
                print(json.dumps({'result':'blocked; stopping', 'http_status':blocks}))
            elif inventories:
                print(json.dumps({'result':'store response observed', 'inventory':inventories},ensure_ascii=False))
            else:
                print(json.dumps({'result':'no verified inventory response',
                    'visible_selector':(await page.locator('body').inner_text())[-18000:]}, ensure_ascii=False))
        except Exception as exc:
            print(json.dumps({'result':'browser test incomplete', 'error_type':type(exc).__name__}))
        finally:
            await browser.close()


if __name__ == '__main__':
    asyncio.run(main())
