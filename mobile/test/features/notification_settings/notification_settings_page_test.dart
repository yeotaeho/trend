// 05 알림 설정 테스트 — fixture 샘플 값, 텔레그램 409 되돌림, 세그먼트·피커 PATCH 본문, 채널 보조 줄 규칙.
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/notification_settings/notification_settings_page.dart';

/// Fixture 저장소에 넘기면서 PATCH 본문을 모은다.
class _RecordingSettings implements SettingsRepository {
  _RecordingSettings(this._inner);

  final SettingsRepository _inner;
  final List<Map<String, Object?>> patches = [];

  @override
  Future<InterestsSettings> interests() => _inner.interests();

  @override
  Future<InterestsSettings> saveInterests(InterestsSettings settings) =>
      _inner.saveInterests(settings);

  @override
  Future<NotificationSettings> notifications() => _inner.notifications();

  @override
  Future<NotificationSettings> updateNotifications(Map<String, Object?> patch) {
    patches.add(patch);
    return _inner.updateNotifications(patch);
  }
}

Future<_RecordingSettings> _pump(
  WidgetTester tester, {
  Duration delay = Duration.zero,
}) async {
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final fixture = FixtureSettingsRepository(FixtureStore(delay: delay));
  // rootBundle 은 fake async 밖에서만 끝나므로 fixture 를 먼저 읽어 둔다.
  await tester.runAsync(fixture.notifications);
  final settings = _RecordingSettings(fixture);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [settingsRepositoryProvider.overrideWithValue(settings)],
      child: MaterialApp(
        theme: buildAppTheme(),
        home: const NotificationSettingsPage(),
      ),
    ),
  );
  await tester.pumpAndSettle();
  return settings;
}

AppToggle _toggleOf(WidgetTester tester, String title) => tester.widget(
  find.descendant(
    of: find.widgetWithText(ToggleRow, title),
    matching: find.byType(AppToggle),
  ),
);

List<DeliveryChoice> _selectedSegments(WidgetTester tester) => tester
    .widgetList<SegmentedControl<DeliveryChoice>>(
      find.byType(SegmentedControl<DeliveryChoice>),
    )
    .map((control) => control.selected)
    .toList();

Finder _inPicker(Finder finder, {int index = 0}) => find.descendant(
  of: find.byType(CupertinoPicker).at(index),
  matching: finder,
);

