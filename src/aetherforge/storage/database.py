from __future__ import annotations

from pathlib import Path

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from aetherforge.config import settings
from aetherforge.storage.models import Base, JenkinsJob, JiraIssue, KnowledgeChunk, KnowledgeDocument


def _engine_url() -> str:
    url = settings.database_url
    if url.startswith("sqlite"):
        Path("data").mkdir(exist_ok=True)
    return url


connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(_engine_url(), connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    Base.metadata.create_all(engine)


def get_session() -> Session:
    return SessionLocal()


def is_empty(session: Session) -> bool:
    return session.scalar(select(KnowledgeDocument.id).limit(1)) is None


def seed_if_needed(session: Session, documents: list[dict], chunks: list[dict], issues: list[dict], jobs: list[dict]) -> None:
    if not is_empty(session):
        return
    for doc in documents:
        session.add(KnowledgeDocument(**doc))
    for chunk in chunks:
        session.add(KnowledgeChunk(**chunk))
    for issue in issues:
        session.add(JiraIssue(**issue))
    for job in jobs:
        session.add(JenkinsJob(**job))
    session.commit()
