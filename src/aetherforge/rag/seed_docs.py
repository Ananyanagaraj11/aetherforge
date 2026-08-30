"""Seeded industrial runbooks. Fictional procedures for the live demo — not customer IP."""

DOCUMENTS: list[dict] = [
    {
        "doc_id": "SOP-HVAC-014",
        "title": "HVAC Zone Temperature Drift — Diagnosis Runbook",
        "category": "Facilities",
        "owner": "Building Automation",
        "body": (
            "Symptom: a single HVAC zone reports supply-air temperature drift greater than 2.5F from setpoint "
            "for more than 15 minutes. Step 1: confirm sensor health in the BMS — compare zone SAT against the "
            "adjacent zone and the AHU discharge sensor. If the delta exceeds 4F, flag the sensor for calibration "
            "and open a Jira Facilities ticket with priority High. Step 2: inspect damper command versus feedback. "
            "A stuck VAV damper is the most common cause; cycle the actuator and watch feedback for 90 seconds. "
            "Step 3: check chilled-water valve position and differential pressure. If valve is 100% open and SAT "
            "still drifts, escalate to Mechanical Engineering and page the on-call facilities lead. "
            "Do not override the plant sequencer from the AI console. Human-in-the-loop approval is required "
            "before any write-back to the BMS. After correction, attach the trend export to the Jira ticket "
            "and move it to In Review for the facilities supervisor."
        ),
    },
    {
        "doc_id": "SOP-BMS-022",
        "title": "Building Automation Alarm Storm — Containment",
        "category": "Facilities",
        "owner": "Building Automation",
        "body": (
            "An alarm storm is defined as more than 40 new BMS alarms in 5 minutes on a single site. "
            "First action: freeze non-critical alarm paging and keep life-safety and fire circuits active. "
            "Identify the root controller by grouping alarms on device_id. If a single NAE or supervisory "
            "controller accounts for over 70% of alarms, isolate that controller from the write path and "
            "fail over trending to the historian. Open Jira issue type Incident, label bms-storm, assign "
            "the site automation lead. Do not mass-acknowledge alarms. Capture a 15-minute alarm dump to "
            "object storage and attach the path on the ticket. After containment, run the Jenkins job "
            "bms-config-audit against the site before returning the controller to write mode."
        ),
    },
    {
        "doc_id": "SOP-K8S-007",
        "title": "Kubernetes Production Rollback Procedure",
        "category": "Platform",
        "owner": "Platform Engineering",
        "body": (
            "Use this procedure when a production Deployment on the aetherforge namespace fails readiness "
            "or error rate exceeds 2% for 5 minutes. Step 1: confirm the Jenkins deploy job and the Git SHA "
            "on the failing ReplicaSet. Step 2: kubectl rollout undo deployment/aetherforge-api -n aetherforge. "
            "Step 3: watch kubectl rollout status and confirm HPA desired replicas return to the previous "
            "baseline. Step 4: if the undo is blocked by a mutated PodDisruptionBudget, scale the new RS to 0 "
            "and the previous RS to the last known replica count. Step 5: open or update the linked Jira "
            "change ticket to Failed / Rolled Back, attach CloudWatch or Prometheus links, and notify the "
            "on-call in the platform channel. Schema migrations are never rolled back automatically — "
            "HITL approval is required for any down-migration. After stability, file a post-incident review "
            "ticket of type Task with label pir."
        ),
    },
    {
        "doc_id": "SOP-PG-011",
        "title": "PostgreSQL Replica Lag and Failover Playbook",
        "category": "Data",
        "owner": "Data Platform",
        "body": (
            "Replica lag above 30 seconds on the primary PostgreSQL cluster is a Sev-2. Check "
            "pg_stat_replication for replay_lag and write_lag. Common causes: a long transaction on the "
            "primary, a missing index causing sequential scans, or saturation of the replica's IOPS. "
            "Mitigation: kill the blocking query only after confirming it is not a migration, then "
            "rebuild the hottest missing index during the next CAB window. If lag exceeds 5 minutes, "
            "stop application writes that are not idempotent and page the data platform on-call. "
            "Promoting a replica requires HITL plus a recorded change ticket. After promotion, run "
            "Jenkins job aetherforge-db-failover-verify and update the Jira incident with the new "
            "primary endpoint. Application services read DATABASE_URL from the Kubernetes secret "
            "aetherforge-db and will recycle pods on secret rotation."
        ),
    },
    {
        "doc_id": "POL-CHG-003",
        "title": "Production Change Management and CAB Policy",
        "category": "Governance",
        "owner": "Release Management",
        "body": (
            "All production schema changes, BMS write-backs, and Kubernetes production deploys require "
            "a Jira Change ticket in status CAB Approved before Jenkins can promote to prod. "
            "Standard changes (docs, dashboard copy, feature flags default-off) may use the expedited "
            "path with one peer approval. Normal changes need two reviewers and a CAB slot. Emergency "
            "changes may start in Jenkins with a Sev-1 incident linked, but the Change ticket must be "
            "filed within 60 minutes and reviewed in the next CAB. The AI planner may draft the ticket "
            "and the Jenkins job parameters; a human must click Approve in the HITL queue. "
            "Never let an agent merge to main or apply Terraform without that gate."
        ),
    },
    {
        "doc_id": "SOP-SEC-019",
        "title": "Access Control System Failover",
        "category": "Security",
        "owner": "Physical Security",
        "body": (
            "If the primary access-control head-end is unreachable, doors remain in last known state. "
            "Do not broadcast unlock. Fail over the API hostname in Kubernetes to the secondary "
            "head-end service, then verify badge reads on two test readers. Open a Sev-2 Jira incident "
            "assigned to Physical Security and Platform Engineering. If failover exceeds 10 minutes, "
            "notify the site security manager. After restore, run Jenkins job access-control-smoke "
            "and attach the reader logs to the ticket."
        ),
    },
    {
        "doc_id": "SOP-SENS-008",
        "title": "Industrial Sensor Calibration Window",
        "category": "Operations",
        "owner": "Reliability Engineering",
        "body": (
            "Temperature, pressure, and vibration sensors on critical assets are calibrated every 90 days. "
            "A drift ticket is auto-drafted when the RAG monitor sees three consecutive out-of-band "
            "readings. Calibration must be scheduled in Jira as a Change, not a Bug. The technician "
            "attaches the certificate PDF and Jenkins job sensor-cal-ingest updates the knowledge base "
            "chunk for that asset. Agents may recommend a calibration window; they may not mark a "
            "sensor healthy without HITL."
        ),
    },
    {
        "doc_id": "SOP-INC-001",
        "title": "Incident Escalation Matrix",
        "category": "Governance",
        "owner": "SRE",
        "body": (
            "Sev-1: customer-facing outage or life-safety system failure — page SRE, facilities lead, "
            "and the incident commander within 5 minutes. Sev-2: degraded production or replica lag — "
            "page the owning team. Sev-3: single-site or single-service defect — Jira ticket in the "
            "team board is enough. The AetherForge planner maps retrieved runbooks to a suggested "
            "severity. Humans confirm severity before paging. Every Sev-1/2 must have a Jira Incident "
            "and a linked Jenkins postmortem draft job."
        ),
    },
    {
        "doc_id": "ARCH-AF-001",
        "title": "AetherForge Runtime Architecture",
        "category": "Platform",
        "owner": "AI Platform",
        "body": (
            "AetherForge is a knowledge operating system. FastAPI serves the control plane. PostgreSQL "
            "stores documents, chunks, workflow runs, Jira projections, HITL reviews, and the audit log. "
            "Hybrid retrieval combines BM25 lexical search with TF-IDF vectors and reciprocal rank fusion, "
            "then a deterministic reranker. Agents run as a directed graph: Retriever, Analyst, Planner, "
            "Reviewer. The Planner drafts a Jira issue and an optional Jenkins job. The Reviewer pauses "
            "the graph until HITL approval. Production deploys use Kubernetes (Deployment, Service, HPA) "
            "and a Jenkins pipeline that lints, tests, builds the image, and applies manifests. "
            "Redis may be attached for cache and job fan-out; the demo path is fully durable on PostgreSQL."
        ),
    },
    {
        "doc_id": "SOP-JEN-004",
        "title": "Jenkins Promotion Gates",
        "category": "Platform",
        "owner": "Release Engineering",
        "body": (
            "The aetherforge pipeline has four stages: Lint, Test, Image, Deploy. Deploy to staging "
            "is automatic after tests pass. Deploy to production requires a Jira Change in CAB Approved "
            "and a matching HITL approval id in the job parameters. The pipeline writes the build number "
            "back onto the Jira issue. If tests fail, the issue moves to Blocked and the agent run is "
            "marked failed. Never skip tests with -DskipTests on this pipeline."
        ),
    },
]


