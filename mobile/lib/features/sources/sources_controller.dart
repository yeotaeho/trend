// 06 수집 소스 상태 — GET /sources 를 읽고, 소스 on/off 를 낙관적으로 반영하며 활성 소스 수도 맞춘다.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

final sourcesProvider =
    AsyncNotifierProvider.autoDispose<SourcesController, SourcesResponse>(
      SourcesController.new,
    );

class SourcesController extends AsyncNotifier<SourcesResponse> {
  @override
  Future<SourcesResponse> build() =>
      ref.watch(sourceRepositoryProvider).sources();

  /// 토글을 먼저 반영하고 `PATCH /sources/{id}` 한다. 실패하면 되돌리고 예외를 다시 던진다.
  Future<void> setEnabled(String sourceId, {required bool enabled}) async {
    final previous = state.value;
    if (previous == null) return;
    final source = previous.sources.firstWhere((s) => s.id == sourceId);
    state = AsyncData(_replace(previous, source.withEnabled(enabled)));
    try {
      final saved = await ref
          .read(sourceRepositoryProvider)
          .setEnabled(sourceId, enabled: enabled);
      final current = state.value;
      if (ref.mounted && current != null) {
        state = AsyncData(_replace(current, saved));
      }
    } catch (_) {
      if (ref.mounted) state = AsyncData(previous);
      rethrow;
    }
  }
}

/// [updated] 로 같은 ID 소스를 바꾸고, `enabled` 가 바뀐 만큼 `enabled_count` 를 옮긴다.
SourcesResponse _replace(SourcesResponse response, Source updated) {
  final before = response.sources.firstWhere((s) => s.id == updated.id);
  final delta = (updated.enabled ? 1 : 0) - (before.enabled ? 1 : 0);
  return SourcesResponse(
    stats: response.stats.withEnabledCount(response.stats.enabledCount + delta),
    sources: [
      for (final source in response.sources)
        source.id == updated.id ? updated : source,
    ],
    plannedSources: response.plannedSources,
  );
}
