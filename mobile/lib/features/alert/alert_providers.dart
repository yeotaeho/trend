// 알림 프로바이더 — 피드·07 상세·최근 판정이 함께 보는 판정·찜 상태(낙관적 갱신·롤백)와 07 조회.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/labels.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

/// 알림 하나의 사용자 쪽 상태.
class AlertUserState {
  const AlertUserState({required this.feedback, required this.isSaved});

  AlertUserState.of(Alert alert)
    : this(feedback: alert.feedback, isSaved: alert.isSaved);

  final FeedbackVerdict? feedback;
  final bool isSaved;
}

/// 앱에서 바꾼 판정·찜을 알림 id 로 들고 있다. 서버에서 읽은 값보다 우선한다.
///
/// 쓰기는 먼저 상태를 바꾸고 저장소를 부른다. 실패하면 그 쓰기가 바꾼 값을
/// 되돌리고 (그 뒤 다른 쓰기가 덮었으면 그대로 둔다) 오류를 다시 던진다.
class AlertUserStates extends Notifier<Map<String, AlertUserState>> {
  @override
  Map<String, AlertUserState> build() => const {};

  /// [verdict] 가 `null` 이면 판정 해제.
  Future<void> setFeedback(Alert alert, FeedbackVerdict? verdict) async {
    final repository = ref.read(alertRepositoryProvider);
    await _change(
      alert,
      (s) => AlertUserState(feedback: verdict, isSaved: s.isSaved),
      () => verdict == null
          ? repository.clearFeedback(alert.id)
          : repository.setFeedback(alert.id, verdict),
    );
    ref.invalidate(recentFeedbackProvider);
  }

  Future<void> setSaved(Alert alert, {required bool saved}) {
    final repository = ref.read(savedRepositoryProvider);
    return _change(
      alert,
      (s) => AlertUserState(feedback: s.feedback, isSaved: saved),
      () => saved ? repository.save(alert.id) : repository.unsave(alert.id),
    );
  }

  Future<void> _change(
    Alert alert,
    AlertUserState Function(AlertUserState current) change,
    Future<Object?> Function() write,
  ) async {
    final before = state[alert.id];
    final next = change(before ?? AlertUserState.of(alert));
    state = {...state, alert.id: next};
    try {
      await write();
    } catch (_) {
      if (identical(state[alert.id], next)) {
        state = before == null
            ? ({...state}..remove(alert.id))
            : {...state, alert.id: before};
      }
      rethrow;
    }
  }
}

final alertUserStatesProvider =
    NotifierProvider<AlertUserStates, Map<String, AlertUserState>>(
      AlertUserStates.new,
    );

/// [alert] 의 지금 판정·찜. 앱에서 바꾼 값이 있으면 그것을 쓴다.
AlertUserState watchAlertUserState(WidgetRef ref, Alert alert) =>
    ref.watch(alertUserStatesProvider.select((states) => states[alert.id])) ??
    AlertUserState.of(alert);

/// 07 상세 + 근거. 화면을 열 때마다 새로 읽는다.
final alertDetailProvider = FutureProvider.autoDispose
    .family<AlertDetail, String>(
      (ref, alertId) => ref.watch(alertRepositoryProvider).alert(alertId),
    );

/// 07 최근 판정. 판정을 바꾸면 다시 읽는다.
final recentFeedbackProvider = FutureProvider.autoDispose<RecentFeedback>(
  (ref) => ref.watch(alertRepositoryProvider).recentFeedback(),
);
