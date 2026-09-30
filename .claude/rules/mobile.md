---
description: 플러터 앱 화면·상태·저장소·푸시를 고치거나 테스트할 때, 저장한 값이 화면에서 되돌아가거나 응답이 엉뚱한 화면·기간에 붙을 때, 위젯 테스트가 끝나지 않고 멈출 때, 화면이 디자인과 다를 때.
paths:
  - "mobile/**"
---

# 플러터 앱 규칙

## 실행

```bash
cd mobile
flutter analyze                  # 이슈 0건이어야 한다
flutter test                     # 전체 위젯·단위 테스트
flutter run -d chrome --dart-define=USE_FIXTURES=false --dart-define=APP_API_TOKEN=<토큰>
```

- 빌드 주입값은 `lib/core/config.dart` 의 `API_BASE_URL`(기본 `http://localhost:8000/api/v1`)·`APP_API_TOKEN`·`USE_FIXTURES`(기본 true) 셋이다.
- **TEMP 경로에 한글이 있으면 flutter_tester 가 로드에 실패한다.** `TEMP=C:\tmp\fltemp` 처럼 ASCII 경로로 바꿔 돌린다.
- flutter 가 없는 PC 도 있다. `flutter --version` 이 안 되면 사용자에게 알리고 백엔드 쪽만 검증한다.
- 화면 확인은 웹 빌드를 폭 390 으로 띄워 `docs/design/screens/*.png` 와 대조한다.

## 상태·비동기 — 같은 종류가 화면 다섯 곳에서 나왔다

- **await 뒤에는 화면이 바뀌었을 수 있다.** 시트·피커·하위 화면에서 돌아오면 `mounted` 를 확인한다. 보기·기간을 바꾼 뒤 도착한 이전 요청의 응답은 버린다. 재조회가 실패하면 이전 값보다 오류를 먼저 보인다.
- **낙관적 갱신 실패는 실패한 필드·항목만 되돌린다.** 전체 스냅샷으로 되돌리면 겹쳐서 성공한 다른 저장까지 지운다. 겹친 저장은 직렬화하고, 가장 나중 저장이 화면을 정하며, 실패하면 마지막으로 서버가 확인한 값으로 돌아간다. 시나리오는 `test/features/optimistic_writes_test.dart` 에 더한다.
- **부수 작업 실패가 본 흐름을 막지 않게 한다.** 알림 권한 준비가 실패해도 시작 딥링크와 기기 등록은 진행한다.

## fixture·테스트

- 저장소는 `Api*`(dio) 와 `Fixture*`(`assets/fixtures/*.json`) 두 벌이다. 계약 예시가 바뀌면 fixture 도 같이 바꾼다.
- **Fixture 저장소는 에셋 번들 캐시를 쓰지 않는다**(`loadString(..., cache: false)`). 캐시된 Future 는 이전 위젯 테스트의 FakeAsync zone 에 묶여 다음 테스트에서 끝나지 않는다. 같은 문제를 Polecat 셋이 따로 고친 적이 있다.
- 위젯 테스트는 `test/helpers.dart` 의 도우미로 고정 시계·asset 캐시 비우기·`ProviderScope`(fixture 지연 0)로 감싼다.
- `Api*` 저장소 테스트는 dio 모의 어댑터로 메서드·경로·쿼리·본문을 확인한다.
- 새 테스트는 수정 전 코드에서 먼저 실패하는 것을 본다.

## 계약·디자인

- 계약은 `docs/api/app-api-v1.md` 다. 바뀌면 fixture 와 `app/api/v1/schemas/` 를 같은 PR 에서 맞춘다(규칙 `app-api`).
- 픽셀 기준은 `docs/design/source/*.dc.html` 이고 Figma 보다 우선한다. 기준 폭은 390 이다. 화면별 명세는 `docs/design/screens/`, 백엔드와의 차이는 `docs/design/gap-matrix.md`.
- `lib/app/router.dart` 와 `test/app/router_test.dart` 는 화면을 붙일 때마다 건드리는 파일이라 병렬 작업의 충돌 지점이다. 병합 뒤 쓰이지 않는 자리표시 화면을 지운다.
