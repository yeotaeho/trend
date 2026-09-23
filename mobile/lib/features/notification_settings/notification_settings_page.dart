// 05 알림 설정 화면 — 채널·알림 피로·중요도별 강도·탐색 슬롯. 모든 변경은 즉시 PATCH 한다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/labels.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import 'notification_settings_controller.dart';
import 'pickers.dart';

const EdgeInsets _rowCardPadding = EdgeInsets.symmetric(
  horizontal: 16,
  vertical: 4,
);

/// 하루 push 상한 범위 (계약 4.4).
const int _minPushCap = 1;
const int _maxPushCap = 50;

class NotificationSettingsPage extends ConsumerWidget {
  const NotificationSettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final settings = ref.watch(notificationSettingsProvider);
    return Scaffold(
      appBar: const SubTopBar(title: '알림 설정'),
      body: switch (settings) {
        AsyncData(:final value) => _Body(settings: value),
        AsyncError(:final error) => ErrorState(
          message: error is ApiException ? error.message : '설정을 불러오지 못했습니다.',
          onRetry: () => ref.invalidate(notificationSettingsProvider),
        ),
        _ => const LoadingState(),
      },
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.settings});

  final NotificationSettings settings;

  /// 저장하다 실패하면 컨트롤러가 되돌린 뒤 서버 `message` 를 스낵바로 보여 준다.
  Future<void> _save(
    BuildContext context,
    WidgetRef ref,
    Map<String, Object?> patch,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref.read(notificationSettingsProvider.notifier).save(patch);
    } on ApiException catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    void save(Map<String, Object?> patch) => _save(context, ref, patch);
    final channels = settings.channels;
    final quiet = settings.quietHours;

    Widget channelRow(
      NotifyChannel channel, {
      required bool enabled,
      String? subtitle,
      bool isLast = false,
    }) => ToggleRow(
      title: channel.label,
      subtitle: subtitle,
      value: enabled,
      isLast: isLast,
      onChanged: (value) => save({
        'channels': {
          channel.value: {'enabled': value},
        },
      }),
    );

    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        const SectionLabel('채널'),
        AppCard(
          padding: _rowCardPadding,
          gap: 0,
          children: [
            channelRow(
              NotifyChannel.fcm,
              enabled: channels.fcm.enabled,
              subtitle: fcmSubtitle(channels.fcm),
            ),
            channelRow(
              NotifyChannel.discord,
              enabled: channels.discord.enabled,
              subtitle: discordSubtitle(channels.discord),
            ),
            channelRow(
              NotifyChannel.telegram,
              enabled: channels.telegram.enabled,
              subtitle: channels.telegram.connected ? null : _notConnected,
              isLast: true,
            ),
          ],
        ),
        const SectionLabel('알림 피로 방지'),
        AppCard(
          padding: _rowCardPadding,
          gap: 0,
          children: [
            ValueRow(
              title: '하루 push 상한',
              value: '${settings.dailyPushCap}건',
              onTap: () async {
                final value = await showNumberPicker(
                  context,
                  title: '하루 push 상한',
                  initial: settings.dailyPushCap,
                  min: _minPushCap,
                  max: _maxPushCap,
                  format: (value) => '$value건',
                );
                if (!context.mounted) return;
                if (value != null && value != settings.dailyPushCap) {
                  save({'daily_push_cap': value});
                }
              },
            ),
            ValueRow(
              title: '무음 시간',
              subtitle: '${quiet.timezone} · 무음 중엔 피드에만 쌓입니다',
              value: quietHoursLabel(quiet),
              onTap: () async {
                final range = await showHourRangePicker(
                  context,
                  title: '무음 시간',
                  start: _hourOf(quiet.start),
                  end: _hourOf(quiet.end),
                );
                if (range == null || !context.mounted) return;
                final start = formatHour(range.$1);
                final end = formatHour(range.$2);
                if (start != quiet.start || end != quiet.end) {
                  save({
                    'quiet_hours': {'start': start, 'end': end},
                  });
                }
              },
            ),
            ToggleRow(
              title: '같은 이슈 하루 1건',
              subtitle: '버전 형제 릴리즈는 제목에 병기',
              value: settings.dedupeSameIssueDaily,
              isLast: true,
              onChanged: (value) => save({'dedupe_same_issue_daily': value}),
            ),
          ],
        ),
        const SectionLabel('중요도별 강도'),
        AppCard(
          children: [
            Column(
              crossAxisAlignment: CrossAxisAlignment.stretch,
              spacing: 14,
              children: [
                for (final band in ImportanceBand.values)
                  _DeliveryGroup(
                    band: band,
                    selected: _deliveryOf(band),
                    onChanged: (choice) => save({
                      'delivery_by_importance': {band.value: choice.value},
                    }),
                  ),
              ],
            ),
          ],
        ),
        const SectionLabel('실험'),
        AppCard(
          padding: _rowCardPadding,
          gap: 0,
          children: [
            ToggleRow(
              title: '탐색 슬롯',
              subtitle: '점수 경계 항목을 하루 1건 🧪로 보내 라벨을 모읍니다',
              value: settings.explorationSlot.enabled,
              isLast: true,
              onChanged: (value) => save({
                'exploration_slot': {'enabled': value},
              }),
            ),
          ],
        ),
      ],
    );
  }

  DeliveryChoice _deliveryOf(ImportanceBand band) {
    final delivery = settings.deliveryByImportance;
    return switch (band) {
      ImportanceBand.high => delivery.high,
      ImportanceBand.mid => delivery.mid,
      ImportanceBand.low => delivery.low,
    };
  }
}

