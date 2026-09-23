// DropGroup 카드 — 펼침/접힘 헤더(소스별은 아이콘 타일)와 DroppedItem 줄(제목·복원·탈락 태그·사유), 더 보기.
import 'package:flutter/widgets.dart';

import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';

/// 소스 종류 → 아이콘 타일 아이콘. `hackernews`·`hf_papers` 는 디자인이 없어 가까운 아이콘을 고른다.
String sourceTypeIcon(SourceType type) => switch (type) {
  SourceType.githubRelease => 'github',
  SourceType.youtube => 'youtube',
  SourceType.hackernews => 'trend',
  SourceType.hfPapers => 'flask',
  SourceType.rss || SourceType.unknown => 'rss',
};

class DropGroupCard extends StatelessWidget {
  const DropGroupCard({
    super.key,
    required this.title,
    required this.summary,
    required this.count,
    required this.expanded,
    required this.onToggle,
    required this.items,
    required this.reasonOf,
    required this.isRestored,
    required this.onRestore,
    this.icon,
    this.hasMore = false,
    this.loadingMore = false,
    this.onLoadMore,
  });

  final String title;
  final String summary;
  final int count;

  /// 소스별 보기의 아이콘 타일. 없으면 타일을 그리지 않는다.
  final String? icon;
  final bool expanded;
  final VoidCallback onToggle;

  /// 펼쳤을 때 보이는 항목 (preview 또는 더 불러온 목록).
  final List<DroppedItem> items;
  final String Function(DroppedItem item) reasonOf;
  final bool Function(DroppedItem item) isRestored;
  final ValueChanged<DroppedItem> onRestore;
  final bool hasMore;
  final bool loadingMore;
  final VoidCallback? onLoadMore;

  @override
  Widget build(BuildContext context) {
    final showMore = expanded && hasMore;
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 6),
      gap: 0,
      children: [
        _header(),
        if (expanded)
          for (final (index, item) in items.indexed)
            DroppedItemRow(
              item: item,
              reason: reasonOf(item),
              restored: isRestored(item),
              isLast: index == items.length - 1 && !showMore,
              onRestore: () => onRestore(item),
            ),
        if (showMore) _moreButton(),
      ],
    );
  }

  Widget _header() {
    return Semantics(
      button: true,
      expanded: expanded,
      child: GestureDetector(
        onTap: onToggle,
        behavior: HitTestBehavior.opaque,
        child: Container(
          padding: const EdgeInsets.symmetric(vertical: 8),
          decoration: expanded ? const BoxDecoration(border: _divider) : null,
          child: Row(
            spacing: 12,
            children: [
              if (icon != null)
                Container(
                  width: 36,
                  height: 36,
                  alignment: Alignment.center,
                  decoration: BoxDecoration(
                    color: AppColors.subtle,
                    borderRadius: BorderRadius.circular(AppRadius.button),
                  ),
                  child: AppIcon(
                    icon!,
                    size: 18,
                    color: AppColors.textSecondary,
                  ),
                ),
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  children: [
                    Text(title, style: AppText.labelStrong),
                    if (summary.isNotEmpty)
                      Text(summary, style: AppText.captionSm),
                  ],
                ),
              ),
              Text('$count', style: AppText.count),
              AppIcon(
                expanded ? 'chevd' : 'chev',
                size: 16,
                color: AppColors.chevron,
              ),
            ],
          ),
        ),
      ),
    );
  }

  Widget _moreButton() {
    return GestureDetector(
      onTap: loadingMore ? null : onLoadMore,
      behavior: HitTestBehavior.opaque,
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 12),
        child: Text(
          '더 보기',
          textAlign: TextAlign.center,
          style: AppText.captionStrong.copyWith(
            color: loadingMore ? AppColors.textTertiary : AppColors.primary,
          ),
        ),
      ),
    );
  }
}

const BorderSide _dividerSide = BorderSide(color: AppColors.track);
const Border _divider = Border(bottom: _dividerSide);

/// 걸러진 항목 한 줄. 윗줄 제목 + RestoreButton, 아랫줄 탈락 태그 + 사유.
class DroppedItemRow extends StatelessWidget {
  const DroppedItemRow({
    super.key,
    required this.item,
    required this.reason,
    required this.restored,
    required this.isLast,
    required this.onRestore,
  });

  final DroppedItem item;
  final String reason;
  final bool restored;
  final bool isLast;
  final VoidCallback onRestore;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 10),
      decoration: isLast ? null : const BoxDecoration(border: _divider),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: 6,
        children: [
          Row(
            spacing: 8,
            children: [
              Expanded(child: Text(item.title, style: AppText.bodyDropped)),
              RestoreButton(restored: restored, onTap: onRestore),
            ],
          ),
          Row(
            spacing: 8,
            children: [
              StageTag(item.droppedGate),
              if (reason.isNotEmpty)
                Flexible(child: Text(reason, style: AppText.captionSm)),
            ],
          ),
        ],
      ),
    );
  }
}