def chunk_documents(documents: list[dict] | None = None) -> list[dict]:
    docs = documents or DOCUMENTS
    chunks: list[dict] = []
    for doc in docs:
        sentences = [s.strip() for s in doc["body"].replace("  ", " ").split(". ") if s.strip()]
        buf: list[str] = []
        part = 0
        for sentence in sentences:
            buf.append(sentence.rstrip("."))
            if len(" ".join(buf)) > 280:
                part += 1
                text = ". ".join(buf) + "."
                chunks.append(
                    {
                        "chunk_id": f"{doc['doc_id']}-c{part}",
                        "doc_id": doc["doc_id"],
                        "title": doc["title"],
                        "category": doc["category"],
                        "text": text,
                        "token_count": len(text.split()),
                    }
                )
                buf = []
        if buf:
            part += 1
            text = ". ".join(buf) + "."
            chunks.append(
                {
                    "chunk_id": f"{doc['doc_id']}-c{part}",
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "category": doc["category"],
                    "text": text,
                    "token_count": len(text.split()),
                }
            )
    return chunks


SEED_ISSUES: list[dict] = [
    {
        "key": "AF-1041",
        "summary": "HVAC Zone 4 SAT drift — sensor vs damper diagnosis",
        "description": "Opened from AetherForge run after SOP-HVAC-014 retrieval.",
        "status": "In Progress",
        "priority": "High",
        "issue_type": "Incident",
        "assignee": "Priya Shah",
        "labels": "hvac,hitl,facilities",
        "linked_run_id": "",
        "jenkins_job": "aetherforge-ci",
        "jenkins_status": "SUCCESS",
    },
    {
        "key": "AF-1042",
        "summary": "CAB: promote aetherforge-api 1.0.0 to production",
        "description": "Requires two reviewers per POL-CHG-003.",
        "status": "CAB Review",
        "priority": "Medium",
        "issue_type": "Change",
        "assignee": "Release Board",
        "labels": "cab,kubernetes,jenkins",
        "linked_run_id": "",
        "jenkins_job": "aetherforge-deploy-prod",
        "jenkins_status": "PENDING",
    },
    {
        "key": "AF-1038",
        "summary": "PostgreSQL replica lag playbook drill",
        "description": "Tabletop using SOP-PG-011.",
        "status": "Done",
        "priority": "Medium",
        "issue_type": "Task",
        "assignee": "Marcus Lee",
        "labels": "postgres,sre",
        "linked_run_id": "",
        "jenkins_job": "aetherforge-db-failover-verify",
        "jenkins_status": "SUCCESS",
    },
    {
        "key": "AF-1033",
        "summary": "BMS alarm storm containment — Site North",
        "description": "Controller isolation completed. Awaiting config audit job.",
        "status": "In Review",
        "priority": "High",
        "issue_type": "Incident",
        "assignee": "Elena Voss",
        "labels": "bms-storm,facilities",
        "linked_run_id": "",
        "jenkins_job": "bms-config-audit",
        "jenkins_status": "RUNNING",
    },
    {
        "key": "AF-1029",
        "summary": "Add hybrid-search rerank weights to knowledge index",
        "description": "Platform enhancement tracked from ARCH-AF-001.",
        "status": "To Do",
        "priority": "Low",
        "issue_type": "Story",
        "assignee": "Unassigned",
        "labels": "rag,platform",
        "linked_run_id": "",
        "jenkins_job": "aetherforge-ci",
        "jenkins_status": "",
    },
    {
        "key": "AF-1024",
        "summary": "Access-control head-end failover smoke",
        "description": "Quarterly drill per SOP-SEC-019.",
        "status": "Done",
        "priority": "High",
        "issue_type": "Change",
        "assignee": "Jordan Adeyemi",
        "labels": "security,kubernetes",
        "linked_run_id": "",
        "jenkins_job": "access-control-smoke",
        "jenkins_status": "SUCCESS",
    },
]


