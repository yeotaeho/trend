// 03 피드 화면 — 필터 칩·요약 줄·FeedCard 목록 (무한 스크롤·당겨서 새로고침·빈 상태).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/routes.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/snack.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import 'feed_card.dart';
import 'feed_providers.dart';

class FeedPage extends ConsumerStatefulWidget {
  const FeedPage({super.key});

  @override
  ConsumerState<FeedPage> createState() => _FeedPageState();
}

class _FeedPageState extends ConsumerState<FeedPage> {
  /// 목록 끝에서 이만큼 남으면 다음 페이지를 부른다.
  static const double _loadMoreExtent = 400;

  final ScrollController _scroll = ScrollController();
  FeedFilter _filter = FeedFilter.all;

  @override
  void initState() {
    super.initState();
    _scroll.addListener(_onScroll);
  }

  @override
  void dispose() {
    _scroll.dispose();
    super.dispose();
  }

  void _onScroll() {
    if (_scroll.position.extentAfter > _loadMoreExtent) return;
    runOrSnack(
      context,
      () => ref.read(feedProvider(_filter).notifier).loadMore(),
    );
  }

  void _select(FeedFilter filter) {
    if (filter == _filter) return;
    setState(() => _filter = filter);
    if (_scroll.hasClients) _scroll.jumpTo(0);
  }

  Future<void> _refresh() async {
    ref
      ..invalidate(todayStatsProvider)
      ..invalidate(feedProvider(_filter));
    try {
      await ref.read(feedProvider(_filter).future);
    } catch (_) {
      // 오류는 목록 자리의 ErrorState 가 보여 준다.
    }
  }

  @override
  Widget build(BuildContext context) {
    final feed = ref.watch(feedProvider(_filter));
    return Scaffold(
      appBar: RootTopBar(
        title: '오늘',
        actions: [
          for (final icon in const ['search', 'bell'])
            GestureDetector(
              onTap: () => showSnack(context, '준비 중'),
              behavior: HitTestBehavior.opaque,
              child: AppIcon(icon, size: 22, color: AppColors.textPrimary),
            ),
        ],
      ),
      body: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        children: [
          SingleChildScrollView(
            scrollDirection: Axis.horizontal,
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
            child: Row(
              spacing: AppSpacing.chipGap,
              children: [
                for (final filter in FeedFilter.values)
                  AppChip(
                    label: filter.label,
                    selected: filter == _filter,
                    onTap: () => _select(filter),
                  ),
              ],
            ),
          ),
          const _SummaryLine(),
          Expanded(
            child: RefreshIndicator(
              onRefresh: _refresh,
              color: AppColors.primary,
              child: feed.when(
                loading: () => const _Scrollable(child: LoadingState()),
                error: (error, _) => _Scrollable(
                  child: ErrorState(
                    message: errorMessage(error),
                    onRetry: () => ref.invalidate(feedProvider(_filter)),
                  ),
                ),
                data: (state) => state.items.isEmpty
                    ? const _Scrollable(child: _Empty())
                    : ListView.separated(
                        controller: _scroll,
                        physics: const AlwaysScrollableScrollPhysics(),
                        padding: const EdgeInsets.only(bottom: 16),
                        itemCount: state.items.length + (state.hasMore ? 1 : 0),
                        separatorBuilder: (_, _) =>
                            const SizedBox(height: AppSpacing.cardListGap),
                        itemBuilder: (context, index) =>
                            index < state.items.length
                            ? FeedCard(
                                key: ValueKey(state.items[index].id),
                                alert: state.items[index],
                              )
                            : const LoadingState(),
                      ),
              ),
            ),
          ),
        ],
      ),
    );
  }
}

/// `오늘 push 4 / 15` 와 `걸러짐 571건 보기 ›` (→ 09).
class _SummaryLine extends ConsumerWidget {
  const _SummaryLine();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(todayStatsProvider).value;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          Text(
            stats == null
                ? ''
                : '오늘 push ${stats.pushSentToday} / ${stats.dailyPushCap}',
            style: AppText.captionMd,
          ),
          if (stats != null) _FilteredLink(count: stats.filteredCount),
        ],
      ),
    );
  }
}

class _FilteredLink extends StatelessWidget {
  const _FilteredLink({required this.count});

  final int count;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: () =>
          context.go('${AppRoutes.filtered}?view=${FilteredView.source.value}'),
      behavior: HitTestBehavior.opaque,
      child: Text('걸러짐 $count건 보기 ›', style: AppText.captionStrong),
    );
  }
}

/// 필터 결과가 없을 때 — 디자인이 없어 문구와 걸러짐 링크만 둔다.
class _Empty extends ConsumerWidget {
  const _Empty();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = ref.watch(todayStatsProvider).value;
    return Padding(
      padding: const EdgeInsets.all(32),
      child: Column(
        spacing: 12,
        children: [
          Text(
            '오늘 받은 알림이 없습니다',
            textAlign: TextAlign.center,
            style: AppText.captionMd,
          ),
          if (stats != null) _FilteredLink(count: stats.filteredCount),
        ],
      ),
    );
  }
}

/// 당겨서 새로고침이 되도록 상태 위젯을 스크롤 안에 둔다.
class _Scrollable extends StatelessWidget {
  const _Scrollable({required this.child});

  final Widget child;

  @override
  Widget build(BuildContext context) {
    return ListView(
      physics: const AlwaysScrollableScrollPhysics(),
      children: [child],
    );
  }
}
