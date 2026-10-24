# iPhone Duo stock tracker — Apple pickup verified

**Updated after further research on 24 October 2026. Apple pickup now works in direct, unauthenticated tests from this computer.** The earlier disabled-Apple conclusion was incomplete: a separate pickup endpoint works even though the combined fulfillment endpoint returned HTTP 541. The tracker now enables this verified pickup adapter. This is still incomplete three-retailer coverage, and GitHub-hosted access must be tested separately.

## Stock-only scope

The tracker checks whether the requested white 256GB or 512GB variant is available. Shipping dates, delivery estimates and delayed-order offers are excluded from alerts and coverage reports.

| Retailer | Automated stock coverage |
|---|---|
| Apple Spain | Enabled: Passeig de Gràcia (R368) and La Maquinista (R406), both capacities |
| MediaMarkt Spain | Conditional page access; delayed orders do not count as stock. Local pickup remains unverified. |
| Fnac Spain | Disabled: direct HTTP 403 and browser CAPTCHA; no automated stock source verified |

Apple’s separate pickup endpoint returned HTTP 200 in two local tests. The response matched both requested white variants and the two Barcelona stores. The tracker alerts per store and capacity, suppressing unchanged results. Missing or unknown data is not interpreted as out of stock.

**GitHub Actions access passed its first test** in [run 40119754890](https://github.com/beatrizjacob/iphone-duo-tracker/actions/runs/40119754890). Both Apple and MediaMarkt returned usable responses. Future requests may still be blocked. A blocked source pauses and reports its failure. No proxies, fingerprint spoofing, cookie replay or challenge solving are used.

The stock-only configuration does not need Apple’s shipping endpoint. MediaMarkt’s observed delayed-order signal is treated as not in stock, and no delivery dates are included. See [VERIFICATION.md](VERIFICATION.md) for historical research evidence.

## Deployed repository

The repository is [beatrizjacob/iphone-duo-tracker](https://github.com/beatrizjacob/iphone-duo-tracker). You approved making it public to keep the ten-minute schedule free on standard GitHub-hosted runners. Code, stock preferences, workflow logs and stock-state history are public; the Telegram bot token and chat ID stay in GitHub Actions secrets. The workflow is configured at minutes 2, 12, 22, 32, 42 and 52 UTC. This project uses no larger runners or paid stock service and does not alter account billing settings.

For private local setup, run `python3 setup_github.py --repo beatrizjacob/iphone-duo-tracker`. The helper asks for the bot token with hidden input, lets you select your own chat, saves both GitHub Actions secrets through the existing GitHub login, and sends a setup message. It does not print the token or store it in a local file. The local `.setup-complete.json` receipt contains only the repository name and completion flags and is ignored by Git.

A manual workflow run with `verify_access=true` tests retailers without secrets or state changes. A normal workflow run tests the complete setup after secrets have been saved.

## 1. Create your Telegram bot

1. Open the official [@BotFather](https://t.me/BotFather) in Telegram. Send `/newbot` and follow the name/username prompts.
2. Keep the returned bot token private. Do not paste it into a repository, issue, screenshot, or this chat.
3. Open your new bot's chat and send `/start`. A bot cannot initiate a private chat until you contact it.
4. In this extracted project folder run:

   ```sh
   python3 telegram_setup.py
   ```

   Paste the token into the hidden prompt. The helper calls Telegram's documented `getUpdates` method and prints only private chat IDs. Choose **your own** ID. For a fresh bot with only your chat, there should be one.

If nothing appears, send a new message and retry. Use a dedicated bot: `getUpdates` does not work while a webhook is active, and another polling client may consume updates. Do not disable another bot's integrations to fix this.

Official references: [Telegram bot creation tutorial](https://core.telegram.org/bots/tutorial), [Bot API](https://core.telegram.org/bots/api#getupdates), [sendMessage](https://core.telegram.org/bots/api#sendmessage).

## 2. Put the files in a GitHub repository

Create a new repository named `iphone-duo-tracker`. For zero Actions runner charges, choose a **public** repository and standard GitHub-hosted runners. Code, product preferences, stock-state history and logs will then be public. The bot token and chat ID belong only in Actions secrets.

From this extracted folder, if you use Git locally:

```sh
git init -b main
git add .
git commit -m "Add conservative iPhone stock monitor"
git remote add origin https://github.com/YOUR_USERNAME/iphone-duo-tracker.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your account. Sign in with GitHub's supported authentication if prompted. Choose an empty repository initially, without a generated README, to avoid a first-push conflict.

If uploading through GitHub's web interface, ensure `.github/workflows/stock.yml` is present at the repository root. Hidden folders can be omitted by file pickers. The workflow file must be committed on the default branch. Do not upload the enclosing `iphone-duo-tracker` folder as an extra nesting level.

No extra Python libraries, paid stock service, Telegram subscription, OpenAI key, or personal GitHub token is required. The workflow uses GitHub's automatic `GITHUB_TOKEN` to save state. Private repositories have a plan-dependent free allowance and can incur usage charges beyond it; this project does not set billing limits for you. See [GitHub Actions billing and usage](https://docs.github.com/en/actions/concepts/billing-and-usage).

## 3. Add the two GitHub secrets

In your repository open **Settings → Secrets and variables → Actions → New repository secret**:

| Secret name | Value |
|---|---|
| `TELEGRAM_BOT_TOKEN` | Token supplied by BotFather |
| `TELEGRAM_CHAT_ID` | Your private chat ID printed by the helper |

Never put these values in `config.json`. The workflow injects them only into its notification/checker step. Error messages suppress token-bearing request URLs. If a token is exposed, revoke it through BotFather and replace this secret.

Under **Settings → Actions → General**, allow this repository's workflows. The workflow requests `contents: write` to maintain a dedicated `stock-state` branch. Organization policy or branch rules can still block writes; permit this branch or use a personal repository where you control the policy. Keep branch protections on your main source branch as desired.

## 4. Test Telegram, then the checker

1. Go to **Actions → iPhone stock monitor → Run workflow**.
2. Check **test_telegram** and run it. You should receive “StockWatch setup test. No stock claim.” This run makes no retailer requests.
3. Run again with **test_telegram unchecked**. It performs the permitted checks, creates `stock-state`, and sends the initial coverage report.
4. Open the run's **Summary**. Confirm the explicit disabled/unknown sources. A green run with Apple pickup or MediaMarkt observations still means incomplete coverage. A red run with no observations can mean all sources are blocked. Review both the Summary and Telegram message.
5. Open the `stock-state` branch and inspect `state.json` for pause reasons, next-check timestamps and last observations.

The project is deployed in your GitHub repository. Parser, notification decisions and state recovery passed 37 tests locally and on GitHub; retailer access also passed on GitHub. The full [deployment run 40120111752](https://github.com/beatrizjacob/iphone-duo-tracker/actions/runs/40120111752) passed: Telegram accepted its initial coverage report and the stock-state branch was saved. The monitoring workflow is active. Expected cooldown skips remain quiet and count as successful runs.

## Schedule and notification behavior

The configured schedule is every 10 minutes at minutes 2, 12, 22, 32, 42 and 52 UTC, with one shared concurrency group. It makes at most one robots request plus one data request per eligible retailer: one batched Apple pickup request and one MediaMarkt category request, with a minimum 10-second gap and the site's larger Crawl-delay if present. A 5-minute minimum interval in persistent state prevents rapid repeat checks while allowing scheduled jobs to tolerate runner timing variations. Existing hourly success deadlines migrate to the new interval; retailer rate-limit and access-block backoffs are preserved. Do not lower the interval to work around blocks.

Ten-minute checks can still miss brief restocks. GitHub's scheduler can be delayed or drop runs under load; **this cannot promise instant alerts**. Scheduled workflows run from the default branch, and GitHub may disable public-repository schedules after 60 days of inactivity. Check the Actions page periodically; state-branch commits are not a guaranteed workaround. See [GitHub scheduled workflow behavior](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows#schedule).

Only `available` stock results trigger product alerts. Delayed orders never trigger an alert, and there is no delivery-estimate opt-in. Separate notices report meaningful changes in monitoring coverage.

Stock messages deduplicate by product, store/channel and stock result. A confirmed unavailable result re-arms a future stock alert. A network error or unknown result does not re-arm it. Successful notifications are saved after delivery; failed sends are retried on the next eligible run. Coverage notices are sent on meaningful coverage changes, including newly seen unknown stock statuses. Unchanged results remain quiet.

State is stored on `stock-state`, rather than an expiring Actions cache. Saves never force-push, and the workflow tries to save even after a checker failure. A crash after Telegram accepted a message but before state was saved can still produce a duplicate: Telegram and GitHub do not share a transaction. A failed state load stops the checker rather than silently resetting deduplication. Failure emails from GitHub are useful if Telegram itself stops working; enable them in your GitHub notification preferences.

## Access blocks and future coverage

- HTTP 401/403/407/451/541, challenge pages and disallowed robots paths pause a source for manual review. No same-run retry, proxy, browser impersonation, CAPTCHA solving, cookie harvesting or authentication bypass is used.
- HTTP 429 honors Retry-After (seconds or HTTP date) with at least one hour's cooldown. Other transient failures use exponential backoff up to 24 hours.
- Responses must stay on the same retailer host. Network timeouts and changed schemas produce no stock claim.
- If MediaMarkt pauses, leave it paused until permitted access is independently established. Do not repeatedly reset it to defeat protections.
- Apple pickup is enabled for the two verified Barcelona stores. Fnac still needs a verified automated stock response and adapter. MediaMarkt pickup remains unknown. Generic national availability or pickup labels do not establish local inventory.
- `postal_code: "08002"` is an explicit central-Barcelona search location, now used by the Apple pickup adapter. It does not represent your home address. Exact configured stores R368/R406 must be returned; changing the search postcode to another region will safely fail validation unless you also verify and update the store configuration.

After permitted access has actually been restored, the circuit breaker can be reset locally against the state branch:

```sh
python3 state_git.py load
python3 checker.py --reset-source mediamarkt
python3 state_git.py save
```

These commands require a local authenticated clone with write access. Wait until no workflow is active to avoid a concurrent state update. The script refuses non-fast-forward saves. Do not delete the whole state branch to clear a pause; doing so loses alert history.

## Local verification without secrets or retailer requests

```sh
python3 -m unittest discover -s tests -v
python3 checker.py --fixture tests/fixtures/mediamarkt.json --apple-fixture tests/fixtures/apple-pickup.json
```

The fixtures contain reduced, real Apple pickup and MediaMarkt responses captured on 24 October 2026. Apple-only offline inspection is available with `--apple-fixture tests/fixtures/apple-pickup.json`. The MediaMarkt evidence will eventually expire and then correctly report stock as unknown; the test freezes time to validate its original meaning. All positive immediate-stock events used in tests are synthetic and are never represented as verified retailer observations.

`python3 checker.py --dry-run` makes live retailer requests subject to the same rules, but does not send Telegram messages or persist state. Repeated dry runs do not have persistent cooldown protection; do not use them for polling or to retry a blocked source.

## Files

- `checker.py`: access controls, page parsing, deduplication, notifications and coverage reporting.
- `state_git.py`: isolated durable state branch, without modifying source files.
- `telegram_setup.py`: local token-safe private chat ID lookup.
- `config.json`: product identities and explicit coverage limitations.
- `.github/workflows/stock.yml`: schedule and manual Telegram test.
- `tests/`: 40 meaningful offline tests, including local Git state recovery.
- `VERIFICATION.md`: source evidence and precise blocked/unverified boundaries.
