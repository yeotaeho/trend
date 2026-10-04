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
flutter run --dart-define-from-file=env/prod.json   # 운영 서버. 토큰은 git 제외 파일에만 둔다
```

- 빌드 주입값은 `lib/core/config.dart` 의 `API_BASE_URL`(기본 `http://localhost:8000/api/v1`)·`APP_API_TOKEN`·`USE_FIXTURES`(기본은 `API_BASE_URL` 을 줬으면 false, 아니면 true) 셋이다. 실행·토큰 절차는 `mobile/README.md`.
- **TEMP 경로에 한글이 있으면 flutter_tester 가 로드에 실패한다**(한글 경로가 도구를 깨뜨린 사건 09-02 asyncpg · 09-18 ssh · 09-28 flutter). `TEMP=C:\tmp\fltemp` 처럼 ASCII 경로로 바꿔 돌린다.
- flutter 가 없는 PC 도 있다. `flutter --version` 이 안 되면 사용자에게 알리고 백엔드 쪽만 검증한다.
- 화면 확인은 웹 빌드를 폭 390 으로 띄워 `docs/design/screens/*.png` 와 대조한다.

## 상태·비동기

> 독립 사건 둘 이상으로 관찰된 것만 둔다(괄호는 사건 날짜). 한 번 관찰은 `lessons/BANK.md` 에, 한 곳의 이유는 코드 주석·테스트에 있다(fixture 번들 캐시, 겹친 낙관적 쓰기).

- **await 뒤에는 화면이 바뀌었을 수 있다**(09-24, 09-28, 10-03 — 화면 여섯 곳). 시트·피커·하위 화면에서 돌아오면 `mounted` 를 확인한다. 보기·기간을 바꾼 뒤 도착한 이전 요청의 응답은 버린다. 재조회가 실패하면 이전 값보다 오류를 먼저 보인다. 다른 화면에서 온 신호는 첫 로딩 중에도 세어 두고, 그 확인과 상태 반영 사이에는 await 를 두지 않는다(`SavedController.build`). 화면이 사라져도 끝내야 하는 일(캐시 무효화 등)은 `mounted` 로 건너뛰지 말고, await 전에 잡아 둔 앱 수준 객체(`ScaffoldMessenger`·`ProviderScope.containerOf`)로 한다(10-05 05 찜 재알림).

## fixture·테스트

- 저장소는 `Api*`(dio) 와 `Fixture*`(`assets/fixtures/*.json`) 두 벌이다. 계약 예시가 바뀌면 fixture 도 같이 바꾼다.
- 위젯 테스트는 `test/helpers.dart` 의 도우미로 고정 시계·asset 캐시 비우기·`ProviderScope`(fixture 지연 0)로 감싼다.
- `Api*` 저장소 테스트는 dio 모의 어댑터로 메서드·경로·쿼리·본문을 확인한다.
- 새 테스트는 수정 전 코드에서 먼저 실패하는 것을 본다.

## 계약·디자인

- 계약은 `docs/api/app-api-v1.md` 다. 바뀌면 fixture 와 `app/api/v1/schemas/` 를 같은 PR 에서 맞춘다(규칙 `app-api`).
- 픽셀 기준은 `docs/design/source/*.dc.html` 이고 Figma 보다 우선한다. 기준 폭은 390 이다. 화면별 명세는 `docs/design/screens/`, 백엔드와의 차이는 `docs/design/gap-matrix.md`.
