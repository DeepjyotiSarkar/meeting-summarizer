const API = ""; // same-origin: backend serves this file too

const el = (id) => document.getElementById(id);
let currentMeetingId = null;
let pollTimer = null;

// ---------- Upload ----------
el("dropzone").addEventListener("change", () => {
  const f = el("file-input").files[0];
  el("dropzone-label").textContent = f ? f.name : "Drop audio file or click to browse";
});

el("upload-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const file = el("file-input").files[0];
  const title = el("title-input").value.trim() || "Untitled Meeting";
  if (!file) return;

  const fd = new FormData();
  fd.append("file", file);
  fd.append("title", title);

  el("upload-btn").disabled = true;
  el("upload-status").textContent = "Uploading…";

  try {
    const res = await fetch(`${API}/meetings/upload`, { method: "POST", body: fd });
    if (!res.ok) throw new Error(await res.text());
    const meeting = await res.json();
    el("upload-status").textContent = "Processing started — this can take a minute.";
    el("upload-form").reset();
    el("dropzone-label").textContent = "Drop audio file or click to browse";
    await loadMeetingList();
    selectMeeting(meeting.id);
  } catch (err) {
    el("upload-status").textContent = "Upload failed: " + err.message;
  } finally {
    el("upload-btn").disabled = false;
  }
});

// ---------- Tabs ----------
document.querySelectorAll(".tab-btn").forEach((btn) => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach((b) => b.classList.remove("active"));
    btn.classList.add("active");
    const tab = btn.dataset.tab;
    el("meeting-list").style.display = tab === "meetings" ? "flex" : "none";
    el("action-list").style.display = tab === "actions" ? "flex" : "none";
    if (tab === "actions") loadActionDashboard();
  });
});

// ---------- Meeting list ----------
async function loadMeetingList() {
  const res = await fetch(`${API}/meetings`);
  const meetings = await res.json();
  const container = el("meeting-list");
  container.innerHTML = "";
  if (!meetings.length) {
    container.innerHTML = `<p class="empty-hint">No meetings yet — upload one above.</p>`;
    return;
  }
  meetings.forEach((m) => {
    const row = document.createElement("div");
    row.className = "meeting-row";
    row.innerHTML = `<span class="mr-title">${escapeHtml(m.title)}</span>
      <span class="mr-meta">${m.status}${m.health_score != null ? " · score " + m.health_score : ""}</span>`;
    row.addEventListener("click", () => selectMeeting(m.id));
    container.appendChild(row);
  });
}

async function loadActionDashboard() {
  const res = await fetch(`${API}/action-items?status=open`);
  const items = await res.json();
  const container = el("action-list");
  container.innerHTML = "";
  if (!items.length) {
    container.innerHTML = `<p class="empty-hint">No open action items. 🎉</p>`;
    return;
  }
  items.forEach((item) => {
    const row = document.createElement("div");
    row.className = "meeting-row";
    row.innerHTML = `<span class="mr-title">${escapeHtml(item.description)}</span>
      <span class="mr-meta">${item.owner || "unassigned"} · ${item.deadline || "no date"} · ${item.priority}</span>`;
    container.appendChild(row);
  });
}

// ---------- Select / poll a meeting ----------
async function selectMeeting(id) {
  currentMeetingId = id;
  el("empty-state").hidden = true;
  el("meeting-view").hidden = false;
  clearInterval(pollTimer);
  await refreshMeeting();
  pollTimer = setInterval(async () => {
    const m = await refreshMeeting();
    if (m && (m.status === "done" || m.status === "failed")) clearInterval(pollTimer);
  }, 3000);
}

async function refreshMeeting() {
  if (!currentMeetingId) return null;
  const res = await fetch(`${API}/meetings/${currentMeetingId}`);
  if (!res.ok) return null;
  const m = await res.json();
  renderMeeting(m);
  return m;
}

