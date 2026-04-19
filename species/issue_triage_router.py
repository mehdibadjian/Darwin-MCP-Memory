"""issue_triage_router species — Deterministic rule-based GitHub issue router.

Maps issue labels, title keywords, and optional file-path mentions to specific
team members or teams. Designed to pipe directly after github_issue_classifier.
"""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Default routing table  (label -> list of assignees, ordered by priority)
# ---------------------------------------------------------------------------

_DEFAULT_ROUTING: dict[str, list[str]] = {
    "bug":              ["backend-lead",  "backend-team"],
    "feature":         ["product-lead",  "product-team"],
    "docs":            ["docs-lead",     "docs-team"],
    "question":        ["support-lead",  "support-team"],
    "security":        ["security-lead", "security-team"],
    "performance":     ["backend-lead",  "infra-team"],
    "ci":              ["devops-lead",   "devops-team"],
    "needs-triage":    ["triage-team"],
}

# Path-based routing: if title/body mentions these path fragments -> assign
_PATH_ROUTING: list[tuple[str, list[str]]] = [
    (r"\bfrontend\b|\bui\b|\breact\b|\bvue\b|\bcss\b",   ["frontend-team"]),
    (r"\binfra\b|\bdocker\b|\bk8s\b|\bkubernetes\b",     ["devops-team"]),
    (r"\bdatabase\b|\bsql\b|\bmigration\b|\bschema\b",   ["data-team"]),
    (r"\bapi\b|\bendpoint\b|\brest\b|\bgrpc\b",          ["backend-team"]),
]

_MAX_ASSIGNEES = 3


def issue_triage_router(
    labels: list[str],
    title: str = "",
    body: str = "",
    routing_table: Optional[dict] = None,
    max_assignees: int = _MAX_ASSIGNEES,
) -> dict:
    """Assign a GitHub issue to team members based on labels and content.

    Designed to accept output from ``github_issue_classifier`` directly:
        classifier_result = github_issue_classifier(title, body)
        assigner_result   = issue_triage_router(
            labels=classifier_result['labels'],
            title=title,
            body=body,
        )

    Args:
        labels:        List of label strings (from classifier).
        title:         Issue title (used for path-based routing).
        body:          Issue body (used for path-based routing).
        routing_table: Optional override / extension of the default routing table.
        max_assignees: Cap on returned assignees (default 3).

    Returns:
        dict with keys:
            status            - 'ok' or 'error'
            assignees         - list[str] (deduplicated, capped at max_assignees)
            primary_assignee  - str (first pick or 'triage-team')
            routing_reasons   - list[str] explaining each assignment
            unrouted_labels   - list[str] labels that had no routing rule
    """
    if not isinstance(labels, list):
        return {"status": "error", "error": "labels must be a list"}

    table = dict(_DEFAULT_ROUTING)
    if routing_table:
        for k, v in routing_table.items():
            table[k] = v if isinstance(v, list) else [v]

    text = f"{title} {body}".lower()

    assignees: list[str] = []
    seen: set[str] = set()
    reasons: list[str] = []
    unrouted: list[str] = []

    # --- Label-based routing ---
    for label in labels:
        candidates = table.get(label.lower())
        if candidates:
            for c in candidates:
                if c not in seen:
                    assignees.append(c)
                    seen.add(c)
            reasons.append(f"label '{label}' → {candidates[:2]}")
        else:
            unrouted.append(label)

    # --- Path/content-based routing ---
    for pattern, teams in _PATH_ROUTING:
        if re.search(pattern, text):
            for t in teams:
                if t not in seen:
                    assignees.append(t)
                    seen.add(t)
            reasons.append(f"content pattern '{pattern[:30]}' → {teams}")

    # --- Fallback ---
    if not assignees:
        assignees = ["triage-team"]
        reasons.append("no matching rules → fallback triage-team")

    assignees = assignees[:max_assignees]
    primary = assignees[0] if assignees else "triage-team"

    return {
        "status": "ok",
        "assignees": assignees,
        "primary_assignee": primary,
        "routing_reasons": reasons,
        "unrouted_labels": unrouted,
    }
