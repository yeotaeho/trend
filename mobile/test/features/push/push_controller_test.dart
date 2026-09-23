// 푸시 연동 테스트 — 기동·갱신 때 기기 등록 1회씩, fixture 모드 no-op, 알림 탭 딥링크, 포그라운드 스낵바·피드 새로고침.
import 'dart:async';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/app.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/providers.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/alert/alert_detail_page.dart';
import 'package:tech_radar/features/push/push_controller.dart';
import 'package:tech_radar/features/push/push_messaging.dart';

import '../../helpers.dart';

class _FakeMessaging implements PushMessaging {
  _FakeMessaging({this.initial});

  final PushMessage? initial;
  final refresh = StreamController<String>.broadcast();
  final foreground = StreamController<PushMessage>.broadcast();
  final opened = StreamController<PushMessage>.broadcast();
  int prepared = 0;

  @override
  Future<void> prepare() async => prepared++;

  @override
  Future<String?> getToken() async => 'token-1';

  @override
  Stream<String> get onTokenRefresh => refresh.stream;

  @override
  Stream<PushMessage> get onForeground => foreground.stream;

  @override
  Stream<PushMessage> get onOpened => opened.stream;

  @override
  Future<PushMessage?> initialMessage() async => initial;
}

class _FakeDevices implements DeviceRepository {
  final tokens = <String>[];

  @override
  Future<DeviceRegistration> register({
    required String token,
    required DevicePlatform platform,
    String? appVersion,
  }) async {
    tokens.add(token);
    return DeviceRegistration(
      id: '${tokens.length}',
      platform: platform,
      registeredAt: DateTime.utc(2026, 9, 24),
    );
  }

  @override
  Future<void> unregister(String token) async {}
}

/// 피드 조회 횟수를 센다.
class _CountingFeed implements FeedRepository {
  _CountingFeed(this._inner);

  final FeedRepository _inner;
  int feedCalls = 0;

  @override
  Future<TodayStats> todayStats() => _inner.todayStats();

  @override
  Future<CursorPage<Alert>> feed({
    FeedFilter filter = FeedFilter.all,
    String? cursor,
    int? limit,
  }) {
    feedCalls++;
    return _inner.feed(filter: filter, cursor: cursor, limit: limit);
  }
}

ProviderContainer _container(
  _FakeMessaging messaging,
  _FakeDevices devices, {
  required bool fixtures,
}) {
  final container = ProviderContainer(
    overrides: [
      useFixturesProvider.overrideWithValue(fixtures),
      deviceRepositoryProvider.overrideWithValue(devices),
      pushMessagingProvider.overrideWithValue(messaging),
    ],
  );
  addTearDown(container.dispose);
  return container;
}

Future<void> _pumpApp(
  WidgetTester tester,
  _FakeMessaging messaging, {
  _CountingFeed? feed,
}) async {
  tester.view
    ..physicalSize = const Size(390, 2400)
    ..devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: fixtureOverrides(
        extra: [
          pushMessagingProvider.overrideWithValue(messaging),
          if (feed != null) feedRepositoryProvider.overrideWithValue(feed),
        ],
      ),
      child: const TechRadarApp(),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  group('기기 등록', () {
    test('기동 때 1회, 토큰 갱신 때 1회 등록한다', () async {
      final messaging = _FakeMessaging();
      final devices = _FakeDevices();
      final container = _container(messaging, devices, fixtures: false);

      container.read(pushControllerProvider);
      await pumpEventQueue();
      expect(messaging.prepared, 1);
      expect(devices.tokens, ['token-1']);

      messaging.refresh.add('token-2');
      await pumpEventQueue();
      expect(devices.tokens, ['token-1', 'token-2']);
    });

    test('fixture 모드면 등록하지 않는다', () async {
      final messaging = _FakeMessaging();
      final devices = _FakeDevices();
      final container = _container(messaging, devices, fixtures: true);

      container.read(pushControllerProvider);
      await pumpEventQueue();
      messaging.refresh.add('token-2');
      await pumpEventQueue();
      expect(devices.tokens, isEmpty);
    });

    test('Firebase 가 없으면 푸시를 시작하지 않는다', () {
      final container = ProviderContainer();
      addTearDown(container.dispose);
      expect(container.read(pushControllerProvider), isNull);
    });
  });

  group('알림 탭', () {
    testWidgets('종료 상태에서 누른 알림은 기동 후 07 을 연다', (tester) async {
      await _pumpApp(
        tester,
        _FakeMessaging(
          initial: const PushMessage(
            data: {'alert_id': '18342', 'type': 'alert'},
          ),
        ),
      );
      expect(find.byType(AlertDetailPage), findsOneWidget);
    });

    testWidgets('백그라운드에서 누른 재알림도 07 을 연다', (tester) async {
      final messaging = _FakeMessaging();
      await _pumpApp(tester, messaging);
      expect(find.byType(AlertDetailPage), findsNothing);

      messaging.opened.add(
        const PushMessage(data: {'alert_id': '18342', 'type': 'resurface'}),
      );
      await tester.pumpAndSettle();
      expect(find.byType(AlertDetailPage), findsOneWidget);
    });
  });

  testWidgets('포그라운드 수신은 스낵바를 띄우고 피드를 새로 읽으며, 보기는 07 을 연다', (tester) async {
    final messaging = _FakeMessaging();
    final feed = _CountingFeed(
      FixtureFeedRepository(FixtureStore(delay: Duration.zero)),
    );
    await _pumpApp(tester, messaging, feed: feed);
    final before = feed.feedCalls;

    messaging.foreground.add(
      const PushMessage(
        title: '[릴리즈] MCP Python SDK v2.2.0',
        data: {'alert_id': '18342', 'type': 'alert'},
      ),
    );
    await tester.pumpAndSettle();
    expect(find.text('[릴리즈] MCP Python SDK v2.2.0'), findsOneWidget);
    expect(feed.feedCalls, before + 1);
    expect(find.byType(AlertDetailPage), findsNothing);

    await tester.tap(find.text('보기'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDetailPage), findsOneWidget);
  });
}
