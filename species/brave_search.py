"""Brave Search species — Cloud-less AI plan, Phase 4a.

MCP tool that wraps the Brave Search API for real-time web research.
Registered with short_description: "Search web for real-time facts."

Environment:
    BRAVE_API_KEY — obtain from https://api.search.brave.com/
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request
from typing import Optional


BRAVE_SEARCH_URL = "https://api.search.brave.com/res/v1/web/search"


def brave_search(
    query: str,
    count: int = 5,
    country: str = "us",
    api_key: Optional[str] = None,
) -> dict:
    """Search the web using the Brave Search API.

    Args:
        query:   Search query string.
        count:   Number of results to return (max 20).
        country: Two-letter country code for localised results.
        api_key: Brave API key. Falls back to BRAVE_API_KEY env var.

    Returns:
        dict with keys:
            status  — "ok" or "error"
            query   — echoed query
            results — list of {title, url, snippet}
            error   — present only on failure
    """
    key = api_key or os.environ.get("BRAVE_API_KEY", "")
    if not key:
        return {
            "status": "error",
            "query": query,
            "error": "BRAVE_API_KEY environment variable not set.",
        }

    params = urllib.parse.urlencode({
        "q": query,
        "count": min(int(count), 20),
        "country": country,
    })
    url = f"{BRAVE_SEARCH_URL}?{params}"

    req = urllib.request.Request(
        url,
        headers={
            "Accept": "application/json",
            "Accept-Encoding": "gzip",
            "X-Subscription-Token": key,
        },
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = resp.read()
            # urllib does not auto-decompress; handle gzip if present.
            if resp.info().get("Content-Encoding") == "gzip":
                import gzip
                raw = gzip.decompress(raw)
            data = json.loads(raw)
    except urllib.error.HTTPError as exc:
        return {"status": "error", "query": query, "error": f"HTTP {exc.code}: {exc.reason}"}
    except Exception as exc:
        return {"status": "error", "query": query, "error": str(exc)}

    results = []
    for item in data.get("web", {}).get("results", []):
        results.append({
            "title": item.get("title", ""),
            "url": item.get("url", ""),
            "snippet": item.get("description", ""),
        })

    return {"status": "ok", "query": query, "results": results}
