// 헤더 — 탭 루트 RootTopBar(제목 22/700) 와 하위 SubTopBar(뒤로가기 + 18/600). 상태바는 SafeArea.
import 'package:flutter/widgets.dart';

import '../icons.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

class RootTopBar extends StatelessWidget implements PreferredSizeWidget {
  const RootTopBar({super.key, required this.title, this.actions = const []});

  final String title;

  /// 아이콘 22 두 개(gap 14) 또는 `최근 14일` 같은 텍스트.
  final List<Widget> actions;

  @override
  Size get preferredSize => const Size.fromHeight(AppSpacing.topBarHeight);

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: SizedBox(
        height: AppSpacing.topBarHeight,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.rootTopBarPadding,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Text(title, style: AppText.titleRoot),
              Row(
                mainAxisSize: MainAxisSize.min,
                spacing: 14,
                children: actions,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

class SubTopBar extends StatelessWidget implements PreferredSizeWidget {
  const SubTopBar({
    super.key,
    required this.title,
    this.actions = const [],
    this.onBack,
  });

  final String title;

  /// 아이콘 22 또는 `저장` 텍스트 버튼 (gap 8).
  final List<Widget> actions;

  /// 기본은 현재 라우트를 닫는다.
  final VoidCallback? onBack;

  @override
  Size get preferredSize => const Size.fromHeight(AppSpacing.topBarHeight);

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      bottom: false,
      child: SizedBox(
        height: AppSpacing.topBarHeight,
        child: Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.subTopBarPadding,
          ),
          child: Row(
            mainAxisAlignment: MainAxisAlignment.spaceBetween,
            children: [
              Semantics(
                button: true,
                label: '뒤로',
                child: GestureDetector(
                  onTap: onBack ?? () => Navigator.maybePop(context),
                  behavior: HitTestBehavior.opaque,
                  child: Row(
                    spacing: 8,
                    children: [
                      const AppIcon(
                        'back',
                        size: 20,
                        color: AppColors.textPrimary,
                      ),
                      Text(title, style: AppText.titleSub),
                    ],
                  ),
                ),
              ),
              Row(
                mainAxisSize: MainAxisSize.min,
                spacing: 8,
                children: actions,
              ),
            ],
          ),
        ),
      ),
    );
  }
}
