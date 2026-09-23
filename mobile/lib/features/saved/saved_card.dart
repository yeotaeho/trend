// 11 SavedCard — 메타(소스·찜한 날·안 읽음 점·폴더 배지), 제목, 메모 박스, 원문·폴더·찜 해제.
import 'package:flutter/widgets.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';

class SavedCard extends StatelessWidget {
  const SavedCard({
    super.key,
    required this.item,
    this.onTap,
    this.onOpen,
    this.onFolder,
    this.onMemo,
    this.onUnsave,
  });

  final SavedItem item;

  /// 카드 탭 → 07.
  final VoidCallback? onTap;

  /// `원문`.
  final VoidCallback? onOpen;

  /// `폴더` → 폴더 이동 시트.
  final VoidCallback? onFolder;

  /// 메모 박스 탭·카드 길게 누르기 → 메모 편집 시트.
  final VoidCallback? onMemo;

  /// 찜 버튼 → 해제 + 되돌리기 스낵바.
  final VoidCallback? onUnsave;

  @override
  Widget build(BuildContext context) {
    final folder = item.folder;
    final memo = item.memo;
    return GestureDetector(
      onTap: onTap,
      onLongPress: onMemo,
      behavior: HitTestBehavior.opaque,
      child: AppCard(
        gap: 10,
        children: [
          Row(
            spacing: 8,
            children: [
              Expanded(
                child: Row(
                  spacing: 8,
                  children: [
                    Flexible(
                      child: Text(
                        '${item.sourceName} · ${savedDate(item.savedAt)}',
                        style: AppText.captionMd,
                        maxLines: 1,
                        overflow: TextOverflow.ellipsis,
                      ),
                    ),
                    if (!item.isRead) const UnreadDot(),
                  ],
                ),
              ),
              if (folder != null)
                AppBadge(
                  label: folder.name,
                  background: AppColors.infoSoft,
                  foreground: AppColors.info,
                ),
            ],
          ),
          Text(item.title, style: AppText.titleCard),
          if (memo != null) _MemoBox(memo: memo, onTap: onMemo),
          Row(
            spacing: 8,
            children: [
              OpenButton(label: '원문', onTap: onOpen),
              OpenButton(label: '폴더', icon: 'folder', onTap: onFolder),
              const Spacer(),
              BookmarkButton(saved: true, onTap: onUnsave),
            ],
          ),
        ],
      ),
    );
  }
}

/// 메타 행 날짜 — 찜한 날을 늘 `M월 d일` 로 쓴다 (상대시간 아님).
String savedDate(DateTime savedAt) {
  final local = savedAt.toLocal();
  return '${local.month}월 ${local.day}일';
}

/// 안 읽음 점 6×6 `#2D5BE3`.
class UnreadDot extends StatelessWidget {
  const UnreadDot({super.key});

  @override
  Widget build(BuildContext context) {
    return Semantics(
      label: '안 읽음',
      child: Container(
        width: 6,
        height: 6,
        decoration: BoxDecoration(
          color: AppColors.primary,
          borderRadius: BorderRadius.circular(AppRadius.unreadDot),
        ),
      ),
    );
  }
}

class _MemoBox extends StatelessWidget {
  const _MemoBox({required this.memo, this.onTap});

  final String memo;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 10, vertical: 8),
        decoration: BoxDecoration(
          color: AppColors.subtle,
          borderRadius: BorderRadius.circular(AppRadius.segmentPiece),
        ),
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.start,
          spacing: 8,
          children: [
            Text('메모', style: AppText.captionSmStrong),
            Expanded(child: Text(memo, style: AppText.captionNote)),
          ],
        ),
      ),
    );
  }
}
