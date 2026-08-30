from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy import select

from aetherforge import __version__
from aetherforge.agents.orchestrator import AgentGraph, serialize_run
from aetherforge.integrations import jira as jira_svc
from aetherforge.observability.metrics import ASKS, GROUNDED, HITL_RESOLVED, OPEN_ISSUES, metrics_response
from aetherforge.rag.pipeline import RagPipeline
from aetherforge.rag.seed_docs import DOCUMENTS, SEED_ISSUES, SEED_JOBS, chunk_documents
from aetherforge.storage.database import get_session, init_db, seed_if_needed
from aetherforge.storage.models import AuditEvent, HitlReview, JenkinsJob, JiraIssue, KnowledgeDocument, WorkflowRun

ROOT = Path(__file__).resolve().parents[3]
DASHBOARD = ROOT / "dashboard"

rag = RagPipeline()
graph = AgentGraph(rag)


def bootstrap() -> None:
    init_db()
    session = get_session()
    try:
        seed_if_needed(session, DOCUMENTS, chunk_documents(), SEED_ISSUES, SEED_JOBS)
        rag.load(session)
        OPEN_ISSUES.set(jira_svc.count_open(session))
    finally:
        session.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    bootstrap()
    yield


app = FastAPI(
    title="AetherForge",
    description="Industrial knowledge OS — hybrid RAG, agentic workflows, Jira, Jenkins, PostgreSQL",
    version=__version__,
    lifespan=lifespan,
)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

if DASHBOARD.exists():
    app.mount("/assets", StaticFiles(directory=DASHBOARD), name="assets")

bootstrap()


class AskRequest(BaseModel):
    query: str = Field(min_length=3, max_length=800)


class HitlRequest(BaseModel):
    reviewer: str = "human"
    feedback: str = ""


class IssueCreate(BaseModel):
    summary: str
    description: str = ""
    issue_type: str = "Task"
    priority: str = "Medium"
    assignee: str = "Unassigned"
    labels: str = "manual"
    jenkins_job: str = "aetherforge-ci"


@app.get("/")
async def index() -> FileResponse:
    page = DASHBOARD / "index.html"
    if not page.exists():
        raise HTTPException(status_code=404, detail="Dashboard missing")
    return FileResponse(page)


@app.get("/health")
async def health() -> dict:
    session = get_session()
    try:
        docs = session.scalar(select(KnowledgeDocument.id).limit(1)) is not None
        return {
            "status": "ok",
            "service": "aetherforge",
            "version": __version__,
            "knowledge_ready": docs,
            "stack": ["FastAPI", "PostgreSQL", "hybrid-RAG", "Jira", "Jenkins", "Kubernetes"],
        }
    finally:
        session.close()


@app.get("/metrics")
async def metrics() -> Response:
    body, content_type = metrics_response()
    return Response(content=body, media_type=content_type)


@app.get("/api/overview")
async def overview() -> dict:
    session = get_session()
    try:
        docs = session.scalars(select(KnowledgeDocument)).all()
        runs = session.scalars(select(WorkflowRun)).all()
        pending = session.scalars(select(HitlReview).where(HitlReview.status == "pending")).all()
        issues = session.scalars(select(JiraIssue)).all()
        jobs = session.scalars(select(JenkinsJob)).all()
        return {
            "documents": len(docs),
            "runs": len(runs),
            "pending_hitl": len(pending),
            "jira_open": sum(1 for i in issues if i.status != "Done"),
            "jira_total": len(issues),
            "jenkins_jobs": len(jobs),
            "categories": sorted({d.category for d in docs}),
        }
    finally:
        session.close()


@app.get("/api/knowledge")
async def knowledge() -> list[dict]:
    session = get_session()
    try:
        docs = session.scalars(select(KnowledgeDocument)).all()
        return [
            {
                "doc_id": d.doc_id,
                "title": d.title,
                "category": d.category,
                "owner": d.owner,
                "excerpt": d.body[:240],
            }
            for d in docs
        ]
    finally:
        session.close()


@app.get("/api/knowledge/search")
async def knowledge_search(q: str) -> dict:
    hits = rag.retrieve(q, k=6)
    return {
        "query": q,
        "hits": [
            {
                "chunk_id": h.chunk_id,
                "doc_id": h.doc_id,
                "title": h.title,
                "category": h.category,
                "score": h.score,
                "bm25": h.bm25,
                "vector": h.vector,
                "excerpt": h.text,
            }
            for h in hits
        ],
    }


