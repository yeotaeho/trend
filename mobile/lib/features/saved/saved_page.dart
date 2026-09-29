// 11 찜 화면 — 폴더 칩·정렬·안 읽음 토글·SavedCard 목록·안내 카드. 쓰기 실패는 스낵바로 알린다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';
import 'package:url_launcher/url_launcher.dart';

import '../../app/routes.dart';
import '../../core/icons.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import 'saved_card.dart';
import 'saved_controller.dart';
import 'saved_sheets.dart';

class SavedPage extends ConsumerStatefulWidget {
  const SavedPage({super.key});

  @override
  ConsumerState<SavedPage> createState() => _SavedPageState();
}

class _SavedPageState extends ConsumerState<SavedPage> {
  SavedController get _controller => ref.read(savedControllerProvider.notifier);

  SavedState get _state => ref.read(savedControllerProvider).requireValue;

  void _message(String text, {SnackBarAction? action}) {
    ScaffoldMessenger.of(context)
      ..hideCurrentSnackBar()
      ..showSnackBar(
        SnackBar(content: Text(text), action: action, persist: false),
      );
  }

  /// 쓰기 실패는 컨트롤러가 되돌리고, 여기서는 서버 `message` 를 보여 준다.
  Future<void> _run(Future<void> Function() body) async {
    try {
      await body();
    } catch (e) {
      if (mounted) _message(errorMessage(e));
    }
  }

  void _openDetail(SavedItem item) {
    _run(() => _controller.markRead(item));
    context.push(AppRoutes.alert(item.alertId));
  }

  Future<void> _openOriginal(SavedItem item) async {
    _run(() => _controller.markRead(item));
    var opened = false;
    try {
      opened = await launchUrl(
        Uri.parse(item.url),
        mode: LaunchMode.externalApplication,
      );
    } catch (_) {
      opened = false;
    }
    if (!opened && mounted) _message('원문을 열 수 없습니다.');
  }

  Future<void> _moveFolder(SavedItem item) async {
    final pick = await showFolderMoveSheet(
      context,
      folders: _state.folders.folders,
      current: item.folder,
    );
    if (pick == null || !mounted) return;
    var target = pick.folder;
    if (pick.create) {
      final folder = await _createFolder();
      if (folder == null) return;
      target = folder.ref;
    }
    if (target?.id == item.folder?.id) return;
    await _run(() => _controller.moveToFolder(item, target));
  }

  Future<Folder?> _createFolder() => showFolderNameDialog<Folder>(
    context,
    title: '새 폴더',
    maxLength: _state.meta.limits.folderNameMax,
    submit: _controller.createFolder,
  );

  Future<void> _editMemo(SavedItem item) async {
    final memo = await showMemoSheet(
      context,
      initial: item.memo,
      maxLength: _state.meta.limits.memoMax,
    );
    if (memo == null || memo.trim() == (item.memo ?? '')) return;
    await _run(() => _controller.editMemo(item, memo));
  }

  Future<void> _unsave(SavedItem item) async {
    final int index;
    try {
      index = await _controller.unsave(item);
    } catch (e) {
      if (mounted) _message(errorMessage(e));
      return;
    }
    if (!mounted) return;
    _message(
      '찜을 해제했습니다.',
      action: SnackBarAction(
        label: '되돌리기',
        textColor: AppColors.primaryMuted,
        onPressed: () => _run(() => _controller.undoUnsave(item, index)),
      ),
    );
  }

  Future<void> _pickSort() async {
    final sort = await showSortSheet(context, _state.query.sort);
    if (sort != null && sort != _state.query.sort) {
      await _controller.setSort(sort);
    }
  }

  @override
  Widget build(BuildContext context) {
    final async = ref.watch(savedControllerProvider);
    return Scaffold(
      appBar: RootTopBar(
        title: '찜',
        actions: [
          _TopBarIcon(
            icon: 'search',
            label: '검색',
            onTap: () => _message('준비 중'),
          ),
          _TopBarIcon(
            icon: 'dots',
            label: '폴더 관리',
            onTap: async.hasValue ? () => showFolderManageSheet(context) : null,
          ),
        ],
      ),
      body: switch (async) {
        AsyncValue(:final value?) => _body(value),
        AsyncValue(:final error?) => ErrorState(
          message: errorMessage(error),
          onRetry: () => ref.invalidate(savedControllerProvider),
        ),
        _ => const LoadingState(),
      },
    );
  }

