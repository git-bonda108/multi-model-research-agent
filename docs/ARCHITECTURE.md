# Architecture

This document describes the system as it exists in the code at HEAD. File and class names are real; nothing here is aspirational.

## Component map

```
multi-model-research-agent/
├── research_agent_app.py      # primary app (single file)
│   ├── WebSearchTool          # Tavily + Serper search, dedup by URL
│   ├── VideoSearchTool        # YouTube search, view-count parse + sort
│   ├── SageLensAgenticSystem  # coordinator: clients, keys, pipeline
│   │   ├── _initialize_agents()        # 3 role definitions (research/content/analysis)
│   │   ├── _generate_with_agent()      # role instructions + Chat Completions
│   │   ├── _generate_with_openai()     # gpt-4-turbo, temp 0.3, max_tokens 4000
│   │   ├── _generate_with_anthropic()  # claude-3-5-sonnet-20241022, max_tokens 4000
│   │   ├── _generate_with_deepseek()   # deepseek-chat via OpenAI-compatible base_url
│   │   └── process_query_agentic()     # the pipeline entry point
│   └── main()                 # Streamlit UI: input, 6 result tabs, version history
├── multi-model-research-agent.py               # baseline app (single file)
│   ├── SageLensSystem         # OpenAI + Anthropic clients, search config
│   │   ├── _search_web / _search_videos
│   │   ├── _generate_content  # per-provider generation
│   │   └── process_query      # generate first, then search
│   └── main()                 # simpler two-column UI
├── test_setup.py              # environment check script (imports + env vars)
├── requirements.txt           # enhanced app dependencies
├── requirements-multi-model-research-agent.txt # baseline app dependencies
├── .env.example               # placeholder key template
├── .streamlit/config.toml     # server/theme settings (headless, port 8501, XSRF on)
└── .devcontainer/devcontainer.json  # Codespaces: installs deps, runs multi-model-research-agent.py
```

Both applications are self-contained single files with no shared module; the enhanced app is a superset rewrite of the baseline, not an import of it.

## Data flow, end to end (enhanced app)

1. **Input.** `main()` collects a topic string from a Streamlit text area. On Generate, it constructs a fresh `SageLensAgenticSystem` (clients are re-created per query, not cached).
2. **Key resolution.** `get_secret()` tries `st.secrets` (attribute access, then dict access) and falls back to `os.getenv`, stripping whitespace and quotes. Only `OPENAI_API_KEY` is mandatory; missing optional keys disable the corresponding provider or search source rather than failing.
3. **Web search.** `WebSearchTool.search()` queries Tavily (max 5 results) then Serper (10 organic results plus the knowledge-graph entry when present), sequentially, each in its own try/except. Results are normalized to `{title, url, snippet}`, deduplicated by URL preserving order, and truncated to 10.
4. **Video search.** `VideoSearchTool.search()` scrapes YouTube via the `youtube_search` package, parses view strings ("1.2M", "500K") into numbers, sorts descending, returns the top 5 as `{title, url, views}`.
5. **Context assembly.** The top 5 web results are folded into the generation prompt as `- title: snippet` lines, with snippets truncated to 200 characters (150 in fallback mode). This is the entire retrieval-augmentation step: prompt injection of search snippets, no embeddings, no chunking, no citation grounding beyond what the model chooses to do.
6. **Generation — agentic mode.** Three stages run strictly in sequence, each output feeding the next prompt:
   - *Research stage*: synthesizes the topic plus web context into a structured research document.
   - *Content stage*: rewrites the research output for polish.
   - *Analysis stage*: extracts takeaways and implications from the content output.

   Each stage calls `_generate_with_agent()`, which reads the `Agent` object's `instructions` and `model` attributes and issues a plain Chat Completions call (`gpt-4-turbo`, temperature 0.3, `max_tokens` 4000) with the instructions prepended. The SDK `Runner` is intentionally not used (the code comments cite async issues); the `Agent` objects function as typed prompt containers.
