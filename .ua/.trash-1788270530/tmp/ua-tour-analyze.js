// 투어 설계용 그래프 토폴로지 분석 — 팬인/팬아웃·엔트리포인트·BFS·클러스터 계산
const fs = require("fs");

const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) {
  console.error("usage: node ua-tour-analyze.js <input.json> <output.json>");
  process.exit(1);
}

let data;
try {
  data = JSON.parse(fs.readFileSync(inPath, "utf8"));
} catch (e) {
  console.error("input read/parse failed: " + e.message);
  process.exit(1);
}

const nodes = data.nodes || [];
const edges = data.edges || [];
const layers = data.layers || [];

const byId = new Map(nodes.map((n) => [n.id, n]));
const name = (id) => (byId.get(id) ? byId.get(id).name : id);

// A/B. fan-in / fan-out
const fanIn = new Map();
const fanOut = new Map();
for (const n of nodes) {
  fanIn.set(n.id, 0);
  fanOut.set(n.id, 0);
}
for (const e of edges) {
  if (fanOut.has(e.source)) fanOut.set(e.source, fanOut.get(e.source) + 1);
  if (fanIn.has(e.target)) fanIn.set(e.target, fanIn.get(e.target) + 1);
}
const rank = (m, key) =>
  [...m.entries()]
    .map(([id, v]) => ({ id, [key]: v, name: name(id) }))
    .sort((a, b) => b[key] - a[key])
    .slice(0, 20);

const fanInRanking = rank(fanIn, "fanIn");
const fanOutRanking = rank(fanOut, "fanOut");

// C. entry point candidates
const ENTRY_NAMES = new Set([
  "index.ts", "index.js", "main.ts", "main.js", "app.ts", "app.js",
  "server.ts", "server.js", "mod.rs", "main.go", "main.py", "main.rs",
  "manage.py", "app.py", "wsgi.py", "asgi.py", "run.py", "__main__.py",
  "Application.java", "Main.java", "Program.cs", "config.ru", "index.php",
  "App.swift", "Application.kt", "main.cpp", "main.c",
]);
const foutVals = [...fanOut.values()].sort((a, b) => b - a);
const finVals = [...fanIn.values()].sort((a, b) => a - b);
const foutTop10 = foutVals[Math.floor(foutVals.length * 0.1)] ?? 0;
const finBottom25 = finVals[Math.floor(finVals.length * 0.25)] ?? 0;

const scored = [];
for (const n of nodes) {
  let s = 0;
  const fp = n.filePath || "";
  const depth = fp.split("/").length;
  if (n.type === "document") {
    if (fp === "README.md") s += 5;
    else if (depth === 1 && fp.endsWith(".md")) s += 2;
  } else {
    if (ENTRY_NAMES.has(n.name)) s += 3;
    if (depth <= 2) s += 1;
    if (fanOut.get(n.id) >= foutTop10) s += 1;
    if (fanIn.get(n.id) <= finBottom25) s += 1;
  }
  if (s > 0) scored.push({ id: n.id, score: s, name: n.name, type: n.type, summary: n.summary || "" });
}
scored.sort((a, b) => b.score - a.score);
const entryPointCandidates = scored.slice(0, 5);

// D. BFS from top code entry point
const adj = new Map(nodes.map((n) => [n.id, []]));
for (const e of edges) {
  if ((e.type === "imports" || e.type === "calls") && adj.has(e.source)) {
    adj.get(e.source).push(e.target);
  }
}
const codeEntry = scored.find((c) => c.type !== "document");
const start = codeEntry ? codeEntry.id : nodes[0] && nodes[0].id;
const order = [];
const depthMap = {};
if (start) {
  const q = [start];
  depthMap[start] = 0;
  const seen = new Set([start]);
  while (q.length) {
    const cur = q.shift();
    order.push(cur);
    for (const nxt of adj.get(cur) || []) {
      if (!seen.has(nxt)) {
        seen.add(nxt);
        depthMap[nxt] = depthMap[cur] + 1;
        q.push(nxt);
      }
    }
  }
}
const byDepth = {};
for (const [id, d] of Object.entries(depthMap)) {
  (byDepth[d] = byDepth[d] || []).push(id);
}

// E. non-code inventory
const bucket = { documentation: [], infrastructure: [], data: [], config: [] };
const MAP = {
  document: "documentation",
  service: "infrastructure",
  pipeline: "infrastructure",
  resource: "infrastructure",
  table: "data",
  schema: "data",
  endpoint: "data",
  config: "config",
};
for (const n of nodes) {
  const b = MAP[n.type];
  if (b) bucket[b].push({ id: n.id, name: n.name, type: n.type, summary: n.summary || "" });
}

// F. clusters — mutual edges seeded, expanded by 2+ connections
const undirected = new Map();
const pairKey = (a, b) => (a < b ? a + "|" + b : b + "|" + a);
const edgeSet = new Set();
for (const e of edges) {
  edgeSet.add(e.source + ">" + e.target);
  const k = pairKey(e.source, e.target);
  undirected.set(k, (undirected.get(k) || 0) + 1);
}
const neighbors = new Map(nodes.map((n) => [n.id, new Set()]));
for (const e of edges) {
  if (neighbors.has(e.source)) neighbors.get(e.source).add(e.target);
  if (neighbors.has(e.target)) neighbors.get(e.target).add(e.source);
}
const clusters = [];
const claimed = new Set();
for (const e of edges) {
  if (!edgeSet.has(e.target + ">" + e.source)) continue; // not mutual
  if (claimed.has(e.source) || claimed.has(e.target)) continue;
  const members = new Set([e.source, e.target]);
  let grew = true;
  while (grew && members.size < 5) {
    grew = false;
    for (const n of nodes) {
      if (members.has(n.id) || claimed.has(n.id)) continue;
      let hits = 0;
      for (const m of members) if (neighbors.get(n.id) && neighbors.get(n.id).has(m)) hits++;
      if (hits >= 2) {
        members.add(n.id);
        grew = true;
        break;
      }
    }
  }
  let edgeCount = 0;
  for (const x of members) for (const y of members) if (x !== y && edgeSet.has(x + ">" + y)) edgeCount++;
  for (const m of members) claimed.add(m);
  clusters.push({ nodes: [...members], edgeCount });
}
clusters.sort((a, b) => b.edgeCount - a.edgeCount);

// H. summary index
const nodeSummaryIndex = {};
for (const n of nodes) {
  nodeSummaryIndex[n.id] = { name: n.name, type: n.type, summary: n.summary || "" };
}

const out = {
  scriptCompleted: true,
  entryPointCandidates,
  fanInRanking,
  fanOutRanking,
  bfsTraversal: { startNode: start, order, depthMap, byDepth },
  nonCodeFiles: bucket,
  clusters: clusters.slice(0, 10),
  layers: {
    count: layers.length,
    list: layers.map((l) => ({ id: l.id, name: l.name, description: l.description })),
  },
  nodeSummaryIndex,
  totalNodes: nodes.length,
  totalEdges: edges.length,
};

fs.writeFileSync(outPath, JSON.stringify(out, null, 1));
console.log("ok nodes=" + nodes.length + " edges=" + edges.length + " start=" + start);
