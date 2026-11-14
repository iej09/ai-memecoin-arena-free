> **Deployment safety:** GitHub Actions scheduling is disabled unless the repository variable `ARENA_ENABLED` is explicitly set to `true`. Use the separate **Check free APIs without starting tournament** workflow before enabling the schedule. No real trades are ever made.

# AI Memecoin Arena: **$0 API / $0 hosting** paper-only pilot

**Goal:** Compare three AI models and a deterministic benchmark on **live Solana market data** over a 7-day paper-trading window. Each starts with **CAD $1,000 virtual cash**, may commit up to **75% of marked equity**, and is never allowed to place a real on-chain transaction. The rules include a 25%-per-token limit, simulated adverse fills, and cash-out at the deadline. Models are judged on *realistically liquidatable* paper account value, not token price screenshots.

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

## Launch on a $0 GitHub-hosted schedule (recommended for the free first test)

### Step 1. Create your free API keys **without adding billing**

- **Gemini:** Open [Google AI Studio / API keys](https://aistudio.google.com/apikey), make a **Free Tier** API project, and create an API key. Never attach a billing account to this project. Default model is `gemini-3.8-flash`; if it is not available on your free-tier project, check the provider's current list and change `GEMINI_MODEL` in `.env.example` or in the GitHub workflow environment to a free-eligible model.
- **Groq:** Open [Groq Cloud API keys](https://console.groq.com/keys), stay on the **Free** plan, and create an API key. Do not upgrade to Developer or attach a payment method. The two models share the same Groq account's quotas.
- **Jupiter:** No key is required; the keyless API is limited to about 0.5 requests/second. You may optionally create a **Free** Jupiter key through [Jupiter Developer Platform](https://developers.jup.ag/portal) to raise the request rate. Avoid its paid plans.

**Do not paste any key in ChatGPT, GitHub source files, GitHub Issues, or screenshots.** Keys go only into GitHub **repository secrets**.

### Step 2. Create the free cloud repository

1. Create a **public** GitHub repository named `ai-memecoin-arena-free` (GitHub Free plan).
2. Extract this ZIP on your own computer.
3. Upload the **contents** of the `ai_memecoin_arena_free` folder to the **root** of the repository, including the hidden `.github/workflows/free-paper-tournament.yml` file. The easiest Windows route is [GitHub Desktop](https://desktop.github.com/): choose **File > Add local repository > Create a Repository**, pick the extracted folder, then **Publish repository** and leave **Keep this code private** **unchecked**. Alternatively, with Git installed, run in the extracted `ai_memecoin_arena_free` directory:

   ```bash
   git init
   git add .
   git commit -m "initial free paper arena"
   git branch -M main
   git remote add origin https://github.com/YOUR-USERNAME/ai-memecoin-arena-free.git
   git push -u origin main
   ```

   Replace `YOUR-USERNAME` with your GitHub username. Do not run the commands with `.env` or real API keys tracked; `.env` is in `.gitignore`.
4. In GitHub repository **Settings > Secrets and variables > Actions > New repository secret**, save `GEMINI_API_KEY`, `GROQ_API_KEY`, and optionally `JUPITER_API_KEY`.
5. In **Settings > Pages**, set **Build and deployment > Source = GitHub Actions**. It should not be set to deploy from the `main/docs` branch: automatic commits made with `GITHUB_TOKEN` do not trigger branch-based Pages builds.
6. In **Settings > Actions > General > Workflow permissions**, permit Actions to write repository contents if your repository policy blocks it. The workflow itself requests only `contents: write`, `pages: write`, and `id-token: write` scopes.
7. Open the **Actions** tab > **Zero-cost paper trading tournament** > **Run workflow** (on branch `main`). This runs the free-provider and market-data preflight and **one** live-market paper tick. No clock starts until a permitted candidate passes the safety filter.
8. Once the workflow succeeds, the scheduler will attempt four ticks per hour (`:11`, `:26`, `:41`, `:56` UTC). Its current state is stored as a compressed SQLite snapshot in `state/tournament.sqlite3.gz`, so restarting a GitHub job does **not** reset the balances or deadline. The worker publishes the public scoreboard via a GitHub Pages artifact each run. The Pages URL is shown under **Settings > Pages > Visit site** or in the deployment step.
9. At the deadline, the next available scheduled tick values or attempts to liquidate all paper positions, marks unsellable positions at zero, and publishes CSVs under the website's `/results/` folder (also committed to `docs/results`). GitHub scheduling delays can make the final quote later than the exact 168-hour boundary: **that timing limitation must be reported with the results**.
10. After the final report, use **Actions > Zero-cost paper trading tournament > ... > Disable workflow** to stop unnecessary scheduled runs.

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
- A strategy can invest **at most 75% of liquidatable equity** overall; new purchases have 73% headroom and no individual token can exceed 25% of equity. New buys require positive buy **and** reverse sell quotes, adequate liquidity, token authority restrictions and risk screening.
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
