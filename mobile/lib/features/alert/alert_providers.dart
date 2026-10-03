// 알림 프로바이더 — 피드·07 상세·최근 판정이 함께 보는 판정·찜 상태(낙관적 갱신·롤백)와 07 조회.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/labels.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

/// 알림 하나의 사용자 쪽 상태.
class AlertUserState {
  const AlertUserState({required this.feedback, required this.isSaved});

  final FeedbackVerdict? feedback;
  final bool isSaved;
}

/// 앱에서 바꾼 판정·찜. `null` 인 필드는 서버에서 읽은 값을 쓴다.
/// 11 찜 탭은 판정을 모른 채 찜만 바꾸므로 필드마다 따로 덮는다.
class AlertOverride {
  const AlertOverride({this.feedback, this.isSaved});

  /// 판정 해제도 덮은 값이라 레코드로 감싼다. `(null,)` 은 해제, `null` 은 서버 값이다.
  final (FeedbackVerdict?,)? feedback;
  final bool? isSaved;

  AlertUserState resolve(Alert alert) => AlertUserState(
    feedback: feedback == null ? alert.feedback : feedback!.$1,
    isSaved: isSaved ?? alert.isSaved,
  );
}

/// 앱에서 바꾼 판정·찜을 알림 id 로 들고 있다. 서버에서 읽은 값보다 우선한다.
///
/// 쓰기는 먼저 상태를 바꾸고 저장소를 부른다. 실패하면 그 쓰기가 바꾼 값을
/// 되돌리고 (그 뒤 다른 쓰기가 덮었으면 그대로 둔다) 오류를 다시 던진다.
class AlertUserStates extends Notifier<Map<String, AlertOverride>> {
  @override
  Map<String, AlertOverride> build() => const {};

  /// [verdict] 가 `null` 이면 판정 해제.
  Future<void> setFeedback(Alert alert, FeedbackVerdict? verdict) async {
    final repository = ref.read(alertRepositoryProvider);
    await _change(
      alert.id,
      (o) => AlertOverride(feedback: (verdict,), isSaved: o.isSaved),
      () => verdict == null
          ? repository.clearFeedback(alert.id)
          : repository.setFeedback(alert.id, verdict),
    );
    ref.invalidate(recentFeedbackProvider);
  }

  /// 쓰기가 끝나면 [savedWritesProvider] 를 올려 11 찜 탭이 목록을 다시 읽게 한다.
  Future<void> setSaved(Alert alert, {required bool saved}) async {
    final repository = ref.read(savedRepositoryProvider);
    await _change(
      alert.id,
      (o) => AlertOverride(feedback: o.feedback, isSaved: saved),
      () => saved ? repository.save(alert.id) : repository.unsave(alert.id),
    );
    ref.read(savedWritesProvider.notifier).bump();
  }

  /// 11 찜 탭이 이미 서버에 쓴 찜을 피드·07 에도 맞춘다. 판정은 건드리지 않는다.
  void markSaved(String alertId, {required bool saved}) {
    state = {
      ...state,
      alertId: AlertOverride(
        feedback: state[alertId]?.feedback,
        isSaved: saved,
      ),
    };
  }

  Future<void> _change(
    String alertId,
    AlertOverride Function(AlertOverride current) change,
    Future<Object?> Function() write,
  ) async {
    final before = state[alertId];
    final next = change(before ?? const AlertOverride());
    state = {...state, alertId: next};
    try {
      await write();
    } catch (_) {
      if (identical(state[alertId], next)) {
        state = before == null
            ? ({...state}..remove(alertId))
            : {...state, alertId: before};
      }
      rethrow;
    }
  }
}

final alertUserStatesProvider =
    NotifierProvider<AlertUserStates, Map<String, AlertOverride>>(
      AlertUserStates.new,
    );

/// 피드·07 에서 찜 쓰기가 끝날 때마다 하나씩 오른다. 11 찜 탭이 듣고 목록을 다시 읽는다.
class SavedWrites extends Notifier<int> {
  @override
  int build() => 0;

  void bump() => state++;
}

final savedWritesProvider = NotifierProvider<SavedWrites, int>(SavedWrites.new);

/// [alert] 의 지금 판정·찜. 앱에서 바꾼 값이 있으면 그것을 쓴다.
AlertUserState watchAlertUserState(WidgetRef ref, Alert alert) =>
    (ref.watch(alertUserStatesProvider.select((states) => states[alert.id])) ??
            const AlertOverride())
        .resolve(alert);

/// 07 상세 + 근거. 화면을 열 때마다 새로 읽는다.
final alertDetailProvider = FutureProvider.autoDispose
    .family<AlertDetail, String>(
      (ref, alertId) => ref.watch(alertRepositoryProvider).alert(alertId),
    );

/// 07 최근 판정. 판정을 바꾸면 다시 읽는다.
final recentFeedbackProvider = FutureProvider.autoDispose<RecentFeedback>(
  (ref) => ref.watch(alertRepositoryProvider).recentFeedback(),
);
