# Evaluation

An honest account of what is tested today, what the code demonstrably handles, and what an evaluation harness for this system should look like.

## What exists today

**There is no automated test suite.** No pytest/unittest files, no CI workflow, no assertions over application behavior, and no quality metrics are computed anywhere in the code.

The one verification artifact is `test_setup.py` — an environment check script, not a test suite. Run it with:

```bash
python test_setup.py
```

It checks exactly two things:

1. **Imports** — that `streamlit`, `openai`, `anthropic`, `tavily`, `youtube_search`, `dotenv`, and `requests` import, and whether the optional OpenAI Agents SDK is importable under any of its names (`agents`, `openai.agents`).
2. **Environment variables** — that `OPENAI_API_KEY` is set (required) and reports on `ANTHROPIC_API_KEY`, `TAVILY_API_KEY`, `SERPER_API_KEY` (optional).

It exits non-zero if a required package or key is missing. It does not call any API, exercise the pipeline, or validate output.

No performance, quality, or cost metrics exist in the code or docs to cite. The UI displays per-query latency and word count, but these are shown to the user, not recorded or asserted against.

## Edge cases the code visibly handles

Enumerated from the source (`sage_lens_enhanced.py` unless noted):

- **Missing required keys** — validated before client construction; the app halts via `st.stop()` with step-by-step remediation for both Streamlit Cloud and local `.env` setups (both apps).
- **Missing optional keys** — the corresponding provider/search source is set to `None` and skipped; the pipeline continues with whatever is available.
- **Key formatting noise** — keys are stripped of surrounding whitespace and quotes on read (`get_secret`).
- **Search provider failure** — Tavily and Serper are each wrapped in their own try/except; a failure in one produces a warning and does not block the other.
- **Serper HTTP 403** — silently skipped by design (the code comments this explicitly), so a bad Serper key degrades to Tavily-only search rather than surfacing an error.
- **HTTP timeouts** — Serper requests carry an explicit timeout (15s enhanced, 10s baseline). No retry logic exists anywhere; a timed-out call is a skipped source.
- **Malformed search results** — results lacking a `url`/`link`/`id` field are filtered out; missing titles default to "Untitled".
- **Duplicate URLs** — deduplicated across Tavily and Serper, preserving first-seen order.
- **View-count parsing** — "1.2M" / "500K" / plain-number formats are parsed; anything unparseable (including "N/A") falls back to 0 rather than raising.
- **Agents SDK absent** — three import paths are attempted; if all fail the UI checkbox is disabled and the app runs in fallback mode.
- **Agent-stage failure** — `_generate_with_agent` falls back to a plain OpenAI call; if that also fails it returns `None` and the pipeline continues.
- **Provider call failure** — each `_generate_with_*` returns `None` on exception; fallback mode selects among whichever providers returned content. If none did, the UI shows a "check your API keys" error instead of crashing.
- **Empty input** — the Generate button is a no-op unless the topic is non-blank.

Two behaviors worth knowing when reading the code (documented here for accuracy, not fixed, since this repository pass is documentation-only):

- The Top Videos tab re-sorts by a `views_num` field that `VideoSearchTool.search()` strips from its return value, so the re-sort is a no-op; ordering is correct only because the tool already sorted before returning.
- `metadata.tavily_used` / `metadata.serper_used` record whether a key was *configured*, not whether that source actually returned results for the query.

## Proposed evaluation harness

Nothing below exists yet; this is the harness the system should have.

**Prerequisite refactor (test seam).** Extract the pipeline out of Streamlit: a `pipeline.py` whose functions accept injected clients and return plain dicts, with the Streamlit files reduced to UI shells. Without this seam, nothing below is cleanly automatable because the current methods call `st.*` directly.

**1. Deterministic unit tests (no network, run in CI on every push).**
- View-count parser: table-driven cases — "1.2M", "500K", "1,234", "N/A", empty, garbage.
- URL deduplication and result normalization from canned Tavily/Serper JSON fixtures.
- `get_secret` precedence: Streamlit secrets over env var, quote/whitespace stripping.
- Provider-selection rule: given mocked provider outputs, assert longest-wins and the all-`None` path.
- Serper response handling: 200 with knowledge graph, 200 without, 403 (silent skip), 500 (warning path), timeout.

**2. Golden-dataset pipeline evaluation (network, run nightly or pre-release).**
- *Dataset shape:* 20–30 fixed topics spanning technical, current-events, and ambiguous queries, each with: the topic string, 3–5 must-cover subtopics, and 2–3 known-authoritative domains that should plausibly appear in references.
- *Metrics per run:* subtopic coverage (LLM-as-judge with a fixed rubric prompt and pinned judge model), reference count and domain hit rate, video result count, end-to-end latency per stage, token usage and cost per provider.
- *Gates:* fail the run if coverage falls below an agreed floor, if any stage's p95 latency regresses by more than an agreed percentage against the stored baseline, or if the pipeline returns empty content for any golden topic.
- *Comparative check:* run the same topics through agentic mode and fallback mode; the three-call agentic chain triples generation cost, and this is the experiment that would justify (or retire) it.

**3. Smoke test (network, minimal spend, on every deploy).** One fixed topic through the full pipeline with real keys; assert non-empty content, at least one web reference when search keys are present, and no unhandled exception.

Until at least layer 1 exists, any change to parsing, selection, or search-handling logic ships unverified.
