// 아키텍처 구조 분석 스크립트 — 디렉터리 그룹·임포트 그래프·패턴 매칭 계산
const fs = require('fs');
const [, , inPath, outPath] = process.argv;
if (!inPath || !outPath) { console.error('usage: node ua-arch-analyze.js <in> <out>'); process.exit(1); }

try {
  const { fileNodes, importEdges, allEdges } = JSON.parse(fs.readFileSync(inPath, 'utf8'));
  const byId = new Map(fileNodes.map(n => [n.id, n]));
  const paths = fileNodes.map(n => n.filePath || '');

  // common directory prefix
  const segs = paths.filter(Boolean).map(p => p.split('/'));
  const prefix = [];
  if (segs.length) {
    const first = segs[0];
    for (let i = 0; i < first.length - 1; i++) {
      if (segs.every(s => s.length > i + 1 && s[i] === first[i])) prefix.push(first[i]); else break;
    }
  }
  const groupOf = (p) => {
    const s = p.split('/').slice(prefix.length);
    return s.length > 1 ? s[0] : '(root)';
  };

  const directoryGroups = {}, nodeTypeGroups = {}, groupByNode = {};
  for (const n of fileNodes) {
    const g = groupOf(n.filePath || n.id);
    (directoryGroups[g] = directoryGroups[g] || []).push(n.id);
    groupByNode[n.id] = g;
    (nodeTypeGroups[n.type] = nodeTypeGroups[n.type] || []).push(n.id);
  }

  // fan in/out + inter-group imports
  const fileFanIn = {}, fileFanOut = {}, inter = {}, intra = {}, touched = {};
  for (const e of importEdges) {
    fileFanOut[e.source] = (fileFanOut[e.source] || 0) + 1;
    fileFanIn[e.target] = (fileFanIn[e.target] || 0) + 1;
    const a = groupByNode[e.source], b = groupByNode[e.target];
    if (a === undefined || b === undefined) continue;
    touched[a] = (touched[a] || 0) + 1;
    if (b !== a) touched[b] = (touched[b] || 0) + 1;
    if (a === b) intra[a] = (intra[a] || 0) + 1;
    else inter[a + ' ' + b] = (inter[a + ' ' + b] || 0) + 1;
  }
  const interGroupImports = Object.entries(inter)
    .map(([k, count]) => { const [from, to] = k.split(' '); return { from, to, count }; })
    .sort((x, y) => y.count - x.count);
  const intraGroupDensity = {};
  for (const g of Object.keys(directoryGroups)) {
    const internalEdges = intra[g] || 0, totalEdges = touched[g] || 0;
    intraGroupDensity[g] = { internalEdges, totalEdges, density: totalEdges ? +(internalEdges / totalEdges).toFixed(2) : 0 };
  }

  // dominant dependency direction
  const seen = new Set(), dependencyDirection = [];
  for (const { from, to, count } of interGroupImports) {
    const key = [from, to].sort().join(' ');
    if (seen.has(key)) continue;
    seen.add(key);
    const rev = inter[to + ' ' + from] || 0;
    if (count > rev) dependencyDirection.push({ dependent: from, dependsOn: to });
    else if (rev > count) dependencyDirection.push({ dependent: to, dependsOn: from });
  }

  // cross-category (non-import) edges
  const cc = {};
  for (const e of allEdges) {
    const s = byId.get(e.source), t = byId.get(e.target);
    if (!s || !t) continue;
    const k = [s.type, t.type, e.type].join(' ');
    cc[k] = (cc[k] || 0) + 1;
  }
  const crossCategoryEdges = Object.entries(cc).map(([k, count]) => {
    const [fromType, toType, edgeType] = k.split(' ');
    return { fromType, toType, edgeType, count };
  }).filter(x => x.edgeType !== 'imports').sort((a, b) => b.count - a.count);

  // directory pattern matching
  const DIR = [
    [/^(routes|routers|api|controllers?|endpoints|handlers|serializers|blueprints)$/, 'api'],
    [/^(services?|core|lib|domain|logic|internal|signals|composables|mailers|jobs|channels)$/, 'service'],
    [/^(models?|db|data|persistence|repository|entities|entity|migrations|sql|database)$/, 'data'],
    [/^(components|views|pages|ui|layouts|screens)$/, 'ui'],
    [/^(middleware|plugins|interceptors|guards)$/, 'middleware'],
    [/^(utils?|helpers|common|shared|tools|pkg|templatetags)$/, 'utility'],
    [/^(config|constants|env|settings|management|commands)$/, 'config'],
    [/^(__tests__|tests?|specs?)$/, 'test'],
    [/^(types|interfaces|schemas?|contracts|dtos?|dto|request|response)$/, 'types'],
    [/^hooks$/, 'hooks'],
    [/^(store|state|reducers|actions|slices)$/, 'state'],
    [/^(assets|static|public)$/, 'assets'],
    [/^(cmd|bin)$/, 'entry'],
    [/^(docs|documentation|wiki)$/, 'documentation'],
    [/^(deploy|deployment|infra|infrastructure|docker|k8s|kubernetes|helm|charts|terraform|tf)$/, 'infrastructure'],
    [/^[.](github|gitlab|circleci)$/, 'ci-cd'],
    [/^scripts$/, 'utility'],
    [/^(pipeline|sources|notify)$/, 'service'],
  ];
  const patternMatches = {};
  for (const g of Object.keys(directoryGroups)) {
    const hit = DIR.find(([re]) => re.test(g));
    patternMatches[g] = hit ? hit[1] : (g === '(root)' ? 'root' : 'unknown');
  }

  // file-level pattern matching
  const filePattern = (p, type) => {
    const base = p.split('/').pop() || '';
    if (/^test_.*[.]py$|[.]test[.]|[.]spec[.]|_test[.]go$|Test[.]java$|_spec[.]rb$|Tests[.]cs$/.test(base)) return 'test';
    if (/^[.]github\/workflows\//.test(p) || /^[.]gitlab-ci[.]yml$|^Jenkinsfile$/.test(base)) return 'ci-cd';
    if (/^Dockerfile|^docker-compose|[.]tf$|[.]tfvars$|^Makefile$|^Caddyfile$|^[.]dockerignore$/.test(base)) return 'infrastructure';
    if (/[.]sql$/.test(base)) return 'data';
    if (/[.](graphql|gql|proto)$/.test(base)) return 'types';
    if (/[.](md|rst)$/.test(base)) return 'documentation';
    if (/^(wsgi|asgi)[.]py$/.test(base)) return 'config';
    if (/^(manage|main|__main__|__init__)[.]py$|^index[.](t|j)s$/.test(base)) return 'entry';
    if (/^(pyproject[.]toml|alembic[.]ini|Cargo[.]toml|go[.]mod|Gemfile|pom[.]xml|build[.]gradle|composer[.]json|package[.]json)$/.test(base)) return 'config';
    if (/^[.]env|[.]ya?ml$|[.]ini$|[.]toml$/.test(base)) return 'config';
    return type === 'file' ? 'code' : type;
  };
  const filePatternMatches = {};
  for (const n of fileNodes) filePatternMatches[n.id] = filePattern(n.filePath || '', n.type);

  // deployment topology
  const has = (re) => paths.some(p => re.test(p));
  const infraFiles = [...new Set(paths.filter(p => /Dockerfile|docker-compose|[.]tf$|Caddyfile|dockerignore|[.]github\/workflows\//.test(p)))];
  const deploymentTopology = {
    hasDockerfile: has(/Dockerfile/), hasCompose: has(/docker-compose/), hasK8s: has(/k8s|kubernetes|helm/),
    hasTerraform: has(/[.]tf$/), hasCI: has(/[.]github\/workflows\//), infraFiles,
  };

  // data pipeline
  const dataPipeline = {
    schemaFiles: [...new Set(paths.filter(p => /schemas?[.]py$|[.]sql$|[.]graphql$|[.]proto$/.test(p)))],
    migrationFiles: [...new Set(paths.filter(p => /alembic|migrations/.test(p)))],
    dataModelFiles: [...new Set(paths.filter(p => /models[.]py$|\/db\//.test(p)))],
    apiHandlerFiles: [...new Set(paths.filter(p => /\/api\//.test(p)))],
  };

  // documentation coverage
  const docPaths = paths.filter(p => /[.](md|rst)$/.test(p));
  const groupsWithDocs = new Set(docPaths.map(groupOf));
  const totalGroups = Object.keys(directoryGroups).length;
  const docCoverage = {
    groupsWithDocs: groupsWithDocs.size, totalGroups,
    coverageRatio: totalGroups ? +(groupsWithDocs.size / totalGroups).toFixed(2) : 0,
    undocumentedGroups: Object.keys(directoryGroups).filter(g => !groupsWithDocs.has(g)),
  };

  const filesPerGroup = {}, nodeTypeCounts = {};
  for (const [g, v] of Object.entries(directoryGroups)) filesPerGroup[g] = v.length;
  for (const [t, v] of Object.entries(nodeTypeGroups)) nodeTypeCounts[t] = v.length;

  const out = {
    scriptCompleted: true, commonPrefix: prefix.join('/'), directoryGroups, nodeTypeGroups,
    crossCategoryEdges, interGroupImports, intraGroupDensity, patternMatches, filePatternMatches,
    deploymentTopology, dataPipeline, docCoverage, dependencyDirection,
    fileStats: { totalFileNodes: fileNodes.length, filesPerGroup, nodeTypeCounts },
    fileFanIn, fileFanOut,
  };
  fs.writeFileSync(outPath, JSON.stringify(out, null, 2));
  console.log('OK', fileNodes.length, 'nodes ->', outPath);
} catch (err) {
  console.error((err && err.stack) || String(err));
  process.exit(1);
}
