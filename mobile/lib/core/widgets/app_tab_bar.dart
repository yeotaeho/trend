// 하단 탭바 — 높이 80, 4탭(피드·찜·설정·내 프로필), 활성 #2D5BE3 / 비활성 #8A877F.
import 'package:flutter/widgets.dart';

import '../icons.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

/// 탭 순서 = 탭 인덱스. 찜 탭은 활성이어도 윤곽선 `bookmark` 아이콘이다.
const List<(String icon, String label)> appTabs = [
  ('home', '피드'),
  ('bookmark', '찜'),
  ('sliders', '설정'),
  ('user', '내 프로필'),
];

class AppTabBar extends StatelessWidget {
  const AppTabBar({super.key, required this.currentIndex, required this.onTap});

  final int currentIndex;
  final ValueChanged<int> onTap;

  @override
  Widget build(BuildContext context) {
    return Container(
      height: AppSpacing.tabBarHeight,
      decoration: const BoxDecoration(
        color: AppColors.surface,
        border: Border(top: BorderSide(color: AppColors.borderCard)),
      ),
      child: Row(
        crossAxisAlignment: CrossAxisAlignment.start,
        children: [
          for (final (index, (icon, label)) in appTabs.indexed)
            Expanded(
              child: _TabCell(
                icon: icon,
                label: label,
                active: index == currentIndex,
                onTap: () => onTap(index),
              ),
            ),
        ],
      ),
    );
  }
}

class _TabCell extends StatelessWidget {
  const _TabCell({
    required this.icon,
    required this.label,
    required this.active,
    required this.onTap,
  });

  final String icon;
  final String label;
  final bool active;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    final color = active ? AppColors.primary : AppColors.textTertiary;
    return Semantics(
      button: true,
      selected: active,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Padding(
          padding: const EdgeInsets.only(top: 10),
          child: Column(
            mainAxisSize: MainAxisSize.min,
            spacing: 4,
            children: [
              AppIcon(icon, size: 22, color: color),
              Text(
                label,
                style: AppText.tabLabel.copyWith(
                  color: color,
                  fontWeight: active ? FontWeight.w600 : FontWeight.w500,
                ),
              ),
            ],
          ),
        ),
      ),
    );
  }
}
