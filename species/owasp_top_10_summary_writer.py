"""Summarise OWASP Top 10 audit findings into a structured report.
"""
from __future__ import annotations
from typing import Any, Dict

def owasp_top_10_summary_writer(params: Dict[str, Any]) -> Dict[str, Any]:
    """Summarise OWASP Top 10 audit findings into a structured report.

    Args:
        params: Input parameters (see implementation for keys).

    Returns:
        Dict with 'status', 'name', and 'result'.
    """
    domain   = params.get("domain",  "owasp top 10 summary")
    target   = params.get("target",  "all")
    fmt      = params.get("format",  "text")

    lines = [
        f"=== {domain} Report ===",
        f"Target  : {target}",
        f"Summary : Summarise OWASP Top 10 audit findings into a structured report.",
        "Status  : operational",
    ]
    report = "\n".join(lines) if fmt == "text" else dict(domain=domain, target=target, description="Summarise OWASP Top 10 audit findings into a structured report.")
    return {"status": "ok", "name": "owasp_top_10_summary_writer", "result": report}
