"""Sage Lens MCP server.

Exposes the research pipeline's capabilities over the Model Context Protocol
(stdio transport) so any MCP client — Claude Desktop, an agent runtime, an IDE —
can call them as typed tools:

  web_search       Tavily primary, automatic Serper failover
  video_search     YouTube results ranked by view count
  generate_report  research-report generation over a multi-model fallback chain
                   (GPT-4 Turbo -> Claude 3.5 Sonnet -> DeepSeek); degrades
                   gracefully to whichever provider is configured and healthy
  provider_status  live capability introspection: which providers are usable now

plus a `sage://capabilities` resource describing the toolset and fallback order.

Run:  python mcp_server/sage_lens_mcp.py
Keys: OPENAI_API_KEY, ANTHROPIC_API_KEY, DEEPSEEK_API_KEY,
      TAVILY_API_KEY, SERPER_API_KEY  (any subset; the server adapts)
"""

import json
import os

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP

load_dotenv(override=True)

mcp = FastMCP("sage-lens")

LLM_FALLBACK_ORDER = ["openai", "anthropic", "deepseek"]


def _providers() -> dict:
    return {
        "openai": bool(os.getenv("OPENAI_API_KEY")),
        "anthropic": bool(os.getenv("ANTHROPIC_API_KEY")),
        "deepseek": bool(os.getenv("DEEPSEEK_API_KEY")),
        "tavily": bool(os.getenv("TAVILY_API_KEY")),
        "serper": bool(os.getenv("SERPER_API_KEY")),
    }


@mcp.tool()
def web_search(query: str, max_results: int = 10) -> str:
    """Search the web. Tries Tavily first; on failure or missing key, fails over
    to Serper. Returns a JSON list of {title, url, snippet, source_engine}."""
    results, engine, errors = [], None, []
    if os.getenv("TAVILY_API_KEY"):
        try:
            from tavily import TavilyClient

            hits = TavilyClient(api_key=os.environ["TAVILY_API_KEY"]).search(
                query=query, max_results=max_results
            ).get("results", [])
            results = [
                {"title": h.get("title", ""), "url": h.get("url", ""),
                 "snippet": h.get("content", "")[:300]} for h in hits
            ]
            engine = "tavily"
        except Exception as exc:  # noqa: BLE001 - degrade to the next engine
            errors.append(f"tavily: {exc}")
    if not results and os.getenv("SERPER_API_KEY"):
        try:
            resp = requests.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": os.environ["SERPER_API_KEY"]},
                json={"q": query, "num": max_results}, timeout=20,
            )
            resp.raise_for_status()
            results = [
                {"title": h.get("title", ""), "url": h.get("link", ""),
                 "snippet": h.get("snippet", "")} for h in resp.json().get("organic", [])
            ]
            engine = "serper"
        except Exception as exc:  # noqa: BLE001
            errors.append(f"serper: {exc}")
    return json.dumps(
        {"engine": engine, "results": results[:max_results], "errors": errors}, indent=2
    )


@mcp.tool()
def video_search(query: str, max_results: int = 5) -> str:
    """Search YouTube and rank results by view count. Returns a JSON list of
    {title, url, channel, views}."""
    from youtube_search import YoutubeSearch

    raw = YoutubeSearch(query, max_results=max(10, max_results)).to_dict()
    videos = []
    for r in raw:
        views = "".join(ch for ch in r.get("views", "0") if ch.isdigit()) or "0"
        videos.append({
            "title": r.get("title", ""),
            "url": f"https://www.youtube.com/watch?v={r.get('id', '')}",
            "channel": r.get("channel", ""),
            "views": int(views),
        })
    videos.sort(key=lambda v: v["views"], reverse=True)
    return json.dumps(videos[:max_results], indent=2)


def _call_openai(prompt: str) -> str:
    from openai import OpenAI

    resp = OpenAI().chat.completions.create(
        model="gpt-4-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=2000,
    )
    return resp.choices[0].message.content


def _call_anthropic(prompt: str) -> str:
    import anthropic

    resp = anthropic.Anthropic().messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=2000,
        messages=[{"role": "user", "content": prompt}],
    )
    return resp.content[0].text


def _call_deepseek(prompt: str) -> str:
    resp = requests.post(
        "https://api.deepseek.com/chat/completions",
        headers={"Authorization": f"Bearer {os.environ['DEEPSEEK_API_KEY']}"},
        json={"model": "deepseek-chat",
              "messages": [{"role": "user", "content": prompt}],
              "max_tokens": 2000},
        timeout=90,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


_CALLERS = {"openai": _call_openai, "anthropic": _call_anthropic, "deepseek": _call_deepseek}


@mcp.tool()
def generate_report(topic: str, web_context: str = "") -> str:
    """Generate a structured research report on a topic. Walks the multi-model
    fallback chain (gpt-4-turbo -> claude-3-5-sonnet -> deepseek-chat): the first
    healthy, configured provider answers; provider errors degrade to the next.
    Returns JSON {provider, report, attempts}."""
    prompt = f"Create a comprehensive, well-structured research document about: {topic}"
    if web_context:
        prompt += f"\n\nRelevant web-search context:\n{web_context}"
    attempts = []
    available = _providers()
    for name in LLM_FALLBACK_ORDER:
        if not available.get(name):
            attempts.append({"provider": name, "status": "not configured"})
            continue
        try:
            report = _CALLERS[name](prompt)
            attempts.append({"provider": name, "status": "ok"})
            return json.dumps({"provider": name, "report": report, "attempts": attempts}, indent=2)
        except Exception as exc:  # noqa: BLE001 - degrade to the next provider
            attempts.append({"provider": name, "status": f"error: {exc}"})
    return json.dumps({"provider": None, "report": None, "attempts": attempts}, indent=2)


@mcp.tool()
def provider_status() -> str:
    """Report which search engines and model providers are configured right now,
    and the order the report generator will try them in."""
    return json.dumps({"providers": _providers(), "llm_fallback_order": LLM_FALLBACK_ORDER}, indent=2)


@mcp.resource("sage://capabilities")
def capabilities() -> str:
    """Machine-readable capability manifest for MCP clients."""
    return json.dumps({
        "name": "sage-lens",
        "tools": ["web_search", "video_search", "generate_report", "provider_status"],
        "search_failover": ["tavily", "serper"],
        "llm_fallback_order": LLM_FALLBACK_ORDER,
        "models": ["gpt-4-turbo", "claude-3-5-sonnet-20241022", "deepseek-chat"],
        "degradation": "every tool absorbs provider failures and reports attempts instead of raising",
    }, indent=2)


if __name__ == "__main__":
    mcp.run()
