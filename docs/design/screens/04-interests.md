# 04 관심사

- 원본 HTML: [`../source/Interests.dc.html`](../source/Interests.dc.html) · Figma node `5:2` · 프레임 390 × 1340 (세로 스크롤) · 스크린샷 [04-interests.png](04-interests.png) (Figma)
- 하단 탭: **설정** 활성 (설정 하위, 뒤로가기)

## 목적

선별·판정 프롬프트에 들어가는 관심사 프로필을 편집한다. 자기소개·관심 없음 문장, 관심 카테고리(taxonomy) 선택, 주목 스택·저장소 키워드, 변화 종류(kind)별 점수 가중치.

## 레이아웃 (위 → 아래)

### 1. 하위 TopBar
| 요소 | 내용 | 스타일 | 인터랙션 |
|---|---|---|---|
| `back` | 20 | primary | 설정 루트 |
| 제목 | `관심사` | 18 / 600 | – |
| 우측 | `저장` | 14 / 600 / `#2D5BE3` | 명시 저장. 저장 전 뒤로가기는 확인 다이얼로그 |

### 2. SectionLabel `나를 한 줄로 (선별 프롬프트에 그대로 들어갑니다)`
### 3. 프로필 카드 — 기본 Card (padding 16, gap 12)
- 본문 14 / 400 / lh 1.6 / primary — `AI 시스템 개발자. LLM 애플리케이션·에이전트·MCP를 직접 만든다. 주력 스택: Python(FastAPI, SQLAlchemy, Pydantic), Postgres, Docker, TypeScript/Next.js.`
- 보조 줄 12 tertiary — `관심 없음: 채용·홍보·입문 튜토리얼·개발과 무관한 금융 콘텐츠`
- 카드 탭 → 두 필드 편집 (편집 UI 디자인 없음, 바텀시트 권장).

### 4. SectionLabel `카테고리 · 8 / 12 선택` (선택 수 동적)
### 5. 택소노미 그리드 — `grid 2열 (minmax(0,1fr))`, gap 8, `px 16`
TaxonomyCell — flex space-between, `padding 12px 14px`, radius 12, 1px 테두리.
- 좌 — 라벨 14 / 600, 그 아래 slug 11 `mono`.
- 우 — 체크 원 18×18 radius 9.
- **선택** — 배경·테두리 `#1C1B19`, 라벨 흰색, slug `#B8B4AB`, 체크 원 `#2D5BE3` 채움 + `check` 12 흰색.
- **미선택** — 흰 배경, 테두리 `#D9D5CC`, 라벨 primary, slug `#8A877F`, 체크 원은 1.5px `#D9D5CC` 빈 원.
- 탭 → 선택 토글, 섹션 라벨 카운트 갱신.

| 라벨 | slug | 샘플 |
|---|---|---|
| 새 모델·벤치마크 | `llm-model` | 선택 |
| 에이전트 패턴 | `agent` | 선택 |
| MCP·IDE·CLI | `mcp-tooling` | 선택 |
| 추론 최적화 | `inference-opt` | 선택 |
| RAG·검색 | `rag-retrieval` | – |
| 학습·파인튜닝 | `training-finetune` | – |
| Python 백엔드 | `python-backend` | 선택 |
| Next.js·React | `web-frontend` | 선택 |
| DevOps·인프라 | `devops-infra` | – |
| 안전·평가 | `ai-safety-eval` | – |
| 논쟁·가격·정책 | `dev-community` | 선택 |
| 영상 채널 | `video` | 선택 |

slug 12개는 `config/rules.yaml` `policy.taxonomy` 와 같은 순서·값이다 (선별이 항목마다 1~3개 고르는 어휘). 라벨은 앱 표시용이며 계약 4.0 `GET /meta` 가 준다.

### 6. SectionLabel `주목 스택 · 저장소`
### 7. 스택 칩 — flex wrap, gap 8, `px 16`
미선택 Chip (흰 배경, `#D9D5CC`, 13/500 `#55524B`) — `claude` `mcp` `langgraph` `fastapi` `pydantic` `next.js` `uv`, 마지막 `+ 추가` (같은 스타일).
- `+ 추가` → 키워드 입력 (디자인 없음). 삭제는 길게 눌러 확인 (디자인 없음).

### 8. SectionLabel `변화 종류별 가중치 (kind)`
### 9. kind 가중치 카드 — Card `padding 4px 16px`, gap 0, Row 6개 ([tokens Row](../tokens.md#row-row))
- 좌 — 라벨 15/500, 보조 줄 kind 코드 12 tertiary.
- 우 — 값 14 `mono` (음수 `#B5651D`, 그 밖 `#55524B`) + `chev` 16 `#B8B4AB`.
- 행 탭 → 숫자 편집 (디자인 없음). 스테퍼 −0.50 ~ +0.50, 단계 0.05.

| 라벨 | kind | 값 (HTML 그대로) |
|---|---|---|
| 메이저 릴리즈 | `release_major` | `+0` |
| 패치 릴리즈 | `release_patch` | `0` |
| 기법·논문 | `technique` | `0` |
| 서베이·전망 | `survey` | `−0.15` |
| 튜토리얼 | `tutorial` | `−0.05` |
| 홍보·구인 | `promo` | `−0.30` |

- 샘플 값은 main 의 `config/rules.yaml` `scoring.kind_weights` 와 같다.
- 디자인은 6행이다. `news`·`other` 는 행이 없고 앱은 이 둘을 편집하지 않는다 (서버 값을 그대로 돌려 보낸다, 계약 4.3).
- 표기는 `+0` 과 `0` 이 섞여 있다. 앱은 `+0.00` / `−0.15` 처럼 부호·소수 2자리로 통일하고 마이너스는 U+2212 를 쓴다.

### 10. TabBar — **설정** 활성

## 데이터 필드 · 설정값

| 필드 | 타입 | 예시 | 비고 |
|---|---|---|---|
| `profile.self_description` | string | `AI 시스템 개발자. …` | 선별·판정 프롬프트 정책 |
| `profile.not_interested` | string | `채용·홍보·…` | 화면에는 `관심 없음: ` 접두 |
| `taxonomy[]` | {slug, label}[] | 12개 | `GET /meta` |
| `selected_categories` | string[] | 8개 | `N / 12 선택` |
| `watch_keywords` | string[] | `claude, mcp, …` | `focus_stack` + `focus_repos` |
| `kind_weights` | map<kind, float> | `{survey: -0.15, …}` | 점수에 그대로 더한다 |

## 엣지
- 카테고리 0개면 저장 비활성. 최대 선택 수 제한은 없다.
- 프로필 문장이 길면 카드가 늘어난다.

## Figma 와 다른 점 (HTML 우선)
- 제목 웨이트 600, 헤더 높이 44 + 56.
- 택소노미 셀은 radius 12, `padding 12px 14px`, slug 11 `mono`, 선택 slug 색 `#B8B4AB` 다.
- 스택 칩 글자는 `#55524B` 다 (Figma 추출본 `#1C1B19`).
- kind 값은 `mono` 이고 0·양수 색은 `#55524B` 다 (추출본 `#1C1B19`). 행은 고정 64 가 아니라 `min-height 52` + `py 10` 이다.
