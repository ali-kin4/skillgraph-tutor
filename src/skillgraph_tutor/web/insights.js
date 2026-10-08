/* SkillGraph Insights — visual analytics view: mastery heat map, skill averages,
   growth trajectory with scenario projections, and rule-based insights.
   Dependency-free SVG/HTML; every number comes from the local API. */

const SVG_NS = "http://www.w3.org/2000/svg";
const BINS = [
  {min:0.85, color:"#0d366b", ink:"#fff", label:"85+"},
  {min:0.70, color:"#1c5cab", ink:"#fff", label:"70–84"},
  {min:0.60, color:"#3987e5", ink:"#fff", label:"60–69"},
  {min:0.40, color:"#86b6ef", ink:"#13233f", label:"40–59"},
  {min:0,    color:"#cde2fb", ink:"#13233f", label:"<40"},
];
const SERIES = {
  history:{color:"#3b5bdb", label:"Recorded mastery"},
  practice:{color:"#0f9f8f", label:"With weekly practice"},
  noPractice:{color:"#9b5de5", label:"Without practice"},
};
const KIND_ICON = {growth:"↗", bottleneck:"◎", projection:"✦", reviews:"◷"};

let ctx;
let state = {scope:"cohort", weeks:8, sort:"name", showValues:false, concept:"", data:null, seq:0};
let resizeTimer;

const bin = (value) => BINS.find(b => value >= b.min);
const pct = (value) => value === null || value === undefined ? "—" : Math.round(value * 100) + "%";
const shortName = (name) => {
  const parts = name.trim().split(/\s+/);
  return parts.length > 1 ? parts[0] + " " + parts[parts.length - 1][0] + "." : name;
};
// Soft hyphens let long single-word skill names wrap inside narrow heat-map columns.
const hyphenate = (text) => text.replace(/\S{11,}/g, w => w.slice(0, 6) + "­" + w.slice(6));
const shortDate = (iso) => new Date(iso).toLocaleDateString("en", {month:"short", day:"numeric"});

export function initInsights(context) {
  ctx = context;
  const $ = ctx.$;
  $("#insightScope").addEventListener("change", e => { state.scope = e.target.value; loadInsights(); });
  $("#insightSort").addEventListener("change", e => { state.sort = e.target.value; renderHeatmap(); });
  $("#insightValues").addEventListener("change", e => { state.showValues = e.target.checked; renderHeatmap(); });
  $("#insightHorizon").addEventListener("click", e => {
    const button = e.target.closest("[data-weeks]");
    if (!button) return;
    state.weeks = Number(button.dataset.weeks);
    ctx.$$("#insightHorizon [data-weeks]").forEach(b => b.setAttribute("aria-pressed", String(b === button)));
    loadInsights();
  });
  document.addEventListener("click", e => {
    const target = e.target.closest("[data-focus-concept]");
    if (!target) return;
    const concept = target.dataset.focusConcept;
    state.concept = state.concept === concept ? "" : concept;
    renderHeatmap();
    renderBars();
  });
  const view = $("#view-insights");
  view.addEventListener("pointerover", showTip);
  view.addEventListener("focusin", showTip);
  view.addEventListener("pointerout", hideTip);
  view.addEventListener("focusout", hideTip);
  window.addEventListener("resize", () => {
    clearTimeout(resizeTimer);
    resizeTimer = setTimeout(() => { if (state.data) renderTrajectory(); }, 120);
  });
}

export function fillInsightScopes(snapshot) {
  const esc = ctx.esc;
  const groups = snapshot.groups.map(g =>
    '<option value="group:' + esc(g.name) + '">' + esc(g.name) + "</option>").join("");
  const learners = snapshot.students.map(s =>
    '<option value="learner:' + esc(s.id) + '">' + esc(s.name) + "</option>").join("");
  const select = ctx.$("#insightScope");
  select.innerHTML = '<option value="cohort">Whole cohort</option>' +
    (groups ? '<optgroup label="Learning groups">' + groups + "</optgroup>" : "") +
    (learners ? '<optgroup label="Learners">' + learners + "</optgroup>" : "");
  if (![...select.options].some(o => o.value === state.scope)) state.scope = "cohort";
  select.value = state.scope;
}

