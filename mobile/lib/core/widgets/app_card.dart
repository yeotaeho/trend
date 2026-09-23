// 카드·섹션 라벨 — 흰 배경 1px 테두리 반경 14 카드와 12/600 자간 0.04em 라벨.
import 'package:flutter/widgets.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

class AppCard extends StatelessWidget {
  const AppCard({
    super.key,
    required this.children,
    this.padding = const EdgeInsets.all(AppSpacing.cardPadding),
    this.gap = AppSpacing.cardGap,
    this.margin = const EdgeInsets.symmetric(horizontal: AppSpacing.cardMargin),
  });

  final List<Widget> children;

  /// 화면마다 다르다 (행 목록 `4px 16px`, 소스 `2px 16px`, 그룹 `6px 16px` …).
  final EdgeInsetsGeometry padding;
  final double gap;
  final EdgeInsetsGeometry margin;

  @override
  Widget build(BuildContext context) {
    return Container(
      margin: margin,
      padding: padding,
      decoration: BoxDecoration(
        color: AppColors.surface,
        border: Border.all(color: AppColors.borderCard),
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        mainAxisSize: MainAxisSize.min,
        spacing: gap,
        children: children,
      ),
    );
  }
}

/// 섹션 제목 한 줄. 우측 요소가 없고 `소스별 · 많은 순` 처럼 한 문자열로 쓴다.
class SectionLabel extends StatelessWidget {
  const SectionLabel(this.text, {super.key});

  final String text;

  @override
  Widget build(BuildContext context) {
    return Align(
      alignment: Alignment.centerLeft,
      child: Padding(
        padding: const EdgeInsets.fromLTRB(20, 20, 20, 8),
        child: Text(text, style: AppText.sectionLabel),
      ),
    );
  }
}
