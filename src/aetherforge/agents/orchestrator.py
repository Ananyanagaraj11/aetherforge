from __future__ import annotations

import json
import re
import uuid
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from aetherforge.rag.hybrid import ScoredChunk
from aetherforge.rag.pipeline import RagPipeline
from aetherforge.storage.models import AuditEvent, HitlReview, WorkflowRun

HIGH_RISK = (
    "prod", "production", "outage", "failover", "unlock", "write-back", "rollback",
    "sev-1", "sev1", "promote", "schema", "bms",
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _severity(query: str, hits: list[ScoredChunk]) -> str:
    text = (query + " " + " ".join(h.text for h in hits[:2])).lower()
    if any(w in text for w in ("sev-1", "life-safety", "outage", "unlock")):
        return "Sev-1"
    if any(w in text for w in ("lag", "storm", "rollback", "failover", "drift")):
        return "Sev-2"
    return "Sev-3"


def _requires_hitl(query: str, severity: str) -> bool:
    q = query.lower()
    if severity in {"Sev-1", "Sev-2"}:
        return True
    return any(w in q for w in HIGH_RISK)


def _ticket_type(query: str, severity: str) -> str:
    q = query.lower()
    if "change" in q or "promote" in q or "schema" in q or "calibrat" in q:
        return "Change"
    if severity in {"Sev-1", "Sev-2"} or "incident" in q or "outage" in q:
        return "Incident"
    return "Task"


def _assignee(hits: list[ScoredChunk]) -> str:
    owners = {
        "Facilities": "Priya Shah",
        "Platform": "Marcus Lee",
        "Data": "Marcus Lee",
        "Governance": "Release Board",
        "Security": "Jordan Adeyemi",
        "Operations": "Elena Voss",
    }
    if not hits:
        return "Unassigned"
    return owners.get(hits[0].category, "Unassigned")


def _jenkins_job(ticket_type: str, hits: list[ScoredChunk]) -> str:
    primary = ((hits[0].doc_id + " " + hits[0].text) if hits else "").lower()
    if "sop-k8s" in primary or "rollback" in primary:
        return "aetherforge-deploy-prod"
    if "sop-pg" in primary or "replica lag" in primary:
        return "aetherforge-db-failover-verify"
    if "sop-bms" in primary or "alarm storm" in primary:
        return "bms-config-audit"
    if "sop-sec" in primary or "access-control" in primary:
        return "access-control-smoke"
    if ticket_type == "Change":
        return "aetherforge-deploy-staging"
    return "aetherforge-ci"


def synthesize(query: str, hits: list[ScoredChunk]) -> dict:
    if not hits:
        return {
            "answer": (
                "Insufficient grounded evidence in the knowledge base. "
                "AetherForge will not invent a procedure. Draft a research ticket so a human can add the runbook."
            ),
            "confidence": 0.18,
            "grounded": False,
        }
    top = hits[0]
    supporting = hits[1:3]
    severity = _severity(query, hits)
    lines = [
        f"Grounded answer from {top.doc_id} ({top.title}). Suggested severity: {severity}.",
        "",
        top.text,
    ]
    if supporting:
        lines.append("")
        lines.append("Supporting evidence:")
        for h in supporting:
            lines.append(f"- {h.doc_id}: {h.text[:220]}")
    lines.append("")
    lines.append(
        "Citations are mandatory. No step above was generated without a retrieved chunk. "
        "Write-backs, failovers, and production deploys still require HITL."
    )
    confidence = min(0.96, 0.55 + top.score * 4 + 0.08 * len(hits))
    return {
        "answer": "\n".join(lines),
        "confidence": round(confidence, 3),
        "grounded": True,
        "severity": severity,
    }


class AgentGraph:
    """Retriever → Analyst → Planner → Reviewer (HITL). LangGraph-style state machine."""

    def __init__(self, rag: RagPipeline):
        self.rag = rag

    def run(self, session: Session, query: str) -> dict:
        run_id = f"run-{uuid.uuid4().hex[:10]}"
        steps: list[dict] = []

        steps.append({"agent": "retriever", "status": "running", "at": _now(), "detail": "Hybrid BM25 + TF-IDF + RRF"})
        hits = self.rag.retrieve(query, k=5)
        steps[-1]["status"] = "done"
        steps[-1]["hits"] = [h.chunk_id for h in hits]

        steps.append({"agent": "analyst", "status": "running", "at": _now(), "detail": "Cite-or-abstain synthesis"})
        synthesis = synthesize(query, hits)
        steps[-1]["status"] = "done"
        steps[-1]["confidence"] = synthesis["confidence"]

        severity = synthesis.get("severity") or _severity(query, hits)
        ticket_type = _ticket_type(query, severity)
        hitl = _requires_hitl(query, severity) or not synthesis["grounded"]
        ticket = {
            "summary": _summary(query, hits),
            "description": synthesis["answer"][:1200],
            "issue_type": ticket_type,
            "priority": "High" if severity in {"Sev-1", "Sev-2"} else "Medium",
            "assignee": _assignee(hits),
            "labels": ",".join(sorted({h.category.lower() for h in hits[:3]} | {"aetherforge"})),
            "jenkins_job": _jenkins_job(ticket_type, hits),
            "severity": severity,
        }

        steps.append(
            {
                "agent": "planner",
                "status": "done",
                "at": _now(),
                "detail": f"Drafted {ticket_type} + Jenkins {ticket['jenkins_job']}",
            }
        )

        reviewer_status = "awaiting_human" if hitl else "auto_approved"
        steps.append(
            {
                "agent": "reviewer",
                "status": reviewer_status,
                "at": _now(),
                "detail": "HITL gate before Jira write / Jenkins promote" if hitl else "Low-risk path",
            }
        )

        citations = [
            {
                "chunk_id": h.chunk_id,
                "doc_id": h.doc_id,
                "title": h.title,
                "category": h.category,
                "score": h.score,
                "bm25": h.bm25,
                "vector": h.vector,
                "excerpt": h.text[:280],
            }
            for h in hits
        ]
        status = "awaiting_human" if hitl else "completed"
        run = WorkflowRun(
            run_id=run_id,
            query=query,
            status=status,
            confidence=synthesis["confidence"],
            answer=synthesis["answer"],
            citations_json=json.dumps(citations),
            steps_json=json.dumps(steps),
            proposed_ticket_json=json.dumps(ticket),
            requires_hitl="true" if hitl else "false",
        )
        session.add(run)
        session.add(
            AuditEvent(
                event_id=f"evt-{uuid.uuid4().hex[:10]}",
                run_id=run_id,
                actor="retriever+analyst+planner",
                event_type="workflow.started",
                detail=query[:400],
            )
        )
        review_id = None
        if hitl:
            review_id = f"hitl-{uuid.uuid4().hex[:10]}"
            session.add(
                HitlReview(
                    review_id=review_id,
                    run_id=run_id,
                    action="create_jira_and_jenkins",
                    payload_json=json.dumps(ticket),
                    status="pending",
                )
            )
        session.commit()
        return serialize_run(run, review_id=review_id)


def _summary(query: str, hits: list[ScoredChunk]) -> str:
    clean = re.sub(r"\s+", " ", query).strip().rstrip("?")
    if hits:
        return f"{clean[:90]} — {hits[0].doc_id}"
    return clean[:120] or "Knowledge gap — add runbook"


def serialize_run(run: WorkflowRun, review_id: str | None = None) -> dict:
    return {
        "run_id": run.run_id,
        "query": run.query,
        "status": run.status,
        "confidence": run.confidence,
        "answer": run.answer,
        "citations": json.loads(run.citations_json or "[]"),
        "steps": json.loads(run.steps_json or "[]"),
        "proposed_ticket": json.loads(run.proposed_ticket_json or "{}"),
        "requires_hitl": run.requires_hitl == "true",
        "review_id": review_id,
        "created_at": run.created_at.isoformat() if run.created_at else None,
    }
