"""system_design_analyzer species — Darwin-MCP.

Accepts a high-level product prompt (e.g. "Build a real-time crypto-arbitrage bot")
and produces a LeanKG-style Graph of required sub-agents and their interactions
BEFORE a single line of code is written.

Output schema:
  {
    "status": "ok",
    "prompt": "<echoed>",
    "graph": {
      "nodes": [{"id": str, "role": str, "description": str, "type": str}],
      "edges": [{"from": str, "to": str, "interaction": str, "protocol": str}]
    },
    "summary": str,
    "agent_count": int,
    "edge_count": int
  }
"""
from __future__ import annotations

import re
from typing import Optional

# ---------------------------------------------------------------------------
# Domain heuristics — map keywords -> agent archetypes
# ---------------------------------------------------------------------------

_KEYWORD_ARCHETYPES: list[tuple[list[str], str, str, str]] = [
    (["real-time", "realtime", "stream", "live", "tick", "websocket", "ws"],
     "data_ingestion_agent", "Real-Time Data Ingestion", "ingestion"),
    (["price", "market", "exchange", "binance", "coinbase", "kraken", "feed", "ohlcv"],
     "market_data_agent", "Market Data Feed", "data"),
    (["arbitrage", "spread", "opportunity", "signal", "detect", "scanner"],
     "signal_detection_agent", "Signal / Opportunity Detector", "analysis"),
    (["strategy", "backtest", "simulate", "alpha", "model"],
     "strategy_agent", "Strategy & Backtesting Engine", "strategy"),
    (["order", "execute", "trade", "buy", "sell", "position", "fill"],
     "execution_agent", "Order Execution Engine", "execution"),
    (["risk", "limit", "exposure", "hedge", "stop", "drawdown"],
     "risk_management_agent", "Risk Management Agent", "risk"),
    (["portfolio", "balance", "allocation", "pnl", "profit"],
     "portfolio_agent", "Portfolio Manager", "finance"),
    (["auth", "login", "jwt", "oauth", "session", "user"],
     "auth_agent", "Authentication & Identity Agent", "security"),
    (["database", "db", "postgres", "mysql", "mongo", "redis", "store", "persist"],
     "persistence_agent", "Data Persistence Layer", "storage"),
    (["cache", "redis", "memcache", "ttl"],
     "cache_agent", "Cache / State Store", "storage"),
    (["notify", "alert", "email", "sms", "webhook", "push"],
     "notification_agent", "Notification & Alerting Agent", "output"),
    (["log", "monitor", "metric", "observ", "trace", "grafana", "prometheus"],
     "observability_agent", "Observability & Monitoring Agent", "infra"),
    (["api", "rest", "graphql", "grpc", "gateway", "endpoint", "http"],
     "api_gateway_agent", "API Gateway / Controller", "interface"),
    (["nlp", "llm", "gpt", "claude", "gemma", "ai", "language model", "chatbot"],
     "llm_orchestrator_agent", "LLM Orchestration Agent", "ai"),
    (["scheduler", "cron", "queue", "task", "worker", "job", "celery"],
     "task_scheduler_agent", "Task Scheduler / Queue Worker", "infra"),
    (["dashboard", "ui", "frontend", "react", "vue", "next", "chart", "visual"],
     "dashboard_agent", "Dashboard / UI Agent", "frontend"),
    (["config", "env", "secret", "vault", "setting"],
     "config_agent", "Configuration Manager", "infra"),
    (["crypto", "blockchain", "defi", "wallet", "chain", "token", "nft"],
     "blockchain_agent", "Blockchain / DeFi Interface Agent", "blockchain"),
    (["test", "qa", "quality", "assert", "spec", "pytest", "jest"],
     "testing_agent", "QA & Testing Agent", "quality"),
    (["deploy", "ci", "cd", "docker", "k8s", "kubernetes", "infra", "devops"],
     "devops_agent", "CI/CD & Deployment Agent", "infra"),
]

_CORE_ORCHESTRATOR = {
    "id": "orchestrator_agent",
    "role": "System Orchestrator",
    "description": "Central coordinator: routes signals, manages lifecycle, enforces circuit-breakers.",
    "type": "orchestrator",
}

