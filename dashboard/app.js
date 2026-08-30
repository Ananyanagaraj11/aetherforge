const SUGGESTIONS = [
  "HVAC zone 4 supply temperature is drifting. What is the runbook and should we open a ticket?",
  "How do we roll back a failed Kubernetes production release?",
  "PostgreSQL replica lag is over 30 seconds. What is the escalation path?",
  "Who has to approve a production schema change before Jenkins can promote?",
  "BMS alarm storm on Site North — containment steps?",
];

const titles = {
  command: "Command",
  knowledge: "Knowledge base",
  agents: "Agent runs",
  jira: "Jira · AF",
  hitl: "HITL queue",
  ops: "Jenkins · Kubernetes",
};

const $ = (id) => document.getElementById(id);

async function api(path, opts) {
  const res = await fetch(path, {
    headers: { "Content-Type": "application/json" },
    ...opts,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "Request failed");
  }
  return res.json();
}

function badge(text) {
  const cls = String(text || "").replace(/\s+/g, "_");
  return `<span class="badge ${cls}">${text || "—"}</span>`;
}

async function refreshChips() {
  const o = await api("/api/overview");
  $("chips").innerHTML = `
    <span class="chip"><strong>${o.documents}</strong> runbooks</span>
    <span class="chip"><strong>${o.jira_open}</strong> open Jira</span>
    <span class="chip"><strong>${o.pending_hitl}</strong> HITL</span>
    <span class="chip"><strong>${o.jenkins_jobs}</strong> Jenkins jobs</span>
  `;
  $("kpis").innerHTML = `
    <div class="kpi"><b>${o.documents}</b><span>Knowledge documents</span></div>
    <div class="kpi"><b>${o.runs}</b><span>Agent runs</span></div>
    <div class="kpi"><b>${o.pending_hitl}</b><span>Waiting on humans</span></div>
    <div class="kpi"><b>${o.jira_open}/${o.jira_total}</b><span>Open / total AF issues</span></div>
  `;
}

function renderRun(run) {
  $("answer").classList.remove("empty");
  $("answer").textContent = run.answer;
  $("timeline").classList.remove("empty");
  $("timeline").innerHTML = (run.steps || []).map((s) => `
    <div class="step">
      <div class="dot ${s.status}"></div>
      <div>
        <div><b>${s.agent}</b> ${badge(s.status)}</div>
        <div class="meta">${s.detail || ""}</div>
      </div>
    </div>
  `).join("");
  $("cites").innerHTML = (run.citations || []).map((c) => `
    <div class="cite">
      <b>${c.doc_id}</b> · ${c.title}<br/>
      score ${c.score} · bm25 ${c.bm25} · vector ${c.vector}<br/>
      ${c.excerpt}
    </div>
  `).join("") || "<div class='empty'>No grounded chunks — system abstained.</div>";
  const t = run.proposed_ticket || {};
  $("ticket").innerHTML = `
    <div class="ticket">
      <div class="key">${t.issue_type || "Ticket"} · ${t.priority || ""} · ${t.severity || ""}</div>
      <div class="sum">${t.summary || ""}</div>
      <div class="sub">Assignee ${t.assignee || "—"} · Jenkins <b>${t.jenkins_job || "—"}</b></div>
      <div class="sub">Labels ${t.labels || ""}</div>
    </div>
    ${run.review_id ? `<div style="display:flex;gap:8px;margin-top:10px">
      <button class="btn small" onclick="resolveHitl('${run.review_id}', true)">Approve → Jira + Jenkins</button>
      <button class="btn small danger" onclick="resolveHitl('${run.review_id}', false)">Reject</button>
    </div>` : `<p class="empty">No HITL gate for this run.</p>`}
  `;
}

async function ask(query) {
  $("answer").textContent = "Running retriever → analyst → planner → reviewer…";
  $("answer").classList.remove("empty");
  const run = await api("/api/ask", { method: "POST", body: JSON.stringify({ query }) });
  renderRun(run);
  await refreshChips();
  await loadHitl();
  await loadRuns();
  await loadBoard();
}

async function resolveHitl(id, approved) {
  const path = approved ? "approve" : "reject";
  await api(`/api/hitl/${id}/${path}`, {
    method: "POST",
    body: JSON.stringify({ reviewer: "demo-reviewer", feedback: approved ? "Approved from console" : "Rejected from console" }),
  });
  await Promise.all([refreshChips(), loadHitl(), loadBoard(), loadJenkins(), loadAudit()]);
  $("ticket").insertAdjacentHTML("beforeend", `<p class="empty">${approved ? "Approved. Ticket written to the AF board and Jenkins job queued." : "Rejected. No Jira write."}</p>`);
}

async function loadKnowledge() {
  const docs = await api("/api/knowledge");
  $("knowledgeTable").innerHTML = `
    <tr><th>ID</th><th>Title</th><th>Category</th><th>Owner</th></tr>
    ${docs.map((d) => `<tr><td>${d.doc_id}</td><td>${d.title}</td><td>${d.category}</td><td>${d.owner}</td></tr>`).join("")}
  `;
}

