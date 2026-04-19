"""github_webhook_handler species — Parses GitHub webhook payloads for issue events.

Accepts raw GitHub webhook JSON (issues.opened / issues.edited / issues.labeled /
issues.assigned) and extracts a normalised, triage-ready dict.
"""
from __future__ import annotations

import json
from typing import Optional, Union

_SUPPORTED_ACTIONS = frozenset([
    "opened", "edited", "labeled", "unlabeled",
    "assigned", "unassigned", "closed", "reopened",
])


def github_webhook_handler(
    payload: Union[str, dict],
    event_type: str = "issues",
) -> dict:
    """Parse a GitHub webhook payload into a structured triage dict.

    Args:
        payload:    Raw GitHub webhook body as JSON string or already-parsed dict.
        event_type: GitHub event header value (default 'issues').

    Returns:
        dict with keys:
            status          - 'ok' or 'error'
            event_type      - echoed event type
            action          - issue action (opened/edited/etc.)
            issue_number    - int
            title           - str
            body            - str (may be empty)
            author          - str GitHub login
            existing_labels - list[str]
            assignees       - list[str]
            repo_full_name  - str (owner/repo)
            html_url        - str
            is_triage_ready - bool (True if opened/edited/reopened)
    """
    # --- Parse payload ---
    if isinstance(payload, str):
        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            return {"status": "error", "error": f"Invalid JSON: {exc}"}
    elif isinstance(payload, dict):
        data = payload
    else:
        return {"status": "error", "error": "payload must be a JSON string or dict"}

    # --- Validate event ---
    if event_type != "issues":
        return {
            "status": "error",
            "error": f"Unsupported event type '{event_type}'. Only 'issues' is handled.",
        }

    action = data.get("action", "")
    if action not in _SUPPORTED_ACTIONS:
        return {
            "status": "error",
            "error": f"Unsupported action '{action}'. Supported: {sorted(_SUPPORTED_ACTIONS)}",
        }

    issue = data.get("issue", {})
    if not issue:
        return {"status": "error", "error": "Missing 'issue' object in payload"}

    repository = data.get("repository", {})

    # --- Extract fields ---
    issue_number = issue.get("number", -1)
    title = issue.get("title", "").strip()
    body = (issue.get("body") or "").strip()
    author = (issue.get("user") or {}).get("login", "unknown")
    html_url = issue.get("html_url", "")
    repo_full_name = repository.get("full_name", "unknown/unknown")

    existing_labels = [
        lbl.get("name", "") for lbl in issue.get("labels", []) if lbl.get("name")
    ]
    assignees = [
        a.get("login", "") for a in issue.get("assignees", []) if a.get("login")
    ]

    is_triage_ready = action in ("opened", "edited", "reopened")

    return {
        "status": "ok",
        "event_type": event_type,
        "action": action,
        "issue_number": issue_number,
        "title": title,
        "body": body,
        "author": author,
        "existing_labels": existing_labels,
        "assignees": assignees,
        "repo_full_name": repo_full_name,
        "html_url": html_url,
        "is_triage_ready": is_triage_ready,
    }
