# Verification record — updated 24 October 2026

**Current scope: stock only.** Historical shipping research below is retained as evidence. Shipping estimates are excluded from the current checker, alerts and coverage reports. Delayed-order offers do not count as in stock.

## Result of follow-up research

**Apple Barcelona pickup is now verified and implemented.** This supersedes the initial claim that no Barcelona pickup source had been established. The old combined fulfillment endpoint failed; a distinct pickup endpoint returned valid product-specific JSON with ordinary Python requests, without cookies, authentication, proxies or browser fingerprint impersonation.

Discovery sources: the authors of [apple-pickup-monitor](https://github.com/bilune/apple-pickup-monitor) and [apple-store](https://github.com/woke/apple-store) describe the separate pickup interface. Their source code is primary evidence of their implementations, not a guarantee of Apple’s ongoing API support. We did not install or run their software or adopt their protection-bypass suggestions.

## Exact successful Apple request

```text
GET https://www.apple.com/es/shop/retail/pickup-message?pl=true&location=08002&parts.0=MK2D4QL%2FA&parts.1=MK2F4QL%2FA
```

First recorded success: **24 October 2026, 19:38 CEST**, HTTP 200, JSON. A second live test through the delivered checker, including a fresh robots check, also succeeded during this session. User agent identified StockWatch. The response’s body.location was 08002, head.status was 200, and the two returned stores matched Barcelona, Spain.

| Store | Verified store ID | White 256GB | White 512GB |
|---|---|---|---|
| Passeig de Gràcia | R368 | pickupDisplay = unavailable | pickupDisplay = unavailable |
| La Maquinista | R406 | pickupDisplay = unavailable | pickupDisplay = unavailable |

These are historical observations, not current stock promises. Each entry’s partNumber and localized product title matched the requested capacity and white finish. The fixture `tests/fixtures/apple-pickup.json` preserves the actual response fields used for decisions; it contains no fabricated availability.

The `available` enum interpretation is supported by the [client author’s parser](https://github.com/woke/apple-store/blob/main/src/apple_store/availability.py). Our parser additionally requires eligible pickup and rejects a conflicting unavailable quote. Positive-restock behavior is tested with synthetic fixture mutations, clearly labeled. No live in-stock result was observed.

[Apple robots.txt](https://www.apple.com/robots.txt) was readable; its general policy did not disallow this pickup path. That is not a documented API contract or a guarantee that a cloud runner will be accepted.

## Apple shipping

The earlier direct validation request used the combined fulfillment path advertised in Apple’s product HTML:

```text
/es/shop/fulfillment-messages?fae=true&pl=true&parts.0=MK2D4QL%2FA&parts.1=MK2F4QL%2FA&location=08002
```

It returned HTTP 541. That establishes rejection of that exact request, not rejection of every possible shipping query. Follow-up source research found clients use postalCode and additional shipping parameters; their working delivery fallbacks involve challenge cookies/fingerprint transport, which were excluded from this project. We then made one plain request using the corrected shipping parameters from that source (postalCode=08002, little=false, mts.0=regular, mts.1=sticky, mts.2=compact, fts=true and geoLocated=false, with the verified 256GB part). It also returned HTTP 541 at 19:43 CEST. No authenticated or disguised shipping request was attempted.

In the normal [256GB product browser flow](https://www.apple.com/es/shop/buy-iphone/iphone-duo/pantalla-de-7%2C6%E2%80%B3-256gb-blanco-estelar), we entered 08002 using Apple’s delivery dialog. It displayed a delayed January 25 delivery estimate. This is a verified browser observation for 256GB only, not a confirmed immediate-stock offer and not an automated shipping adapter. [Apple’s official help](https://www.apple.com/es/shop/help/shipping_delivery) describes the postcode/store availability flow. The captured screenshot is supplied beside the package as `apple-delivery-08002.png`.

A local normal-browser monitor could potentially read these visible estimates, but that automation has not been built or validated here. The stock-only checker omits Apple shipping entirely.

## GitHub Actions deployment verified

The private repository [beatrizjacob/iphone-duo-tracker](https://github.com/beatrizjacob/iphone-duo-tracker) was created on 24 October 2026. [Access-verification run 40119754890](https://github.com/beatrizjacob/iphone-duo-tracker/actions/runs/40119754890) completed successfully at 20:14 CEST on a GitHub-hosted Ubuntu runner.

Its logs show all four Apple store/capacity combinations returned unavailable, with exact configured store IDs and part numbers. MediaMarkt's robots and category fetch also succeeded on that runner and returned the observed no-stock signals; pickup remains unknown. All 36 offline tests passed in that initial access run as well. Fnac remained disabled.

This verifies cloud access for that run, without cookies, proxies, challenge solving or fingerprint impersonation. It does not guarantee future access. The checker pauses if a retailer later blocks it. Telegram credentials and complete notification/state persistence are separate deployment checks.

## Fnac follow-up

The [256GB Fnac product page](https://www.fnac.es/Apple-iPhone-Duo-7-6-256-GB-Blanco-estelar-Telefono-movil/a13483448) displayed a **DataDome CAPTCHA** when opened through the normal browser. We stopped without interacting with the challenge. This corroborates the original direct HTTP 403 but still does not prove that every authorized Fnac integration is impossible.

[Fnac Spain’s official help](https://www.fnac.es/ayuda?question=como-comprobar-online-si-un-producto-esta-disponible-en-la-tienda-139275) describes customer-facing store selection. [Fnac Darty’s API documentation overview](https://marketplace.fnacdarty.com/s/ressources/les-liens-de-connexion-a-nos-outils) describes marketplace seller APIs for managing the seller’s own offers/orders; it does not establish a public consumer endpoint for Fnac-owned Barcelona inventory. No free, permitted automated Fnac Spain stock source was validated. Fnac remains disabled.

## Confirmed product listings

| Retailer | Capacity | Verified listing | Identity source |
|---|---|---|---|
| Apple | 256GB white | [Apple configuration](https://www.apple.com/es/shop/buy-iphone/iphone-duo/pantalla-de-7%2C6%E2%80%B3-256gb-blanco-estelar) | Apple product HTML analytics: MK2D4QL/A, Star White |
| Apple | 512GB white | [Apple configuration](https://www.apple.com/es/shop/buy-iphone/iphone-duo/pantalla-de-7%2C6%E2%80%B3-512gb-blanco-estelar) | Apple product HTML analytics: MK2F4QL/A, Star White |
| MediaMarkt | 256GB white | [MediaMarkt 1674375](https://www.mediamarkt.es/es/product/_apple-iphone-duo-blanco-estrella-256-gb-76-oled-super-retina-xdr-plegable-5g-chip-a20-pro-siri-ai-ios-1674375.html) | Live category HTML Product node with matching title, ID and product URL |
| MediaMarkt | 512GB white | [MediaMarkt 1674377](https://www.mediamarkt.es/es/product/_apple-iphone-duo-blanco-estrella-512-gb-76-oled-super-retina-xdr-plegable-5g-chip-a20-pro-siri-ai-ios-1674377.html) | Same live HTML, matching product node |
| Fnac | 256GB white | [Fnac a13483448](https://www.fnac.es/Apple-iPhone-Duo-7-6-256-GB-Blanco-estelar-Telefono-movil/a13483448) | Retailer-page reader: title, capacity and Star White selection |
| Fnac | 512GB white | [Fnac a13483450](https://www.fnac.es/Apple-iPhone-Duo-7-6-512-GB-Blanco-estelar-Telefono-movil/a13483450) | Retailer-page reader: title and capacity |

Retailers use “blanco estelar”, “Blanco estrella”, and “Star White” for the requested white variant. Product codes are taken from the retailer responses, not guessed from other capacities.

## MediaMarkt evidence retained from initial investigation

Direct category HTML returned HTTP 200 and contained product-specific CofrDeliveryFeature and CofrPickupFeature records in embedded apolloState.

- 1674375: AVAILABLE_OUTSIDE_REASONABLE_TIME_FRAME, with a 13 November estimate; classified as not in stock by the current stock-only checker.
- 1674377: NOT_AVAILABLE; classified as shipping unavailable.
- Pickup: storeId null, NO_STORE_SELECTED; no Barcelona stock conclusion.

Direct robots access returned 403 even though the page reader could display its policy. Fresh readable robots and data responses are mandatory in the checker. No private GraphQL endpoint was guessed or used.

## Remaining validation boundaries

- Apple pickup: verified both locally and on a GitHub-hosted runner; future uptime remains unproven.
- Apple shipping: normal 256GB browser estimate observed; scheduled shipping not implemented.
- Fnac: direct and browser access blocked; no automated adapter.
- MediaMarkt: shipping signals conditional on access; local pickup unverified.
- Telegram secrets were entered privately by the user; local setup delivery was confirmed by the user, and GitHub delivery was accepted in the full deployment run.
- Private GitHub deployment created; live notification setup is tracked separately.
- 40 offline tests now cover parsing, wrong identities, missing stores/parts, synthetic restock alerts, delivery failures, deduplication and durable state.

## Full notification deployment

[Run 40120111752](https://github.com/beatrizjacob/iphone-duo-tracker/actions/runs/40120111752) passed at 20:19 CEST on 24 October 2026. Both secret names were present (values were not read); Telegram accepted the initial coverage report; the stock-state branch persisted all four Apple results and its successful report marker. Apple and MediaMarkt had zero source failures. The repository is private and the hourly workflow is active.

## Ten-minute public deployment

The user approved changing this repository to public so the standard GitHub-hosted runner schedule can remain free. The prepared schedule runs at minutes 2, 12, 22, 32, 42 and 52 UTC, with a five-minute minimum polling interval to tolerate scheduling jitter. Successful hourly deadlines migrate automatically; all error cooldowns and paused-source controls remain intact. All 40 local tests passed. Historical references to private/hourly deployment above describe the earlier setup.
