// 09·10 걸러진 항목 화면 — 세그먼트로 소스별·종류별·관문별 보기를 바꾸고, 그룹 펼침·더 보기·👍 복원.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';
import 'drop_group_card.dart';
import 'filtered_text.dart';

final filteredSummaryProvider = FutureProvider.autoDispose<FilteredSummary>(
  (ref) => ref.watch(filteredRepositoryProvider).summary(),
);

final filteredGroupsProvider = FutureProvider.autoDispose
    .family<FilteredGroups, (FilteredView, GroupSort)>(
      (ref, arg) => ref
          .watch(filteredRepositoryProvider)
          .groups(view: arg.$1, sort: arg.$2),
    );

/// 그룹을 펼쳐 `더 보기` 로 불러온 목록. 첫 페이지가 preview 를 대신한다.
class _LoadedItems {
  const _LoadedItems(this.items, this.nextCursor);

  final List<DroppedItem> items;
  final String? nextCursor;
}

class FilteredPage extends ConsumerStatefulWidget {
  const FilteredPage({super.key, this.initialView = FilteredView.source});

  final FilteredView initialView;

  @override
  ConsumerState<FilteredPage> createState() => _FilteredPageState();
}

class _FilteredPageState extends ConsumerState<FilteredPage> {
  late FilteredView _view = widget.initialView;
  GroupSort _sort = GroupSort.countDesc;

  /// 펼친 그룹 키. `null` 이면 기본값 — 첫 그룹만 펼침. 보기를 바꾸면 기본값으로 돌아간다.
  Set<String>? _expanded;
  final Map<String, _LoadedItems> _loaded = {};
  final Set<String> _loadingMore = {};

  /// 이 화면에서 복원·취소한 결과. 저장소를 다시 읽기 전까지 항목의 `restored` 를 덮는다.
  final Map<String, bool> _restored = {};
  final Set<String> _restoring = {};

  void _setView(FilteredView view) {
    if (view == _view) return;
    setState(() {
      _view = view;
      _expanded = null;
      _loaded.clear();
      _loadingMore.clear();
    });
  }

  void _toggleSort() => setState(() {
    _sort = _sort == GroupSort.countDesc
        ? GroupSort.nameAsc
        : GroupSort.countDesc;
  });

  Set<String> _expandedKeys(List<FilteredGroup> groups) =>
      _expanded ?? {if (groups.isNotEmpty) groups.first.key};

  void _toggleGroup(List<FilteredGroup> groups, String key) {
    final keys = {..._expandedKeys(groups)};
    if (!keys.remove(key)) keys.add(key);
    setState(() => _expanded = keys);
  }

  Future<void> _loadMore(FilteredGroup group) async {
    final view = _view;
    final key = group.key;
    if (!_loadingMore.add(key)) return;
    setState(() {});
    final loaded = _loaded[key];
    try {
      final page = await ref
          .read(filteredRepositoryProvider)
          .items(view: view, key: key, cursor: loaded?.nextCursor);
      if (!mounted || view != _view) return;
      setState(() {
        _loaded[key] = _LoadedItems([
          ...?loaded?.items,
          ...page.items,
        ], page.nextCursor);
      });
    } on ApiException catch (e) {
      _showSnack(e.message);
    } finally {
      if (mounted && view == _view) setState(() => _loadingMore.remove(key));
    }
  }

  bool _isRestored(DroppedItem item) => _restored[item.id] ?? item.restored;

  Future<void> _toggleRestore(DroppedItem item) async {
    if (!_restoring.add(item.id)) return;
    final restored = _isRestored(item);
    final repository = ref.read(filteredRepositoryProvider);
    try {
      if (restored) {
        await repository.cancelRestore(item.id);
      } else {
        await repository.restore(item.id);
      }
      if (!mounted) return;
      setState(() => _restored[item.id] = !restored);
      if (!restored) _showSnack('피드에 추가했습니다');
    } on ApiException catch (e) {
      _showSnack(e.message);
    } finally {
      _restoring.remove(item.id);
    }
  }

  void _showSnack(String message) {
    if (!mounted) return;
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(SnackBar(content: Text(message)));
  }