export async function loadInsights() {
  const ticket = ++state.seq;
  ctx.$("#view-insights").setAttribute("aria-busy", "true");
  renderHeatmap();
  renderBars();
  try {
    const data = await ctx.requestJson("/api/insights?scope=" + encodeURIComponent(state.scope) +
      "&weeks=" + state.weeks);
    if (ticket !== state.seq) return;
    state.data = data;
    renderInsightCard();
    renderBars();
    renderTrajectory();
  } catch (err) {
    if (ticket !== state.seq) return;
    ctx.$("#insightList").innerHTML = '<div class="empty-state">' + ctx.esc(err.message) + "</div>";
  } finally {
    if (ticket === state.seq) ctx.$("#view-insights").removeAttribute("aria-busy");
  }
}

function scopedStudents() {
  const all = ctx.snapshot().students;
  const [kind, ...rest] = state.scope.split(":");
  const value = rest.join(":");
  if (kind === "group") return all.filter(s => s.group === value);
  if (kind === "learner") return all.filter(s => s.id === value);
  return all;
}

function conceptMeans(students) {
  return ctx.snapshot().concepts.map((concept, index) => {
    const values = students.map(s => s.concepts[index].mastery).filter(v => v !== null);
    return {
      name:concept.name,
      mean:values.length ? values.reduce((a, b) => a + b, 0) / values.length : null,
      observed:values.length,
    };
  });
}

/* ---------- Insight card ---------- */

function highlight(text, concepts) {
  let html = ctx.esc(text);
  [...concepts].sort((a, b) => b.length - a.length).forEach(name => {
    const safe = ctx.esc(name);
    html = html.split(safe).join('<button type="button" class="insight-concept" data-focus-concept="' +
      safe + '">' + safe + "</button>");
  });
  return html;
}

function renderInsightCard() {
  const items = state.data.insights;
  ctx.$("#insightList").innerHTML = items.length ? items.map(item =>
    '<li class="insight-item insight-' + ctx.esc(item.kind) + '"><span class="insight-kind" aria-hidden="true">' +
    (KIND_ICON[item.kind] || "✦") + '</span><div><strong>' + ctx.esc(item.title) + "</strong><p>" +
    highlight(item.text, item.concepts) + "</p></div></li>").join("")
    : '<li class="empty-state">Not enough observations for insights yet.</li>';
}

/* ---------- Heat map ---------- */

function renderHeatmap() {
  const esc = ctx.esc;
  const concepts = ctx.snapshot().concepts;
  const rows = scopedStudents().slice();
  if (state.sort === "low") rows.sort((a, b) => (a.meanMastery ?? 2) - (b.meanMastery ?? 2));
  if (state.sort === "high") rows.sort((a, b) => (b.meanMastery ?? -1) - (a.meanMastery ?? -1));
  const grid = ctx.$("#heatmap");
  grid.style.setProperty("--cols", concepts.length);
  grid.classList.toggle("show-values", state.showValues);
  const head = '<div class="hm-corner">Learner</div>' + concepts.map(c =>
    '<button type="button" class="hm-col' + (state.concept === c.name ? " is-focus" : "") +
    '" data-focus-concept="' + esc(c.name) + '" aria-pressed="' + (state.concept === c.name) + '">' +
    esc(hyphenate(c.name)) + "</button>").join("");
  const body = rows.map(s =>
    '<div class="hm-row"><button type="button" class="hm-name" data-open-learner="' +
    esc(s.id) + '" title="' + esc(s.name) + '">' + esc(shortName(s.name)) + "</button>" +
    s.concepts.map(c => {
      const b = c.mastery === null ? null : bin(c.mastery);
      const label = s.name + ", " + c.concept + ": " + (b ? pct(c.mastery) + " mastery" : "not observed");
      const style = b ? ' style="background:' + b.color + ";color:" + b.ink + '"' : "";
      return '<button type="button" class="hm-cell' + (b ? "" : " is-missing") +
        (state.concept && state.concept !== c.concept ? " is-dim" : "") + '"' + style +
        ' data-open-learner="' + esc(s.id) + '" data-tip="' + esc(label) + '" aria-label="' + esc(label) +
        '"><span>' + (b ? Math.round(c.mastery * 100) : "") + "</span></button>";
    }).join("") + "</div>").join("");
  grid.innerHTML = '<div class="hm-row hm-head">' + head + "</div>" +
    (body || '<div class="empty-state">No learners in this scope.</div>');
  ctx.$("#heatmapCaption").textContent = rows.length + " learner" + (rows.length === 1 ? "" : "s") +
    " × " + concepts.length + " concepts";
  ctx.$("#heatmapLegend").innerHTML = BINS.slice().reverse().map(b =>
    '<span><i style="background:' + b.color + '"></i>' + b.label + "</span>").join("") +
    '<span><i class="is-missing"></i>Not observed</span>';
}

