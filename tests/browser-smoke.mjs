import { chromium } from "playwright";
import { mkdir } from "node:fs/promises";

const origin = process.env.SKILLGRAPH_URL || "http://127.0.0.1:8765";
const screenshots = "screenshots";
await mkdir(screenshots, {recursive:true});
let browser;
let errors=[];
function assert(condition,message){if(!condition)throw new Error(message);}
async function main(){
  browser=await chromium.launch({headless:true,args:["--no-sandbox"]});
  const page=await browser.newPage({viewport:{width:1440,height:940},deviceScaleFactor:1,acceptDownloads:true});
  page.on("pageerror",err=>errors.push(err.message));
  page.on("console",msg=>{if(msg.type()==="error")errors.push("console: "+msg.text());});
  await page.goto(origin,{waitUntil:"domcontentloaded"});
  await page.locator(".kpi").first().waitFor({timeout:20000});
  assert(await page.locator(".kpi").count()===4,"Missing dashboard metric cards");
  assert(await page.locator("#kpiGrid").innerText().then(t=>t.includes("16")),"Demo cohort did not load");
  const barWidth=await page.locator(".mastery-bars .bar-fill").first().evaluate(el=>el.getBoundingClientRect().width);
  assert(barWidth>20,"Expected colored mastery bars to have visible width; got "+barWidth);
  await page.screenshot({path:screenshots+"/01-overview-desktop.png",fullPage:true});
  await page.locator('[data-view="learners"]').click();
  await page.locator("#learnerRows tr").first().waitFor();
  assert(await page.locator("#learnerRows tr").count()===16,"Expected sixteen fictional learners");
  await page.locator("#learnerSearch").fill("Amelia");
  assert(await page.locator("#learnerRows tr").count()===1,"Search did not filter learners");
  await page.locator("#learnerRows [data-open-learner]").click();
  await page.locator("#learnerDetail:not([hidden])").waitFor();
  await page.screenshot({path:screenshots+"/02-learner-detail.png",fullPage:true});
  await page.locator('[data-view="map"]').click();
  await page.locator(".graph-node").first().waitFor();
  assert(await page.locator(".graph-node").count()===9,"Knowledge map missing concepts");
  await page.locator("#mapLearner").click();
  await page.locator("#graphLearnerSelect").selectOption("learner-01");
  await page.locator('.graph-node[data-graph-node="Functions"]').click();
  assert((await page.locator("#nodeDetails").innerText()).includes("Functions"),"Node details did not update");
  await page.screenshot({path:screenshots+"/03-knowledge-map.png",fullPage:true});
  await page.locator('[data-view="reviews"]').click();
  await page.locator("#reviewRows tr").first().waitFor();
  assert(await page.locator("#reviewRows [data-review-learner]").count()>0,"No reviews in seeded cohort");
  await page.screenshot({path:screenshots+"/04-review-center.png",fullPage:true});
  await page.locator('[data-view="coach"]').click();
  await page.locator("#coachLearner").selectOption("learner-01");
  await page.locator("#coachConcept").selectOption("Python Essentials");
  await page.locator("#coachStart").click();
  await page.locator(".assistant-bubble").filter({hasText:"Hint:"}).waitFor();
  await page.locator("#coachAnswer").fill("A variable stores a value under a descriptive name.");
  await page.locator("#coachSend").click();
  await page.locator(".user-bubble").filter({hasText:"variable stores"}).waitFor();
  await page.locator("#confidence").fill("0.85");
  await page.locator("#assessmentForm button[type=submit]").click();
  await page.locator("#assessmentFeedback").getByText("Recorded:",{exact:false}).waitFor();
  await page.screenshot({path:screenshots+"/05-coaching-and-assessment.png",fullPage:true});
  await page.locator('[data-view="reports"]').click();
  await page.locator("#groupRows tr").first().waitFor();
  assert(await page.locator("#groupRows tr").count()===3,"Expected three learning groups");
  const downloadPromise=page.waitForEvent("download");
  await page.locator("#exportCsv").click();
  const download=await downloadPromise;
  assert(download.suggestedFilename().endsWith(".csv"),"CSV export failed");
  await page.screenshot({path:screenshots+"/06-cohort-reports.png",fullPage:true});
  await page.setViewportSize({width:390,height:844});
  await page.reload({waitUntil:"domcontentloaded"});
  await page.locator(".kpi").first().waitFor();
  await page.waitForTimeout(350);
  const overflow=await page.evaluate(()=>document.documentElement.scrollWidth>window.innerWidth+1);
  if(overflow) {
    const offenders=await page.evaluate(()=>Array.from(document.querySelectorAll("body *")).filter(el=>el.getBoundingClientRect().right>window.innerWidth+1 && getComputedStyle(el).display!=="none").slice(0,14).map(el=>({tag:el.tagName,id:el.id,cls:el.className?.baseVal||el.className,right:Math.round(el.getBoundingClientRect().right)})));
    throw new Error("Mobile dashboard has horizontal overflow: "+JSON.stringify(offenders));
  }
  await page.screenshot({path:screenshots+"/07-mobile-overview.png",fullPage:true});
  await page.locator("#menuButton").click();
  await page.locator("#sidebar.open").waitFor();
  await page.locator('[data-view="learners"]').click();
  await page.locator("#view-learners.active").waitFor();
  assert(await page.locator("#drawerShade").isHidden(),"Mobile drawer backdrop remained open");
  await page.screenshot({path:screenshots+"/08-mobile-learners.png",fullPage:true});
  assert(errors.length===0,"Browser exceptions: "+errors.join("; "));
  console.log("PASS browser: overview, search, learner details, graph, reviews, coaching, assessment, CSV and mobile");
}
try {await main();}
catch(err){console.error("FAIL browser:",err.stack || err);if(browser){const pages=browser.contexts().flatMap(ctx=>ctx.pages());if(pages[0])await pages[0].screenshot({path:screenshots+"/failure.png",fullPage:true}).catch(()=>{});}process.exitCode=1;}
finally {if(browser)await browser.close();}