  @override
  Widget build(BuildContext context) {
    final summary = ref.watch(filteredSummaryProvider);
    return Scaffold(
      appBar: SubTopBar(
        title: '걸러진 항목',
        actions: [
          Semantics(
            button: true,
            label: '검색',
            child: GestureDetector(
              onTap: () => _showSnack('준비 중'),
              behavior: HitTestBehavior.opaque,
              child: const AppIcon(
                'search',
                size: 22,
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
      body: ListView(
        padding: const EdgeInsets.only(bottom: 16),
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(16, 4, 16, 10),
            child: SegmentedControl<FilteredView>(
              values: FilteredView.values,
              selected: _view,
              labelOf: (view) => view.label,
              onChanged: _setView,
            ),
          ),
          ...switch (summary) {
            AsyncData(:final value) => _content(value),
            AsyncError(:final error) => [
              ErrorState(
                message: _errorMessage(error),
                onRetry: () => ref.invalidate(filteredSummaryProvider),
              ),
            ],
            _ => const [LoadingState()],
          },
        ],
      ),
    );
  }

  List<Widget> _content(FilteredSummary summary) {
    final empty = summary.filteredTotal == 0;
    return [
      _SummaryCard(summary: summary, note: summaryNote(summary, _view)),
      if (!empty) ...[
        Semantics(
          button: true,
          child: GestureDetector(
            onTap: _toggleSort,
            behavior: HitTestBehavior.opaque,
            child: SectionLabel('${_view.label} · ${_sort.label}'),
          ),
        ),
        _groups(summary),
      ],
    ];
  }

  Widget _groups(FilteredSummary summary) {
    final args = (_view, _sort);
    return switch (ref.watch(filteredGroupsProvider(args))) {
      AsyncData(:final value) => Column(
        spacing: 10,
        children: [
          for (final group in value.groups)
            _groupCard(value.groups, group, summary),
        ],
      ),
      AsyncError(:final error) => ErrorState(
        message: _errorMessage(error),
        onRetry: () => ref.invalidate(filteredGroupsProvider(args)),
      ),
      _ => const LoadingState(),
    };
  }

  Widget _groupCard(
    List<FilteredGroup> groups,
    FilteredGroup group,
    FilteredSummary summary,
  ) {
    final loaded = _loaded[group.key];
    final view = _view;
    return DropGroupCard(
      key: ValueKey('drop-group-${group.key}'),
      title: groupTitle(group, view),
      summary: groupSummary(
        group,
        view,
        borderlineRange: summary.borderline.range,
      ),
      count: group.count,
      icon: view == FilteredView.source
          ? sourceTypeIcon(group.source?.type ?? SourceType.unknown)
          : null,
      expanded: _expandedKeys(groups).contains(group.key),
      onToggle: () => _toggleGroup(groups, group.key),
      items: loaded?.items ?? group.preview,
      reasonOf: (item) => reasonLine(item, view),
      isRestored: _isRestored,
      onRestore: _toggleRestore,
      hasMore: loaded == null
          ? group.count > group.preview.length
          : loaded.nextCursor != null,
      loadingMore: _loadingMore.contains(group.key),
      onLoadMore: () => _loadMore(group),
    );
  }
}

String _errorMessage(Object error) =>
    error is ApiException ? error.message : '불러오지 못했습니다.';

/// 요약 카드 — `오늘 걸러짐 N / 수집 M`, `최근 N시간`, GateBar + 범례, 보기별 안내.
class _SummaryCard extends StatelessWidget {
  const _SummaryCard({required this.summary, required this.note});

  final FilteredSummary summary;
  final String note;

  @override
  Widget build(BuildContext context) {
    final empty = summary.filteredTotal == 0;
    return AppCard(
      gap: 10,
      children: [
        Row(
          spacing: 8,
          children: [
            Expanded(
              child: Text.rich(
                TextSpan(
                  text: '오늘 걸러짐 ${summary.filteredTotal}',
                  children: [
                    TextSpan(
                      text: ' / 수집 ${summary.collectedTotal}',
                      style: AppText.bodySm.copyWith(
                        color: AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
                style: AppText.summaryTitle,
              ),
            ),
            Text('최근 ${summary.windowHours}시간', style: AppText.captionMd),
          ],
        ),
        if (empty)
          Text('오늘 걸러진 항목이 없습니다', style: AppText.captionNote)
        else ...[
          GateBar(counts: summary.gateCounts),
          Text(note, style: AppText.captionNote),
        ],
      ],
    );
  }
}
