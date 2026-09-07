// 레이어 배정 — 구조 분석 결과를 읽어 layers.json 생성
const fs = require('fs');
const root = 'C:/Users/COM-KMAB/Documents/trend/';
const r = JSON.parse(fs.readFileSync(root + '.ua/tmp/ua-arch-results.json', 'utf8'));
const ids = [].concat(...Object.values(r.directoryGroups));
const P = id => id.split(':').slice(1).join(':');
const base = s => s.split(':')[0];

const ROOT_CONFIG = ['.env.example', 'alembic.ini', 'pyproject.toml'];
const ROOT_INFRA = ['Dockerfile', 'docker-compose.yml', 'Caddyfile', '.dockerignore'];

const L = [
  { id: 'layer:api', name: 'API·웹훅 레이어',
    description: 'GitHub 릴리즈 웹훅, 텔레그램 봇 콜백, 디스코드 상호작용을 받는 FastAPI 라우터와 헬스체크 엔드포인트를 담당한다.',
    sel: s => s.startsWith('app/api/') },
  { id: 'layer:sources', name: '수집 소스 플러그인',
    description: 'RSS·GitHub Releases·YouTube 채널을 소스 하나당 파일 하나로 구현한 Source 프로토콜 수집기와 등록 레지스트리.',
    sel: s => s.startsWith('app/sources/') },
  { id: 'layer:pipeline', name: '검증 파이프라인',
    description: '적재·정규화·임베딩부터 중복 제거, exclude 규칙, LLM 선별·판정, 점수화까지 NEW 항목을 단계별 관문으로 통과시키는 핵심 로직.',
    sel: s => s.startsWith('app/pipeline/') },
  { id: 'layer:notify', name: '발송 어댑터',
    description: 'Notifier 프로토콜을 구현한 텔레그램·디스코드 어댑터와, 알림 강도·하루 상한·무음 시간을 결정하는 발송 정책.',
    sel: s => s.startsWith('app/notify/') },
  { id: 'layer:jobs', name: '잡 오케스트레이션·운영 스크립트',
    description: 'APScheduler 로 수집·파이프라인·발송 잡을 주기 실행하는 스케줄러와, 임베딩 백필·중복 임계값 보정·주간 튜닝 리포트 같은 수동 운영 스크립트.',
    sel: s => s.startsWith('app/jobs/') || s.startsWith('scripts/') },
  { id: 'layer:data', name: '데이터 레이어',
    description: 'SQLAlchemy 모델·세션·벡터 컬럼 타입, LLM 호출 예산 예약과 피드백 upsert, Alembic 마이그레이션과 items·decisions·summaries 등 테이블 정의.',
    sel: s => s.startsWith('app/db/') },
  { id: 'layer:core', name: '앱 코어·설정',
    description: 'FastAPI 앱과 스케줄러를 같은 프로세스로 띄우는 엔트리, pydantic-settings 설정 로더와 공용 Pydantic 스키마·구조화 로깅, 그리고 소스·규칙 YAML 및 프로젝트 빌드 설정.',
    sel: s => /^app\/[^/]+$/.test(s) || s.startsWith('config/') || ROOT_CONFIG.includes(s) },
  { id: 'layer:test', name: '테스트 레이어',
    description: 'respx 로 HTTP 를 모킹한 단위 테스트, Neon dev 브랜치를 대상으로 하는 통합 테스트, 소스별 실제 응답 fixture.',
    sel: s => s.startsWith('tests/') },
  { id: 'layer:infrastructure', name: '인프라·CI/CD',
    description: 'app·caddy 컨테이너 구성과 리버스 프록시 설정, ruff→mypy→pytest 검사 후 GHCR 이미지 빌드와 VM SSH 배포로 이어지는 GitHub Actions 워크플로.',
    sel: s => ROOT_INFRA.includes(base(s)) || s.startsWith('.github/') },
  { id: 'layer:documentation', name: '문서 레이어',
    description: '기획서·구현도와 검증 파이프라인 v2 설계·구현서, 코딩 규약을 담은 CLAUDE.md 등 프로젝트 설계 문서.',
    sel: s => /\.md$/.test(s) },
];

const out = [], seen = new Set();
for (const l of L) {
  const n = ids.filter(id => !seen.has(id) && l.sel(P(id)));
  n.forEach(i => seen.add(i));
  out.push({ id: l.id, name: l.name, description: l.description, nodeIds: n });
}
const missing = ids.filter(i => !seen.has(i));
console.log('missing:', missing);
console.log(out.map(o => o.id + ' ' + o.nodeIds.length).join('\n'));
console.log('sum', out.reduce((a, b) => a + b.nodeIds.length, 0), 'of', ids.length, 'layers', out.length);
if (missing.length === 0 && out.every(o => o.nodeIds.length)) {
  fs.mkdirSync(root + '.ua/intermediate', { recursive: true });
  fs.writeFileSync(root + '.ua/intermediate/layers.json', JSON.stringify(out, null, 2), 'utf8');
  console.log('written');
}
