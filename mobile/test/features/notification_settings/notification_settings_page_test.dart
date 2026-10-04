// 05 알림 설정 테스트 — fixture 샘플 값, 텔레그램 409 되돌림, 세그먼트·피커 PATCH 본문, 찜 재알림, 채널 보조 줄 규칙.
import 'dart:async';

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
import 'package:tech_radar/features/settings/settings_providers.dart';

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

/// `meta()` 를 몇 번 읽었는지 센다. 저장 뒤 /meta 캐시를 버렸는지 본다.
class _CountingMeta implements MetaRepository {
  _CountingMeta(this._inner);

  final MetaRepository _inner;
  int calls = 0;

  @override
  Future<Meta> meta() {
    calls++;
    return _inner.meta();
  }
}

/// 마지막 [_pump] 가 붙인 /meta 저장소.
late _CountingMeta _meta;

/// [show] 를 주면 false 로 바꿔 05 를 닫을 수 있다(ProviderScope 는 남는다).
Future<_RecordingSettings> _pump(
  WidgetTester tester, {
  Duration delay = Duration.zero,
  ValueNotifier<bool>? show,
}) async {
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final store = FixtureStore(delay: delay);
  final fixture = FixtureSettingsRepository(store);
  // rootBundle 은 fake async 밖에서만 끝나므로 fixture 를 먼저 읽어 둔다.
  await tester.runAsync(fixture.notifications);
  final settings = _RecordingSettings(fixture);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        settingsRepositoryProvider.overrideWithValue(settings),
        // push 상한 범위는 /meta 에서 읽는다. 같은 store 라 이미 읽혀 있다.
        metaRepositoryProvider.overrideWithValue(
          _meta = _CountingMeta(FixtureMetaRepository(store)),
        ),
      ],
      child: MaterialApp(
        theme: buildAppTheme(),
        home: show == null
            ? const NotificationSettingsPage()
            : ValueListenableBuilder<bool>(
                valueListenable: show,
                builder: (_, visible, _) => visible
                    ? const NotificationSettingsPage()
                    : const Scaffold(), // 돌아간 앞 화면
              ),
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
    // 끄면 상한이 0 이라 라벨에서 숫자가 빠진다.
    expect(_toggleOf(tester, '같은 이슈 하루 상한').value, isFalse);
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

  testWidgets('찜 재알림 피커에서 한 칸 올려 완료하면 8일을 저장하고 /meta 를 다시 읽는다', (tester) async {
    final settings = await _pump(tester);
    expect(find.text('읽지 않은 찜을 앱 푸시로 한 번 다시 알립니다'), findsOneWidget);

    await tester.tap(find.text('7일 뒤'));
    await tester.pumpAndSettle();
    await tester.drag(_inPicker(find.text('7일 뒤')), const Offset(0, -36));
    await tester.pumpAndSettle();
    await tester.tap(find.text('완료'));
    await tester.pumpAndSettle();

    expect(settings.patches.single, {'resurface_after_days': 8});
    expect(find.text('8일 뒤'), findsOneWidget);
    expect(_meta.calls, 1);

    // 11 찜 안내 문구가 이 값을 /meta 로 읽는다. 저장했으면 다음에 다시 읽는다.
    await tester.tap(find.text('8일 뒤'));
    await tester.pumpAndSettle();
    expect(_meta.calls, 2);
  });

  testWidgets('찜 재알림 저장 중에 05 를 떠나도 끝나면 /meta 캐시를 버린다', (tester) async {
    const delay = Duration(milliseconds: 300);
    final show = ValueNotifier(true);
    final settings = await _pump(tester, delay: delay, show: show);

    await tester.tap(find.text('7일 뒤'));
    await tester.pump(delay); // /meta 읽기
    await tester.pumpAndSettle();
    await tester.drag(_inPicker(find.text('7일 뒤')), const Offset(0, -36));
    await tester.pumpAndSettle();
    await tester.tap(find.text('완료'));
    await tester.pump();
    show.value = false; // PATCH 가 끝나기 전에 화면을 닫는다
    await tester.pump();
    await tester.pump(delay);
    await tester.pump();

    expect(settings.patches.single, {'resurface_after_days': 8});
    final container = ProviderScope.containerOf(
      tester.element(find.byType(MaterialApp)),
    );
    unawaited(container.read(metaProvider.future));
    await tester.pump(delay);
    expect(_meta.calls, 2);
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

    test('무음 시간은 시작과 끝이 같으면 무음 끔', () {
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
        '무음 끔',
      );
    });
  });

  testWidgets('저장하면 되돌리기 스낵바가 뜨고 누르면 이전 값으로 PATCH 한다', (tester) async {
    final settings = await _pump(tester);

    await tester.tap(find.byWidget(_toggleOf(tester, '탐색 슬롯')));
    await tester.pumpAndSettle();
    expect(find.text('저장했습니다.'), findsOneWidget);

    await tester.tap(find.text('되돌리기'));
    await tester.pumpAndSettle();

    expect(settings.patches, [
      {
        'exploration_slot': {'enabled': false},
      },
      {
        'exploration_slot': {'enabled': true},
      },
    ]);
    expect(_toggleOf(tester, '탐색 슬롯').value, isTrue);
    expect(find.text('되돌렸습니다.'), findsOneWidget);
  });

  testWidgets('보낼 채널이 모두 꺼지면 저장 전에 묻고, 취소하면 보내지 않는다', (tester) async {
    final settings = await _pump(tester);

    // FCM 을 꺼도 디스코드가 남아 묻지 않는다. 찜 재알림 멈춤은 상태 줄에만 뜬다.
    await tester.tap(find.byWidget(_toggleOf(tester, '앱 푸시 (FCM)')));
    await tester.pumpAndSettle();
    expect(find.text('이대로 저장할까요?'), findsNothing);
    expect(find.byKey(const ValueKey('blocked-resurface_off')), findsOneWidget);

    await tester.tap(find.byWidget(_toggleOf(tester, 'Discord 채널')));
    await tester.pumpAndSettle();
    expect(find.text('이대로 저장할까요?'), findsOneWidget);
    expect(find.text(DeliveryBlocked.noChannel.label), findsOneWidget);
    await tester.tap(find.text('취소'));
    await tester.pumpAndSettle();
    expect(settings.patches, hasLength(1));
    expect(_toggleOf(tester, 'Discord 채널').value, isTrue);

    await tester.tap(find.byWidget(_toggleOf(tester, 'Discord 채널')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('저장'));
    await tester.pumpAndSettle();
    expect(settings.patches.last, {
      'channels': {
        'discord': {'enabled': false},
      },
    });
    expect(find.byKey(const ValueKey('blocked-no_channel')), findsOneWidget);
  });

  testWidgets('같은 이슈 토글은 저장만 알리고 되돌리기를 주지 않는다', (tester) async {
    await _pump(tester);

    await tester.tap(find.byWidget(_toggleOf(tester, '같은 이슈 하루 1건')));
    await tester.pumpAndSettle();

    expect(find.text('저장했습니다.'), findsOneWidget);
    expect(find.text('되돌리기'), findsNothing);
  });
}
