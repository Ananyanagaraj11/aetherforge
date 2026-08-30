# AetherForge architecture

AetherForge is a **knowledge operating system**: retrieve grounded procedures, run a four-agent graph, pause for human approval, then write Jira and queue Jenkins.

```
Ask ──► Retriever (BM25 + TF-IDF + RRF + rerank)
      ──► Analyst (cite-or-abstain)
      ──► Planner (Jira draft + Jenkins job)
      ──► Reviewer (HITL)
            ├── Approve ──► Jira AF-* + Jenkins queue
            └── Reject  ──► audit only
```

## Persistence (PostgreSQL)

| Table | Role |
|-------|------|
| `knowledge_documents` / `knowledge_chunks` | Runbook corpus |
| `workflow_runs` | Agent graph state |
| `hitl_reviews` | Human gates |
| `jira_issues` | Project AF board |
| `jenkins_jobs` | Pipeline projection |
| `audit_events` | Append-only trail |

SQLite is the demo default. `DATABASE_URL` switches to PostgreSQL in Docker Compose and Kubernetes.

## Control plane

FastAPI serves the industrial console and `/api/*`. Prometheus scrapes `/metrics`. Kubernetes readiness uses `/health`.

## Delivery

- **Jenkinsfile** — lint → pytest → image → staging apply → HITL promote to prod
- **GitHub Actions** — same lint/test gate on every PR
- **Kubernetes** — Deployment (2 replicas), Service, HPA 2–8, Ingress, PostgreSQL StatefulSet

Production RAG at a company would swap the local hybrid index for LangGraph + Pinecone/hybrid search and a real Jira/Jenkins client. The adapters and state machine are already shaped for that.
