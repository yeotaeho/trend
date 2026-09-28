// 05 알림 설정 상태 — GET 으로 읽고, 바꿀 키만 PATCH 하며 낙관적으로 먼저 반영한다. 저장은 한 번에 하나씩.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/json_merge.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repositories.dart';
import '../../data/repositories/repository_providers.dart';

final notificationSettingsProvider =
    AsyncNotifierProvider.autoDispose<
      NotificationSettingsController,
      NotificationSettings
    >(NotificationSettingsController.new);

class NotificationSettingsController
    extends AsyncNotifier<NotificationSettings> {
  /// 서버가 마지막으로 돌려준 설정. 마지막 저장이 실패하면 이 값으로 되돌린다.
  late NotificationSettings _confirmed;

  /// 저장은 앞 요청이 끝난 뒤 보낸다. 응답이 요청 순서대로 와야 마지막 응답이 최종 상태다.
  Future<void> _queue = Future.value();
  int _latest = 0;

  @override
  Future<NotificationSettings> build() async =>
      _confirmed = await ref.watch(settingsRepositoryProvider).notifications();

  /// [patch] (`{"daily_push_cap": 20}` 처럼 바꿀 키만) 를 화면에 먼저 반영하고 저장한다.
  /// 실패하면 예외를 다시 던진다 (계약 1.5). 화면은 가장 나중 저장의 결과를 따른다.
  Future<void> save(Map<String, Object?> patch) {
    final current = state.value;
    if (current == null) return Future.value();
    state = AsyncData(
      NotificationSettings.fromJson(deepMerge(current.toJson(), patch)),
    );
    final repository = ref.read(settingsRepositoryProvider);
    final op = ++_latest;
    final run = _queue.then((_) => _send(repository, op, patch));
    _queue = run.catchError((Object _) {});
    return run;
  }

  Future<void> _send(
    SettingsRepository repository,
    int op,
    Map<String, Object?> patch,
  ) async {
    try {
      _confirmed = await repository.updateNotifications(patch);
    } finally {
      // 뒤에 저장이 남아 있으면 그 결과가 화면을 정한다. 실패면 마지막으로 확인된 값이다.
      if (ref.mounted && op == _latest) state = AsyncData(_confirmed);
    }
  }
}
