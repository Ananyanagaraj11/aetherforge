from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, generate_latest

ASKS = Counter("aetherforge_asks_total", "Ask requests")
HITL_RESOLVED = Counter("aetherforge_hitl_resolved_total", "HITL resolutions", ["decision"])
GROUNDED = Counter("aetherforge_grounded_answers_total", "Grounded vs abstain", ["grounded"])
OPEN_ISSUES = Gauge("aetherforge_open_jira_issues", "Non-done Jira issues")


def metrics_response() -> tuple[bytes, str]:
    return generate_latest(), CONTENT_TYPE_LATEST
