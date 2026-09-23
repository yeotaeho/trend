// go_router 구성 — 4탭 StatefulShellRoute + 탭별 중첩 스택, 07 은 루트 네비게이터(탭바 없음).
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/labels.dart';
import '../features/filtered/filtered_page.dart';
import 'placeholder_page.dart';
import 'routes.dart';
import 'tab_shell.dart';

final routerProvider = Provider<GoRouter>((ref) {
  final router = createRouter();
  ref.onDispose(router.dispose);
  return router;
});

GoRouter createRouter({String initialLocation = AppRoutes.feed}) {
  final rootKey = GlobalKey<NavigatorState>();
  return GoRouter(
    navigatorKey: rootKey,
    initialLocation: initialLocation,
    routes: [
      StatefulShellRoute.indexedStack(
        builder: (context, state, navigationShell) =>
            TabShell(navigationShell: navigationShell),
        branches: [
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.feed,
                builder: (context, state) => PlaceholderPage(
                  screen: '03',
                  title: '오늘',
                  isRoot: true,
                  links: [
                    PlaceholderLink(
                      '걸러진 항목',
                      '${AppRoutes.filtered}?view=${FilteredView.source.value}',
                    ),
                    PlaceholderLink(
                      '피드백 · 판정 근거',
                      AppRoutes.alert('sample'),
                      push: true,
                    ),
                  ],
                ),
                routes: [
                  GoRoute(
                    path: 'filtered',
                    builder: (context, state) {
                      final view = FilteredView.values.firstWhere(
                        (v) => v.value == state.uri.queryParameters['view'],
                        orElse: () => FilteredView.source,
                      );
                      return FilteredPage(initialView: view);
                    },
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.saved,
                builder: (context, state) => PlaceholderPage(
                  screen: '11',
                  title: '찜',
                  isRoot: true,
                  links: [
                    PlaceholderLink(
                      '피드백 · 판정 근거',
                      AppRoutes.alert('sample'),
                      push: true,
                    ),
                  ],
                ),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.settings,
                builder: (context, state) => const PlaceholderPage(
                  screen: '–',
                  title: '설정',
                  isRoot: true,
                  links: [
                    PlaceholderLink('관심사', AppRoutes.interests),
                    PlaceholderLink('알림 설정', AppRoutes.notifications),
                    PlaceholderLink('수집 소스', AppRoutes.sources),
                  ],
                ),
                routes: [
                  GoRoute(
                    path: 'interests',
                    builder: (context, state) =>
                        const PlaceholderPage(screen: '04', title: '관심사'),
                  ),
                  GoRoute(
                    path: 'notifications',
                    builder: (context, state) =>
                        const PlaceholderPage(screen: '05', title: '알림 설정'),
                  ),
                  GoRoute(
                    path: 'sources',
                    builder: (context, state) =>
                        const PlaceholderPage(screen: '06', title: '수집 소스'),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.profile,
                builder: (context, state) => PlaceholderPage(
                  screen: '08',
                  title: '내 프로필',
                  isRoot: true,
                  links: [
                    PlaceholderLink('주간 리포트', AppRoutes.report('latest')),
                  ],
                ),
                routes: [
                  GoRoute(
                    path: 'reports/:reportId',
                    builder: (context, state) => PlaceholderPage(
                      screen: '–',
                      title: '주간 리포트',
                      note: state.pathParameters['reportId'],
                    ),
                  ),
                ],
              ),
            ],
          ),
        ],
      ),
      GoRoute(
        path: '/alerts/:alertId',
        parentNavigatorKey: rootKey,
        builder: (context, state) => PlaceholderPage(
          screen: '07',
          title: '피드백',
          note: state.pathParameters['alertId'],
        ),
      ),
    ],
  );
}
