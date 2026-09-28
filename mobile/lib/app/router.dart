// go_router 구성 — 4탭 StatefulShellRoute + 탭별 중첩 스택, 07 은 루트 네비게이터(탭바 없음).
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../core/labels.dart';
import '../features/alert/alert_detail_page.dart';
import '../features/feed/feed_page.dart';
import '../features/profile/profile_page.dart';
import '../features/profile/report_page.dart';
import '../features/saved/saved_page.dart';
import '../features/settings/interests_page.dart';
import '../features/settings/settings_page.dart';
import '../features/notification_settings/notification_settings_page.dart';
import '../features/sources/sources_page.dart';
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
                builder: (context, state) => const FeedPage(),
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
                builder: (context, state) => const SavedPage(),
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.settings,
                builder: (context, state) => const SettingsPage(),
                routes: [
                  GoRoute(
                    path: 'interests',
                    builder: (context, state) => const InterestsPage(),
                  ),
                  GoRoute(
                    path: 'notifications',
                    builder: (context, state) =>
                        const NotificationSettingsPage(),
                  ),
                  GoRoute(
                    path: 'sources',
                    builder: (context, state) => const SourcesPage(),
                  ),
                ],
              ),
            ],
          ),
          StatefulShellBranch(
            routes: [
              GoRoute(
                path: AppRoutes.profile,
                builder: (context, state) => const ProfilePage(),
                routes: [
                  GoRoute(
                    path: 'reports/:reportId',
                    builder: (context, state) =>
                        ReportPage(reportId: state.pathParameters['reportId']!),
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
        builder: (context, state) =>
            AlertDetailPage(alertId: state.pathParameters['alertId']!),
      ),
    ],
  );
}
