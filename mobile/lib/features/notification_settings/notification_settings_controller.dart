// 05 알림 설정 상태 — GET 으로 읽고, 바꿀 키만 PATCH 하며 낙관적으로 먼저 반영한다.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/json_merge.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

final notificationSettingsProvider =
    AsyncNotifierProvider.autoDispose<
      NotificationSettingsController,
      NotificationSettings
    >(NotificationSettingsController.new);

class NotificationSettingsController
    extends AsyncNotifier<NotificationSettings> {
  @override
  Future<NotificationSettings> build() =>
      ref.watch(settingsRepositoryProvider).notifications();

  /// [patch] (`{"daily_push_cap": 20}` 처럼 바꿀 키만) 를 화면에 먼저 반영하고 저장한다.
  /// 실패하면 이전 상태로 되돌리고 예외를 다시 던진다 (계약 1.5).
  Future<void> save(Map<String, Object?> patch) async {
    final previous = state.value;
    if (previous == null) return;
    state = AsyncData(
      NotificationSettings.fromJson(deepMerge(previous.toJson(), patch)),
    );
    try {
      final saved = await ref
          .read(settingsRepositoryProvider)
          .updateNotifications(patch);
      if (ref.mounted) state = AsyncData(saved);
    } catch (_) {
      if (ref.mounted) state = AsyncData(previous);
      rethrow;
    }
  }
}
