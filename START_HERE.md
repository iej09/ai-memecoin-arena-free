# Start Here - AI Memecoin Arena v1.1 (Free Paper-Only)

No real funds, wallets, exchange logins, seed phrases or paid cloud services are used. **Do not send passwords or API keys in ChatGPT.**

1. **GitHub (public/free):** Add and connect GitHub in ChatGPT's Settings > Plugins, or set up [GitHub](https://github.com/) yourself. A **public** repository is necessary for the standard Actions runners to have zero usage fees. Suggested name: `ai-memecoin-arena-free`.
2. **Gemini (Free tier):** Sign in to [Google AI Studio](https://aistudio.google.com/apikey), create an API key in a **project without a billing account**. Default model is `gemini-3.8-flash`. Confirm the project's model is available on the free tier.
3. **Groq (Free plan):** Sign in to [Groq Cloud](https://console.groq.com/keys), verify Free plan, create an API key. Default models: `openai/gpt-oss-120b` and `qwen/qwen3.8-27b`, both sharing that account's quota. Do **not** upgrade.
4. **Deploy the extracted folder:** Upload the **contents** of this folder to the root of the new GitHub repo, including hidden `.github/workflows/free-paper-tournament.yml`. [GitHub Desktop](https://desktop.github.com/) can help if you prefer no terminal. Never upload a real `.env` file.
5. **Store keys privately:** GitHub repository > Settings > Secrets and variables > Actions > New repository secret. Add `GEMINI_API_KEY`, `GROQ_API_KEY`. `JUPITER_API_KEY` is optional and may remain unset. Keys go here, **not in a chat message or committed file**.
6. **Enable the free dashboard:** GitHub repo > Settings > Pages > Build and deployment > Source = GitHub Actions. Check Settings > Actions > General > Workflow permissions if the worker cannot commit result snapshots.
7. **Enable the tournament when ready:** The scheduled trading job is **OFF by default**. In GitHub Settings > Secrets and variables > Actions > Variables, set `ARENA_ENABLED` to `true` only after the secrets and verification job work. Before enabling, use Actions > Check free APIs without starting tournament > Run workflow.
8. **First safe launch:** Repository > Actions > Zero-cost paper trading tournament > Run workflow (main). It runs a live API preflight first; if keys/models fail, the seven-day clock does **not** start. If the market feed works but no token passes conservative filters, the dashboard shows `NOT_STARTED` until eligible data appears.
9. **Verify:** Check Actions logs for `MODEL CHECK` on all three agents, `Run exactly one PAPER-ONLY tick`, and `Deploy the updated scoreboard`. Visit the Pages URL under Settings > Pages. The scorecard records 7 days once the first valid market shortlist exists.
10. **At deadline:** Inspect live USD/CAD equity, trade costs, unreadable or stale quotes, missed scans, losses and whether holdings could actually be liquidated. Do **not** conclude profitable paper trading proves live profitability.

**Important limits:** This is NOT a continuous low-latency trading server. It attempts a scan every 15 minutes, with model decisions every four ticks. GitHub can drop/delay jobs. There is no paid X/Birdeye/Helius feed. Gemini and Groq may return `429` if your **free** quota is reached. There is no wallet or trading-key code anywhere in this version.

Read `README.md` for all details.
