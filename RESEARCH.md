# Additional stock research — 24 October 2026

## Amazon Spain

The supplied link's path and referral metadata refer to different variants. Product titles, selected sizes and selected ASIN inputs were checked in an ordinary browser and in direct responses using the monitor's truthful StockWatch user agent:

| Variant | Canonical listing | Selected ASIN |
|---|---|---|
| White 256GB | https://www.amazon.es/dp/B0HJ9QGJJJ | B0HJ9QGJJJ |
| White 512GB | https://www.amazon.es/dp/B0HJB52JYX | B0HJB52JYX |

Both pages returned HTTP 200 locally and explicitly reported temporarily out of stock while still offering purchase buttons. Therefore cart buttons are not stock evidence. The selected seller was Amazon, merchant A1AT7YVPFBWXBL. The adapter validates ASIN, title, colour, capacity and merchant. Only explicit current-stock wording can trigger an alert; missing, ambiguous or unfamiliar wording stays unknown. Positive-stock tests are synthetic; no live positive stock result has been observed.

The normal public `/dp/ASIN` page is the only stock input. The current `robots.txt` generic policy permits these paths, but prohibits special availability/twister endpoints and many offer/account routes. Those are not requested. The user-owned monitor identifies itself as StockWatch; it does not impersonate an allowed bot. Each product check is preceded by a fresh robots check and a minimum ten-second gap. HTTP blocks/challenges pause Amazon. No Amazon login, private API, proxy or cookie reuse is needed.

Scope: selected Amazon retail offer only, not all Marketplace sellers. Availability is the Spain product page's stock statement; delivery eligibility for an exact Barcelona address is not established. No checkout or purchase is performed. GitHub-hosted access verification is pending.

## MediaMarkt pickup

The normal product page's **Seleccionar tienda** drawer works in the research browser. Searching Barcelona returns named stores and product-specific pickup wording. For white 256GB, active Barcelona stores including La Maquinista (955), Diagonal Mar (233), Francesc Macià (1450), Plaça Catalunya (1766) and Ronda Sant Antoni (1997) showed future collection on 16 November, not immediate store stock. Triangle Tech Village (6296) was marked permanently closed. These are a dated observation of one capacity, not a claim about the other capacity or future availability.

The page's own referenced JavaScript contains `GetClosestStoresByZipCodeOrCityWithFoundLocation`, `closestStoresWithFoundLocation` and product-specific `cofrProductAggregate` / `cofrPickupFeature` fields, using the observed `/api/v1/graphql` path. One read-only query using the actual query structure and the truthful monitor user agent returned HTTP 403. No response schema or working direct inventory request was validated. We stopped rather than changing fingerprints, replaying cookies or attempting protection bypasses. A query's presence in JavaScript does not establish that our automated requests are permitted or supported.

A separate manual-only GitHub workflow tests an ordinary fresh Chromium browser opening the public product page and operating its store selector. It never directly calls the inventory endpoint and stops on HTTP blocks or visible challenges. Its result will determine whether a browser adapter is realistic on GitHub. The scheduled checker continues to label pickup unknown unless and until a real inventory response and adapter are verified.

MediaMarkt's [official collection explanation](https://www.mediamarkt.es/es/service/recogidas-y-env%C3%ADos) distinguishes rapid collection from other fulfilment options. An order that will be transferred to a store later is not counted as immediate store stock here.

## Fnac and practical alternatives

Direct product access returned HTTP 403, and the normal research browser encountered a DataDome CAPTCHA. No consumer inventory endpoint or successful automated stock response has been verified. Fnac remains disabled. Marketplace seller APIs are not evidence of a public consumer stock API.

The [official Fnac app](https://www.fnac.es/app-fnac) explicitly supports checking product availability in a favourite store. This is a verified manual alternative; the page does not establish an automatic restock alert, public API or Telegram integration.

For websites that load normally on an existing computer, a local browser monitor is another candidate. [Distill local monitors](https://distill.io/docs/web-monitor/cloud-local-monitors/) require the computer/browser to remain running. Its [free plan](https://distill.io/pricing/) has limited cloud frequency and no free webhooks; do not assume it supplies free ten-minute cloud checks or Telegram alerts. Store drawers that require repeated actions may exceed the free plan's capabilities; a saved store preference must actually persist and expose the chosen stock field before using a basic page monitor.

For automatic store-selection steps plus Telegram, [self-hosted changedetection.io](https://github.com/dgtlmoon/changedetection.io) supports a browser fetcher, browser steps, filters and Apprise notifications including Telegram. Software can be free on an already-running computer/NAS; hosting, power and setup are still needed. It is a candidate, not a tested Fnac/MM solution, and does not remove CAPTCHAs or access restrictions. A small local custom browser checker could reuse this project's Telegram and deduplication logic under the same conditions. Keep checks at roughly ten minutes, monitor only the product/store stock field, and pause if the site challenges access.