async function loadRuns() {
  const runs = await api("/api/runs");
  $("runsTable").innerHTML = `
    <tr><th>Run</th><th>Query</th><th>Status</th><th>Confidence</th></tr>
    ${runs.map((r) => `<tr><td class="key">${r.run_id}</td><td>${r.query}</td><td>${badge(r.status)}</td><td>${r.confidence}</td></tr>`).join("") || "<tr><td colspan='4'>No runs yet</td></tr>"}
  `;
}

async function loadBoard() {
  const data = await api("/api/jira/issues");
  const cols = data.columns || {};
  $("board").innerHTML = Object.entries(cols).map(([name, items]) => `
    <div class="col">
      <h5>${name} · ${items.length}</h5>
      ${items.map((t) => `
        <div class="ticket">
          <div class="key">${t.key} · ${t.issue_type}</div>
          <div class="sum">${t.summary}</div>
          <div class="sub">${t.assignee} · ${t.priority}<br/>${t.jenkins_job ? "Jenkins " + t.jenkins_job + " " + (t.jenkins_status || "") : ""}</div>
        </div>
      `).join("")}
    </div>
  `).join("");
}

async function loadHitl() {
  const items = await api("/api/hitl");
  if (!items.length) {
    $("hitlList").innerHTML = "<div class='empty'>Queue is clear. Run a production-risk query on Command to create a review.</div>";
    return;
  }
  $("hitlList").innerHTML = items.map((h) => `
    <div class="ticket">
      <div class="key">${h.review_id}</div>
      <div class="sum">${h.ticket.summary || ""}</div>
      <div class="sub">${h.ticket.issue_type} · ${h.ticket.jenkins_job} · run ${h.run_id}</div>
      <div style="display:flex;gap:8px;margin-top:8px">
        <button class="btn small" onclick="resolveHitl('${h.review_id}', true)">Approve</button>
        <button class="btn small danger" onclick="resolveHitl('${h.review_id}', false)">Reject</button>
      </div>
    </div>
  `).join("");
}

async function loadJenkins() {
  const jobs = await api("/api/jenkins/jobs");
  $("jenkinsTable").innerHTML = `
    <tr><th>Job</th><th>Build</th><th>Status</th><th>Stage</th><th>Issue</th></tr>
    ${jobs.map((j) => `<tr><td>${j.job_name}</td><td>#${j.last_build}</td><td>${badge(j.status)}</td><td>${j.stage}</td><td>${j.linked_issue}</td></tr>`).join("")}
  `;
}

async function loadOps() {
  const ops = await api("/api/ops");
  $("opsPanel").innerHTML = `
    <p><b>Namespace</b> ${ops.kubernetes.namespace} · <b>Deployment</b> ${ops.kubernetes.deployment}</p>
    <p>Replicas ${ops.kubernetes.replicas} · HPA ${ops.kubernetes.hpa} · Ready ${ops.kubernetes.ready}</p>
    <p><b>PostgreSQL</b> ${ops.postgres.role}</p>
    <p><b>Jira project</b> ${ops.jira_project}</p>
  `;
  await loadJenkins();
  await loadAudit();
}

async function loadAudit() {
  const rows = await api("/api/audit");
  $("auditTable").innerHTML = `
    <tr><th>Event</th><th>Actor</th><th>Type</th><th>Detail</th></tr>
    ${rows.map((r) => `<tr><td>${r.event_id}</td><td>${r.actor}</td><td>${r.event_type}</td><td>${r.detail}</td></tr>`).join("")}
  `;
}

function show(page) {
  document.querySelectorAll(".page").forEach((el) => el.classList.toggle("active", el.id === page));
  document.querySelectorAll(".nav button[data-page]").forEach((el) => el.classList.toggle("active", el.dataset.page === page));
  $("pageTitle").textContent = titles[page];
  if (page === "knowledge") loadKnowledge();
  if (page === "agents") loadRuns();
  if (page === "jira") loadBoard();
  if (page === "hitl") loadHitl();
  if (page === "ops") loadOps();
}

document.querySelectorAll(".nav button[data-page]").forEach((btn) => {
  btn.addEventListener("click", () => show(btn.dataset.page));
});

$("suggestions").innerHTML = SUGGESTIONS.map((q) => `<button type="button">${q}</button>`).join("");
$("suggestions").querySelectorAll("button").forEach((btn) => {
  btn.addEventListener("click", () => {
    $("query").value = btn.textContent;
    ask(btn.textContent);
  });
});

$("askBtn").addEventListener("click", () => {
  const q = $("query").value.trim();
  if (q.length > 2) ask(q);
});
$("query").addEventListener("keydown", (e) => {
  if (e.key === "Enter") $("askBtn").click();
});

refreshChips().catch((err) => {
  $("answer").textContent = err.message;
});
