// 레이어 배정 생성기 — filenodes.json 의 모든 노드를 정확히 한 레이어에 배정하고 검증
const fs = require('fs');
const root = 'C:/project/trend';
const nodes = JSON.parse(fs.readFileSync(root + '/.ua/tmp/filenodes.json', 'utf8'));
const all = Array.isArray(nodes) ? nodes : (nodes.fileNodes || nodes.nodes);

const LAYERS = [
  { id: 'layer:api', name: 'API 레이어',
    description: 'GitHub 릴리스·텔레그램 피드백 웹훅을 수신하고 헬스체크를 제공하는 FastAPI 라우터 모음.' },
  { id: 'layer:collector', name: '수집 레이어',
    description: 'Source 프로토콜과 레지스트리를 축으로 GitHub Releases·RSS·YouTube 등 외부 소스를 폴링해 원시 항목을 가져오는 플러그인 계층.' },
  { id: 'layer:pipeline', name: '파이프라인 레이어',
    description: 'URL 정규화·pg_trgm 중복제거·규칙 필터·가중합 점수화·LLM 요약 판단을 순차 관문으로 처리하는 핵심 처리 계층.' },
  { id: 'layer:notification', name: '발송 레이어',
    description: 'Notifier 프로토콜과 텔레그램 어댑터, 그리고 알림 강도·하루 상한·무음 시간을 결정하는 발송 정책.' },
  { id: 'layer:orchestration', name: '잡·스케줄러 레이어',
    description: 'APScheduler 로 수집·파이프라인·발송 잡을 주기 실행하고, 수동 실행·백필용 CLI 를 제공하는 오케스트레이션 계층.' },
  { id: 'layer:data', name: '데이터 레이어',
    description: 'SQLAlchemy async 모델과 세션, Alembic 마이그레이션, 그리고 큐 역할까지 겸하는 Postgres 테이블 6종.' },
  { id: 'layer:core', name: '코어·설정 레이어',
    description: 'FastAPI 앱 진입점과 pydantic-settings 설정 로더, 구조화 로깅, 공용 Pydantic 스키마, 그리고 소스·규칙 YAML 과 프로젝트 설정.' },
  { id: 'layer:infrastructure', name: '인프라·배포 레이어',
    description: 'Docker 이미지와 Compose 서비스(app·caddy), Caddy 리버스 프록시, GHCR 빌드·SSH 배포로 이어지는 GitHub Actions CI/CD.' },
  { id: 'layer:test', name: '테스트 레이어',
    description: 'respx 로 HTTP 를 모킹하는 pytest 단위 테스트와 소스별 실제 응답 fixture.' },
  { id: 'layer:documentation', name: '문서 레이어',
    description: '제품 기획서·구현 설계서와 코딩 규약을 담은 에이전트 지침 문서.' },
];

const pick = (n) => {
  const p = n.filePath || '';
  const id = n.id;
  if (p.startsWith('tests/')) return 'layer:test';
  if (p.startsWith('app/api/')) return 'layer:api';
  if (p.startsWith('app/sources/')) return 'layer:collector';
  if (p.startsWith('app/pipeline/')) return 'layer:pipeline';
  if (p.startsWith('app/notify/')) return 'layer:notification';
  if (p.startsWith('app/jobs/') || p.startsWith('scripts/')) return 'layer:orchestration';
  if (p.startsWith('app/db/') || p === 'alembic.ini') return 'layer:data';
  if (/^app\/(main|config|log|schemas|__init__)\.py$/.test(p) || p.startsWith('config/')
      || p === '.env.example' || p === 'pyproject.toml' || p === '.serena/project.yml') return 'layer:core';
  if (/^(Dockerfile|docker-compose\.yml|Caddyfile|\.dockerignore)$/.test(p)
      || p.startsWith('.github/')) return 'layer:infrastructure';
  if (/\.md$/.test(p)) return 'layer:documentation';
  throw new Error('unassigned: ' + id + ' (' + p + ')');
};

const bucket = Object.fromEntries(LAYERS.map(l => [l.id, []]));
for (const n of all) bucket[pick(n)].push(n.id);

const out = LAYERS.map(l => ({ ...l, nodeIds: bucket[l.id] })).filter(l => l.nodeIds.length);
const total = out.reduce((s, l) => s + l.nodeIds.length, 0);
const seen = new Set(out.flatMap(l => l.nodeIds));
if (total !== all.length || seen.size !== all.length) {
  throw new Error(`coverage mismatch: assigned=${total} unique=${seen.size} expected=${all.length}`);
}

fs.mkdirSync(root + '/.ua/intermediate', { recursive: true });
fs.writeFileSync(root + '/.ua/intermediate/layers.json', JSON.stringify(out, null, 2), 'utf8');
console.log('layers:', out.length, 'total nodes:', total);
for (const l of out) console.log(' ', l.id, l.name, l.nodeIds.length);
