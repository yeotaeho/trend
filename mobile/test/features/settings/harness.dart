// 설정 화면 테스트 도우미 — fixture 저장소로 앱 라우터를 띄우고, 관심사 PUT 본문을 캡처하는 fake 저장소.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:package_info_plus/package_info_plus.dart';
import 'package:tech_radar/app/router.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';

/// 테스트마다 부른다. 이전 테스트의 fake-async 구역에서 시작한 fixture 읽기 future 가
/// `rootBundle` 캐시에 남으면 다음 테스트에서 끝나지 않는다.
void setUpSettingsTests() {
  setUp(() {
    rootBundle.clear();
    PackageInfo.setMockInitialValues(
      appName: '기술 파악',
      packageName: 'dev.techradar.tech_radar',
      version: '0.1.0',
      buildNumber: '1',
      buildSignature: '',
    );
  });
}

/// fixture 구현에 위임하고 `saveInterests` 본문을 모아 둔다. [saveError] 가 있으면 저장 대신 던진다.
class CapturingSettingsRepository implements SettingsRepository {
  CapturingSettingsRepository(this._inner);

  final SettingsRepository _inner;
  final List<Map<String, dynamic>> savedBodies = [];
  Object? saveError;

  @override
  Future<InterestsSettings> interests() => _inner.interests();

  @override
  Future<InterestsSettings> saveInterests(InterestsSettings settings) async {
    savedBodies.add(settings.toJson());
    if (saveError case final error?) throw error;
    return _inner.saveInterests(settings);
  }

  @override
  Future<NotificationSettings> notifications() => _inner.notifications();

  @override
  Future<NotificationSettings> updateNotifications(
    Map<String, Object?> patch,
  ) => _inner.updateNotifications(patch);
}

/// 390 폭 세로로 긴 화면에 앱 라우터를 [at] 에서 띄운다. 설정 저장소는 같은 fixture 상태를 쓰는 캡처 저장소다.
Future<(GoRouter, CapturingSettingsRepository)> pumpSettingsApp(
  WidgetTester tester, {
  required String at,
}) async {
  tester.view
    ..physicalSize = const Size(390, 2000)
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final store = FixtureStore(delay: Duration.zero);
  final settings = CapturingSettingsRepository(
    FixtureSettingsRepository(store),
  );
  final router = createRouter(initialLocation: at);
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        fixtureStoreProvider.overrideWithValue(store),
        settingsRepositoryProvider.overrideWithValue(settings),
      ],
      child: MaterialApp.router(theme: buildAppTheme(), routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  return (router, settings);
}