_EDGE_RULES: list[tuple[str, str, str, str]] = [
    ("data_ingestion_agent",   "market_data_agent",    "push raw ticks",          "WebSocket / SSE"),
    ("market_data_agent",      "signal_detection_agent","normalised OHLCV feed",  "internal queue"),
    ("signal_detection_agent", "orchestrator_agent",   "opportunity signal",       "async event"),
    ("orchestrator_agent",     "strategy_agent",       "evaluate signal",          "RPC / function call"),
    ("strategy_agent",         "risk_management_agent","proposed order",           "sync call"),
    ("risk_management_agent",  "execution_agent",      "approved order",           "command message"),
    ("execution_agent",        "persistence_agent",    "trade record",             "SQL / NoSQL write"),
    ("execution_agent",        "portfolio_agent",      "position update",          "event bus"),
    ("execution_agent",        "notification_agent",   "fill notification",        "pub/sub"),
    ("portfolio_agent",        "observability_agent",  "PnL metrics",              "metrics push"),
    ("orchestrator_agent",     "observability_agent",  "system health metrics",    "metrics push"),
    ("orchestrator_agent",     "api_gateway_agent",    "expose endpoints",         "HTTP/REST"),
    ("api_gateway_agent",      "auth_agent",           "validate token",           "JWT validation"),
    ("api_gateway_agent",      "dashboard_agent",      "serve UI data",            "HTTP/REST"),
    ("cache_agent",            "signal_detection_agent","cached price snapshots",  "read-through"),
    ("persistence_agent",      "cache_agent",          "warm cache on write",      "async callback"),
    ("task_scheduler_agent",   "orchestrator_agent",   "scheduled trigger",        "cron event"),
    ("llm_orchestrator_agent", "orchestrator_agent",   "AI-generated directive",   "tool call / MCP"),
    ("observability_agent",    "notification_agent",   "threshold alert",          "webhook"),
    ("devops_agent",           "orchestrator_agent",   "deployment health",        "health-check poll"),
    ("config_agent",           "orchestrator_agent",   "runtime config",           "env injection"),
    ("blockchain_agent",       "execution_agent",      "on-chain tx result",       "async callback"),
    ("testing_agent",          "orchestrator_agent",   "test report",              "CI event"),
]


def system_design_analyzer(
    prompt: str,
    include_infra: bool = True,
    include_testing: bool = True,
) -> dict:
    """Analyse *prompt* and emit a LeanKG-style sub-agent graph.

    Args:
        prompt:          High-level system description.
        include_infra:   Whether to include infra/devops/config agents (default True).
        include_testing: Whether to include QA/testing agent (default True).

    Returns:
        dict with keys: status, prompt, graph {nodes, edges}, summary,
        agent_count, edge_count.
    """
    if not prompt or not prompt.strip():
        return {"status": "error", "error": "prompt must not be empty"}

    prompt_lower = prompt.lower()
    matched_ids: set[str] = set()
    nodes: list[dict] = [_CORE_ORCHESTRATOR.copy()]
    matched_ids.add("orchestrator_agent")

    for keywords, agent_id, role, agent_type in _KEYWORD_ARCHETYPES:
        if not include_infra and agent_type == "infra":
            continue
        if not include_testing and agent_type == "quality":
            continue
        if any(kw in prompt_lower for kw in keywords):
            if agent_id not in matched_ids:
                nodes.append({
                    "id": agent_id,
                    "role": role,
                    "description": _build_description(role, prompt),
                    "type": agent_type,
                })
                matched_ids.add(agent_id)

    if len(nodes) == 1:
        nodes.append({
            "id": "planner_agent",
            "role": "Domain Planner",
            "description": f"Breaks down '{prompt.strip()}' into actionable sub-tasks.",
            "type": "planning",
        })
        matched_ids.add("planner_agent")

    edges: list[dict] = []
    seen_edges: set[tuple] = set()

    for from_id, to_id, interaction, protocol in _EDGE_RULES:
        if from_id in matched_ids and to_id in matched_ids:
            key = (from_id, to_id)
            if key not in seen_edges:
                edges.append({
                    "from": from_id,
                    "to": to_id,
                    "interaction": interaction,
                    "protocol": protocol,
                })
                seen_edges.add(key)

    for node in nodes:
        nid = node["id"]
        if nid == "orchestrator_agent":
            continue
        has_edge = any(e["from"] == nid or e["to"] == nid for e in edges)
        if not has_edge:
            edges.append({
                "from": nid,
                "to": "orchestrator_agent",
                "interaction": "reports status / receives directives",
                "protocol": "internal event bus",
            })

    summary = _build_summary(prompt, nodes, edges)

    return {
        "status": "ok",
        "prompt": prompt,
        "graph": {"nodes": nodes, "edges": edges},
        "summary": summary,
        "agent_count": len(nodes),
        "edge_count": len(edges),
    }


def _build_description(role: str, prompt: str) -> str:
    topic = re.sub(r"build\s+a?\s*", "", prompt.strip(), flags=re.IGNORECASE)[:60]
    return f"{role} — handles {topic.strip('.') or 'system'} concerns."


def _build_summary(prompt: str, nodes: list[dict], edges: list[dict]) -> str:
    types = sorted({n["type"] for n in nodes})
    return (
        f'System design for "{prompt.strip()}" requires {len(nodes)} agents '
        f"across {len(types)} layers ({', '.join(types)}) connected by "
        f"{len(edges)} directed interactions."
    )
