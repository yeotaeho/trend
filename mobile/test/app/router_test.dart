// 내비게이션 테스트 — 4탭 전환 활성 색, 찜 탭 윤곽선 아이콘, 하위 경로 탭바 유지, 07 탭바 없음.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:tech_radar/app/router.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/theme/app_colors.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/core/widgets/app_tab_bar.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/filtered/filtered_page.dart';

Future<GoRouter> _pumpApp(WidgetTester tester, {String? at}) async {
  final router = createRouter(initialLocation: at ?? AppRoutes.feed);
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        filteredRepositoryProvider.overrideWithValue(
          _EmptyFilteredRepository(),
        ),
      ],
      child: MaterialApp.router(theme: buildAppTheme(), routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  return router;
}

Finder _inTabBar(Finder finder) =>
    find.descendant(of: find.byType(AppTabBar), matching: finder);

/// 탭바의 [label] 탭 아이콘.
AppIcon _tabIcon(WidgetTester tester, String label) {
  final index = appTabs.indexWhere((tab) => tab.$2 == label);
  return tester
      .widgetList<AppIcon>(_inTabBar(find.byType(AppIcon)))
      .elementAt(index);
}

Color? _tabLabelColor(WidgetTester tester, String label) =>
    tester.widget<Text>(_inTabBar(find.text(label))).style?.color;

void _expectActive(WidgetTester tester, String active) {
  for (final (_, label) in appTabs) {
    final expected = label == active
        ? AppColors.primary
        : AppColors.textTertiary;
    expect(_tabIcon(tester, label).color, expected, reason: '$label 아이콘');
    expect(_tabLabelColor(tester, label), expected, reason: '$label 라벨');
  }
}

void main() {
  testWidgets('첫 화면은 피드 탭이 활성이다', (tester) async {
    await _pumpApp(tester);

    expect(find.byType(AppTabBar), findsOneWidget);
    _expectActive(tester, '피드');
  });

  testWidgets('탭 4개를 누르면 활성 색 #2D5BE3 이 옮겨 간다', (tester) async {
    final router = await _pumpApp(tester);
    final locations = {
      '찜': AppRoutes.saved,
      '설정': AppRoutes.settings,
      '내 프로필': AppRoutes.profile,
      '피드': AppRoutes.feed,
    };

    for (final MapEntry(key: label, value: location) in locations.entries) {
      await tester.tap(_inTabBar(find.text(label)));
      await tester.pumpAndSettle();

      _expectActive(tester, label);
      expect(router.state.uri.path, location);
    }
  });

  testWidgets('찜 탭은 활성이어도 윤곽선 bookmark 아이콘이다', (tester) async {
    await _pumpApp(tester);
    await tester.tap(_inTabBar(find.text('찜')));
    await tester.pumpAndSettle();

    final icon = _tabIcon(tester, '찜');
    expect(icon.name, 'bookmark');
    expect(icon.color, AppColors.primary);
    expect(
      _inTabBar(
        find.byWidgetPredicate((w) => w is AppIcon && w.name == 'bookmarkfill'),
      ),
      findsNothing,
    );
  });

  testWidgets('하위 경로에서도 탭바를 유지하고 부모 탭을 활성 표시한다', (tester) async {
    final router = await _pumpApp(tester);

    router.go(AppRoutes.interests);
    await tester.pumpAndSettle();
    expect(find.byType(AppTabBar), findsOneWidget);
    expect(find.text('관심사'), findsOneWidget);
    _expectActive(tester, '설정');

    router.go('${AppRoutes.filtered}?view=kind');
    await tester.pumpAndSettle();
    expect(find.byType(AppTabBar), findsOneWidget);
    expect(find.text('걸러진 항목'), findsOneWidget);
    expect(
      tester.widget<FilteredPage>(find.byType(FilteredPage)).initialView,
      FilteredView.kind,
    );
    _expectActive(tester, '피드');
  });

  testWidgets('하위 화면의 뒤로가기는 탭 루트로 돌아간다', (tester) async {
    final router = await _pumpApp(tester);
    await tester.tap(_inTabBar(find.text('설정')));
    await tester.pumpAndSettle();
    await tester.tap(find.text('알림 설정'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.notifications);

    await tester.tap(
      find.byWidgetPredicate((w) => w is AppIcon && w.name == 'back'),
    );
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.settings);
  });

  testWidgets('07 은 루트 네비게이터에 올라가 탭바가 없다', (tester) async {
    final router = await _pumpApp(tester);

    router.push(AppRoutes.alert('42'));
    await tester.pumpAndSettle();

    expect(find.byType(AppTabBar), findsNothing);
    expect(find.text('피드백'), findsOneWidget);

    router.pop();
    await tester.pumpAndSettle();
    expect(find.byType(AppTabBar), findsOneWidget);
  });

  testWidgets('탭별 스택은 탭을 옮겨도 유지되고 활성 탭을 다시 누르면 루트로', (tester) async {
    final router = await _pumpApp(tester, at: AppRoutes.interests);
    await tester.tap(_inTabBar(find.text('피드')));
    await tester.pumpAndSettle();
    await tester.tap(_inTabBar(find.text('설정')));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.interests);

    await tester.tap(_inTabBar(find.text('설정')));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.settings);
  });

  testWidgets('07 경로로 바로 들어가도 탭바가 없다', (tester) async {
    await _pumpApp(tester, at: AppRoutes.alert('42'));

    expect(find.byType(AppTabBar), findsNothing);
    expect(find.textContaining('화면 07'), findsOneWidget);
  });
}

/// 걸러진 항목 화면이 fixture 를 읽지 않고 바로 그려지게 하는 빈 요약.
class _EmptyFilteredRepository extends Fake implements FilteredRepository {
  @override
  Future<FilteredSummary> summary({int? hours}) async => const FilteredSummary(
    windowHours: 24,
    filteredTotal: 0,
    collectedTotal: 0,
    gateCounts: {},
    borderline: Borderline(count: 0, range: [0.35, 0.45]),
    unclassifiedCount: 0,
  );
}