  Widget _body(SavedState s) {
    final items = s.visible;
    return NotificationListener<ScrollNotification>(
      onNotification: (n) {
        if (n.metrics.axis == Axis.vertical && n.metrics.extentAfter < 400) {
          _controller.loadMore();
        }
        return false;
      },
      child: RefreshIndicator(
        color: AppColors.primary,
        onRefresh: _controller.refresh,
        child: CustomScrollView(
          physics: const AlwaysScrollableScrollPhysics(),
          slivers: [
            SliverToBoxAdapter(child: _folderChips(s)),
            SliverToBoxAdapter(child: _sortRow(s)),
            if (s.reloading)
              const SliverToBoxAdapter(child: LoadingState())
            else if (s.listError case final error?)
              SliverToBoxAdapter(
                child: ErrorState(
                  message: errorMessage(error),
                  onRetry: _controller.retry,
                ),
              )
            else if (items.isEmpty)
              SliverToBoxAdapter(child: EmptyState(message: _emptyMessage(s)))
            else
              SliverList.separated(
                itemCount: items.length,
                separatorBuilder: (_, _) =>
                    const SizedBox(height: AppSpacing.cardListGap),
                itemBuilder: (context, i) {
                  final item = items[i];
                  return SavedCard(
                    key: ValueKey(item.alertId),
                    item: item,
                    onTap: () => _openDetail(item),
                    onOpen: () => _openOriginal(item),
                    onFolder: () => _moveFolder(item),
                    onMemo: () => _editMemo(item),
                    onUnsave: () => _unsave(item),
                  );
                },
              ),
            if (s.loadingMore) const SliverToBoxAdapter(child: LoadingState()),
            SliverToBoxAdapter(child: _guide(s)),
            const SliverToBoxAdapter(child: SizedBox(height: 24)),
          ],
        ),
      ),
    );
  }

  Widget _folderChips(SavedState s) {
    final selected = s.query.folderId;
    return SingleChildScrollView(
      scrollDirection: Axis.horizontal,
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 12),
      child: Row(
        spacing: AppSpacing.chipGap,
        children: [
          FolderChip(
            label: '전체',
            count: s.folders.totalCount,
            selected: selected == null,
            onTap: () => _controller.selectFolder(null),
          ),
          for (final folder in s.folders.folders)
            FolderChip(
              label: folder.name,
              count: folder.count,
              selected: selected == folder.id,
              onTap: () => _controller.selectFolder(folder.id),
            ),
          FolderChip(label: '+', onTap: _createFolder),
        ],
      ),
    );
  }

  /// `최근 찜한 순` (정렬 시트) · `안 읽음 N` (토글). 켜지면 강조색이다.
  Widget _sortRow(SavedState s) {
    final folderId = s.query.folderId;
    final unread = folderId == null
        ? s.folders.unreadCount
        : s.folders.folders
                  .where((f) => f.id == folderId)
                  .firstOrNull
                  ?.unreadCount ??
              0;
    final unreadOnly = s.query.unreadOnly;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 0, 20, 8),
      child: Row(
        mainAxisAlignment: MainAxisAlignment.spaceBetween,
        children: [
          GestureDetector(
            onTap: _pickSort,
            behavior: HitTestBehavior.opaque,
            child: Text(s.query.sort.label, style: AppText.captionMd),
          ),
          Semantics(
            button: true,
            toggled: unreadOnly,
            child: GestureDetector(
              onTap: _controller.toggleUnreadOnly,
              behavior: HitTestBehavior.opaque,
              child: Text(
                '안 읽음 $unread',
                style: unreadOnly ? AppText.captionStrong : AppText.captionMd,
              ),
            ),
          ),
        ],
      ),
    );
  }

  String _emptyMessage(SavedState s) {
    if (s.query.unreadOnly) return '안 읽은 찜이 없습니다.';
    if (s.query.folderId != null) return '이 폴더에 찜한 알림이 없습니다.';
    return '찜한 알림이 없습니다.\n피드에서 찜하면 여기에 모입니다.';
  }

  Widget _guide(SavedState s) {
    return Column(
      children: [
        const SectionLabel('찜 안내'),
        AppCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
          children: [
            Text(
              '찜한 항목은 알림 상한·무음 시간과 무관하게 보관되고, 유용/불필요 판정에는 '
              '반영되지 않습니다. 읽지 않은 찜이 ${s.meta.resurfaceUnreadAfterDays}일 '
              '지나면 조용한 알림으로 한 번 다시 알려드립니다.',
              style: AppText.captionMd.copyWith(height: 1.6),
            ),
          ],
        ),
      ],
    );
  }
}

/// RootTopBar 우측 아이콘 22 (`#1C1B19`).
class _TopBarIcon extends StatelessWidget {
  const _TopBarIcon({required this.icon, required this.label, this.onTap});

  final String icon;
  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: label,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: AppIcon(icon, size: 22, color: AppColors.textPrimary),
      ),
    );
  }
}
