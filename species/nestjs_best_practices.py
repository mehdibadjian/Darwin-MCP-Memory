
import re
import urllib.request
import urllib.error

_GH_RAW = "https://raw.githubusercontent.com/nestjs/docs.nestjs.com/master/content"
_UA = "Mozilla/5.0 (compatible; DarwinMCP/1.0)"
_TIMEOUT = 10

_DOC_PATHS = {
    "quickstart":  "/first-steps.md",
    "structure":   "/recipes/structure.md",
    "modules":     "/modules.md",
    "di":          "/fundamentals/custom-providers.md",
    "config":      "/techniques/configuration.md",
    "validation":  "/techniques/validation.md",
    "security":    "/security/helmet.md",
    "testing":     "/fundamentals/testing.md",
    "pipeline":    "/faq/request-lifecycle.md",
}

_SECTIONS = list(_DOC_PATHS.keys())


def _fetch(path: str) -> str:
    """Fetch raw markdown from NestJS GitHub docs. Returns text or error string."""
    url = _GH_RAW + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"[fetch error: HTTP {e.code}]"
    except Exception as e:
        return f"[fetch error: {e}]"


def _extract_section(md: str, max_chars: int = 3000) -> dict:
    """Pull key practices and first code block from markdown."""
    # Collect bullet points as practices
    bullets = re.findall(r"^[-*] (.+)$", md, re.MULTILINE)
    # Collect first typescript/bash code block
    code_match = re.search(r"```(?:typescript|bash|ts|js)\n([^`]+)```", md)
    example = code_match.group(1).strip() if code_match else ""
    # Summary = first non-empty non-heading line
    lines = [l.strip() for l in md.splitlines() if l.strip() and not l.startswith("#")]
    summary = lines[0][:200] if lines else ""
    return {
        "summary": summary,
        "practices": [b.strip() for b in bullets[:8]],
        "example": example[:1500],
    }


def run(topic: str = "all") -> dict:
    """
    Return live NestJS best-practice guidance fetched from the official docs.

    Source: https://github.com/nestjs/docs.nestjs.com
    topic: "all" | "quickstart" | "structure" | "modules" | "di" |
           "config" | "validation" | "security" | "testing" | "pipeline"
    """
    if topic == "all":
        return {
            "topic": "all",
            "sections": _SECTIONS,
            "tip": "Call run(topic=<section>) to fetch live docs for that topic.",
            "source": "https://github.com/nestjs/docs.nestjs.com",
        }

    if topic not in _DOC_PATHS:
        return {"error": f"Unknown topic '{topic}'", "available": _SECTIONS}

    md = _fetch(_DOC_PATHS[topic])
    if md.startswith("[fetch error"):
        return {"topic": topic, "error": md, "source": _GH_RAW + _DOC_PATHS[topic]}

    parsed = _extract_section(md)
    return {
        "topic": topic,
        "summary": parsed["summary"],
        "practices": parsed["practices"],
        "example": parsed["example"],
        "raw_chars": len(md),
        "source": f"https://docs.nestjs.com/{topic.replace('_', '/')}",
        "raw_url": _GH_RAW + _DOC_PATHS[topic],
    }
