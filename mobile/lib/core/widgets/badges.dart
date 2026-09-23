// 배지 — 전달 강도 Badge 4종, 관문별 탈락 태그(StageTag), 공통 AppBadge.
import 'package:flutter/widgets.dart';

import '../labels.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

/// 11/600, `padding 3px 8px`, 반경 6. 찜 폴더 배지도 이것을 쓴다.
class AppBadge extends StatelessWidget {
  const AppBadge({
    super.key,
    required this.label,
    required this.background,
    required this.foreground,
  });

  final String label;
  final Color background;
  final Color foreground;

  @override
  Widget build(BuildContext context) {
    return Container(
      padding: const EdgeInsets.symmetric(horizontal: 8, vertical: 3),
      decoration: BoxDecoration(
        color: background,
        borderRadius: BorderRadius.circular(AppRadius.badge),
      ),
      child: Text(label, style: AppText.badge.copyWith(color: foreground)),
    );
  }
}

class DeliveryBadge extends StatelessWidget {
  const DeliveryBadge(this.mode, {super.key});

  final DeliveryMode mode;

  @override
  Widget build(BuildContext context) {
    final (background, foreground) = switch (mode) {
      DeliveryMode.instant => (AppColors.primarySoft, AppColors.primary),
      DeliveryMode.quiet => (AppColors.subtle, AppColors.textMuted),
      DeliveryMode.feedOnly => (AppColors.feedSoft, AppColors.feed),
      DeliveryMode.experiment => (AppColors.warnSoft, AppColors.warn),
      DeliveryMode.unknown => (AppColors.subtle, AppColors.textMuted),
    };
    return AppBadge(
      label: mode.label,
      background: background,
      foreground: foreground,
    );
  }
}

/// 09·10 걸러진 항목의 `{관문} 탈락` 태그.
class StageTag extends StatelessWidget {
  const StageTag(this.gate, {super.key});

  final Gate gate;

  @override
  Widget build(BuildContext context) {
    final (background, foreground) = switch (gate) {
      Gate.screening => (AppColors.infoSoft, AppColors.info),
      Gate.score => (AppColors.primarySoft, AppColors.primary),
      Gate.judgment => (AppColors.warnSoft, AppColors.warn),
      Gate.exclude ||
      Gate.dedup ||
      Gate.stale ||
      Gate.clusterDup ||
      Gate.unknown => (AppColors.subtle, AppColors.textMuted),
    };
    return AppBadge(
      label: gate.tagLabel,
      background: background,
      foreground: foreground,
    );
  }
}
