from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    doc_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64), index=True)
    body: Mapped[str] = mapped_column(Text)
    owner: Mapped[str] = mapped_column(String(128), default="platform")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    chunk_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    doc_id: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(256))
    category: Mapped[str] = mapped_column(String(64), index=True)
    text: Mapped[str] = mapped_column(Text)
    token_count: Mapped[int] = mapped_column(Integer, default=0)


class WorkflowRun(Base):
    __tablename__ = "workflow_runs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    run_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    query: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    answer: Mapped[str] = mapped_column(Text, default="")
    citations_json: Mapped[str] = mapped_column(Text, default="[]")
    steps_json: Mapped[str] = mapped_column(Text, default="[]")
    proposed_ticket_json: Mapped[str] = mapped_column(Text, default="{}")
    requires_hitl: Mapped[str] = mapped_column(String(8), default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JiraIssue(Base):
    __tablename__ = "jira_issues"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    summary: Mapped[str] = mapped_column(String(512))
    description: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(32), index=True)
    priority: Mapped[str] = mapped_column(String(16), default="Medium")
    issue_type: Mapped[str] = mapped_column(String(32), default="Task")
    assignee: Mapped[str] = mapped_column(String(128), default="Unassigned")
    labels: Mapped[str] = mapped_column(String(256), default="")
    linked_run_id: Mapped[str] = mapped_column(String(64), default="")
    jenkins_job: Mapped[str] = mapped_column(String(128), default="")
    jenkins_status: Mapped[str] = mapped_column(String(32), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class HitlReview(Base):
    __tablename__ = "hitl_reviews"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    review_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    run_id: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    status: Mapped[str] = mapped_column(String(32), index=True, default="pending")
    reviewer: Mapped[str] = mapped_column(String(128), default="")
    feedback: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class AuditEvent(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    event_id: Mapped[str] = mapped_column(String(64), unique=True)
    run_id: Mapped[str] = mapped_column(String(64), default="", index=True)
    actor: Mapped[str] = mapped_column(String(64), default="system")
    event_type: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())


class JenkinsJob(Base):
    __tablename__ = "jenkins_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    job_name: Mapped[str] = mapped_column(String(128), unique=True)
    last_build: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="SUCCESS")
    duration_ms: Mapped[int] = mapped_column(Integer, default=0)
    stage: Mapped[str] = mapped_column(String(64), default="deploy")
    linked_issue: Mapped[str] = mapped_column(String(32), default="")
    updated_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())
