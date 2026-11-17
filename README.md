> **Deployment safety:** GitHub Actions scheduling is disabled unless the repository variable `ARENA_ENABLED` is explicitly set to `true`. Use the separate **Check free APIs without starting tournament** workflow before enabling the schedule. No real trades are ever made.

# AI Memecoin Arena: **$0 API / $0 hosting** paper-only pilot

**Goal:** Compare three AI models and a deterministic benchmark on **live Solana market data** over a 7-day paper-trading window. Each starts with **CAD $1,000 virtual cash**, may commit up to **100% of marked equity**, and is never allowed to place a real on-chain transaction. The rules allow 100% exposure in a single coin or across multiple coins, with simulated adverse fills, upfront network costs, no borrowing, and cash-out at the deadline. Models are judged on *realistically liquidatable* paper account value, not token price screenshots.

**IMPORTANT:** This is the **free edition**, replacing the earlier paid-provider starter. The OpenAI and Anthropic hosted commercial models are **not in the free trial**. The tool uses no real wallet, brokerage login, exchange API, private key, seed phrase, paid social monitoring or cloud subscription. The free-tier AI models **are not GPT-6 or Claude**. A positive result would not establish that the original GPT-6/Claude competition would have won.

**What $0 means:** No provider or hosting fees **provided** you use a **public** GitHub repository and its standard Actions runner, keep Groq and Gemini on their **Free API tiers with no billing enabled**, use free Jupiter keyless/free-plan data, and do not enable paid products. GitHub Pages publishes a public scoreboard. Limits and terms may change. The code cannot see your provider account's billing settings; **you must not link a billing account or upgrade your AI API account** if the non-negotiable requirement is no charges. If a free rate limit or endpoint is unavailable, the affected model records a hold/failure; it never upgrades to a paid service automatically.

**Continuous service caveat:** GitHub Actions runs *cloud jobs on a schedule*, not a persistent 24/7 server. We schedule scans every 15 minutes; model decisions occur every 4 scans (~hourly); protective exit checks happen on each scan. GitHub may delay or drop scheduled jobs, which is recorded in the heartbeat/ledger. This is a **$0 cloud-scheduled trial**, not a genuine low-latency always-on trading system. Memecoin moves lasting less than 15 minutes will often be missed. That is part of the measured limitations of this free pilot.

## Reliability fixes in version 1.1

- AI competitors **and** the rules-only baseline now see the **same eight ranked candidates** per decision. A prior build showed the baseline fifteen while truncating AI prompts to eight, invalidating apples-to-apples comparison.
- A discovery outage no longer updates the *last valid market scan* or falsely claims healthy polling. A failed scan is visible in the site metadata.
- Before kickoff, data or FX outages leave the scoreboard in `NOT_STARTED` and **do not start the seven-day clock**. After kickoff, an unavailable FX reference is marked `LAST_KNOWN`, never silently treated as fresh.
- Cloud job checkout explicitly uses latest `main` after serialized runs, reducing risk of overwriting an older state snapshot. A fatal `--once` worker error fails the workflow instead of exiting green.
- Pages artifacts are kept for only one day to avoid accumulating unnecessary free-tier artifact storage.
- Added failure-path regression tests. These are offline tests. **Actual API responses and provider free-plan eligibility must be verified from the user's account before activation**.

## What is in this ZIP

| Component | Cost | Uses |
|---|---:|---|
| Google Gemini Flash free-tier API | $0 | AI competitor 1 (`gemini_free`) |
| Groq free-tier GPT-OSS 120B | $0 | AI competitor 2 (`groq_gptoss`) |
| Groq free-tier Qwen 3.8 27B | $0 | AI competitor 3 (`groq_qwen`) |
| Rules-based momentum baseline | $0 | Control strategy |
| Jupiter keyless/free API | $0 | Solana token discovery, executable-size swap quotes (read-only) |
| DEX Screener public API + keyless RugCheck where reachable | $0 | Optional bounded deep token research |
| Frankfurter reference exchange rate | $0 | USD/CAD paper accounting |
| GitHub Actions in a **public** repo | $0 | Scheduled cloud execution |
| GitHub Pages public site | $0 | Read-only leaderboard |

No X paid API, Birdeye paid API, Helius paid RPC or Bitquery service is called in this edition. You do **not** have complete influencer/social/smart-wallet intelligence in this $0 build. Social links visible on DEX Screener are weaker evidence than full verified social analysis.

## Deployment status as of November 14, 2026

- GitHub code and unit tests are available; the expanded synthetic test suite checks safety and end-of-week exports.
- A keyless Solana market check found **92 discovered tokens and 10 passing initial safety filters** (a one-time snapshot, not a profit claim).
- Gemini and Groq API keys authenticated for read-only model-list queries. **This does not confirm free-plan billing or live generation.**
- The paper tournament is **NOT_STARTED**, and paid providers, X API, Bitquery and all real trading remain disabled.
- The [GitHub-native status page](STATUS.md) works without GitHub Pages. The visual Pages deployment needs a one-time Pages setup.