function renderMeeting(m) {
  el("mv-title").textContent = m.title;
  const statusBadge = el("mv-status");
  statusBadge.textContent = m.status;
  statusBadge.className = "badge " + (m.status === "done" ? "done" : m.status === "failed" ? "failed" : "");

  el("health-score").textContent = m.health_score != null ? `${m.health_score}/100` : "—";
  el("health-fill").style.width = `${m.health_score || 0}%`;

  const breakdown = m.health_score_breakdown || {};
  el("sub-meters").innerHTML = Object.entries(breakdown).map(([k, v]) => `
    <div class="sub-meter">
      <div class="sm-label">${k}</div>
      <div class="sm-track"><div class="sm-fill" style="width:${v}%"></div></div>
    </div>`).join("");

  el("sentiment-pill").textContent = `sentiment: ${m.sentiment || "—"}`;
  el("summary-text").textContent = m.summary_text || (m.status === "failed" ? `Failed: ${m.error_message}` : "Processing…");

  el("decisions-list").innerHTML = (m.key_decisions || []).map((d) => `<li>${escapeHtml(d)}</li>`).join("")
    || `<li style="opacity:.5">—</li>`;

  el("ai-tbody").innerHTML = (m.action_items || []).map((item) => `
    <tr>
      <td>${escapeHtml(item.description)}</td>
      <td>${item.owner ? escapeHtml(item.owner) : "—"}</td>
      <td>${item.deadline || "—"}</td>
      <td><span class="priority-chip priority-${item.priority}">${item.priority}</span></td>
      <td>
        <select class="status-select" data-item-id="${item.id}">
          <option value="open" ${item.status === "open" ? "selected" : ""}>open</option>
          <option value="done" ${item.status === "done" ? "selected" : ""}>done</option>
        </select>
      </td>
    </tr>`).join("") || `<tr><td colspan="5" style="opacity:.5">No action items extracted.</td></tr>`;

  document.querySelectorAll(".status-select").forEach((sel) => {
    sel.addEventListener("change", async () => {
      await fetch(`${API}/action-items/${sel.dataset.itemId}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: sel.value }),
      });
    });
  });

  el("risks-list").innerHTML = (m.risks_or_open_questions || []).map((r) => `<li>${escapeHtml(r)}</li>`).join("")
    || `<li style="opacity:.5">—</li>`;

  el("email-draft").textContent = m.follow_up_email_draft || "—";

  const segments = (m.transcript_segments || []);
  el("transcript-body").innerHTML = segments.length
    ? segments.map((s) => `<div><b>[${fmtTime(s.start)}]</b> ${escapeHtml(s.text)}</div>`).join("")
    : escapeHtml(m.transcript_text || "—");

  el("btn-ics").onclick = () => window.open(`${API}/meetings/${m.id}/calendar.ics`, "_blank");
  el("btn-docx").onclick = () => window.open(`${API}/meetings/${m.id}/minutes.docx`, "_blank");
}

el("transcript-toggle").addEventListener("click", () => {
  const body = el("transcript-body");
  body.hidden = !body.hidden;
  el("transcript-toggle").textContent = (body.hidden ? "▸" : "▾") + " Full Transcript";
});

el("btn-copy-email").addEventListener("click", () => {
  navigator.clipboard.writeText(el("email-draft").textContent);
  el("btn-copy-email").textContent = "Copied!";
  setTimeout(() => (el("btn-copy-email").textContent = "Copy"), 1500);
});

// ---------- Ask ----------
el("ask-form").addEventListener("submit", async (e) => {
  e.preventDefault();
  const question = el("ask-input").value.trim();
  if (!question) return;
  const scopeAll = el("ask-scope").checked;
  el("ask-answer").textContent = "Thinking…";
  const res = await fetch(`${API}/meetings/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question, meeting_id: scopeAll ? null : currentMeetingId }),
  });
  const data = await res.json();
  el("ask-answer").textContent = data.answer || "No answer returned.";
});

// ---------- Helpers ----------
function fmtTime(sec) {
  sec = Math.floor(sec || 0);
  const m = Math.floor(sec / 60), s = sec % 60;
  return `${m}:${String(s).padStart(2, "0")}`;
}
function escapeHtml(str) {
  const div = document.createElement("div");
  div.textContent = str ?? "";
  return div.innerHTML;
}

loadMeetingList();
