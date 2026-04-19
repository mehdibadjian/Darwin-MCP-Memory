"""github_issue_classifier species — Triage brain for the GitHub Issue Agent.

Takes a GitHub issue title and body, applies keyword heuristics to determine:
  - Suggested labels  (bug, feature, docs, question, security, performance, ci)
  - Priority score    (1=critical, 2=high, 3=medium, 4=low)
  - Suggested assignee from a team roster
  - Triage summary    (one-line human-readable verdict)
"""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Heuristic tables
# ---------------------------------------------------------------------------

_LABEL_KEYWORDS: list[tuple[str, list[str]]] = [
    ("bug",         ["error", "exception", "traceback", "crash", "fail", "broken",
                     "not working", "doesn't work", "bug", "issue", "regression",
                     "unexpected", "wrong", "incorrect"]),
    ("feature",     ["feature", "enhancement", "add", "support", "implement", "request",
                     "would be nice", "suggestion", "new", "ability to", "allow"]),
    ("docs",        ["documentation", "docs", "readme", "typo", "spelling", "unclear",
                     "explain", "example", "guide", "tutorial"]),
    ("question",    ["how to", "how do i", "question", "help", "confused", "unsure",
                     "what is", "is it possible", "can i", "should i"]),
    ("security",    ["security", "vulnerability", "cve", "injection", "xss", "csrf",
                     "auth", "token", "secret", "password", "exploit", "attack"]),
    ("performance", ["slow", "performance", "memory", "cpu", "leak", "latency",
                     "timeout", "bottleneck", "speed", "optimize", "benchmark"]),
    ("ci",          ["ci", "cd", "pipeline", "workflow", "action", "build fail",
                     "test fail", "github actions", "deploy"]),
]

_PRIORITY_BOOSTS: dict[str, int] = {
    "critical":   1, "urgent": 1, "production": 1, "outage": 1,
    "security":   1, "vulnerability": 1, "data loss": 1, "cve": 1,
    "high":       2, "important": 2, "major": 2, "regression": 2,
    "medium":     3, "moderate": 3,
    "low":        4, "minor": 4, "nitpick": 4, "typo": 4,
}

_ASSIGNEE_MAP: dict[str, list[str]] = {
    "bug":         ["backend-team"],
    "feature":     ["product-team"],
    "docs":        ["docs-team"],
    "question":    ["support-team"],
    "security":    ["security-team"],
    "performance": ["backend-team"],
    "ci":          ["devops-team"],
}


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def github_issue_classifier(
    title: str,
    body: str,
    team_roster: Optional[dict] = None,
) -> dict:
    """Classify a GitHub issue using keyword heuristics.

    Args:
        title:       Issue title string.
        body:        Issue body markdown text.
        team_roster: Optional override mapping label -> list[assignee].
                     Merges with and overrides _ASSIGNEE_MAP.

    Returns:
        dict with keys:
            status           - "ok" or "error"
            labels           - list[str] of suggested labels
            priority         - int 1-4 (1=critical, 4=low)
            priority_label   - human-readable priority name
            suggested_assignees - list[str]
            triage_summary   - one-line verdict string
            confidence       - float 0.0-1.0
    """
    if not title or not title.strip():
        return {"status": "error", "error": "title must not be empty"}

    text = f"{title} {body or ''}".lower()
    text = re.sub(r'[`*_#]', ' ', text)  # strip markdown

    roster = dict(_ASSIGNEE_MAP)
    if team_roster:
        roster.update(team_roster)

    # --- Label matching ---
    matched_labels: list[str] = []
    for label, keywords in _LABEL_KEYWORDS:
        if any(kw in text for kw in keywords):
            matched_labels.append(label)

    if not matched_labels:
        matched_labels = ["needs-triage"]

    # --- Priority ---
    base_priority = 3  # default medium
    for kw, score in _PRIORITY_BOOSTS.items():
        if kw in text:
            base_priority = min(base_priority, score)

    # Security always at least high
    if "security" in matched_labels:
        base_priority = min(base_priority, 1)

    _priority_names = {1: "critical", 2: "high", 3: "medium", 4: "low"}
    priority_label = _priority_names[base_priority]

    # --- Assignees ---
    assignees: list[str] = []
    seen: set[str] = set()
    for lbl in matched_labels:
        for a in roster.get(lbl, []):
            if a not in seen:
                assignees.append(a)
                seen.add(a)

    if not assignees:
        assignees = ["maintainer-team"]

    # --- Confidence ---
    kw_hits = sum(
        1 for _, keywords in _LABEL_KEYWORDS
        for kw in keywords if kw in text
    )
    confidence = round(min(1.0, kw_hits / max(1, len(text.split()) * 0.1)), 2)

    # --- Summary ---
    summary = (
        f"[{priority_label.upper()}] {title.strip()[:80]} "
        f"→ {', '.join(matched_labels)} "
        f"| assign: {', '.join(assignees[:2])}"
    )

    return {
        "status": "ok",
        "labels": matched_labels,
        "priority": base_priority,
        "priority_label": priority_label,
        "suggested_assignees": assignees,
        "triage_summary": summary,
        "confidence": confidence,
    }
