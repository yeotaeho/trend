// 투어 설계용 그래프 토폴로지 분석 스크립트
const fs = require('fs');

function main() {
  const inPath = process.argv[2];
  const outPath = process.argv[3];
  if (!inPath || !outPath) throw new Error('usage: node ua-tour-analyze.js <input.json> <output.json>');

  const raw = JSON.parse(fs.readFileSync(inPath, 'utf8'));
  const nodes = raw.nodes || raw.fileNodes || [];
  const edges = raw.edges || [];
  const layers = raw.layers || [];

  const byId = new Map(nodes.map((n) => [n.id, n]));
  const known = (id) => byId.has(id);

  // A/B. fan-in / fan-out (파일 노드 사이 엣지만)
  const fanIn = new Map();
  const fanOut = new Map();
  for (const n of nodes) { fanIn.set(n.id, 0); fanOut.set(n.id, 0); }
  for (const e of edges) {
    if (!known(e.source) || !known(e.target) || e.source === e.target) continue;
    fanOut.set(e.source, fanOut.get(e.source) + 1);
    fanIn.set(e.target, fanIn.get(e.target) + 1);
  }
  const rank = (map, key) =>
    [...map.entries()]
      .map(([id, v]) => ({ id, [key]: v, name: byId.get(id).name }))
      .sort((a, b) => b[key] - a[key])
      .slice(0, 20);

  // C. 엔트리 포인트 후보
  const ENTRY_NAMES = new Set(['index.ts','index.js','main.ts','main.js','app.ts','app.js','server.ts','server.js','mod.rs','main.go','main.py','main.rs','manage.py','app.py','wsgi.py','asgi.py','run.py','__main__.py','Application.java','Main.java','Program.cs','config.ru','index.php','App.swift','Application.kt','main.cpp','main.c']);
  const fanOutVals = [...fanOut.values()].sort((a, b) => b - a);
  const fanInVals = [...fanIn.values()].sort((a, b) => a - b);
  const top10Out = fanOutVals[Math.floor(fanOutVals.length * 0.1)] ?? 0;
  const bot25In = fanInVals[Math.floor(fanInVals.length * 0.25)] ?? 0;

  const entryPointCandidates = nodes
    .map((n) => {
      const p = (n.filePath || '').replace(/\\/g, '/');
      const depth = p.split('/').length;
      let score = 0;
      if (n.type === 'document') {
        if (/^README\.md$/i.test(p)) score += 5;
        else if (depth === 1 && /\.md$/i.test(p)) score += 2;
      } else {
        if (ENTRY_NAMES.has(n.name)) score += 3;
        if (depth <= 2) score += 1;
        if (fanOut.get(n.id) >= top10Out) score += 1;
        if (fanIn.get(n.id) <= bot25In) score += 1;
      }
      return { id: n.id, score, name: n.name, type: n.type, summary: n.summary };
    })
    .filter((c) => c.score > 0)
    .sort((a, b) => b.score - a.score)
    .slice(0, 5);

  // D. BFS — 최상위 코드 엔트리 포인트에서 imports/calls 따라가기
  const adj = new Map(nodes.map((n) => [n.id, []]));
  for (const e of edges) {
    if ((e.type === 'imports' || e.type === 'calls') && known(e.source) && known(e.target)) {
      adj.get(e.source).push(e.target);
    }
  }
  const codeEntry = entryPointCandidates.find((c) => c.type !== 'document');
  const start = codeEntry ? codeEntry.id : nodes[0].id;
  const depthMap = { [start]: 0 };
  const order = [start];
  const queue = [start];
  while (queue.length) {
    const cur = queue.shift();
    for (const nx of adj.get(cur) || []) {
      if (depthMap[nx] === undefined) {
        depthMap[nx] = depthMap[cur] + 1;
        order.push(nx);
        queue.push(nx);
      }
    }
  }
  const byDepth = {};
  for (const [id, d] of Object.entries(depthMap)) (byDepth[d] ||= []).push(id);

  // E. 비코드 파일 인벤토리
  const pick = (types) =>
    nodes.filter((n) => types.includes(n.type)).map((n) => ({ id: n.id, name: n.name, type: n.type, summary: n.summary }));
  const nonCodeFiles = {
    documentation: pick(['document']),
    infrastructure: pick(['service', 'pipeline', 'resource']),
    data: pick(['table', 'schema', 'endpoint']),
    config: pick(['config']),
  };

  // F. 밀결합 클러스터
  const pairKey = (a, b) => (a < b ? a + '|' + b : b + '|' + a);
  const pairCount = new Map();
  for (const e of edges) {
    if (!known(e.source) || !known(e.target) || e.source === e.target) continue;
    if (!['imports', 'calls', 'depends_on', 'related'].includes(e.type)) continue;
    const k = pairKey(e.source, e.target);
    pairCount.set(k, (pairCount.get(k) || 0) + 1);
  }
  const clusters = [];
  const seedPairs = [...pairCount.entries()].filter(([, c]) => c >= 2).sort((a, b) => b[1] - a[1]);
  const used = new Set();
  for (const [k] of seedPairs) {
    const [a, b] = k.split('|');
    if (used.has(a) && used.has(b)) continue;
    const members = new Set([a, b]);
    for (const n of nodes) {
      if (members.has(n.id) || members.size >= 5) continue;
      let links = 0;
      for (const m of members) if (pairCount.has(pairKey(n.id, m))) links++;
      if (links >= 2) members.add(n.id);
    }
    let edgeCount = 0;
    const arr = [...members];
    for (let i = 0; i < arr.length; i++)
      for (let j = i + 1; j < arr.length; j++) edgeCount += pairCount.get(pairKey(arr[i], arr[j])) || 0;
    arr.forEach((x) => used.add(x));
    clusters.push({ nodes: arr, edgeCount });
    if (clusters.length >= 10) break;
  }

  // H. 노드 요약 인덱스
  const nodeSummaryIndex = {};
  for (const n of nodes) nodeSummaryIndex[n.id] = { name: n.name, type: n.type, filePath: n.filePath, summary: n.summary };

  const out = {
    scriptCompleted: true,
    entryPointCandidates,
    fanInRanking: rank(fanIn, 'fanIn'),
    fanOutRanking: rank(fanOut, 'fanOut'),
    bfsTraversal: { startNode: start, order, depthMap, byDepth },
    nonCodeFiles,
    clusters,
    layers: { count: layers.length, list: layers },
    nodeSummaryIndex,
    totalNodes: nodes.length,
    totalEdges: edges.length,
  };
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
  console.log('ok:', outPath, 'nodes', nodes.length, 'start', start);
}

try { main(); } catch (err) { console.error(err.stack || String(err)); process.exit(1); }
