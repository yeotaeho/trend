// 칩 — 필터 Chip(선택 inverse·미선택 윤곽)과 11 찜 폴더 칩(개수 표시).
import 'package:flutter/widgets.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

class AppChip extends StatelessWidget {
  const AppChip({
    super.key,
    required this.label,
    this.selected = false,
    this.onTap,
  });

  final String label;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return _ChipFrame(
      selected: selected,
      onTap: onTap,
      child: Text(label, style: _chipText(selected)),
    );
  }
}

/// 11 찜 폴더 칩. [count] 가 null 이면 (`+` 칩) 개수를 그리지 않는다.
class FolderChip extends StatelessWidget {
  const FolderChip({
    super.key,
    required this.label,
    this.count,
    this.selected = false,
    this.onTap,
  });

  final String label;
  final int? count;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return _ChipFrame(
      selected: selected,
      onTap: onTap,
      child: Row(
        mainAxisSize: MainAxisSize.min,
        spacing: 6,
        children: [
          Text(label, style: _chipText(selected), softWrap: false),
          if (count != null)
            Text(
              '$count',
              softWrap: false,
              style: AppText.labelChip.copyWith(
                fontSize: 12,
                color: selected ? AppColors.chevron : AppColors.textTertiary,
              ),
            ),
        ],
      ),
    );
  }
}

TextStyle _chipText(bool selected) => AppText.labelChip.copyWith(
  color: selected ? AppColors.textInverse : AppColors.textSecondary,
);

/// 선택 칩도 같은 색 1px 테두리를 둬서 미선택과 높이를 맞춘다 (tokens.md Chip).
class _ChipFrame extends StatelessWidget {
  const _ChipFrame({required this.selected, required this.child, this.onTap});

  final bool selected;
  final Widget child;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 9),
        decoration: BoxDecoration(
          color: selected ? AppColors.textPrimary : AppColors.surface,
          border: Border.all(
            color: selected ? AppColors.textPrimary : AppColors.borderControl,
          ),
          borderRadius: BorderRadius.circular(AppRadius.chip),
        ),
        child: child,
      ),
    );
  }
}
