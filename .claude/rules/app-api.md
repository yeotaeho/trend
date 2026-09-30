---
description: 모바일 앱이 쓰는 /api/v1 엔드포인트·응답 스키마·쿼리·페이지네이션을 고치거나 추가할 때, 앱과 서버 응답이 어긋날 때(필드 누락·시각·"오늘" 집계·커서), 앱 계약 문서를 바꿀 때.
paths:
  - "app/api/v1/**"
  - "docs/api/**"
  - "mobile/assets/fixtures/**"
---

# 앱 API v1 규칙

계약서는 `docs/api/app-api-v1.md` 다. 코드보다 계약서가 먼저 바뀌고, 둘이 어긋나면 `v2-다중사용자-1차-구현서.md` 가 이긴다(계약서 10절).

- **세 곳을 같은 PR 에서 맞춘다.** 계약서, 백엔드 응답 모델(`app/api/v1/schemas/<영역>.py`), 앱 fixture(`mobile/assets/fixtures/*.json`). 계약서의 컬럼 표기("컬럼 변경 없음" 등)도 실제 마이그레이션과 대조한다. `notifications.level varchar(10)` 에 `cluster_dup`(11자)이 안 들어간 것을 계약서가 놓친 전례가 있다.
- **인증은 fail-closed 다.** 라우터 전체가 `deps.require_token` 을 거친다. `APP_API_TOKEN` 이 비면 전부 401 이다. 새 라우터도 `app/api/v1/__init__.py` 의 공용 라우터에 붙인다.
- **사용자는 `deps.current_user_id()` 로만 얻는다.** 모든 조회·쓰기를 그 `user_id` 로 거른다.
- **시각은 ISO-8601 UTC `Z`, ID 는 문자열이다.** "오늘" 은 두 뜻이다. 달력일(Asia/Seoul 자정, push·예산)과 최근 24시간(수집·걸러짐, 응답에 `window_hours`)을 섞지 않는다.
- **목록은 커서 페이지네이션이다**(`pagination.py`). 정렬 키가 같은 행은 `id` 내림차순으로 안정 정렬한다.
- **결정 로그 조회는 항목의 "마지막" 행 기준이다.** 탐색 후보·되살림·카테고리 모두 마지막 결정 행으로 판단한다. 같은 조건을 발송 잡과 API 가 따로 복제하지 않게 공용 함수(`explore_candidate` 등)로 둔다.
- **같은 판정을 다시 쓰면 시각을 유지한다.** `created_at` 이 밀리면 옛 판정이 "오늘 판정 수" 와 "최근 판정" 맨 위로 올라온다. 앱에서 정한 판정(`source=app`)은 리액션 폴링이 덮어쓰지 않는다.
- **설정 저장 동시성은 `users` 행 잠금이다.** 첫 저장 때 없는 `user_prefs` 행을 잠그면 동시 첫 저장이 유실된다. 잠금은 `FOR NO KEY UPDATE` 이고, 409 판정은 잠근 뒤의 저장값으로 한다.