SEED_JOBS: list[dict] = [
    {
        "job_name": "aetherforge-ci",
        "last_build": 248,
        "status": "SUCCESS",
        "duration_ms": 312000,
        "stage": "Test",
        "linked_issue": "AF-1029",
    },
    {
        "job_name": "aetherforge-deploy-staging",
        "last_build": 91,
        "status": "SUCCESS",
        "duration_ms": 188000,
        "stage": "Deploy",
        "linked_issue": "AF-1042",
    },
    {
        "job_name": "aetherforge-deploy-prod",
        "last_build": 44,
        "status": "PENDING",
        "duration_ms": 0,
        "stage": "Gate",
        "linked_issue": "AF-1042",
    },
    {
        "job_name": "aetherforge-db-failover-verify",
        "last_build": 17,
        "status": "SUCCESS",
        "duration_ms": 94000,
        "stage": "Verify",
        "linked_issue": "AF-1038",
    },
    {
        "job_name": "bms-config-audit",
        "last_build": 6,
        "status": "RUNNING",
        "duration_ms": 41000,
        "stage": "Audit",
        "linked_issue": "AF-1033",
    },
    {
        "job_name": "access-control-smoke",
        "last_build": 12,
        "status": "SUCCESS",
        "duration_ms": 67000,
        "stage": "Smoke",
        "linked_issue": "AF-1024",
    },
]
