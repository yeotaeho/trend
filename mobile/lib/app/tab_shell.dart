// 탭 셸 — StatefulShellRoute 의 탭별 중첩 스택 위에 하단 탭바를 붙인다.
import 'package:flutter/material.dart';
import 'package:go_router/go_router.dart';

import '../core/widgets/app_tab_bar.dart';

class TabShell extends StatelessWidget {
  const TabShell({super.key, required this.navigationShell});

  final StatefulNavigationShell navigationShell;

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      body: navigationShell,
      bottomNavigationBar: AppTabBar(
        currentIndex: navigationShell.currentIndex,
        // 활성 탭을 다시 누르면 그 탭 스택의 루트로 돌아간다.
        onTap: (index) => navigationShell.goBranch(
          index,
          initialLocation: index == navigationShell.currentIndex,
        ),
      ),
    );
  }
}
