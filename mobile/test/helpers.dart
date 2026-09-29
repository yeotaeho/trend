// 테스트 도우미 — 위젯을 앱 테마로 띄우고, 화면 테스트용 fixture 오버라이드와 라우터 앱을 만든다.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:tech_radar/app/router.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/providers.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';

/// fixture 1번 카드(`delivered_at` 02:18Z)가 `42분 전` 이 되는 시각.
final DateTime fixtureNow = DateTime.utc(2026, 9, 24, 3);

Future<void> pumpInApp(WidgetTester tester, Widget child) {
  return tester.pumpWidget(
    MaterialApp(
      theme: buildAppTheme(),
      home: Scaffold(body: Center(child: child)),
    ),
  );
}

/// 지연 없는 fixture 저장소와 고정 시계. [extra] 는 저장소를 가짜로 바꿀 때 쓴다.
///
/// asset 캐시를 비운다. 앞 테스트의 가짜 시간 안에서 캐시한 Future 를 기다리면 멈춘다.
List<Override> fixtureOverrides({List<Override> extra = const []}) {
  rootBundle.clear();
  return [
    useFixturesProvider.overrideWithValue(true),
    fixtureStoreProvider.overrideWithValue(FixtureStore(delay: Duration.zero)),
    clockProvider.overrideWithValue(() => fixtureNow),
    ...extra,
  ];
}

/// 실제 라우터로 앱을 띄운다. 화면 폭은 디자인 프레임 390 이고, 카드가 다 보이게 길게 둔다.
Future<GoRouter> pumpRouterApp(
  WidgetTester tester, {
  String at = AppRoutes.feed,
  List<Override> extra = const [],
}) async {
  tester.view
    ..physicalSize = const Size(390, 2400)
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  final router = createRouter(initialLocation: at);
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: fixtureOverrides(extra: extra),
      child: MaterialApp.router(theme: buildAppTheme(), routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  return router;
}
