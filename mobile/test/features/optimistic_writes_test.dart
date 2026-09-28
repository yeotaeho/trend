// 낙관적 쓰기가 겹칠 때 — 05 저장 직렬화, 06 소스별 되돌림, 11 찜 되돌리기 부분 실패.
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_riverpod/misc.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/api/api_exception.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/notification_settings/notification_settings_controller.dart';
import 'package:tech_radar/features/saved/saved_controller.dart';
import 'package:tech_radar/features/sources/sources_controller.dart';

import '../helpers.dart';

const _fail = ApiException('unavailable', 'DB 에 연결할 수 없습니다.', status: 503);

/// PATCH 마다 문을 하나 세우고, 테스트가 열거나(성공) 오류로 닫는다(실패).
class _GatedSettings extends FixtureSettingsRepository {
  _GatedSettings(super.store);

  final gates = <Completer<void>>[];

  @override
  Future<NotificationSettings> updateNotifications(
    Map<String, Object?> patch,
  ) async {
    final gate = Completer<void>();
    gates.add(gate);
    await gate.future;
    return super.updateNotifications(patch);
  }
}

class _GatedSources extends FixtureSourceRepository {
  _GatedSources(super.store);

  final gates = <String, Completer<void>>{};

  @override
  Future<Source> setEnabled(String sourceId, {required bool enabled}) async {
    final gate = gates[sourceId] = Completer<void>();
    await gate.future;
    return super.setEnabled(sourceId, enabled: enabled);
  }
}

class _FailingUpdates extends FixtureSavedRepository {
  _FailingUpdates(super.store);

  @override
  Future<SavedItem> update(String alertId, SavedItemPatch patch) async =>
      throw _fail;
}

ProviderContainer _container(List<Override> overrides) {
  final container = ProviderContainer(
    overrides: fixtureOverrides(extra: overrides),
  );
  addTearDown(container.dispose);
  return container;
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('05 저장은 하나씩 보내고, 앞 저장이 실패해도 뒤 저장 값은 남는다', () async {
    final repo = _GatedSettings(FixtureStore(delay: Duration.zero));
    final container = _container([
      settingsRepositoryProvider.overrideWithValue(repo),
    ]);
    container.listen(notificationSettingsProvider, (_, _) {});
    final before = await container.read(notificationSettingsProvider.future);
    final notifier = container.read(notificationSettingsProvider.notifier);

    final first = notifier.save({'daily_push_cap': before.dailyPushCap + 5});
    final second = notifier.save({
      'dedupe_same_issue_daily': !before.dedupeSameIssueDaily,
    });
    await pumpEventQueue();
    expect(repo.gates, hasLength(1), reason: '뒤 저장은 앞 저장이 끝난 뒤 보낸다');

    repo.gates[0].completeError(_fail);
    await expectLater(first, throwsA(isA<ApiException>()));
    await pumpEventQueue();
    repo.gates[1].complete();
    await second;

    final after = container.read(notificationSettingsProvider).requireValue;
    expect(after.dailyPushCap, before.dailyPushCap);
    expect(after.dedupeSameIssueDaily, !before.dedupeSameIssueDaily);
  });

  test('06 겹친 토글 중 하나가 실패하면 그 소스만 되돌린다', () async {
    final repo = _GatedSources(FixtureStore(delay: Duration.zero));
    final container = _container([
      sourceRepositoryProvider.overrideWithValue(repo),
    ]);
    container.listen(sourcesProvider, (_, _) {});
    final before = await container.read(sourcesProvider.future);
    final [a, b, ...] = before.sources;
    final notifier = container.read(sourcesProvider.notifier);

    final failing = notifier.setEnabled(a.id, enabled: !a.enabled);
    final saving = notifier.setEnabled(b.id, enabled: !b.enabled);
    await pumpEventQueue();
    repo.gates[b.id]!.complete();
    await saving;
    repo.gates[a.id]!.completeError(_fail);
    await expectLater(failing, throwsA(isA<ApiException>()));

    final after = container.read(sourcesProvider).requireValue;
    Source byId(String id) => after.sources.firstWhere((s) => s.id == id);
    expect(byId(a.id).enabled, a.enabled);
    expect(byId(b.id).enabled, !b.enabled);
    expect(
      after.stats.enabledCount,
      before.stats.enabledCount + (b.enabled ? -1 : 1),
    );
  });

  test('11 찜 되돌리기에서 메모 PATCH 가 실패해도 다시 생긴 찜은 목록에 남는다', () async {
    final container = _container([
      savedRepositoryProvider.overrideWithValue(
        _FailingUpdates(FixtureStore(delay: Duration.zero)),
      ),
    ]);
    final state = await container.read(savedControllerProvider.future);
    final item = state.items.firstWhere((i) => i.memo != null);
    final notifier = container.read(savedControllerProvider.notifier);

    final index = await notifier.unsave(item);
    await expectLater(
      notifier.undoUnsave(item, index),
      throwsA(isA<ApiException>()),
    );

    final items = container.read(savedControllerProvider).requireValue.items;
    expect(items.map((i) => i.alertId), contains(item.alertId));
  });
}
