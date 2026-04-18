import re
import json
import urllib.request
import urllib.error
import urllib.parse

_BRAIN_BASE = "http://127.0.0.1:8765"  # overridable via run(brain_url=...)
_UA = "Mozilla/5.0 (compatible; DarwinMCP/1.0)"
_TIMEOUT = 15

_TOPICS = {
    "all": "FPGA design best practices overview",
    "hdl": "FPGA HDL coding best practices Verilog VHDL",
    "timing": "FPGA timing constraints static timing analysis best practices",
    "clocking": "FPGA clock domain crossing CDC best practices",
    "simulation": "FPGA simulation testbench verification best practices",
    "synthesis": "FPGA synthesis optimization area speed power best practices",
    "partitioning": "FPGA design partitioning hierarchy floorplan best practices",
    "reset": "FPGA reset strategy synchronous asynchronous best practices",
}

_SECTIONS = [k for k in _TOPICS if k != "all"]


def _brain_search(query: str, brain_url: str, fetch: bool = False) -> list:
    """Call the brain's /search endpoint to get web results."""
    payload = json.dumps({"query": query, "max_results": 5, "fetch": fetch}).encode()
    req = urllib.request.Request(
        f"{brain_url}/search",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {_get_token()}",
            "User-Agent": _UA,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            data = json.loads(resp.read())
        return data.get("results", [])
    except Exception as e:
        return [{"title": "search error", "url": "", "snippet": str(e)}]


def _get_token() -> str:
    import os
    return os.environ.get("MCP_BEARER_TOKEN", "")


def _summarise(results: list) -> dict:
    """Turn search results into structured practices + sources."""
    practices = []
    sources = []
    for r in results:
        snippet = r.get("snippet", "").strip()
        if snippet and len(snippet) > 20:
            practices.append(snippet)
        if r.get("url"):
            sources.append({"title": r.get("title", ""), "url": r["url"]})
    return {"practices": practices[:6], "sources": sources[:5]}


def run(topic: str = "all", brain_url: str = _BRAIN_BASE) -> dict:
    """
    Return FPGA best-practice guidance by searching the web at runtime via the brain.

    The brain's POST /search endpoint does a DuckDuckGo query and returns
    real snippets + URLs — no hardcoded knowledge, always current.

    topic: "all" | "hdl" | "timing" | "clocking" | "simulation" |
           "synthesis" | "partitioning" | "reset"
    brain_url: base URL of the Darwin-God-MCP brain (default: localhost:8765)
    """
    if topic == "all":
        return {
            "topic": "all",
            "sections": _SECTIONS,
            "tip": "Call run(topic=<section>) to search live web for that FPGA topic.",
            "queries": {k: v for k, v in _TOPICS.items() if k != "all"},
        }

    if topic not in _TOPICS:
        return {"error": f"Unknown topic '{topic}'", "available": _SECTIONS}

    query = _TOPICS[topic]
    results = _brain_search(query, brain_url=brain_url)

    if not results or (len(results) == 1 and "error" in results[0].get("title", "")):
        return {
            "topic": topic,
            "error": results[0].get("snippet", "search failed"),
            "query": query,
        }

    summary = _summarise(results)
    return {
        "topic": topic,
        "query": query,
        "practices": summary["practices"],
        "sources": summary["sources"],
        "tip": "Call run(topic, brain_url, fetch=True) via _brain_search for full page text.",
    }
