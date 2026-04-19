"""domain_scout — Dynamic Domain Knowledge Acquisition Agent.

Give Darwin ANY domain and it will:
1. Search the official MCP server registry for matching tools
2. Search the web (DuckDuckGo) for common automation tasks in that domain
3. Cross-reference both sources against the current species registry
4. Enqueue evolve tasks for every gap it finds

There is NO hardcoded domain map — the domain can be anything:
  "docker", "delivery lead", "dotnet", "BD", "IoT firmware",
  "fintech compliance", "Kubernetes", "retrospective facilitation" …

Usage:
    domain_scout({"domain": "delivery lead"})
    domain_scout({"domain": "dotnet", "max_skills": 10, "dry_run": True})
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "dna" / "registry.json"
_BACKLOG_PATH  = Path(__file__).resolve().parent.parent / "dna" / "backlog.json"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _slug(text: str) -> str:
    """Convert arbitrary text to a snake_case skill name."""
    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    text = re.sub(r"_+", "_", text).strip("_")
    return text[:60]


def _read_registry() -> dict:
    if _REGISTRY_PATH.exists():
        try:
            return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"skills": {}}


def _search_mcp_registry(domain: str) -> List[Dict]:
    """Scrape the official MCP server list and return servers relevant to *domain*."""
    candidates = []
    try:
        from brain.engine.scavenger import Scavenger
        servers = Scavenger().fetch_registry()
        keywords = set(_slug(domain).split("_"))

        for srv in servers:
            name    = srv.get("name", "")
            excerpt = srv.get("readme_excerpt", "")
            combined = (name + " " + excerpt).lower()
            # Match if any domain keyword appears in name or excerpt
            if any(kw in combined for kw in keywords if len(kw) > 2):
                skill_name = _slug(name)
                desc = excerpt.strip()[:200] or f"MCP server: {name}"
                candidates.append({
                    "name":        skill_name,
                    "description": desc,
                    "source":      "mcp_registry",
                    "repo_url":    srv.get("repo_url", ""),
                })
        logger.info("domain_scout: MCP registry → %d candidates for '%s'", len(candidates), domain)
    except Exception as exc:
        logger.warning("domain_scout: MCP registry search failed: %s", exc)
    return candidates


def _search_web_tasks(domain: str, max_results: int = 8) -> List[Dict]:
    """Use DuckDuckGo to find common automation tasks/tools for *domain*."""
    candidates = []
    try:
        from brain.utils.web_fetch import search_web

        # Two targeted queries to maximise coverage
        queries = [
            f"{domain} automation tools workflow",
            f"{domain} tasks scripts CLI helper",
        ]
        seen_names: set = set()

        for query in queries:
            results = search_web(query, max_results=max_results)
            for r in results:
                title   = r.get("title", "")
                snippet = r.get("snippet", "")

                # Extract candidate skill names from titles and snippets
                for candidate_text in _extract_tool_phrases(title, snippet, domain):
                    skill_name = _slug(candidate_text)
                    if skill_name and skill_name not in seen_names and len(skill_name) > 4:
                        seen_names.add(skill_name)
                        candidates.append({
                            "name":        skill_name,
                            "description": f"[{domain}] {candidate_text.strip()[:180]}",
                            "source":      "web_search",
                        })

        logger.info("domain_scout: web search → %d candidates for '%s'", len(candidates), domain)
    except Exception as exc:
        logger.warning("domain_scout: web search failed: %s", exc)
    return candidates


def _extract_tool_phrases(title: str, snippet: str, domain: str) -> List[str]:
    """Extract clean, actionable skill names from a search result.

    Only returns phrases where the domain keyword is adjacent to a
    meaningful action verb — avoids noisy/generic results.
    """
    phrases = []
    domain_slug = _slug(domain)
    domain_words = set(domain_slug.split("_"))
    combined = (title + " " + snippet).lower()

    # Pattern: "{domain_word} X tool/manager/checker/…"
    action_suffixes = (
        "tool", "manager", "helper", "generator", "checker", "runner",
        "scanner", "linter", "validator", "deployer", "exporter",
        "tracker", "parser", "builder", "watcher", "reporter", "analyser",
    )
    for dw in domain_words:
        if len(dw) < 3:
            continue
        for m in re.finditer(
            rf'\b{re.escape(dw)}\b\s+([a-z][a-z0-9]{{2,20}})\s+({"|".join(action_suffixes)})\b',
            combined,
        ):
            name = f"{domain_slug}_{_slug(m.group(1))}_{m.group(2)}"
            if len(name) < 60:
                phrases.append(name)

    # Pattern: "automate/manage/track {domain_word} X"
    action_prefixes = ("automate", "manage", "track", "generate", "validate", "monitor", "deploy")
    for dw in domain_words:
        if len(dw) < 3:
            continue
        for m in re.finditer(
            rf'\b({"|".join(action_prefixes)})\s+{re.escape(dw)}\s+([a-z][a-z0-9]{{2,20}})\b',
            combined,
        ):
            verb = m.group(1)
            obj  = _slug(m.group(2))
            if obj and obj != domain_slug:
                name = f"{domain_slug}_{obj}_{verb}r"
                if len(name) < 60:
                    phrases.append(name)

    return phrases[:3]  # strict cap per result


def _synthesise_from_domain(domain_slug: str, known_skills: set) -> List[Dict]:
    """Generate universal skill candidates for any domain using common patterns.

    These are always meaningful regardless of domain and act as a
    guaranteed fallback when MCP registry and web search return nothing.
    """
    patterns = [
        ("status_reporter",    "Report current status, health and KPIs."),
        ("task_tracker",       "Track and manage tasks, owners and due dates."),
        ("workflow_automator", "Automate repetitive workflow steps end-to-end."),
        ("template_generator", "Generate standard documents, configs or code templates."),
        ("health_checker",     "Check quality, completeness and correctness."),
        ("summary_writer",     "Summarise activity, results or logs into a structured report."),
        ("metrics_exporter",   "Collect and export key metrics in a structured format."),
        ("alert_manager",      "Detect threshold breaches and route alerts to the right channel."),
        ("data_validator",     "Validate input data against schema, business rules and constraints."),
        ("changelog_writer",   "Produce a human-readable changelog from structured change data."),
    ]
    candidates = []
    for suffix, desc_template in patterns:
        name = f"{domain_slug}_{suffix}"
        if name not in known_skills:
            candidates.append({
                "name":        name,
                "description": f"[{domain_slug.replace('_', ' ')}] {desc_template}",
                "source":      "synthesised",
            })
    return candidates


def _deduplicate(candidates: List[Dict], known_skills: set, max_skills: int) -> List[Dict]:
    """Remove duplicates and skills already in the registry."""
    seen: set = set()
    unique = []
    for c in candidates:
        name = c["name"]
        if name in known_skills or name in seen or not name:
            continue
        seen.add(name)
        unique.append(c)
        if len(unique) >= max_skills:
            break
    return unique


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def domain_scout(params: Dict[str, Any]) -> Dict[str, Any]:
    """Discover and queue missing skills for any given domain.

    Args:
        params:
            domain      (str)  — any domain, e.g. "docker", "delivery lead", "BD"
            max_skills  (int)  — cap on skills to enqueue per run (default 10)
            priority    (int)  — backlog priority 1-5 (default 2)
            dry_run     (bool) — preview without enqueuing (default False)
            web_search  (bool) — enable web discovery in addition to MCP registry (default True)

    Returns:
        {
            "status":   "ok" | "error",
            "domain":   str,
            "queued":   [{"name": str, "id": str, "source": str}, ...],
            "skipped":  [str],
            "summary":  str,
        }
    """
    domain     = str(params.get("domain", "")).strip()
    max_skills = int(params.get("max_skills", 10))
    priority   = int(params.get("priority", 2))
    dry_run    = bool(params.get("dry_run", False))
    use_web    = bool(params.get("web_search", True))

    if not domain:
        return {"status": "error", "message": "'domain' param is required"}

    registry     = _read_registry()
    known_skills = set(registry.get("skills", {}).keys())

    # --- Discover candidates from both sources ---
    candidates: List[Dict] = []
    candidates += _search_mcp_registry(domain)
    if use_web:
        candidates += _search_web_tasks(domain)

    # Deduplicate and filter against registry
    to_queue = _deduplicate(candidates, known_skills, max_skills)

    # Fallback: synthesise universal patterns when discovery yields nothing
    if not to_queue:
        synthesised = _synthesise_from_domain(_slug(domain), known_skills)
        to_queue = synthesised[:max_skills]

    # Pad with synthesised patterns if discovery found fewer than max_skills
    if len(to_queue) < max_skills:
        synthesised = _synthesise_from_domain(_slug(domain), known_skills)
        seen = {s["name"] for s in to_queue}
        for s in synthesised:
            if s["name"] not in seen and len(to_queue) < max_skills:
                to_queue.append(s)
    queued:  List[Dict] = []
    skipped: List[str]  = list(known_skills & {c["name"] for c in candidates})

    for skill in to_queue:
        if dry_run:
            queued.append({"name": skill["name"], "id": "dry-run", "source": skill.get("source", "?")})
        else:
            try:
                from brain.engine.backlog import enqueue as _enqueue
                item_id = _enqueue(
                    task_type="evolve",
                    payload={
                        "name":                  skill["name"],
                        "description":           skill["description"],
                        "requirements":          [],
                        "domain":                domain,
                        "source":                skill.get("source", "unknown"),
                        "skip_similarity_check": True,
                    },
                    priority=priority,
                    backlog_path=_BACKLOG_PATH,
                )
                queued.append({"name": skill["name"], "id": item_id, "source": skill.get("source", "?")})
                logger.info("domain_scout: queued '%s' (domain=%s, source=%s)",
                            skill["name"], domain, skill.get("source"))
            except Exception as exc:
                logger.error("domain_scout: failed to enqueue '%s': %s", skill["name"], exc)

    summary = (
        f"Domain '{domain}': {len(queued)} skill(s) queued "
        f"({'dry-run' if dry_run else 'live'}), "
        f"{len(skipped)} already in registry."
    )
    logger.info(summary)

    return {
        "status":  "ok",
        "domain":  domain,
        "queued":  queued,
        "skipped": skipped,
        "summary": summary,
    }
