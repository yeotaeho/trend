// 찜 동기화 — 피드·07 의 찜 쓰기와 11 찜 탭의 쓰기가 서로의 화면에 반영된다.
import 'dart:async';

import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/alert/alert_providers.dart';
import 'package:tech_radar/features/saved/saved_controller.dart';

import '../helpers.dart';

/// 첫 `folders()` 만 [gate] 가 열릴 때까지 붙잡는다 — 찜 탭 첫 로딩이 늦게 끝나는 순서.
class _SlowFirstFolders extends FixtureSavedRepository {
  _SlowFirstFolders(super.store);

  final gate = Completer<void>();
  bool _first = true;

  @override
  Future<FolderList> folders() async {
    if (_first) {
      _first = false;
      await gate.future;
    }
    return super.folders();
  }
}

/// 피드 카드·07 이 그리는 찜 표시 — 앱에서 바꾼 값이 있으면 그것, 없으면 서버 값.
bool _shownSaved(ProviderContainer container, Alert alert) =>
    container.read(alertUserStatesProvider)[alert.id]?.isSaved ?? alert.isSaved;

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late ProviderContainer container;

  setUp(() {
    container = ProviderContainer(overrides: fixtureOverrides());
    addTearDown(container.dispose);
  });

  Future<List<Alert>> feedAlerts() async =>
      (await container.read(feedRepositoryProvider).feed()).items;

  test('피드에서 찜하면 이미 열어 둔 찜 탭 목록에 나타난다', () async {
    await container.read(savedControllerProvider.future);
    final alert = (await feedAlerts()).firstWhere((a) => !a.isSaved);

    await container
        .read(alertUserStatesProvider.notifier)
        .setSaved(alert, saved: true);
    await pumpEventQueue();

    final items = container.read(savedControllerProvider).requireValue.items;
    expect(items.map((i) => i.alertId), contains(alert.id));
  });

  test('찜 탭 첫 로딩 중에 끝난 피드 찜도 목록에 나타난다', () async {
    late _SlowFirstFolders slow;
    container = ProviderContainer(
      overrides: fixtureOverrides(
        extra: [
          savedRepositoryProvider.overrideWith(
            (ref) => slow = _SlowFirstFolders(ref.watch(fixtureStoreProvider)),
          ),
        ],
      ),
    );
    addTearDown(container.dispose);
    final alert = (await feedAlerts()).firstWhere((a) => !a.isSaved);

    final loading = container.read(savedControllerProvider.future);
    await pumpEventQueue(); // 첫 목록은 찜 전에 받았고 폴더만 남았다.
    await container
        .read(alertUserStatesProvider.notifier)
        .setSaved(alert, saved: true);
    slow.gate.complete();
    final state = await loading;

    expect(state.items.map((i) => i.alertId), contains(alert.id));
  });

  test('찜 탭에서 해제하면 피드·07 의 찜 표시도 해제된다', () async {
    final alert = (await feedAlerts()).firstWhere((a) => a.isSaved);
    final saved = await container.read(savedControllerProvider.future);
    final item = saved.items.firstWhere((i) => i.alertId == alert.id);

    await container.read(savedControllerProvider.notifier).unsave(item);

    expect(_shownSaved(container, alert), isFalse);
  });

  test('찜 탭에서 되돌리면 피드·07 의 찜 표시도 돌아온다', () async {
    final alert = (await feedAlerts()).firstWhere((a) => a.isSaved);
    final saved = await container.read(savedControllerProvider.future);
    final item = saved.items.firstWhere((i) => i.alertId == alert.id);
    final notifier = container.read(savedControllerProvider.notifier);

    final index = await notifier.unsave(item);
    await notifier.undoUnsave(item, index);

    expect(_shownSaved(container, alert), isTrue);
  });
}