/* ---------- Skill averages ---------- */

function renderBars() {
  const esc = ctx.esc;
  const growth = Object.fromEntries((state.data?.growth || []).map(g => [g.name, g.delta]));
  const means = conceptMeans(scopedStudents());
  ctx.$("#skillBars").innerHTML = means.map(c => {
    const delta = growth[c.name];
    const chip = delta === undefined || delta === null ? "" :
      '<span class="delta ' + (delta >= 0 ? "up" : "down") + '">' + (delta >= 0 ? "+" : "−") +
      Math.abs(Math.round(delta * 100)) + "</span>";
    const tip = c.name + ": " + pct(c.mean) + " mean · " + c.observed + " observed" +
      (delta !== undefined && delta !== null ? " · " + (delta >= 0 ? "+" : "") + Math.round(delta * 100) +
      " pts in 4 weeks" : "");
    return '<button type="button" class="skill-bar' + (state.concept === c.name ? " is-focus" : "") +
      (state.concept && state.concept !== c.name ? " is-dim" : "") + '" data-focus-concept="' + esc(c.name) +
      '" data-tip="' + esc(tip) + '" aria-label="' + esc(tip) + '"><span class="skill-name">' + esc(c.name) +
      '</span><span class="skill-track"><span class="skill-fill" style="width:' +
      (c.mean === null ? 0 : Math.max(1.5, c.mean * 100)) + '%"></span></span><span class="skill-val">' +
      pct(c.mean) + "</span>" + chip + "</button>";
  }).join("");
}

/* ---------- Growth trajectory ---------- */

function el(name, attrs = {}, text) {
  const node = document.createElementNS(SVG_NS, name);
  Object.entries(attrs).forEach(([k, v]) => node.setAttribute(k, v));
  if (text !== undefined) node.textContent = text;
  return node;
}

