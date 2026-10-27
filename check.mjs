// Smoke-test the built site in headless Chrome with Framer, Google Fonts and YouTube
// image hosts blocked, so anything still loaded from them shows up as a failure.
// Usage: python3 serve.py & node check.mjs [http://localhost:8000]
import { spawn } from "node:child_process";
import { mkdtempSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const BASE = process.argv[2] ?? "http://localhost:8000";
const CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome";
const BLOCK = ["*://framerusercontent.com/*", "*://framer.com/*", "*://*.framer.com/*", "*://*.framerstatic.com/*",
  "*://fonts.gstatic.com/*", "*://fonts.googleapis.com/*", "*://i.ytimg.com/*"];
const sleep = ms => new Promise(r => setTimeout(r, ms));

const profile = mkdtempSync(join(tmpdir(), "check-"));
const chrome = spawn(CHROME, ["--headless=new", "--remote-debugging-port=9333", `--user-data-dir=${profile}`,
  "--window-size=1400,900", "--no-first-run", "about:blank"], { stdio: "ignore" });

let targets;
for (let i = 0; i < 50 && !targets; i++) {
  try { targets = await (await fetch("http://127.0.0.1:9333/json")).json(); } catch { await sleep(200); }
}
const ws = new WebSocket(targets.find(t => t.type === "page").webSocketDebuggerUrl);
await new Promise(r => (ws.onopen = r));
let id = 0;
const pending = new Map(), events = [];
ws.onmessage = e => {
  const m = JSON.parse(e.data);
  if (m.id && pending.has(m.id)) { pending.get(m.id)(m); pending.delete(m.id); } else events.push(m);
};
const send = (method, params = {}) => new Promise(r => { const i = ++id; pending.set(i, r); ws.send(JSON.stringify({ id: i, method, params })); });
const run = async expr => (await send("Runtime.evaluate", { expression: expr, awaitPromise: true, returnByValue: true })).result.result?.value;

await send("Network.enable"); await send("Runtime.enable"); await send("Page.enable");
await send("Network.setBlockedURLs", { urls: BLOCK });
await send("Network.setCacheDisabled", { cacheDisabled: true });

const problems = () => {
  const p = [];
  for (const e of events) {
    if (e.method === "Network.responseReceived" && e.params.response.status >= 400 && e.params.type !== "Document")
      p.push(`${e.params.response.status} ${e.params.response.url}`);
    if (e.method === "Network.loadingFailed" && e.params.blockedReason) p.push(`needs blocked host: ${e.params.blockedReason}`);
    if (e.method === "Network.requestWillBeSent" && /framer(usercontent|static)?\.com|gstatic|ytimg/.test(new URL(e.params.request.url).host))
      p.push(`external: ${e.params.request.url}`);
    if (e.method === "Runtime.exceptionThrown") p.push(`error: ${e.params.exceptionDetails.exception?.description?.split("\n")[0]}`);
    if (e.method === "Runtime.consoleAPICalled" && e.params.type === "error") p.push(`console.error: ${String(e.params.args[0]?.value ?? e.params.args[0]?.description).split("\n")[0]}`);
  }
  events.length = 0;
  return [...new Set(p)];
};
const pageState = `(()=>{const im=[...document.images];return{path:location.pathname+location.hash,text:document.body.innerText.length,
  broken:im.filter(i=>i.complete&&i.naturalWidth===0).length,fontsFailed:[...document.fonts].filter(f=>f.status==='error').length}})()`;

let failures = 0;
const report = (label, state, issues, ok) => {
  const bad = !ok || issues.length || state.broken || state.fontsFailed;
  if (bad) failures++;
  console.log(`${bad ? "FAIL" : "ok  "} ${label.padEnd(34)} ${state.path.slice(0, 50).padEnd(51)} text=${state.text} broken=${state.broken} fontsFailed=${state.fontsFailed}`);
  for (const i of issues) console.log(`       ${i.slice(0, 160)}`);
};

// 1. Load every page directly and scroll through it so lazy images load.
const slugs = await (async () => {
  await send("Page.navigate", { url: BASE + "/" }); await sleep(3000);
  return run(`[...new Set([...document.querySelectorAll('a[href*="portfolio/"]')].map(a=>a.getAttribute('href').split('/').pop().split('#')[0]))]`);
})();
events.length = 0;
for (const path of ["/", ...slugs.map(s => `/portfolio/${s}`)]) {
  await send("Page.navigate", { url: BASE + path }); await sleep(3000);
  await run(`(async()=>{for(let y=0;y<document.body.scrollHeight;y+=600){scrollTo(0,y);await new Promise(r=>setTimeout(r,150))}scrollTo(0,0)})()`);
  await sleep(2000);
  const s = await run(pageState);
  report(`load ${path === "/" ? "home" : "project"}`, s, problems(), s.text > 500);
}

// 2. Client-side navigation: home -> project card -> in-page Back -> card -> browser Back.
await send("Page.navigate", { url: BASE + "/" }); await sleep(3000); problems();
for (const slug of slugs) {
  await run(`document.querySelector('a[href*="${slug}"]').click()`); await sleep(2500);
  let s = await run(pageState);
  report("click card", s, problems(), s.path.endsWith(slug) && s.text > 500);
  await run(`[...document.querySelectorAll('a')].find(a=>a.getAttribute('href')==='../#projects')?.click()`); await sleep(2500);
  s = await run(pageState);
  report("in-page Back", s, problems(), s.path === "/#projects" && s.text > 500);
  await run(`document.querySelector('a[href*="${slug}"]').click()`); await sleep(2500); problems();
  await run(`history.back()`); await sleep(2500);
  s = await run(pageState);
  report("browser Back", s, problems(), s.path.startsWith("/") && !s.path.includes("portfolio") && s.text > 500);
}

// 3. Unknown URL shows the 404 page.
await send("Page.navigate", { url: BASE + "/no/such/page" }); await sleep(3000);
const s404 = await run(pageState);
report("404 page", s404, problems(), s404.text > 0);

ws.close(); chrome.kill();
await sleep(500);
rmSync(profile, { recursive: true, force: true });
console.log(failures ? `\n${failures} check(s) failed` : "\nall checks passed");
process.exit(failures ? 1 : 0);