7. **Generation — fallback mode.** When agentic mode is off or the `openai-agents` package is absent, the same enhanced prompt is sent to OpenAI, then Anthropic, then DeepSeek (each optional, each in sequence), and the response with the greatest character length is selected.
8. **Presentation.** Results render in six tabs: Content (with provider/latency/word-count metrics), References, Top Videos, Analysis, Workflow (static explanatory text), Metrics. The result dict is appended to `st.session_state.history`; the last five entries can be reloaded from a Version History section.

The baseline app follows the same shape with two differences: generation runs before search, and provider selection is always the pick-longest rule over OpenAI + Anthropic.

## Orchestration analysis: what is parallel, sequential, async

- **Everything executes sequentially on the Streamlit script thread.** There is no `asyncio`, no threading, no concurrent futures anywhere in the codebase. Search providers are called one after another; generation providers are called one after another; the three role stages are a strict chain because each consumes the previous stage's text.
- The correct name for the pattern is a **single-coordinator sequential pipeline with role-specialized prompt stages**, plus a **best-of-N provider fallback**. It is not supervisor–worker (no delegation or task decomposition at runtime), not planner–critic (no stage evaluates or rejects another's output), and not event-driven.
- The pipeline order is sensible for the design: search must precede generation because search snippets are prompt context. The three-stage chain trades latency (three model calls instead of one) for structure; nothing in the code measures whether the trade pays off (see EVALUATION.md).
- Obvious parallelization candidates that the code does not take: Tavily/Serper/YouTube are independent and could run concurrently, as could the three fallback providers.

## State and context engineering

- **Session state:** `st.session_state` holds `history` (list of result dicts), `current_result`, and `query_count`. This is in-process memory scoped to one browser session; a page refresh or server restart clears it. There is no database, cache, or file persistence, and no cross-query memory — each query is independent.
- **Context bounding:** context sent to models is bounded by construction — at most 5 web snippets, each truncated (200/150 chars), plus the topic. Output is bounded by `max_tokens=4000` per call. In the agentic chain, each stage's full output becomes the next stage's input, so stage-2 and stage-3 prompts grow with model verbosity; there is no summarization or truncation between stages.
- **Result structure:** every generation returns `{content, provider, latency}`; the pipeline result adds `references.{web,videos}`, optional `analysis`, and `metadata` (timestamp, topic, method, and flags recording which search sources were configured).

## Design decisions and trade-offs visible in the code

- **Single-file Streamlit apps.** Minimal deployment surface (Streamlit Cloud, Codespaces devcontainer both work out of the box) at the cost of testability — UI, orchestration, and providers are interleaved, and most methods call `st.warning`/`st.error` directly, so they cannot run headless without a Streamlit context.
- **Prompt-role "agents" instead of SDK execution.** The code constructs OpenAI Agents SDK objects but routes execution through plain Chat Completions. This avoids the SDK's async runner inside Streamlit's synchronous script model, at the cost of losing actual SDK capabilities (tool calling, handoffs). The UI copy describes a fuller multi-agent system than the execution path implements.
- **Longest-response selection.** The best-of-N rule (`max(versions, key=len)`) is cheap and deterministic but equates length with quality; it also multiplies token cost by the number of configured providers.
- **Graceful degradation over hard failure.** Nearly every external call is wrapped in try/except with a Streamlit warning and an empty-result fallback; a Serper HTTP 403 is silently skipped so the app continues on Tavily alone. Only a missing `OPENAI_API_KEY` (plus `ANTHROPIC_API_KEY` in the baseline) halts the app, via `st.stop()` with remediation instructions.
- **Per-query client construction.** `SageLensAgenticSystem()` is instantiated inside the button handler, so API clients and key resolution are redone on every query. Simple and stateless, but adds per-query overhead and makes connection reuse impossible.
