# Hardening

Current security and operational posture, followed by a staged ladder to production. Grounded in the code at HEAD; items not present in the code are labeled as gaps or proposals.

## Current posture

**Authentication and access control**
- The Streamlit app has no authentication, authorization, or rate limiting of its own. Anyone who can reach port 8501 can issue queries that spend the operator's API credits.
- `.streamlit/config.toml` enables XSRF protection and disables CORS for the packaged config; however, `.devcontainer/devcontainer.json` launches the baseline app with `--server.enableCORS false --server.enableXsrfProtection false`, which is acceptable only inside a Codespaces preview.

**Secrets handling**
- Keys are read from Streamlit secrets or environment variables via `get_secret()`; no key is hard-coded. `.env.example` contains placeholders only. A repository scan at HEAD found no real credentials in any file.
- `.gitignore` covers `.env`, `.env.local`, `*.env`, and `.streamlit/secrets.toml`. (This file previously contained unresolved merge-conflict markers that left the `*.env` pattern inside a conflict block; repaired as part of this documentation pass — see the note at the bottom.)
- Keys live in process memory per query (clients are rebuilt on each Generate click) and are never logged or echoed. Error messages reference key *names*, not values.

**Input/output handling**
- Model output and search-result titles are rendered with `st.markdown(..., unsafe_allow_html=True)` in both apps. Model output and third-party search content are untrusted; this setting allows any HTML they contain to render in the user's browser. This is the most concrete code-level risk in the repository.
- User topic text is interpolated directly into prompts; there is no prompt-injection mitigation, which matters because web-search snippets (attacker-influenceable content) are also folded into the same prompt.

**Error handling and resilience**
- Broad try/except coverage with graceful degradation: failed search sources are skipped, failed providers return `None`, and only missing required keys halt the app. There are no retries and no backoff; Serper calls carry a 15s (enhanced) / 10s (baseline) timeout, while LLM calls rely on SDK defaults.
- One deliberate silent failure: Serper HTTP 403 is swallowed without any user-visible signal, so a revoked Serper key looks like "fewer results" rather than an error.

**Observability**
- None beyond the UI: no logging framework, no structured logs, no metrics export, no tracing. Latency is measured per call but only displayed to the user. If the app misbehaves in deployment, the only evidence is Streamlit's stdout.

**Data**
- No persistence of queries or results (session memory only), so there is no stored-data exposure surface today. Queries and search snippets are transmitted to OpenAI, Anthropic, DeepSeek, Tavily, and Serper under their respective terms.

## Ladder to production

Each rung assumes the previous ones. This ladder is proportionate to what the system is — a single-operator Streamlit research tool — and what it would need to serve untrusted users.

**Rung 1 — Identity, keys, and safe rendering (before any shared deployment)**
- Remove `unsafe_allow_html=True` from every render of model or search content, or sanitize through an HTML allowlist first.
- Put the app behind authentication: Streamlit Cloud viewer allowlist, or an OAuth reverse proxy for self-hosting. Do not expose 8501 directly.
- Move keys to the platform secret store exclusively (Streamlit Cloud secrets or the host's secret manager); stop supporting `.env` in deployed environments. Set per-key spend limits at each provider console.
- Add per-session query throttling (a counter in `st.session_state` is sufficient at first) so a single visitor cannot drain the API budget.

**Rung 2 — Monitoring and cost control**
- Introduce structured logging (stdlib `logging`, JSON formatter): one event per pipeline stage with topic hash, provider, latency, token usage, and error class. Surface the currently-silent Serper 403 as a warning-level log.
- Track token spend per query and per day; alert on budget thresholds. The provider responses already carry usage fields that the code currently discards.
- Add retries with exponential backoff and explicit timeouts on LLM calls; treat providers as unreliable dependencies.
- Stand up the smoke test from EVALUATION.md as a post-deploy check.

**Rung 3 — Deployment engineering**
- Pin dependencies (the requirements files use `>=` ranges; produce a lock file) and reconcile the two requirements files, which currently disagree on the `anthropic` floor (`>=0.8.0` vs `>=0.69.0`).
- Containerize with a non-root user; run behind a TLS-terminating reverse proxy with security headers. Re-enable XSRF protection in every launch path, including the devcontainer command if it is ever reused beyond Codespaces.
- Extract the pipeline from the UI (the same refactor EVALUATION.md needs) so the service can be health-checked and load-tested without a browser.
- CI: run the unit test layer and a dependency-vulnerability scan (`pip-audit`) on every push; block merge on failure.

**Rung 4 — Compliance and lifecycle**
- Document data flows to the five external providers and present them to users of the tool; add a retention statement (trivial today: nothing is retained).
- Add secret scanning (e.g. gitleaks) and history scanning to CI so a leaked key is caught at push time.
- Key rotation runbook: where each key lives, who owns it, rotation cadence, and the revocation path per provider.
- If queries may contain personal or confidential data, gate providers accordingly (zero-retention API tiers where available) and record the decision per provider.

## Repository hygiene notes from this pass

- **No live credentials were found at HEAD.** Nothing requires rotation.
- `.gitignore` contained unresolved Git merge-conflict markers (`<<<<<<<`/`=======`/`>>>>>>>`), which Git treats as literal patterns; the `*.env` ignore rule sat inside a conflict block and was therefore unreliable. The file has been repaired by taking the union of both sides. Verify locally with `git check-ignore -v .env test.env` if in doubt.
