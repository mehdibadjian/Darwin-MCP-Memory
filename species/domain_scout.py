"""domain_scout — Domain Knowledge Acquisition Agent.

Give Darwin a domain name and it will:
1. Look up a curated skill map for that domain
2. Compare against the current species registry
3. Enqueue evolve tasks for every missing skill
4. Return a manifest of what was queued vs already present

Usage via MCP tool invocation:
    domain_scout({"domain": "docker"})
    domain_scout({"domain": "kubernetes", "priority": 2})

Supported domains (case-insensitive):
    docker, kubernetes, git, security, database, python,
    testing, cloud, nestjs, react, fastapi, monitoring
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Domain knowledge map — each entry is a skill to evolve
# ---------------------------------------------------------------------------

_DOMAIN_SKILLS: Dict[str, List[Dict[str, Any]]] = {
    "docker": [
        {"name": "docker_build_push",      "description": "Build a Docker image and push to a registry (Docker Hub or GHCR). Accepts image name, tag, and registry credentials.", "requirements": []},
        {"name": "docker_compose_up",      "description": "Bring up a docker-compose stack. Parse docker-compose.yml, validate services, run docker compose up -d.", "requirements": []},
        {"name": "docker_container_logs",  "description": "Tail or dump logs from a running container by name or ID.", "requirements": []},
        {"name": "docker_cleanup",         "description": "Prune stopped containers, dangling images, unused volumes and networks to reclaim disk space.", "requirements": []},
        {"name": "docker_health_check",    "description": "Inspect running containers and return a health report: status, uptime, port bindings, restart count.", "requirements": []},
        {"name": "docker_env_injector",    "description": "Merge .env files into docker run / docker-compose environment blocks safely.", "requirements": []},
    ],
    "kubernetes": [
        {"name": "k8s_apply_manifest",     "description": "Apply a Kubernetes YAML manifest to a cluster via kubectl apply. Supports dry-run mode.", "requirements": []},
        {"name": "k8s_pod_status",         "description": "Return status, restarts and recent events for all pods in a namespace.", "requirements": []},
        {"name": "k8s_rollout_restart",    "description": "Trigger a rolling restart of a Kubernetes deployment.", "requirements": []},
        {"name": "k8s_logs_aggregator",    "description": "Aggregate logs from all pods in a deployment into a single stream.", "requirements": []},
        {"name": "k8s_secret_manager",     "description": "Create, update and rotate Kubernetes secrets without exposing values in shell history.", "requirements": []},
    ],
    "git": [
        {"name": "git_branch_cleanup",     "description": "Delete merged local and remote branches older than N days.", "requirements": []},
        {"name": "git_pr_summary",         "description": "Summarise all open pull requests in a repo: author, age, review status, CI status.", "requirements": []},
        {"name": "git_commit_linter",      "description": "Validate commit messages against Conventional Commits spec and suggest fixes.", "requirements": []},
        {"name": "git_diff_explainer",     "description": "Parse a git diff and return a human-readable explanation of each changed file.", "requirements": []},
        {"name": "git_tag_release",        "description": "Create a semver git tag, generate a CHANGELOG entry, and push to remote.", "requirements": []},
    ],
    "security": [
        {"name": "secret_scanner",         "description": "Scan a codebase for accidentally committed secrets, API keys and passwords using regex patterns.", "requirements": []},
        {"name": "dependency_audit",       "description": "Run pip-audit / npm audit on a project and return a prioritised vulnerability report.", "requirements": ["pip-audit"]},
        {"name": "ssl_cert_checker",       "description": "Check SSL certificate expiry dates for a list of domains and alert if < 30 days remain.", "requirements": []},
        {"name": "env_file_validator",     "description": "Validate .env files: detect missing required keys, empty values, and insecure defaults.", "requirements": []},
        {"name": "port_scanner",           "description": "Scan a host for open ports and services using Python socket probing.", "requirements": []},
    ],
    "database": [
        {"name": "sql_query_explainer",    "description": "Parse a SQL query and return an explanation of each clause, estimated cost, and optimisation hints.", "requirements": []},
        {"name": "db_migration_runner",    "description": "Apply pending Alembic / Flyway migrations and return a before/after schema diff.", "requirements": []},
        {"name": "db_backup_validator",    "description": "Verify a database backup file is intact: checksum, row count spot-checks.", "requirements": []},
        {"name": "db_connection_pooler",   "description": "Benchmark and tune database connection pool settings for a given load profile.", "requirements": []},
    ],
    "python": [
        {"name": "python_linter",          "description": "Run ruff + mypy on a Python file or directory and return structured diagnostics.", "requirements": ["ruff", "mypy"]},
        {"name": "python_test_generator",  "description": "Analyse a Python module and auto-generate pytest test stubs for all public functions.", "requirements": []},
        {"name": "python_deps_updater",    "description": "Check outdated pip dependencies and generate an updated requirements.txt.", "requirements": []},
        {"name": "python_profiler",        "description": "Profile a Python script with cProfile and return the top-20 slowest functions.", "requirements": []},
        {"name": "python_docstring_gen",   "description": "Generate Google-style docstrings for undocumented Python functions in a file.", "requirements": []},
    ],
    "testing": [
        {"name": "test_coverage_report",   "description": "Run pytest with coverage and return a per-module coverage summary.", "requirements": ["pytest-cov"]},
        {"name": "flaky_test_detector",    "description": "Run a test suite N times and identify tests that pass/fail non-deterministically.", "requirements": []},
        {"name": "test_data_factory",      "description": "Generate realistic fake test data (names, emails, dates, UUIDs) for a given schema.", "requirements": ["faker"]},
        {"name": "api_contract_tester",    "description": "Validate a running API against its OpenAPI spec: check all endpoints, schemas and status codes.", "requirements": []},
    ],
    "monitoring": [
        {"name": "log_anomaly_detector",   "description": "Parse application logs and detect error spikes, unusual patterns and P99 latency regressions.", "requirements": []},
        {"name": "uptime_monitor",         "description": "HTTP health-check a list of URLs on a schedule and alert on failures.", "requirements": []},
        {"name": "metrics_exporter",       "description": "Collect CPU, RAM, disk and network metrics and export them in Prometheus format.", "requirements": ["psutil"]},
        {"name": "alert_router",           "description": "Route alerts from multiple sources (logs, metrics, webhooks) to Slack or email.", "requirements": []},
    ],
    "cloud": [
        {"name": "droplet_provisioner",    "description": "Provision a DigitalOcean Droplet via API: create, configure SSH, install deps.", "requirements": []},
        {"name": "s3_sync",                "description": "Sync a local directory to an S3-compatible bucket (AWS S3, DO Spaces, Cloudflare R2).", "requirements": ["boto3"]},
        {"name": "dns_manager",            "description": "Create, update and delete DNS records across DigitalOcean and Cloudflare via their APIs.", "requirements": []},
        {"name": "cloud_cost_estimator",   "description": "Estimate monthly cloud costs for a given infrastructure spec.", "requirements": []},
    ],
    "nestjs": [
        {"name": "nestjs_module_scaffold", "description": "Scaffold a NestJS module with controller, service, DTO and spec files following best practices.", "requirements": []},
        {"name": "nestjs_guard_generator", "description": "Generate a JWT AuthGuard with role-based access control for a NestJS app.", "requirements": []},
        {"name": "nestjs_interceptor",     "description": "Generate a NestJS logging/transform interceptor with request tracing.", "requirements": []},
        {"name": "nestjs_pipe_validator",  "description": "Generate a ValidationPipe setup with class-validator decorators for a DTO.", "requirements": []},
    ],
    "react": [
        {"name": "react_component_gen",    "description": "Generate a typed React functional component with props interface and Storybook story.", "requirements": []},
        {"name": "react_hook_extractor",   "description": "Extract repeated logic from React components into a custom hook.", "requirements": []},
        {"name": "react_perf_analyzer",    "description": "Detect unnecessary re-renders and memo opportunities in a React component tree.", "requirements": []},
    ],
    "dotnet": [
        {"name": "dotnet_project_scaffolder",  "description": "Scaffold a .NET 8 Web API project with controllers, services, EF Core DbContext, and xUnit test project.", "requirements": []},
        {"name": "csharp_code_analyzer",       "description": "Analyse C# files for code smells, nullable warnings, and Roslyn diagnostics. Return structured report.", "requirements": []},
        {"name": "nuget_audit",                "description": "Check NuGet packages for known vulnerabilities and outdated versions. Return prioritised upgrade list.", "requirements": []},
        {"name": "ef_migration_runner",        "description": "Generate and apply Entity Framework Core migrations. Detect schema drift between model and database.", "requirements": []},
        {"name": "csharp_test_generator",      "description": "Generate xUnit test stubs for all public methods in a C# class, including Moq setup for dependencies.", "requirements": []},
        {"name": "dotnet_publish_pipeline",    "description": "Build, test and publish a .NET project to a target runtime (linux-x64, win-x64). Return artefact path.", "requirements": []},
        {"name": "csharp_dto_mapper",          "description": "Generate AutoMapper profiles and DTO classes from EF Core entity models.", "requirements": []},
    ],
    "business_development": [
        {"name": "proposal_generator",         "description": "Generate a structured business proposal document from a client brief: exec summary, scope, timeline, pricing.", "requirements": []},
        {"name": "crm_lead_tracker",           "description": "Parse CRM export (CSV/JSON) and return leads by stage, last contact date, and next action due.", "requirements": []},
        {"name": "competitor_analyzer",        "description": "Given a competitor name and domain, summarise their product offering, pricing, and positioning gaps.", "requirements": []},
        {"name": "meeting_action_extractor",   "description": "Parse meeting notes or transcript and extract structured action items with owner, due date, and priority.", "requirements": []},
        {"name": "pipeline_forecaster",        "description": "Forecast revenue from a sales pipeline CSV using weighted stage probabilities and close date distributions.", "requirements": []},
        {"name": "outreach_email_writer",      "description": "Generate personalised BD outreach emails from a contact profile and campaign brief.", "requirements": []},
        {"name": "win_loss_analyser",          "description": "Analyse won/lost deals data to surface patterns: deal size, industry, competitor, sales cycle length.", "requirements": []},
    ],
    "delivery_lead": [
        {"name": "sprint_health_checker",      "description": "Analyse sprint velocity, burndown data and blockers. Flag at-risk stories and suggest corrective actions.", "requirements": []},
        {"name": "stakeholder_report_writer",  "description": "Generate a weekly project status report: RAG status, milestones, risks, decisions needed.", "requirements": []},
        {"name": "risk_register_manager",      "description": "Maintain a project risk register: add risks, update likelihood/impact scores, generate mitigation plans.", "requirements": []},
        {"name": "retrospective_summariser",   "description": "Parse retrospective board data (what went well/badly/actions) and produce a formatted summary with trends.", "requirements": []},
        {"name": "dependency_tracker",         "description": "Track cross-team dependencies: owner, blocked-by, due date, escalation path. Output critical-path view.", "requirements": []},
        {"name": "capacity_planner",           "description": "Calculate team capacity for a sprint given leave, ceremonies, and support allocation. Suggest story point budget.", "requirements": []},
        {"name": "change_request_drafter",     "description": "Draft a formal change request document from a change description: impact, effort, risk, rollback plan.", "requirements": []},
    ],
    "fastapi": [
        {"name": "fastapi_router_gen",         "description": "Generate a FastAPI router with CRUD endpoints, Pydantic schemas and pytest integration tests.", "requirements": ["fastapi", "pydantic"]},
        {"name": "fastapi_auth_middleware",     "description": "Generate FastAPI JWT auth middleware with Bearer token validation.", "requirements": []},
        {"name": "fastapi_rate_limiter",        "description": "Add sliding-window rate limiting middleware to a FastAPI app.", "requirements": []},
    ],
}

# Aliases — alternate names map to the same skill list
_DOMAIN_SKILLS["k8s"]                = _DOMAIN_SKILLS["kubernetes"]
_DOMAIN_SKILLS["sec"]                = _DOMAIN_SKILLS["security"]
_DOMAIN_SKILLS["db"]                 = _DOMAIN_SKILLS["database"]
_DOMAIN_SKILLS["csharp"]             = _DOMAIN_SKILLS["dotnet"]
_DOMAIN_SKILLS["net"]                = _DOMAIN_SKILLS["dotnet"]
_DOMAIN_SKILLS["bd"]                 = _DOMAIN_SKILLS["business_development"]
_DOMAIN_SKILLS["biz_dev"]            = _DOMAIN_SKILLS["business_development"]
_DOMAIN_SKILLS["delivery"]           = _DOMAIN_SKILLS["delivery_lead"]
_DOMAIN_SKILLS["pm"]                 = _DOMAIN_SKILLS["delivery_lead"]
_DOMAIN_SKILLS["project_management"] = _DOMAIN_SKILLS["delivery_lead"]
_DOMAIN_SKILLS["devops"]             = _DOMAIN_SKILLS["docker"] + _DOMAIN_SKILLS["kubernetes"] + _DOMAIN_SKILLS["monitoring"]

_REGISTRY_PATH = Path(__file__).resolve().parent.parent / "dna" / "registry.json"
_BACKLOG_PATH  = Path(__file__).resolve().parent.parent / "dna" / "backlog.json"


def _read_registry() -> dict:
    if _REGISTRY_PATH.exists():
        try:
            return json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"skills": {}}


def domain_scout(params: Dict[str, Any]) -> Dict[str, Any]:
    """Scan a domain knowledge map and enqueue missing skills into the backlog.

    Args:
        params:
            domain   (str) — e.g. "docker", "kubernetes", "security"
            priority (int) — backlog priority 1-5 (default 2)
            dry_run  (bool)— if True, return plan without enqueuing

    Returns:
        {
            "status":   "ok" | "error",
            "domain":   str,
            "queued":   [{"name": str, "id": str}, ...],
            "skipped":  [str],   # already in registry
            "unknown":  bool,    # True if domain not in map
            "summary":  str,
        }
    """
    domain   = str(params.get("domain", "")).strip().lower()
    priority = int(params.get("priority", 2))
    dry_run  = bool(params.get("dry_run", False))

    if not domain:
        return {"status": "error", "message": "domain param is required"}

    skill_map = _DOMAIN_SKILLS.get(domain)
    if skill_map is None:
        available = sorted(k for k in _DOMAIN_SKILLS if "_" not in k or k in ("dry_run",))
        return {
            "status":    "error",
            "domain":    domain,
            "unknown":   True,
            "message":   f"Unknown domain '{domain}'. Available: {available}",
        }

    # Check current registry
    registry    = _read_registry()
    known_skills = set(registry.get("skills", {}).keys())

    queued:  list = []
    skipped: list = []

    for skill in skill_map:
        name = skill["name"]
        if name in known_skills:
            skipped.append(name)
            continue

        if not dry_run:
            try:
                from brain.engine.backlog import enqueue as _enqueue
                item_id = _enqueue(
                    task_type="evolve",
                    payload={
                        "name":        name,
                        "description": skill["description"],
                        "requirements": skill.get("requirements", []),
                        "domain":      domain,
                    },
                    priority=priority,
                    backlog_path=_BACKLOG_PATH,
                )
                queued.append({"name": name, "id": item_id})
                logger.info("domain_scout: queued '%s' (domain=%s)", name, domain)
            except Exception as exc:
                logger.error("domain_scout: failed to enqueue '%s': %s", name, exc)
        else:
            queued.append({"name": name, "id": "dry-run"})

    summary = (
        f"Domain '{domain}': {len(queued)} skill(s) queued, "
        f"{len(skipped)} already in registry."
        + (" [DRY RUN]" if dry_run else "")
    )
    logger.info(summary)

    return {
        "status":  "ok",
        "domain":  domain,
        "queued":  queued,
        "skipped": skipped,
        "summary": summary,
    }
