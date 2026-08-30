from __future__ import annotations

import json
import uuid

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from aetherforge.config import settings
from aetherforge.storage.models import AuditEvent, HitlReview, JenkinsJob, JiraIssue, WorkflowRun


def next_key(session: Session) -> str:
    keys = session.scalars(select(JiraIssue.key)).all()
    nums = []
    prefix = settings.jira_project_key
    for key in keys:
        try:
            nums.append(int(key.split("-")[1]))
        except (IndexError, ValueError):
            continue
    return f"{prefix}-{max(nums, default=1000) + 1}"


def create_issue(session: Session, ticket: dict, run_id: str = "") -> JiraIssue:
    issue = JiraIssue(
        key=next_key(session),
        summary=ticket.get("summary", "AetherForge drafted issue")[:512],
        description=ticket.get("description", ""),
        status="To Do",
        priority=ticket.get("priority", "Medium"),
        issue_type=ticket.get("issue_type", "Task"),
        assignee=ticket.get("assignee", "Unassigned"),
        labels=ticket.get("labels", "aetherforge"),
        linked_run_id=run_id,
        jenkins_job=ticket.get("jenkins_job", "aetherforge-ci"),
        jenkins_status="QUEUED",
    )
    session.add(issue)
    session.add(
        AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:10]}",
            run_id=run_id,
            actor="jira-agent",
            event_type="jira.created",
            detail=issue.key,
        )
    )
    return issue


def issue_to_dict(issue: JiraIssue) -> dict:
    return {
        "key": issue.key,
        "summary": issue.summary,
        "description": issue.description,
        "status": issue.status,
        "priority": issue.priority,
        "issue_type": issue.issue_type,
        "assignee": issue.assignee,
        "labels": [part for part in issue.labels.split(",") if part],
        "linked_run_id": issue.linked_run_id,
        "jenkins_job": issue.jenkins_job,
        "jenkins_status": issue.jenkins_status,
        "created_at": issue.created_at.isoformat() if issue.created_at else None,
    }


def queue_jenkins(session: Session, job_name: str, issue_key: str) -> JenkinsJob:
    job = session.scalar(select(JenkinsJob).where(JenkinsJob.job_name == job_name))
    if job is None:
        job = JenkinsJob(job_name=job_name, last_build=1, status="QUEUED", stage="Queued", linked_issue=issue_key)
        session.add(job)
    else:
        job.last_build += 1
        job.status = "QUEUED"
        job.stage = "Queued"
        job.linked_issue = issue_key
    return job


def resolve_hitl(session: Session, review_id: str, approved: bool, reviewer: str, feedback: str) -> dict:
    review = session.scalar(select(HitlReview).where(HitlReview.review_id == review_id))
    if review is None:
        raise ValueError("HITL review not found")
    if review.status != "pending":
        raise ValueError("HITL review already resolved")
    review.reviewer = reviewer or "human"
    review.feedback = feedback
    review.status = "approved" if approved else "rejected"
    run = session.scalar(select(WorkflowRun).where(WorkflowRun.run_id == review.run_id))
    ticket = json.loads(review.payload_json or "{}")
    issue = None
    if approved:
        issue = create_issue(session, ticket, run_id=review.run_id)
        queue_jenkins(session, ticket.get("jenkins_job", "aetherforge-ci"), issue.key)
        if run:
            run.status = "completed"
    elif run:
        run.status = "rejected"
    session.add(
        AuditEvent(
            event_id=f"evt-{uuid.uuid4().hex[:10]}",
            run_id=review.run_id,
            actor=review.reviewer,
            event_type="hitl.approved" if approved else "hitl.rejected",
            detail=feedback or review.status,
        )
    )
    session.commit()
    return {
        "review_id": review.review_id,
        "status": review.status,
        "issue": issue_to_dict(issue) if issue else None,
        "run_id": review.run_id,
    }


def board(session: Session) -> dict[str, list[dict]]:
    issues = session.scalars(select(JiraIssue).order_by(JiraIssue.id.desc())).all()
    columns = {"To Do": [], "In Progress": [], "CAB Review": [], "In Review": [], "Done": []}
    for issue in issues:
        columns.setdefault(issue.status, [])
        columns[issue.status].append(issue_to_dict(issue))
    return columns


def pending_reviews(session: Session) -> list[dict]:
    rows = session.scalars(select(HitlReview).where(HitlReview.status == "pending").order_by(HitlReview.id.desc())).all()
    out = []
    for row in rows:
        out.append(
            {
                "review_id": row.review_id,
                "run_id": row.run_id,
                "action": row.action,
                "status": row.status,
                "ticket": json.loads(row.payload_json or "{}"),
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
        )
    return out


def count_open(session: Session) -> int:
    return session.scalar(select(func.count(JiraIssue.id)).where(JiraIssue.status != "Done")) or 0
