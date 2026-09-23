# 04 관심사

- Figma node: `5:2` · 프레임 390 × 1340 (세로 스크롤) · 스크린샷: [04-interests.png](04-interests.png)
- 하단 탭: **설정** 활성 (설정 하위 화면, 좌상단 뒤로가기)

## 목적

선별(LLM 필터) 프롬프트에 들어가는 사용자 관심사 프로필을 편집한다: 한 줄 자기소개/제외 주제, 관심 카테고리(택소노미) 선택, 주목 스택·저장소 키워드, 변화 종류(kind)별 점수 가중치.

## 레이아웃 (위 → 아래)

### 1. TopBar (`5:3`) — 높이 77, 뒤로가기 헤더
| 요소 | 내용 | 스타일 | 인터랙션 |
|---|---|---|---|
| `icon/back` 20×20 | 좌측 x=16 | `#1C1B19` | 탭 → 이전 화면(설정 루트) |
| 제목 | `관심사` | Bold 18 / lh 1.4 (텍스트 높이 25) | – |
| 우측 텍스트 버튼 | `저장` | SemiBold 14 `#2D5BE3` | 탭 → 화면 전체 변경사항 저장 (명시적 저장 모델; 저장 전 뒤로가기 시 확인 다이얼로그 권장) |

### 2. SectionLabel `나를 한 줄로 (선별 프롬프트에 그대로 들어갑니다)`
### 3. 프로필 카드 (`5:13`, 358×127) — 편집 가능한 텍스트 영역
- 본문 (Regular 14 / lh 1.55, `#1C1B19`): `AI 시스템 개발자. LLM 애플리케이션·에이전트·MCP를 직접 만든다. 주력 스택: Python(FastAPI, SQLAlchemy, Pydantic), Postgres, Docker, TypeScript/Next.js.`
- 보조 줄 (Regular 12 `#8A877F`): `관심 없음: 채용·홍보·입문 튜토리얼·개발과 무관한 금융 콘텐츠`
- 인터랙션: 카드 탭 → 멀티라인 편집 (두 필드: 자기소개 / 관심 없음). 편집 UI는 디자인 없음 — 인라인 TextField 또는 바텀시트 권장.

### 4. SectionLabel `카테고리 · 8 / 12 선택` (선택 수 / 전체 수 동적)
### 5. 택소노미 그리드 (`5:18`) — 2열, 셀 175×58, 열 간격 8, 행 간격 8, 좌우 padding 16
TaxonomyCell: padding `14` 좌, 제목(SemiBold 14, lh 20) + slug(Regular 10~11, lh 14), 우측 18×18 체크 원.
- **선택**: 배경 `#1C1B19`, 제목 흰색, slug `#8A877F`~연회색, 체크 원 `#2D5BE3` 채움 + 흰 `icon/check`(12)
- **미선택**: 흰 배경, 1px `#D9D5CC` 테두리, 제목 `#1C1B19`, slug `#8A877F`, 체크 원 = 1px `#D9D5CC` 빈 원
- radius 10 (스크린샷 추정), 탭 → 선택 토글, 상단 `N / 12 선택` 갱신

| 표시명 | slug | 샘플 상태 |
|---|---|---|
| 새 모델·벤치마크 | `llm-model` | 선택 |
| 에이전트 패턴 | `agent` | 선택 |
| MCP·IDE·CLI | `mcp-tooling` | 선택 |
| 추론 최적화 | `inference-opt` | 선택 |
| RAG·검색 | `rag-retrieval` | 미선택 |
| 학습·파인튜닝 | `training-finetune` | 미선택 |
| Python 백엔드 | `python-backend` | 선택 |
| Next.js·React | `web-frontend` | 선택 |
| DevOps·인프라 | `devops-infra` | 미선택 |
| 안전·평가 | `ai-safety-eval` | 미선택 |
| 논쟁·가격·정책 | `dev-community` | 선택 |
| 영상 채널 | `video` | 선택 |

### 6. SectionLabel `주목 스택 · 저장소`
### 7. 스택 칩 (`5:103`) — wrap 레이아웃, gap 8, 칩 높이 34
칩: 흰 배경, 1px `#D9D5CC`, radius 20(pill), px 14, Medium 13 `#1C1B19`.
- 값: `claude`, `mcp`, `langgraph`, `fastapi`, `pydantic`, `next.js`, `uv`
- 마지막 칩 `+ 추가` → 키워드 입력 (입력 UI 디자인 없음, 다이얼로그/바텀시트 권장)
- 기존 칩 삭제 방법은 디자인에 없음 → 길게 누르기 또는 칩 탭 시 삭제 확인 권장

### 8. SectionLabel `변화 종류별 가중치 (kind)`
### 9. kind 가중치 카드 (`5:125`, 358×392) — 행 6개, 각 64 높이, 행 사이 1px 구분선 `#EFECE6`
Row: 좌측 제목(Medium 15 `#1C1B19`) + 아래 kind 코드(Regular 12 `#8A877F`), 우측 값(14, 양수/0은 `#1C1B19`, 음수는 `#B5651D`) + `icon/chev` 16.
탭 → 가중치 편집(디자인 없음). 권장: 바텀시트 스테퍼/슬라이더, 범위 −0.50 ~ +0.50, 단계 0.05.

| 표시명 | kind | 값 |
|---|---|---|
| 메이저 릴리즈 | `release_major` | `+0` |
| 패치 릴리즈 | `release_patch` | `0` |
| 기법·논문 | `technique` | `0` |
| 서베이·전망 | `survey` | `−0.15` |
| 튜토리얼 | `tutorial` | `−0.05` |
| 홍보·구인 | `promo` | `−0.30` |

값 표기: 부호 포함 소수 2자리(0은 `0`, `+0`처럼 부호 생략/포함 혼재 — `+0.00` 형식 통일 권장), 마이너스는 유니코드 `−`(U+2212).

### 10. TabBar — 공통, **설정** 활성

## 데이터 필드 · 설정값

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `profile.self_description` | string (multiline) | `AI 시스템 개발자. LLM 애플리케이션…` | 선별 프롬프트에 그대로 삽입 |
| `profile.not_interested` | string | `채용·홍보·입문 튜토리얼·개발과 무관한 금융 콘텐츠` | 화면에는 `관심 없음: ` 접두로 표시 |
| `taxonomy[]` | {slug, label}[] | 12개 (위 표) | 카테고리 전체 목록 (서버 제공 권장) |
| `selected_categories` | string[] (slug) | 8개 | `N / 12 선택` 카운트 |
| `watch_keywords` | string[] | `claude, mcp, langgraph, fastapi, pydantic, next.js, uv` | 주목 스택·저장소 |
| `kind_weights` | map<kind, float> | `{release_major:0, release_patch:0, technique:0, survey:-0.15, tutorial:-0.05, promo:-0.30}` | 점수 가산/감점 |

## 빈 상태 / 엣지
- 카테고리 0개 선택 시 저장 비활성화 권장. 최대 선택 수 제한은 디자인에 없음(12개 전부 가능).
- 프로필 문장이 길면 카드 높이가 늘어남(고정 높이 아님).
