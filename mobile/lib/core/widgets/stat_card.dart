// Stat 카드 — 06 (값 22 + 접미, 캡션 없음) 과 08 (값 24 + 캡션) 두 크기.
import 'package:flutter/widgets.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

enum StatCardSize {
  /// 06 수집 소스 — `12px 14px`, 값 22/700, 접미 13/500 tertiary.
  compact,

  /// 08 내 프로필 — padding 14, 값 24/700, 캡션 11 tertiary.
  large,
}

/// 균등 폭은 부모가 `Expanded` 로 감싸서 맞춘다.
class StatCard extends StatelessWidget {
  const StatCard({
    super.key,
    required this.label,
    required this.value,
    this.suffix,
    this.caption,
    this.size = StatCardSize.large,
  });

  final String label;
  final String value;
  final String? suffix;
  final String? caption;
  final StatCardSize size;

  @override
  Widget build(BuildContext context) {
    final compact = size == StatCardSize.compact;
    final valueStyle = compact ? AppText.statValue : AppText.statValueLg;
    return Container(
      padding: compact
          ? const EdgeInsets.symmetric(horizontal: 14, vertical: 12)
          : const EdgeInsets.all(14),
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.borderCard),
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.start,
        mainAxisSize: MainAxisSize.min,
        spacing: 2,
        children: [
          Text(label, style: AppText.captionSm),
          Text.rich(
            TextSpan(
              text: value,
              style: valueStyle,
              children: [
                if (suffix != null)
                  TextSpan(text: suffix, style: AppText.statSuffix),
              ],
            ),
          ),
          if (caption != null) Text(caption!, style: AppText.captionSm),
        ],
      ),
    );
  }
}
