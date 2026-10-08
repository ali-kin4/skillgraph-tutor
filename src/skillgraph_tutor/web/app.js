/* SkillGraph Insights — dependency-free frontend. No external API calls or telemetry. */

let snapshot = null;
let activeView = "overview";
let selectedLearnerId = "";
let selectedGraphConcept = "";
let graphMode = "cohort";
let graphLearnerId = "";
let toastTimer;
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => Array.from(document.querySelectorAll(sel));
const ESCAPES = {"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"};
const esc = (text) => String(text ?? "").replace(/[&<>"']/g, (key) => ESCAPES[key]);
const fmt = (number, digits=0) => number === null || number === undefined
  ? "—" : (Number(number)*100).toFixed(digits) + "%";
const initials = (name) => name.split(/\s+/).map(part => part[0]).slice(0,2).join("").toUpperCase();
const masteryLabel = (value) => value === null || value === undefined ? "Not observed"
  : value >= 0.7 ? "Strong signal" : value >= 0.6 ? "Developing" : "Needs practice";
const tone = (value) => value === null || value === undefined ? "unknown"
  : value >= 0.7 ? "strong" : value < 0.6 ? "weak" : "moderate";
const riskClass = (value) => value === "Needs support" ? "support"
  : value === "Monitor" ? "monitor" : value === "On track" ? "good" : "unassessed";
const statusPill = (status) => '<span class="pill ' + riskClass(status) + '">' + esc(status) + '</span>';
const personIcon = (name, index=0) => '<span class="initials tone-' + index%3 + '">' + esc(initials(name)) + '</span>';
const conceptMap = () => Object.fromEntries(snapshot.concepts.map(c=>[c.name,c]));
const person = (id) => snapshot.students.find(s => s.id === id);
const compact = (n) => new Intl.NumberFormat("en").format(n);

async function requestJson(path, options) {
  const response = await fetch(path, {cache:"no-store", ...options});
  let data;
  try { data = await response.json(); } catch { throw new Error("Server returned an unreadable response."); }
  if (!response.ok) throw new Error(data.error || "Request failed (" + response.status + ")");
  return data;
}
function notice(text) {
  const node = $("#toast");
  node.textContent = text;
  node.classList.add("show");
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => node.classList.remove("show"),4000);
}
function showError(text) {
  const node=$("#fatalError");
  node.hidden=false;
  node.textContent=text;
}
function switchView(view) {
  const section = $("#view-" + view);
  if (!section) return;
  activeView=view;
  $$(".view").forEach(node=>node.classList.toggle("active",node===section));
  $$(".nav-item[data-view]").forEach(button=>{
    const active = button.dataset.view===view;
    button.classList.toggle("active",active);
    if(active)button.setAttribute("aria-current","page");
    else button.removeAttribute("aria-current");
  });
  const labels={overview:"Overview",learners:"Learners",map:"Knowledge graph",
    reviews:"Review center",reports:"Cohort reports",coach:"Socratic practice",method:"Methodology"};
  $("#breadcrumb").textContent=labels[view] || "Overview";
  closeDrawer();
  if(view==="learners")renderLearners();
  if(view==="map")renderGraph();
  if(view==="reviews")renderReviews();
  if(view==="reports")renderReports();
  window.scrollTo({top:0,behavior:"instant"});
}
function closeDrawer() {
  $("#sidebar").classList.remove("open");
  $("#drawerShade").hidden=true;
  $("#menuButton").setAttribute("aria-expanded","false");
}

function renderMetrics() {
  const metrics=snapshot.metrics;
  const items=[
    ["♙",compact(metrics.learners),"Active learner records"],
    ["◎",fmt(metrics.meanMastery,0),"Mean observed mastery"],
    ["◷",compact(metrics.dueReviews),"Scheduled reviews due"],
    ["✧",compact(metrics.needsSupport),"Needs support by rule"]
  ];
  $("#kpiGrid").innerHTML=items.map(([icon,value,label])=>
    '<article class="kpi"><span class="kpi-icon">' + icon + '</span><div class="kpi-value">' + esc(value) +
    '</div><div class="kpi-label">' + esc(label) + '</div></article>'
  ).join("");
  $("#dateChip").textContent = new Date(snapshot.generatedAt).toLocaleDateString("en",
    {month:"short",day:"numeric",year:"numeric"});
  const label=$("#dataLabel");
  label.textContent=snapshot.sample ? "✧ SYNTHETIC DEMONSTRATION" : "● LOCAL WORKSPACE";
  label.classList.toggle("real",!snapshot.sample);
  $("#navLearners").textContent=compact(metrics.learners);
}
function renderOverview() {
  renderMetrics();
  $("#masteryBars").innerHTML=snapshot.concepts.map(c=>
    '<div class="mastery-row" title="' + esc(c.observed) + ' of ' + esc(snapshot.metrics.learners) + ' learners have an observation">' +
    '<span class="mastery-name">' + esc(c.name) + '</span><div class="bar-track"><div class="bar-fill ' +
    tone(c.mean) + '" style="width:' + (c.mean===null?0:Math.max(0,Math.min(100,c.mean*100))) +
    '%"></div></div><span class="mastery-val">' + fmt(c.mean) + '</span></div>'
  ).join("");
  const levels=snapshot.metrics.supportBands;
  const total=Math.max(1,snapshot.metrics.learners);
  const colors={"Needs support":"#ee806e","Monitor":"#f0ad50","On track":"#22b790","Unassessed":"#c3cad8"};
  let running=0;
  const gradient=Object.entries(levels).map(([name,count])=>{
    const start=running;
    running+=count/total*100;
    return colors[name] + " " + start.toFixed(2) + "% " + running.toFixed(2) + "%";
  }).join(",");
  $("#supportDonut").style.background="conic-gradient(" + gradient + ")";
  $("#donutCount").textContent=compact(snapshot.metrics.learners);
  $("#supportLegend").innerHTML=Object.entries(levels).map(([name,count])=>
    '<div class="legend-row"><i class="legend-dot" style="background:' + colors[name] +
    '"></i><span>' + esc(name) + '</span><strong>' + count + '</strong></div>'
  ).join("");
  $("#bottleneckList").innerHTML=snapshot.bottlenecks.slice(0,4).map((c,i)=>
    '<div class="focus-item"><span class="focus-icon">' + String(i+1).padStart(2,"0") +
    '</span><div class="focus-main"><strong>' + esc(c.name) + '</strong><p>' + c.observed +
    ' observed · ' + c.unobserved + ' not yet observed</p></div><span class="focus-end">' +
    fmt(c.mean) + '</span></div>'
  ).join("") || '<div class="empty-state">No observed mastery data yet.</div>';
  const priorities=snapshot.students.filter(s=>s.support!=="On track")
    .sort((a,b)=>b.dueCount-a.dueCount || (a.meanMastery??2)-(b.meanMastery??2)).slice(0,4);
  $("#priorityLearners").innerHTML=priorities.map((s,i)=>
    '<button type="button" class="priority-item" data-open-learner="' + esc(s.id) +
    '">' + personIcon(s.name,i) + '<span class="priority-main"><strong>' + esc(s.name) +
    '</strong><p>' + esc(s.recommendation) + '</p></span>' +
    statusPill(s.support) + '</button>'
  ).join("") || '<div class="empty-state">No learners currently flagged for follow-up.</div>';
}

function setOptions(select,groups,includeDefault) {
  select.innerHTML=(includeDefault?'<option value="all">All groups</option>':"")+
    groups.map(g=>'<option value="' + esc(g) + '">' + esc(g) + '</option>').join("");
}
function fillChoices() {
  const groups=snapshot.groups.map(g=>g.name);
  setOptions($("#groupFilter"),groups,true);
  setOptions($("#reviewGroupFilter"),groups,true);
  const learnerOptions=snapshot.students.map(s=>'<option value="' + esc(s.id) +
    '">' + esc(s.name) + '</option>').join("");
  $("#coachLearner").innerHTML=learnerOptions;
  $("#graphLearnerSelect").innerHTML='<option value="">Choose learner</option>'+learnerOptions;
  $("#coachConcept").innerHTML=snapshot.concepts.map(c=>'<option value="' + esc(c.name) +
    '">' + esc(c.name) + '</option>').join("");
  if(snapshot.students.length) {
    $("#coachLearner").value=snapshot.students[0].id;
    $("#graphLearnerSelect").value=snapshot.students[0].id;
  }
}
function renderLearners() {
  const query=$("#learnerSearch").value.trim().toLowerCase();
  const group=$("#groupFilter").value;
  const support=$("#supportFilter").value;
  const filtered=snapshot.students.filter(s=>
    (s.name.toLowerCase().includes(query)||s.id.toLowerCase().includes(query)) &&
    (group==="all"||group===s.group) &&
    (support==="all"||support===s.support)
  );
  $("#rosterCount").textContent=filtered.length+" shown";
  $("#learnerRows").innerHTML=filtered.map((s,i)=>
    '<tr><td><span class="cell-person">' + personIcon(s.name,i) +
    '<span><strong>' + esc(s.name) + '</strong><small>' + esc(s.id) + '</small></span></span></td>' +
    '<td>' + esc(s.group) + '</td><td>' + (
      s.meanMastery===null ? '<span>Not observed</span>' :
      '<div class="tiny-progress"><span class="tiny-track"><span style="width:' +
      s.meanMastery*100 + '%"></span></span><span>' + fmt(s.meanMastery) + '</span></div>'
    ) + '</td><td>' + s.observed + ' / ' + s.totalConcepts + '</td><td>' +
    s.dueCount + '</td><td>' + statusPill(s.support) +
    '</td><td><button type="button" class="row-action" data-open-learner="' +
    esc(s.id) + '">View ↗</button></td></tr>'
  ).join("")||'<tr><td colspan="7"><div class="empty-state">No learners match these filters.</div></td></tr>';
  if(selectedLearnerId && person(selectedLearnerId))renderDetail(selectedLearnerId);
}
function renderDetail(id) {
  const s=person(id);
  const host=$("#learnerDetail");
  if(!s)return;
  selectedLearnerId=id;host.hidden=false;
  const values=[["Observed mastery",fmt(s.meanMastery)],["Skills observed",s.observed+" / "+s.totalConcepts],
    ["Reviews due",String(s.dueCount)],["Low signals",String(s.weakCount)]];
  host.innerHTML=
    '<div class="detail-head"><div><p class="eyebrow">LEARNER SNAPSHOT</p><h2>' +
    esc(s.name) + '</h2><p>' + esc(s.group) + ' · ' + esc(s.id) +
    '</p></div><button type="button" class="detail-close" id="closeDetail" aria-label="Close learner details">✕</button></div>' +
    '<div class="detail-metrics">' + values.map(([label,value])=>'<div class="detail-metric"><strong>' +
    esc(value) + '</strong><small>' + esc(label) + '</small></div>').join("") +
    '</div><div class="detail-grid"><div><h3>Concept-level mastery</h3>' +
    s.concepts.map(c=>'<div class="detail-concept"><span>' + esc(c.concept) +
    '</span><div class="bar-track"><div class="bar-fill ' + tone(c.mastery) +
    '" style="width:' + (c.mastery===null?0:c.mastery*100) +
    '%"></div></div><strong>' + fmt(c.mastery) + '</strong></div>').join("") +
    '</div><div><h3>Recommended next step</h3><div class="recommendation-card"><p class="eyebrow">EXPLAINABLE RULE</p><strong>' +
    esc(s.recommendation) + '</strong><p>' + esc(s.support) +
    ' · ' + s.dueCount + ' scheduled reviews due. This is a heuristic signal, not a learner prognosis.</p></div>' +
    '<div class="detail-actions"><button type="button" class="button button-primary" data-coach-learner="' +
    esc(s.id) + '">Open guided practice ↗</button><button type="button" class="button button-outline" data-map-learner="' +
    esc(s.id) + '">View concept map</button></div></div></div>';
  $("#closeDetail").addEventListener("click",()=>{selectedLearnerId="";host.hidden=true;});
}

function buildGraphCoordinates(concepts) {
  const names=concepts.map(c=>c.name);
  const byName=Object.fromEntries(concepts.map(c=>[c.name,c]));
  const depths={};
  const visiting=new Set();
  function depth(name) {
    if(Number.isInteger(depths[name]))return depths[name];
    if(visiting.has(name))return 0;
    visiting.add(name);
    const req=(byName[name]?.requires||[]).filter(r=>names.includes(r));
    const d=req.length ? 1+Math.max(...req.map(depth)) : 0;
    visiting.delete(name);depths[name]=d;return d;
  }
  names.forEach(depth);
  const layers=Object.groupBy ? Object.groupBy(names,n=>depths[n]) : {};
  if(!Object.groupBy)names.forEach(n=>(layers[depths[n]]??=[]).push(n));
  const maxD=Math.max(1,...Object.values(depths));
  const positions={};
  for(const [d,items] of Object.entries(layers)) {
    items.forEach((name,i)=>{
      positions[name]={
        x:130 + (Number(d)/maxD)*720,
        y:70 + (i+1)*(525/(items.length+1))
      };
    });
  }
  return positions;
}
function graphValue(concept) {
  if(graphMode==="learner" && graphLearnerId) {
    const s=person(graphLearnerId);
    return s?.concepts.find(c=>c.concept===concept)?.mastery ?? null;
  }
  return conceptMap()[concept]?.mean ?? null;
}
function renderGraph() {
  const elements=snapshot.concepts;
  if(!elements.length){$("#conceptGraph").innerHTML="";return;}
  if(!selectedGraphConcept||!conceptMap()[selectedGraphConcept]) selectedGraphConcept=elements[0].name;
  const coords=buildGraphCoordinates(elements);
  const edges=elements.flatMap(c=>c.requires.filter(req=>coords[req]).map(req=>{
    const a=coords[req],b=coords[c.name];
    const dx=Math.max(32,(b.x-a.x)*.4);
    return '<path class="graph-edge" d="M '+(a.x+89)+' '+a.y+' C '+(a.x+89+dx)+' '+a.y+', '+
      (b.x-89-dx)+' '+b.y+', '+(b.x-89)+' '+b.y+'" marker-end="url(#arrow)"/>';
  }));
  const nodes=elements.map(c=>{
    const pos=coords[c.name],value=graphValue(c.name),classification=tone(value);
    return '<g class="graph-node ' + classification + (selectedGraphConcept===c.name?" selected":"") +
      '" data-graph-node="' + esc(c.name) +
      '" role="button" tabindex="0" aria-label="Inspect ' + esc(c.name) + '">' +
      '<rect x="' + (pos.x-89) + '" y="' + (pos.y-31) + '" rx="13" ry="13" width="178" height="65"/>' +
      '<text x="' + (pos.x-73) + '" y="' + (pos.y-4) + '" class="node-name">' +
      esc(c.name.length>18?c.name.slice(0,17)+"…":c.name) + '</text>' +
      '<text x="' + (pos.x-73) + '" y="' + (pos.y+16) + '" class="node-sub">' +
      (value===null?"Not observed":fmt(value)+" observed") + '</text></g>';
  });
  $("#conceptGraph").innerHTML=
    '<defs><marker id="arrow" markerWidth="9" markerHeight="9" refX="7" refY="3" orient="auto" markerUnits="strokeWidth"><path d="M0 0 L7 3 L0 6" fill="none" stroke="#b6bed2" stroke-width="1.3"/></marker></defs>' +
    edges.join("")+nodes.join("");
  $("#graphCount").textContent=elements.length+" connected concepts";
  $$("#conceptGraph [data-graph-node]").forEach(el=>{
    el.addEventListener("click",()=>{selectedGraphConcept=el.dataset.graphNode;renderGraph();});
    el.addEventListener("keydown",event=>{
      if(event.key==="Enter"||event.key===" "){event.preventDefault();selectedGraphConcept=el.dataset.graphNode;renderGraph();}
    });
  });
  const c=conceptMap()[selectedGraphConcept];
  const graphMastery=graphValue(c.name);
  $("#nodeDetails").innerHTML=
    '<p class="eyebrow">SELECTED CONCEPT</p><span class="focus-icon">⌘</span><h3>' + esc(c.name) +
    '</h3><p>' + masteryLabel(graphMastery) + '. Select another node to inspect its dependencies and observation coverage.</p>' +
    '<div class="node-stat"><span>Observed mastery</span><strong>' + fmt(graphMastery) + '</strong></div>' +
    '<div class="node-stat"><span>Cohort observations</span><strong>' + c.observed + " / " +
    snapshot.metrics.learners + '</strong></div><div class="node-stat"><span>Below 60% threshold</span><strong>' +
    c.weak + '</strong></div><div class="node-stat"><span>Prerequisite concepts</span><strong>' +
    (c.requires.length?esc(c.requires.join(", ")):"None") + '</strong></div>' +
    '<p class="chart-footnote">Mastery is estimated from recorded outcomes. Missing means unobserved, not failure.</p>' +
    '<div class="node-actions"><button type="button" class="button button-primary" data-practice-concept="' +
    esc(c.name) + '">Practice this skill ↗</button></div>';
}
function renderReviews(){
  const group=$("#reviewGroupFilter").value;
  const rows=snapshot.students.filter(s=>group==="all"||s.group===group)
    .flatMap(s=>s.concepts.filter(c=>c.status==="due").map(c=>({student:s,concept:c})))
    .sort((a,b)=>a.concept.dueAt.localeCompare(b.concept.dueAt));
  const dueLearners=new Set(rows.map(item=>item.student.id)).size;
  const sums=[["◷",rows.length,"Due practice items"],["♙",dueLearners,"Learners with scheduled work"],["◎",snapshot.metrics.concepts,"Mapped learning concepts"]];
  $("#reviewMetrics").innerHTML=sums.map(([icon,count,label])=>
    '<article class="review-stat"><span class="kpi-icon">' + icon + '</span><strong>' +
    count + '</strong><small>' + esc(label) + '</small></article>').join("");
  $("#reviewRows").innerHTML=rows.map((entry,i)=>{
    const due=new Date(entry.concept.dueAt).toLocaleDateString("en",{month:"short",day:"numeric",year:"numeric"});
    return '<tr><td><div class="cell-person">' + personIcon(entry.student.name,i) +
      '<span><strong>' + esc(entry.student.name) + '</strong><small>' + esc(entry.student.group) +
      '</small></span></div></td><td>' + esc(entry.concept.concept) + '</td><td>' +
      fmt(entry.concept.mastery) + '</td><td>' + esc(due) + '</td><td>Guided recall + feedback</td><td>' +
      '<button class="row-action" type="button" data-review-learner="' + esc(entry.student.id) +
      '" data-review-concept="' + esc(entry.concept.concept) + '">Practice ↗</button></td></tr>';
  }).join("") || '<tr><td colspan="6"><div class="empty-state">No scheduled reviews due in this group.</div></td></tr>';
}
function renderReports() {
  $("#groupRows").innerHTML=snapshot.groups.map((g,i)=>
    '<tr><td><div class="cell-person"><span class="focus-icon">' + String(i+1).padStart(2,"0") +
    '</span><span><strong>' + esc(g.name) + '</strong></span></div></td>' +
    '<td>' + g.learners + '</td><td>' +
    '<div class="tiny-progress"><span class="tiny-track"><span style="width:' +
    ((g.meanMastery||0)*100) + '%"></span></span><span>' + fmt(g.meanMastery) + '</span></div>' +
    '</td><td>' + g.dueReviews + '</td><td>' + g.needsSupport + '</td></tr>'
  ).join("")||'<tr><td colspan="5"><div class="empty-state">No cohorts available.</div></td></tr>';
  $("#reportDisclosure").textContent =
    (snapshot.sample?"SYNTHETIC DEMONSTRATION — all learners and outcomes are fictional. ":"") +
    "Snapshot generated " + new Date(snapshot.generatedAt).toLocaleString("en") +
    ". The mean is calculated only over observed concept states; learner counts and review dates are local workspace records. " +
    "Heuristic mastery and support indicators are not validated measures of learning gains or risk of dropout.";
}
function renderMethodology() {
  const d=snapshot.methodology;
  const details=[
    ["◎","Mastery estimates",d.mastery],
    ["◷","Scheduled reviews",d.due],
    ["✧","Support indicators",d.support],
    ["◇","Missing observations",d.missing],
    ["✳","Demo and privacy",snapshot.sample?d.demo:"This is local learner workspace data. No server-side identity verification or user authentication is provided."],
    ["⌘","Socratic practice","The local prompt generator produces deterministic questions, hints, and micro-actions. It is not an LLM, and does not automatically grade answers."],
    ["▥","Reporting integrity","No inferred attendance, demographic scoring, learning gain, predictions, or independently validated assessment claims."]
  ];
  $("#methodCards").innerHTML=details.map(([icon,title,body])=>
    '<article class="panel method-card"><span class="method-icon">' + icon +
    '</span><h3>' + esc(title) + '</h3><p>' + esc(body) + '</p></article>'
  ).join("");
}
function goPractice(id,concept) {
  if(id)$("#coachLearner").value=id;
  if(concept)$("#coachConcept").value=concept;
  $("#coachDialog").innerHTML='<div class="coach-bubble assistant-bubble">Choose Start fresh to begin Socratic practice. The prompts are deterministic and do not grade your answer.</div>';
  $("#coachAnswer").value="";
  $("#assessmentFeedback").textContent="";
  switchView("coach");
}
function addBubble(text,kind) {
  const node=document.createElement("div");
  node.className="coach-bubble "+(kind==="user"?"user-bubble":"assistant-bubble");
  node.textContent=text;
  $("#coachDialog").append(node);
  $("#coachDialog").scrollTop=$("#coachDialog").scrollHeight;
}
async function coachTurn(reset=false) {
  const id=$("#coachLearner").value;
  const concept=$("#coachConcept").value;
  if(!id||!concept)return notice("Choose a learner and concept.");
  const response=reset?"":$("#coachAnswer").value.trim();
  if(reset)$("#coachDialog").replaceChildren();
  if(response)addBubble(response,"user");
  $("#coachSend").disabled=true;
  try {
    const data=await requestJson("/api/tutor",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({studentId:id,concept,response})
    });
    addBubble(data.question+"\n\n"+data.hint+"\n\nNext: "+data.check,"assistant");
    $("#coachAnswer").value="";
  } catch(err){notice(err.message);}
  finally{$("#coachSend").disabled=false;}
}
async function recordAssessment(event) {
  event.preventDefault();
  const studentId=$("#coachLearner").value;
  const concept=$("#coachConcept").value;
  const choice=$('input[name="result"]:checked').value;
  const confidence=Number($("#confidence").value);
  if(!studentId)return notice("Choose a learner.");
  const button=$("#assessmentForm button[type=submit]");
  button.disabled=true;
  try {
    const data=await requestJson("/api/attempt",{
      method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({studentId,concept,correct:choice==="correct",confidence})
    });
    $("#assessmentFeedback").textContent="Recorded: "+fmt(data.before)+" → "+fmt(data.after)+
      ". Next review scheduled. "+(data.synthetic?"Synthetic learner record.":"");
    await reloadSnapshot();
    notice("Practice observation saved locally.");
  } catch(err){notice(err.message);}
  finally{button.disabled=false;}
}
async function reloadSnapshot(){
  snapshot=await requestJson("/api/dashboard");
  renderOverview();
  renderMethodology();
  renderLearners();
  renderReviews();
  renderReports();
  if(activeView==="map")renderGraph();
}
function saveExport(type) {
  const link=document.createElement("a");
  link.href="/api/export."+type;
  link.download="skillgraph-cohort-"+new Date().toISOString().slice(0,10)+"."+type;
  document.body.append(link);link.click();link.remove();
  notice(type.toUpperCase()+" export requested.");
}
function bindEvents() {
  $$("[data-view]").forEach(b=>b.addEventListener("click",()=>switchView(b.dataset.view)));
  $$("[data-goto]").forEach(b=>b.addEventListener("click",()=>switchView(b.dataset.goto)));
  document.addEventListener("click",event=>{
    const b=event.target.closest("[data-open-learner],[data-coach-learner],[data-map-learner],[data-review-learner],[data-practice-concept]");
    if(!b)return;
    if(b.dataset.openLearner){switchView("learners");renderDetail(b.dataset.openLearner);$("#learnerDetail").scrollIntoView({block:"start"});}
    if(b.dataset.coachLearner)goPractice(b.dataset.coachLearner);
    if(b.dataset.mapLearner){
      graphMode="learner";graphLearnerId=b.dataset.mapLearner;
      $("#mapCohort").classList.remove("active");$("#mapLearner").classList.add("active");
      $("#graphLearnerSelect").disabled=false;$("#graphLearnerSelect").value=graphLearnerId;
      switchView("map");
    }
    if(b.dataset.reviewLearner)goPractice(b.dataset.reviewLearner,b.dataset.reviewConcept);
    if(b.dataset.practiceConcept)goPractice(graphMode==="learner"?graphLearnerId:$("#coachLearner").value,b.dataset.practiceConcept);
  });
  ["#learnerSearch","#groupFilter","#supportFilter"].forEach(id=>
    $(id).addEventListener(id==="#learnerSearch"?"input":"change",renderLearners));
  $("#reviewGroupFilter").addEventListener("change",renderReviews);
  $("#mapCohort").addEventListener("click",()=>{
    graphMode="cohort";$("#mapCohort").classList.add("active");
    $("#mapLearner").classList.remove("active");
    $("#graphLearnerSelect").disabled=true;renderGraph();
  });
  $("#mapLearner").addEventListener("click",()=>{
    graphMode="learner";$("#mapLearner").classList.add("active");
    $("#mapCohort").classList.remove("active");
    $("#graphLearnerSelect").disabled=false;
    graphLearnerId=$("#graphLearnerSelect").value;renderGraph();
  });
  $("#graphLearnerSelect").addEventListener("change",event=>{graphLearnerId=event.target.value;renderGraph();});
  $("#coachStart").addEventListener("click",()=>coachTurn(true));
  $("#coachSend").addEventListener("click",()=>coachTurn(false));
  $("#assessmentForm").addEventListener("submit",recordAssessment);
  $("#confidence").addEventListener("input",event=>$("#confidenceValue").textContent=Number(event.target.value).toFixed(2));
  $("#topExport").addEventListener("click",()=>saveExport("csv"));
  $("#exportCsv").addEventListener("click",()=>saveExport("csv"));
  $("#exportJson").addEventListener("click",()=>saveExport("json"));
  $("#menuButton").addEventListener("click",()=>{
    const open=$("#sidebar").classList.toggle("open");
    $("#drawerShade").hidden=!open;
    $("#menuButton").setAttribute("aria-expanded",String(open));
  });
  $("#drawerShade").addEventListener("click",closeDrawer);
  window.addEventListener("keydown",event=>{if(event.key==="Escape")closeDrawer();});
}
async function main(){
  $("#year").textContent=String(new Date().getFullYear());
  bindEvents();
  try {
    snapshot=await requestJson("/api/dashboard");
    fillChoices();
    renderOverview();renderLearners();renderReviews();renderReports();renderMethodology();
    if(snapshot.concepts.length)selectedGraphConcept=snapshot.concepts[0].name;
    renderGraph();
    switchView("overview");
    if(snapshot.sample)notice("Showing clearly labeled synthetic demonstration data.");
  } catch(err){showError("Dashboard could not load: "+err.message+" Check that your workspace is initialized.");}
}
main();
