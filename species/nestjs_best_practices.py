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
    "testing":     "/fundamentals/unit-testing.md",
    "pipeline":    "/faq/request-lifecycle.md",
}

_SECTIONS = list(_DOC_PATHS.keys())


def _fetch(path: str) -> str:
    url = _GH_RAW + path
    try:
        req = urllib.request.Request(url, headers={"User-Agent": _UA})
        with urllib.request.urlopen(req, timeout=_TIMEOUT) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as e:
        return f"[fetch error: HTTP {e.code}]"
    except Exception as e:
        return f"[fetch error: {e}]"


def _extract(md: str) -> dict:
    """Extract summary, practices, and first code example from markdown."""
    lines = md.splitlines()
    summary = ""
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#") and not line.startswith(">"):
            summary = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", line)
            summary = re.sub(r"[`*_]", "", summary).strip()[:200]
            break

    numbered = re.findall(r"^\d+\.\s+(.+)$", md, re.MULTILINE)
    bullets  = re.findall(r"^[-*]\s+`?([^`\n]{5,})`?$", md, re.MULTILINE)
    headings = re.findall(r"^####\s+(.+)$", md, re.MULTILINE)

    if len(numbered) >= 3:
        practices = [p.strip() for p in numbered[:10]]
    elif len(bullets) >= 3:
        practices = [re.sub(r"[`*_\[\]]", "", p).strip() for p in bullets[:10]]
    else:
        practices = [h.strip() for h in headings[:10]]

    code_match = re.search(r"```(?:typescript|bash|ts|js|shell)\n([^`]+)```", md)
    example = code_match.group(1).strip() if code_match else ""

    return {"summary": summary, "practices": practices, "example": example[:1500]}


def run(topic: str = "all") -> dict:
    """
    Return live NestJS best-practice guidance fetched from official docs at runtime.

    Source: https://github.com/nestjs/docs.nestjs.com (raw markdown — always current)
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

    parsed = _extract(md)
    return {
        "topic": topic,
        "summary": parsed["summary"],
        "practices": parsed["practices"],
        "example": parsed["example"],
        "raw_chars": len(md),
        "source": f"https://docs.nestjs.com/{_DOC_PATHS[topic].strip('/').replace('.md', '')}",
        "raw_url": _GH_RAW + _DOC_PATHS[topic],
    }