## Launch on a $0 GitHub-hosted schedule (recommended for the free first test)

### Step 1. Create your free API keys **without adding billing**

- **Gemini:** Open [Google AI Studio / API keys](https://aistudio.google.com/apikey), make a **Free Tier** API project, and create an API key. Never attach a billing account to this project. Default model is `gemini-3.5-flash-lite`; if it is not available on your free-tier project, check the provider's current list and change `GEMINI_MODEL` in `.env.example` or in the GitHub workflow environment to a free-eligible model.
- **Groq:** Open [Groq Cloud API keys](https://console.groq.com/keys), stay on the **Free** plan, and create an API key. Do not upgrade to Developer or attach a payment method. The two models share the same Groq account's quotas.
- **Jupiter:** No key is required; the keyless API is limited to about 0.5 requests/second. You may optionally create a **Free** Jupiter key through [Jupiter Developer Platform](https://developers.jup.ag/portal) to raise the request rate. Avoid its paid plans.

**Do not paste any key in ChatGPT, GitHub source files, GitHub Issues, or screenshots.** Keys go only into GitHub **repository secrets**.

### Step 2. Activate the existing GitHub repository safely

Repository: [iej09/ai-memecoin-arena-free](https://github.com/iej09/ai-memecoin-arena-free).
It already contains the paper-trading engine, tests, and a [GitHub-native scoreboard](STATUS.md).
GitHub Actions secrets `GEMINI_API_KEY` and `GROQ_API_KEY` are present. A safe, read-only API check confirmed these three model IDs are available: `gemini-3.5-flash-lite`, `openai/gpt-oss-120b`, `qwen/qwen3.8-27b`. **Model inference has NOT been tested and the 7-day competition has NOT started.**

1. Verify in [Google AI Studio](https://aistudio.google.com/) that the Gemini project is explicitly **Free Tier with no linked paid billing**. Verify [GroqCloud](https://console.groq.com/) is on the **Free plan**, with no paid plan/automatic billing. If either is not clearly free, **do not proceed**.
2. In [GitHub Actions repository variables](https://github.com/iej09/ai-memecoin-arena-free/settings/variables/actions) create `ARENA_FREE_TIER_VERIFIED` with value `true`, **only after checking both providers yourself**. This is a user attestation; the API metadata endpoints cannot reveal your billing plan.
3. Run [Check free APIs without starting tournament](https://github.com/iej09/ai-memecoin-arena-free/actions/workflows/preflight-only.yml) using **Run workflow**. This sends one small inference request to each of the three models, confirms the structured response and market data, and leaves the 7-day clock off. Stop if it fails. This workflow will **skip** without the verification variable.
4. If every preflight check passes, create repository variable `ARENA_ENABLED` with value `true`. This is the second switch. Both switches must be on before the scheduled tournament worker can run. The first valid paper tick starts the immutable 168-hour countdown.
5. For the first tick, manually run [Zero-cost paper trading tournament](https://github.com/iej09/ai-memecoin-arena-free/actions/workflows/free-paper-tournament.yml). The schedule then attempts four ticks per hour (`:11`, `:26`, `:41`, `:56` UTC). Delays or missed jobs are possible; this is **not** a low-latency permanent server.
6. Track the leaderboard at [STATUS.md](STATUS.md). This Markdown fallback works without GitHub Pages. If you want the richer public visual dashboard, set **Settings > Pages > Build and deployment > Source = GitHub Actions** once. The worker detects this automatically and publishes the visual website at the next paper tick; no extra variable is required. Pages is optional and does not block paper trades.
7. At the seven-day deadline, the next available tick attempts liquidations, marks unsellable tokens at zero, writes final CSVs, and preserves results in the repo. **Disable the scheduled workflow** in GitHub Actions after the final report so jobs stop.

**Important:** The simulator never signs transactions or connects to a real wallet. An AI API key with a linked billing account can still incur usage charges; a repository variable by itself is not a billing guarantee. Never link paid billing just to make a preflight pass. Grok/xAI is **not** included in this free edition.

**Privacy note:** A public repository and Pages site expose your simulated holdings, token picks and trades to everyone. The provider secrets remain secret unless you intentionally reveal them or modify the workflow to print them. Do not put any personal information into paper-trading notes.

## Local dry run without spending a cent

If you have Python 3.12+ installed, you can run **unit tests without even creating accounts**:

```bash
python -m pip install -r requirements-dev.txt
python -m pytest -q
```

These tests use mocked quotes and model responses, and prove that basic accounting, position limits, no-sell-route checks, model route selection, database persistence and static export behave as expected. They **do not prove that live provider APIs will respond**. For a live keyless market-data preflight (no model keys required):

```bash
python -m pip install -r requirements.txt
python tournament.py --check-data
```

A local always-on test uses `.env.example` copied to `.env` with **only free** Gemini and Groq API keys, then `python tournament.py --check` followed by `python tournament.py`. A standalone read-only dashboard may be started using `uvicorn dashboard:app --host 127.0.0.1 --port 8787`. Note that a local computer uses its own electricity and must remain on.

## Risk/strategy rules and honest limits

- The four virtual accounts begin at CAD $1,000 using the first available CAD/USD reference rate; accounting continues in synthetic USDC/USD and reports CAD at subsequent daily FX rates.
- A strategy may invest **up to 100% of available simulated cash**, including in one coin, with no portfolio or per-token reserve requirement. Fees and network cost are paid from the virtual balance first, so truly all-in leaves roughly zero uncommitted cash, never debt. Staying in cash remains optional. New buys require positive buy **and** reverse sell quotes, adequate liquidity, token authority restrictions and risk screening.
- At purchase, the engine applies a modeled 0.5% adverse execution haircut and virtual $0.03 network cost, with another haircut on selling. This **understates** possible catastrophic slippage on very illiquid tokens and can be optimistic. A last price is not accepted as exit value.
- The same candidate feed goes to each AI. Each can ask for one additional bounded DEX Screener / keyless RugCheck research pass per decision (a second AI request consumes more of its free quota). Provider failures are recorded as failures/HOLD, never made-up positive signals.
- Default token risk checks use Jupiter token metadata and audits. Such checks are **not guarantees** against insider distribution, malicious contracts, MEV or exit liquidity disappearing.
- Agents make decisions around hourly by default; risk checks are scheduled around every 15 minutes. An hourly strategy cannot be compared fairly against true high-frequency bots. If the project has low performance, lack of signal freshness is one possible cause.
- The seven-day winner may simply be lucky. Require repeated out-of-sample tests plus realistic loss and API reliability analysis **before even considering a later real-money system**. No real execution exists in this code.

## What if something fails?

- **Missing secrets**: workflow fails during preflight, nothing starts and no money is spent. Add the secrets in GitHub Settings.
- **Model 401/403/404**: key or selected model unavailable; ensure the provider project is still on its free tier. Do **not** enable paid billing as a workaround. Use the provider's free model list and update the workflow environment/model setting, then re-run preflight. Model substitutions after kickoff invalidate a clean same-model comparison; document them.
- **Model 429**: quota exhausted. Bot HOLDs for that decision; no automatic tier upgrade. Check the free quota and lower `DECISION_EVERY` / number of calls *before* kickoff if needed.
- **No eligible tokens**: fail closed; seven-day clock does not start until a qualifying real token appears.
- **Jupiter or FX outage**: the step may fail; GitHub still runs later ticks. Untradeable holdings receive a zero liquidatable mark. Treat missing ticks as a real failure of the free system.
- **Cannot push results**: in GitHub Settings > Actions > General check that Actions has appropriate content write access. The `permissions: contents: write` scope is declared in the workflow. Do not store any GitHub PAT token in `.env`.
- **Pages deployment fails**: enable Pages > Source = GitHub Actions, ensure the `github-pages` deployment environment is allowed, and use Actions logs to diagnose it.

## Optional truly always-on free server (more setup / more risk)

[Oracle Cloud Always Free](https://www.oracle.com/cloud/free/) can provide a VM that runs Docker continuously if an eligible shape is available. Oracle requires a credit/debit card for identity verification (temporary authorization holds may occur), warns that capacity may be unavailable, and may reclaim idle Always Free compute instances. **Do not select a paid shape or upgrade to Pay As You Go.** A free VM avoids GitHub's scheduled cold starts, but we do not recommend it as the first route for someone who wants **no payment details involved at all**. If chosen, launch the included Docker Compose service with only free-tier Gemini and Groq keys.

## Official documentation reviewed (November 2026)

- [GitHub Actions public repository usage pricing](https://docs.github.com/en/actions/concepts/billing-and-usage)
- [GitHub Actions scheduled-workflow delays](https://docs.github.com/en/actions/reference/workflows-and-actions/events-that-trigger-workflows)
- [GitHub Pages custom workflows](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages)
- [Gemini Developer API pricing](https://ai.google.dev/gemini-api/docs/pricing)
- [Gemini rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)
- [Groq free tier billing FAQ](https://console.groq.com/docs/billing-faqs)
- [Groq free-tier model limits](https://console.groq.com/docs/rate-limits)
- [Jupiter Developer API](https://developers.jup.ag/)
- [DEX Screener public API reference](https://docs.dexscreener.com/api/reference)

## Deploy permission blocker

I cannot create the repository or add secrets for you until you grant access through the GitHub connection in ChatGPT, or upload the extracted project yourself. **Do not share passwords, seed phrases or API keys in chat.** The GitHub connection may not permit writing encrypted repository secrets; if not, use GitHub Settings > Secrets and variables > Actions yourself. Even after all code is deployed, the contest is **not running** until GitHub reports a successful preflight and first eligible live-market paper tick.
