// 버튼 — 원문·폴더 OpenButton, 정사각 아이콘 버튼(찜·복원), 유용/불필요 FeedbackButton, 강조 텍스트 버튼.
import 'package:flutter/widgets.dart';

import '../icons.dart';
import '../labels.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

/// 높이 40, 흰 배경 윤곽 버튼. 아이콘 16 + gap 6 + 13/600 (`원문`, 11 의 `폴더`).
class OpenButton extends StatelessWidget {
  const OpenButton({
    super.key,
    required this.label,
    this.icon = 'external',
    this.onTap,
  });

  final String label;
  final String icon;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        height: 40,
        padding: const EdgeInsets.symmetric(horizontal: 14),
        decoration: _outline(AppColors.surface, AppColors.borderControl),
        child: Row(
          mainAxisSize: MainAxisSize.min,
          spacing: 6,
          children: [
            AppIcon(icon, size: 16, color: AppColors.textPrimary),
            Text(label, style: AppText.labelButton),
          ],
        ),
      ),
    );
  }
}

/// 정사각 윤곽 아이콘 버튼. 찜(40×40)·복원(32×32)이 쓴다.
class BoxIconButton extends StatelessWidget {
  const BoxIconButton({
    super.key,
    required this.icon,
    this.onTap,
    this.size = 40,
    this.iconSize = 18,
    this.radius = AppRadius.button,
    this.iconColor = AppColors.textSecondary,
    this.background = AppColors.surface,
    this.borderColor = AppColors.borderControl,
    this.semanticLabel,
  });

  final String icon;
  final VoidCallback? onTap;
  final double size;
  final double iconSize;
  final double radius;
  final Color iconColor;
  final Color background;
  final Color borderColor;
  final String? semanticLabel;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      label: semanticLabel,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          width: size,
          height: size,
          alignment: Alignment.center,
          decoration: _outline(background, borderColor, radius: radius),
          child: AppIcon(icon, size: iconSize, color: iconColor),
        ),
      ),
    );
  }
}

class BookmarkButton extends StatelessWidget {
  const BookmarkButton({super.key, required this.saved, this.onTap});

  final bool saved;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return BoxIconButton(
      icon: saved ? 'bookmarkfill' : 'bookmark',
      iconColor: saved ? AppColors.primary : AppColors.textSecondary,
      semanticLabel: saved ? '찜 해제' : '찜',
      onTap: onTap,
    );
  }
}

/// 09·10 걸러진 항목 👍 복원. 선택 색은 FeedbackButton 선택 색을 쓴다.
class RestoreButton extends StatelessWidget {
  const RestoreButton({super.key, required this.restored, this.onTap});

  final bool restored;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return BoxIconButton(
      icon: 'thumbup',
      size: 32,
      iconSize: 15,
      radius: AppRadius.segmentPiece,
      iconColor: restored ? AppColors.textInverse : AppColors.textSecondary,
      background: restored ? AppColors.textPrimary : AppColors.surface,
      borderColor: restored ? AppColors.textPrimary : AppColors.borderControl,
      semanticLabel: restored ? '복원 취소' : '복원',
      onTap: onTap,
    );
  }
}

class FeedbackButton extends StatelessWidget {
  const FeedbackButton({
    super.key,
    required this.verdict,
    required this.selected,
    this.onTap,
  });

  final FeedbackVerdict verdict;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final foreground = selected
        ? AppColors.textInverse
        : AppColors.textSecondary;
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          height: 40,
          decoration: _outline(
            selected ? AppColors.textPrimary : AppColors.surface,
            selected ? AppColors.textPrimary : AppColors.borderControl,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.center,
            spacing: 6,
            children: [
              AppIcon(
                verdict == FeedbackVerdict.useful ? 'thumbup' : 'thumbdown',
                size: 16,
                color: foreground,
              ),
              Text(
                verdict.label,
                style: AppText.labelButton.copyWith(color: foreground),
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// 유용·불필요 두 버튼이 남은 폭을 나눈다. 선택된 쪽을 다시 누르면 null (해제) 을 알린다.
class FeedbackButtons extends StatelessWidget {
  const FeedbackButtons({super.key, required this.value, this.onChanged});

  final FeedbackVerdict? value;
  final ValueChanged<FeedbackVerdict?>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Row(
      spacing: 8,
      children: [
        for (final verdict in FeedbackVerdict.values)
          Expanded(
            child: FeedbackButton(
              verdict: verdict,
              selected: value == verdict,
              onTap: onChanged == null
                  ? null
                  : () => onChanged!(value == verdict ? null : verdict),
            ),
          ),
      ],
    );
  }
}

/// 14/600 강조색 텍스트 버튼 (04 헤더 `저장`).
class AccentTextButton extends StatelessWidget {
  const AccentTextButton({super.key, required this.label, this.onTap});

  final String label;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Text(
        label,
        style: AppText.labelStrong.copyWith(
          color: onTap == null ? AppColors.textTertiary : AppColors.primary,
        ),
      ),
    );
  }
}

BoxDecoration _outline(
  Color background,
  Color border, {
  double radius = AppRadius.button,
}) {
  return BoxDecoration(
    color: background,
    border: Border.all(color: border),
    borderRadius: BorderRadius.circular(radius),
  );
}