function renderTrajectory() {
  const {history, practice, noPractice, assumptions} = state.data.trajectory;
  const host = ctx.$("#trajectory");
  const width = Math.max(300, host.clientWidth);
  const height = width < 560 ? 260 : 320;
  const pad = {top:18, right:width < 560 ? 54 : 104, bottom:34, left:42};
  const all = [...history, ...practice.slice(1)];
  const t0 = Date.parse(history[0].date);
  const t1 = Date.parse(practice[practice.length - 1].date);
  const x = (iso) => pad.left + (Date.parse(iso) - t0) / (t1 - t0) * (width - pad.left - pad.right);
  const y = (v) => pad.top + (1 - v) * (height - pad.top - pad.bottom);
  const svg = el("svg", {viewBox:"0 0 " + width + " " + height, width, height, role:"group",
    "aria-label":"Mean mastery over time with two scenario projections"});

  const defs = el("defs");
  Object.entries(SERIES).forEach(([key, s]) => {
    const g = el("linearGradient", {id:"fade-" + key, x1:0, y1:0, x2:0, y2:1});
    g.append(el("stop", {offset:"0%", "stop-color":s.color, "stop-opacity":0.16}),
      el("stop", {offset:"100%", "stop-color":s.color, "stop-opacity":0}));
    defs.append(g);
  });
  svg.append(defs);

  [0, 0.25, 0.5, 0.75, 1].forEach(v => {
    svg.append(el("line", {x1:pad.left, x2:width - pad.right, y1:y(v), y2:y(v), class:"tj-grid"}));
    svg.append(el("text", {x:pad.left - 8, y:y(v) + 4, class:"tj-axis", "text-anchor":"end"}, v * 100 + "%"));
  });
  const step = width < 560 ? 4 : 2;
  all.forEach((p, i) => {
    if (i % step === 0 || i === history.length - 1) {
      svg.append(el("text", {x:x(p.date), y:height - 10, class:"tj-axis", "text-anchor":"middle"}, shortDate(p.date)));
    }
  });

  const now = history[history.length - 1];
  svg.append(el("line", {x1:x(now.date), x2:x(now.date), y1:pad.top - 6, y2:height - pad.bottom, class:"tj-now"}));
  svg.append(el("text", {x:x(now.date) - 8, y:pad.top + 6, class:"tj-zone", "text-anchor":"end"}, "Recorded"));
  svg.append(el("text", {x:x(now.date) + 8, y:pad.top + 6, class:"tj-zone"}, "Scenario →"));

  const path = (points) => points.filter(p => p.mean !== null)
    .map((p, i) => (i ? "L" : "M") + x(p.date).toFixed(1) + " " + y(p.mean).toFixed(1)).join(" ");
  const area = (points, key) => {
    const valid = points.filter(p => p.mean !== null);
    if (valid.length < 2) return;
    svg.append(el("path", {d:path(valid) + " L" + x(valid[valid.length - 1].date) + " " + y(0) +
      " L" + x(valid[0].date) + " " + y(0) + " Z", fill:"url(#fade-" + key + ")"}));
  };
  area(history, "history");
  area(practice, "practice");
  area(noPractice, "noPractice");
  const series = {history, practice, noPractice};
  Object.entries(series).forEach(([key, points]) => {
    svg.append(el("path", {d:path(points), class:"tj-line" + (key === "history" ? "" : " is-dashed"),
      stroke:SERIES[key].color}));
    points.forEach((p, i) => {
      if (p.mean === null || (key !== "history" && i === 0)) return;
      svg.append(el("circle", {cx:x(p.date), cy:y(p.mean), r:4, fill:SERIES[key].color, class:"tj-dot"}));
    });
  });
  // Direct end labels keep identity readable without relying on color alone.
  [["practice", practice], ["noPractice", noPractice]].forEach(([key, points]) => {
    const last = points[points.length - 1];
    if (last.mean === null) return;
    const other = (key === "practice" ? noPractice : practice).at(-1).mean ?? last.mean;
    const nudge = Math.abs(other - last.mean) < 0.08 ? (last.mean >= other ? -8 : 8) : 0;
    svg.append(el("text", {x:x(last.date) + 10, y:y(last.mean) + 4 + nudge, class:"tj-end"}, pct(last.mean)));
  });

  const cross = el("line", {class:"tj-cross", y1:pad.top, y2:height - pad.bottom, visibility:"hidden"});
  svg.append(cross);
  const hit = el("rect", {x:pad.left, y:0, width:width - pad.left - pad.right, height, fill:"transparent",
    tabindex:0, "aria-label":"Trajectory values; use arrow keys to step through weeks"});
  svg.append(hit);
  let cursor = history.length - 1;
  const show = (index) => {
    cursor = Math.max(0, Math.min(all.length - 1, index));
    const point = all[cursor];
    const px = x(point.date);
    cross.setAttribute("x1", px);
    cross.setAttribute("x2", px);
    cross.setAttribute("visibility", "visible");
    const rows = cursor < history.length - 1
      ? [["history", history[cursor]]]
      : cursor === history.length - 1
        ? [["history", now]]
        : [["practice", practice[cursor - history.length + 1]], ["noPractice", noPractice[cursor - history.length + 1]]];
    const box = svg.getBoundingClientRect();
    tip(new Date(point.date).toLocaleDateString("en", {month:"short", day:"numeric", year:"numeric"}) +
      rows.map(([key, p]) => "\n" + SERIES[key].label + ": " + pct(p.mean) +
        (p.observed !== undefined ? " (" + p.observed + " obs.)" : "")).join(""),
    box.left + px * box.width / width, box.top + y(rows[0][1].mean ?? 0) * box.height / height);
  };
  const nearest = (clientX) => {
    const box = svg.getBoundingClientRect();
    const px = (clientX - box.left) * width / box.width;
    let best = 0;
    all.forEach((p, i) => { if (Math.abs(x(p.date) - px) < Math.abs(x(all[best].date) - px)) best = i; });
    return best;
  };
  hit.addEventListener("pointermove", e => show(nearest(e.clientX)));
  hit.addEventListener("pointerleave", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
  hit.addEventListener("focus", () => show(cursor));
  hit.addEventListener("blur", () => { cross.setAttribute("visibility", "hidden"); hideTip(); });
  hit.addEventListener("keydown", e => {
    if (e.key === "ArrowLeft" || e.key === "ArrowRight") {
      e.preventDefault();
      show(cursor + (e.key === "ArrowRight" ? 1 : -1));
    }
  });
  host.replaceChildren(svg);

  const endPractice = practice.at(-1).mean;
  const endIdle = noPractice.at(-1).mean;
  ctx.$("#trajectoryLegend").innerHTML =
    legendCard("practice", endPractice, "Projected mean in " + state.weeks + " weeks if each observed concept gets one successful review per week.") +
    legendCard("noPractice", endIdle, "Projected mean in " + state.weeks + " weeks if practice stops and estimates decay.") +
    '<p class="tj-note">' + ctx.esc(assumptions.disclaimer) + "</p>";
  ctx.$("#trajectoryNow").textContent = pct(now.mean);
  ctx.$("#trajectoryTable").innerHTML = '<table><thead><tr><th>Week of</th><th>Recorded</th><th>With practice</th>' +
    "<th>Without practice</th></tr></thead><tbody>" + all.map((p, i) => {
      const f = i - history.length + 1;
      return "<tr><td>" + shortDate(p.date) + "</td><td>" + (i < history.length ? pct(history[i].mean) : "—") +
        "</td><td>" + (f >= 0 ? pct(practice[f].mean) : "—") + "</td><td>" + (f >= 0 ? pct(noPractice[f].mean) : "—") +
        "</td></tr>";
    }).join("") + "</tbody></table>";
}

function legendCard(key, value, text) {
  return '<div class="tj-card tj-' + key + '"><div class="tj-card-head"><i class="tj-swatch ' + key +
    '"></i><span>' + SERIES[key].label + "</span></div><strong>" + pct(value) + "</strong><p>" +
    ctx.esc(text) + "</p></div>";
}

/* ---------- Tooltip ---------- */

function tip(text, clientX, clientY) {
  const node = ctx.$("#chartTip");
  node.textContent = text;
  node.hidden = false;
  const box = node.getBoundingClientRect();
  const left = Math.min(window.innerWidth - box.width - 8, Math.max(8, clientX - box.width / 2));
  const top = clientY - box.height - 12 < 8 ? clientY + 16 : clientY - box.height - 12;
  node.style.left = left + window.scrollX + "px";
  node.style.top = top + window.scrollY + "px";
}

function showTip(event) {
  const target = event.target.closest?.("[data-tip]");
  if (!target) return;
  const box = target.getBoundingClientRect();
  tip(target.dataset.tip, box.left + box.width / 2, box.top);
}

function hideTip(event) {
  if (event?.relatedTarget && event.target.closest?.("[data-tip]")?.contains(event.relatedTarget)) return;
  ctx.$("#chartTip").hidden = true;
}