@app.post("/api/ask")
async def ask(body: AskRequest) -> dict:
    ASKS.inc()
    session = get_session()
    try:
        result = graph.run(session, body.query.strip())
        grounded = "true" if result["citations"] else "false"
        GROUNDED.labels(grounded=grounded).inc()
        OPEN_ISSUES.set(jira_svc.count_open(session))
        return result
    finally:
        session.close()


@app.get("/api/runs")
async def list_runs() -> list[dict]:
    session = get_session()
    try:
        rows = session.scalars(select(WorkflowRun).order_by(WorkflowRun.id.desc())).all()
        return [serialize_run(r) for r in rows[:40]]
    finally:
        session.close()


@app.get("/api/runs/{run_id}")
async def get_run(run_id: str) -> dict:
    session = get_session()
    try:
        row = session.scalar(select(WorkflowRun).where(WorkflowRun.run_id == run_id))
        if not row:
            raise HTTPException(status_code=404, detail="Run not found")
        review = session.scalar(select(HitlReview).where(HitlReview.run_id == run_id))
        return serialize_run(row, review_id=review.review_id if review else None)
    finally:
        session.close()


@app.get("/api/jira/issues")
async def jira_issues() -> dict:
    session = get_session()
    try:
        return {"project": "AF", "columns": jira_svc.board(session)}
    finally:
        session.close()


@app.post("/api/jira/issues")
async def jira_create(body: IssueCreate) -> dict:
    session = get_session()
    try:
        issue = jira_svc.create_issue(session, body.model_dump())
        session.commit()
        OPEN_ISSUES.set(jira_svc.count_open(session))
        return jira_svc.issue_to_dict(issue)
    finally:
        session.close()


@app.get("/api/hitl")
async def hitl_queue() -> list[dict]:
    session = get_session()
    try:
        return jira_svc.pending_reviews(session)
    finally:
        session.close()


@app.post("/api/hitl/{review_id}/approve")
async def hitl_approve(review_id: str, body: HitlRequest) -> dict:
    session = get_session()
    try:
        result = jira_svc.resolve_hitl(session, review_id, True, body.reviewer, body.feedback)
        HITL_RESOLVED.labels(decision="approved").inc()
        OPEN_ISSUES.set(jira_svc.count_open(session))
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    finally:
        session.close()


@app.post("/api/hitl/{review_id}/reject")
async def hitl_reject(review_id: str, body: HitlRequest) -> dict:
    session = get_session()
    try:
        result = jira_svc.resolve_hitl(session, review_id, False, body.reviewer, body.feedback)
        HITL_RESOLVED.labels(decision="rejected").inc()
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from None
    finally:
        session.close()


@app.get("/api/jenkins/jobs")
async def jenkins_jobs() -> list[dict]:
    session = get_session()
    try:
        rows = session.scalars(select(JenkinsJob).order_by(JenkinsJob.job_name)).all()
        return [
            {
                "job_name": r.job_name,
                "last_build": r.last_build,
                "status": r.status,
                "duration_ms": r.duration_ms,
                "stage": r.stage,
                "linked_issue": r.linked_issue,
            }
            for r in rows
        ]
    finally:
        session.close()


@app.get("/api/audit")
async def audit() -> list[dict]:
    session = get_session()
    try:
        rows = session.scalars(select(AuditEvent).order_by(AuditEvent.id.desc())).all()
        return [
            {
                "event_id": r.event_id,
                "run_id": r.run_id,
                "actor": r.actor,
                "event_type": r.event_type,
                "detail": r.detail,
                "created_at": r.created_at.isoformat() if r.created_at else None,
            }
            for r in rows[:50]
        ]
    finally:
        session.close()


@app.get("/api/ops")
async def ops() -> dict:
    session = get_session()
    try:
        return {
            "kubernetes": {
                "namespace": "aetherforge",
                "deployment": "aetherforge-api",
                "replicas": 2,
                "hpa": "2-8",
                "ready": True,
            },
            "postgres": {"engine": "postgresql", "role": "state + knowledge + audit", "ready": True},
            "jenkins": [r.job_name for r in session.scalars(select(JenkinsJob)).all()],
            "jira_project": "AF",
        }
    finally:
        session.close()
