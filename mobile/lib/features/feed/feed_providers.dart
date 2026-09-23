// 03 피드 프로바이더 — 필터별 커서 목록(더 불러오기)과 요약 줄 오늘 통계.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/labels.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

/// 지금까지 불러온 카드와 다음 커서.
class FeedState {
  const FeedState({required this.items, this.nextCursor});

  final List<Alert> items;
  final String? nextCursor;

  bool get hasMore => nextCursor != null;
}

class FeedNotifier extends AsyncNotifier<FeedState> {
  FeedNotifier(this.filter);

  final FeedFilter filter;
  bool _loadingMore = false;

  @override
  Future<FeedState> build() async {
    final page = await ref.watch(feedRepositoryProvider).feed(filter: filter);
    return FeedState(items: page.items, nextCursor: page.nextCursor);
  }

  /// 다음 페이지를 붙인다. 이미 부르는 중이거나 끝이면 아무것도 하지 않는다.
  Future<void> loadMore() async {
    final current = state.value;
    if (current == null || !current.hasMore || _loadingMore) return;
    _loadingMore = true;
    try {
      final page = await ref
          .read(feedRepositoryProvider)
          .feed(filter: filter, cursor: current.nextCursor);
      // 그사이 새로고침했으면 옛 목록에 붙이지 않는다.
      if (!ref.mounted || !identical(state.value, current)) return;
      state = AsyncData(
        FeedState(
          items: [...current.items, ...page.items],
          nextCursor: page.nextCursor,
        ),
      );
    } finally {
      _loadingMore = false;
    }
  }
}

/// 칩을 바꾸면 앞 필터 목록은 버리고 새로 읽는다.
final feedProvider = AsyncNotifierProvider.autoDispose
    .family<FeedNotifier, FeedState, FeedFilter>(FeedNotifier.new);

final todayStatsProvider = FutureProvider.autoDispose<TodayStats>(
  (ref) => ref.watch(feedRepositoryProvider).todayStats(),
);