class _DeliveryGroup extends StatelessWidget {
  const _DeliveryGroup({
    required this.band,
    required this.selected,
    required this.onChanged,
  });

  static const List<DeliveryChoice> _choices = [
    DeliveryChoice.instant,
    DeliveryChoice.quiet,
    DeliveryChoice.feedOnly,
  ];

  final ImportanceBand band;
  final DeliveryChoice selected;
  final ValueChanged<DeliveryChoice> onChanged;

  @override
  Widget build(BuildContext context) {
    return Column(
      crossAxisAlignment: CrossAxisAlignment.start,
      children: [
        Padding(
          padding: const EdgeInsets.only(bottom: 8),
          child: Text(band.label, style: AppText.labelGroup),
        ),
        SegmentedControl<DeliveryChoice>(
          values: _choices,
          selected: selected,
          labelOf: (choice) => choice.label,
          onChanged: (choice) {
            if (choice != selected) onChanged(choice);
          },
        ),
      ],
    );
  }
}

const String _notConnected = '연결 안 됨';

/// 미연결이면 `연결 안 됨`, 기기 0대면 `등록된 기기 없음`, 그 밖엔 보조 줄 없음.
String? fcmSubtitle(FcmChannel fcm) {
  if (!fcm.connected) return _notConnected;
  return fcm.deviceCount == 0 ? '등록된 기기 없음' : null;
}

/// `{channel_name} · 👍/👎 리액션 동기화`. 미연결이면 `연결 안 됨`.
String? discordSubtitle(DiscordChannel discord) {
  if (!discord.connected) return _notConnected;
  final parts = [
    ?discord.channelName,
    if (discord.reactionSync) '👍/👎 리액션 동기화',
  ];
  return parts.isEmpty ? null : parts.join(' · ');
}

/// `23:00 – 08:00`. 시작과 끝이 같으면 무음이 없다 (계약 4.4).
String quietHoursLabel(QuietHours quiet) =>
    quiet.start == quiet.end ? '없음' : '${quiet.start} – ${quiet.end}';

int _hourOf(String hhmm) => int.tryParse(hhmm.split(':').first) ?? 0;
