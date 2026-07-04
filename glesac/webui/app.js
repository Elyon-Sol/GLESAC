"use strict";
const $ = (id) => document.getElementById(id);
const el = (tag, cls, txt) => { const e = document.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; };
const short = (s) => (typeof s === "string" && s.length > 16) ? s.slice(0, 12) + "…" : s;
async function api(u) { const r = await fetch(u); if (!r.ok) throw new Error(r.status + " " + u); return r.json(); }

function chip(label, val) {
  const cls = val === true ? "ok" : val === false ? "bad" : "na";
  return el("span", "chip " + cls, label + (val === true ? " ✓" : val === false ? " ✗" : " –"));
}

async function loadStatus() {
  const box = $("status-card");
  try {
    const s = await api("/api/status");
    const p = $("predicates"); p.innerHTML = "";
    Object.entries(s.readiness || {}).forEach(([k, v]) => p.appendChild(chip(k, v)));

    const sr = s.signed_record || {};
    const sd = $("signed"); sd.innerHTML = "";
    if (sr.present) {
      [["publisher key", sr.publisher_key_id], ["serial", sr.serial],
       ["not_after", sr.not_after]].forEach(([k, v]) => {
        const row = el("div", "kv"); row.appendChild(el("b", null, k)); row.appendChild(el("span", null, String(v))); sd.appendChild(row);
      });
      sd.appendChild((() => { const r = el("div", "kv"); r.appendChild(el("b", null, "fresh")); r.appendChild(chip(sr.fresh ? "fresh" : "stale", sr.fresh)); return r; })());
    } else { sd.appendChild(el("div", "kv muted", "no signed record configured")); }

    const nd = $("nodes"); nd.innerHTML = ""; nd.appendChild(el("div", "muted small", "nodes"));
    Object.entries(s.nodes || {}).forEach(([name, info]) => {
      const ok = info.state === "reachable";
      nd.appendChild(chip(name + ":" + info.state, ok ? true : (info.state === "unconfigured" ? null : false)));
    });
    if (!Object.keys(s.nodes || {}).length) nd.appendChild(el("span", "muted small", " (no node URLs set)"));

    const cap = $("capabilities"); cap.innerHTML = "";
    const caps = s.capabilities || {};
    if (Object.keys(caps).length) {
      const t = el("table"); const h = el("tr");
      ["capability", "built", "wired", "e2e", "transported"].forEach(c => h.appendChild(el("th", null, c)));
      t.appendChild(h);
      Object.entries(caps).forEach(([name, f]) => {
        const tr = el("tr"); tr.appendChild(el("td", "mono", name));
        ["built", "wired_to_default", "exercised_e2e", "transported"].forEach(k => {
          const td = el("td"); td.appendChild(chip("", f[k])); tr.appendChild(td);
        });
        t.appendChild(tr);
      });
      cap.appendChild(t);
    } else { cap.appendChild(el("div", "muted small", "no capabilities block")); }
  } catch (e) { box.appendChild(el("div", "err small", "status error: " + e.message)); }
}

async function loadPending() {
  const box = $("pending"); box.innerHTML = "";
  try {
    const d = await api("/api/pending");
    const holds = d.pending || [];
    if (!holds.length) { box.appendChild(el("div", "muted small", "(no pending holds)")); return; }
    const t = el("table"); const h = el("tr");
    ["request", "decision", "target", "not_after"].forEach(c => h.appendChild(el("th", null, c)));
    t.appendChild(h);
    holds.forEach(r => {
      const tr = el("tr"); const ctx = r.context || {};
      tr.appendChild(el("td", "mono", r.approval_request_id));
      tr.appendChild(el("td", "mono", short(r.decision_sha256)));
      tr.appendChild(el("td", "small muted", ctx.target_url || ""));
      tr.appendChild(el("td", "small muted", ctx.not_after || ""));
      t.appendChild(tr);
    });
    box.appendChild(t);
  } catch (e) { box.appendChild(el("div", "err small", "pending error: " + e.message)); }
}

async function loadLogs() {
  const which = $("which").value, tail = $("tail").value;
  const box = $("logs"); box.innerHTML = "";
  try {
    const d = await api("/api/logs?which=" + which + "&tail=" + tail);
    const recs = d.records || [];
    if (!recs.length) { box.appendChild(el("div", "muted small", "(no records)")); return; }
    const t = el("table"); const h = el("tr");
    ["type/stage", "decision", "request", "detail"].forEach(c => h.appendChild(el("th", null, c)));
    t.appendChild(h);
    recs.slice().reverse().forEach(r => {
      const tr = el("tr");
      tr.appendChild(el("td", null, r.type || (r.decision_sha256 ? "issued" : "?")));
      tr.appendChild(el("td", "mono", short(r.decision_sha256)));
      tr.appendChild(el("td", "mono", short(r.approval_request_id) || ""));
      const det = r.grant_id ? "grant " + short(r.grant_id) : (r.target_url || "");
      tr.appendChild(el("td", "small muted", det));
      t.appendChild(tr);
    });
    box.appendChild(t);
  } catch (e) { box.appendChild(el("div", "err small", "logs error: " + e.message)); }
}

async function loadTrace() {
  const sha = $("sha").value.trim(); if (!sha) return;
  const box = $("trace"); box.innerHTML = "";
  try {
    const d = await api("/api/trace/" + encodeURIComponent(sha));
    const tl = d.timeline || [];
    if (!tl.length) { box.appendChild(el("li", "muted", "(no events for this decision)")); return; }
    tl.forEach(e => {
      const li = el("li", e.stage);
      li.appendChild(el("span", "stage", e.stage));
      const bits = [];
      if (e.approval_request_id) bits.push("req " + short(e.approval_request_id));
      if (e.grant_id) bits.push("grant " + short(e.grant_id));
      if (e.approver_key_id) bits.push(e.approver_key_id);
      if (e.count != null) bits.push("count " + e.count);
      if (bits.length) li.appendChild(el("div", "det", bits.join("  ·  ")));
      box.appendChild(li);
    });
  } catch (e) { box.appendChild(el("li", "err", "trace error: " + e.message)); }
}

$("logs-refresh").addEventListener("click", loadLogs);
$("trace-go").addEventListener("click", loadTrace);
$("sha").addEventListener("keydown", (e) => { if (e.key === "Enter") loadTrace(); });
loadStatus(); loadPending(); loadLogs();