void main() {
  testWidgets('fixture 샘플 값을 디자인 문구대로 보여 준다', (tester) async {
    await _pump(tester);

    expect(find.text('알림 설정'), findsOneWidget);
    expect(find.text('#trend-alerts · 👍/👎 리액션 동기화'), findsOneWidget);
    expect(find.text('연결 안 됨'), findsOneWidget);
    expect(find.text('15건'), findsOneWidget);
    expect(find.text('23:00 – 08:00'), findsOneWidget);
    expect(find.text('Asia/Seoul · 무음 중엔 피드에만 쌓입니다'), findsOneWidget);
    expect(find.text('버전 형제 릴리즈는 제목에 병기'), findsOneWidget);
    expect(find.text('점수 경계 항목을 하루 1건 🧪로 보내 라벨을 모읍니다'), findsOneWidget);
    for (final band in ImportanceBand.values) {
      expect(find.text(band.label), findsOneWidget);
    }
    expect(_selectedSegments(tester), [
      DeliveryChoice.instant,
      DeliveryChoice.quiet,
      DeliveryChoice.feedOnly,
    ]);
    expect(_toggleOf(tester, '앱 푸시 (FCM)').value, isTrue);
    expect(_toggleOf(tester, 'Discord 채널').value, isTrue);
    expect(_toggleOf(tester, 'Telegram 봇').value, isFalse);
    expect(_toggleOf(tester, '같은 이슈 하루 1건').value, isTrue);
    expect(_toggleOf(tester, '탐색 슬롯').value, isTrue);
  });

  testWidgets('미연결 텔레그램을 켜면 먼저 ON 이 됐다가 409 로 OFF 로 돌아오고 안내한다', (tester) async {
    const delay = Duration(milliseconds: 300);
    final settings = await _pump(tester, delay: delay);

    await tester.tap(find.byWidget(_toggleOf(tester, 'Telegram 봇')));
    await tester.pump();
    expect(_toggleOf(tester, 'Telegram 봇').value, isTrue);

    await tester.pump(delay);
    await tester.pump();
    expect(_toggleOf(tester, 'Telegram 봇').value, isFalse);
    expect(find.text('연결 정보가 없는 채널은 켤 수 없습니다.'), findsOneWidget);
    expect(settings.patches.single, {
      'channels': {
        'telegram': {'enabled': true},
      },
    });
  });

  testWidgets('importance 3 세그먼트를 피드만으로 바꾸면 그 키만 PATCH 한다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(
      find.descendant(
        of: find.byType(SegmentedControl<DeliveryChoice>).at(1),
        matching: find.text('피드만'),
      ),
    );
    await tester.pumpAndSettle();

    expect(settings.patches.single, {
      'delivery_by_importance': {'mid': 'feed_only'},
    });
    expect(_selectedSegments(tester), [
      DeliveryChoice.instant,
      DeliveryChoice.feedOnly,
      DeliveryChoice.feedOnly,
    ]);
  });

  testWidgets('이미 선택된 세그먼트를 다시 누르면 PATCH 하지 않는다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(find.text('즉시').first);
    await tester.pumpAndSettle();

    expect(settings.patches, isEmpty);
  });

  testWidgets('토글은 바꾼 키만 PATCH 하고 화면에 남는다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(find.byWidget(_toggleOf(tester, '같은 이슈 하루 1건')));
    await tester.pumpAndSettle();
    await tester.tap(find.byWidget(_toggleOf(tester, '탐색 슬롯')));
    await tester.pumpAndSettle();

    expect(settings.patches, [
      {'dedupe_same_issue_daily': false},
      {
        'exploration_slot': {'enabled': false},
      },
    ]);
    expect(_toggleOf(tester, '같은 이슈 하루 1건').value, isFalse);
    expect(_toggleOf(tester, '탐색 슬롯').value, isFalse);
  });

  testWidgets('push 상한 피커에서 한 칸 올려 완료하면 16건을 저장한다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(find.text('15건'));
    await tester.pumpAndSettle();
    await tester.drag(_inPicker(find.text('15건')), const Offset(0, -36));
    await tester.pumpAndSettle();
    await tester.tap(find.text('완료'));
    await tester.pumpAndSettle();

    expect(settings.patches.single, {'daily_push_cap': 16});
    expect(find.text('16건'), findsOneWidget);
  });

  testWidgets('무음 시간 피커에서 시작을 한 시간 당기면 start·end 를 함께 보낸다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(find.text('23:00 – 08:00'));
    await tester.pumpAndSettle();
    await tester.drag(_inPicker(find.text('23:00')), const Offset(0, 36));
    await tester.pumpAndSettle();
    await tester.tap(find.text('완료'));
    await tester.pumpAndSettle();

    expect(settings.patches.single, {
      'quiet_hours': {'start': '22:00', 'end': '08:00'},
    });
    expect(find.text('22:00 – 08:00'), findsOneWidget);
  });

  testWidgets('피커를 값 그대로 완료하면 PATCH 하지 않는다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(find.text('15건'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('완료'));
    await tester.pumpAndSettle();

    expect(settings.patches, isEmpty);
  });

  group('채널 보조 줄', () {
    test('FCM 은 기기 0대면 등록된 기기 없음, 미연결이면 연결 안 됨', () {
      expect(
        fcmSubtitle(
          const FcmChannel(enabled: true, connected: true, deviceCount: 1),
        ),
        isNull,
      );
      expect(
        fcmSubtitle(
          const FcmChannel(enabled: true, connected: true, deviceCount: 0),
        ),
        '등록된 기기 없음',
      );
      expect(
        fcmSubtitle(
          const FcmChannel(enabled: false, connected: false, deviceCount: 0),
        ),
        '연결 안 됨',
      );
    });

    test('Discord 는 채널 이름과 리액션 동기화를 잇고, 미연결이면 연결 안 됨', () {
      expect(
        discordSubtitle(
          const DiscordChannel(
            enabled: true,
            connected: true,
            channelName: '#trend-alerts',
            reactionSync: true,
          ),
        ),
        '#trend-alerts · 👍/👎 리액션 동기화',
      );
      expect(
        discordSubtitle(
          const DiscordChannel(
            enabled: true,
            connected: true,
            reactionSync: true,
          ),
        ),
        '👍/👎 리액션 동기화',
      );
      expect(
        discordSubtitle(
          const DiscordChannel(
            enabled: false,
            connected: false,
            reactionSync: false,
          ),
        ),
        '연결 안 됨',
      );
    });

    test('무음 시간은 시작과 끝이 같으면 없음', () {
      expect(
        quietHoursLabel(
          const QuietHours(start: '00:00', end: '07:00', timezone: 'UTC'),
        ),
        '00:00 – 07:00',
      );
      expect(
        quietHoursLabel(
          const QuietHours(start: '00:00', end: '00:00', timezone: 'UTC'),
        ),
        '없음',
      );
    });
  });
}
