// 전체 설정 화면 테스트 — fixture 를 분류별 행으로, 앱 값 배지·버전·배포 커밋, 앱 소유 행은 그 화면으로·YAML 행은 GitHub 로.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:url_launcher_platform_interface/link.dart';
import 'package:url_launcher_platform_interface/url_launcher_platform_interface.dart';

import 'harness.dart';

class _FakeLauncher extends UrlLauncherPlatform {
  final launched = <String>[];

  @override
  LinkDelegate? get linkDelegate => null;

  @override
  Future<bool> launchUrl(String url, LaunchOptions options) async {
    launched.add(url);
    return true;
  }
}

Finder _row(String key) => find.byKey(ValueKey('setting-$key'));

void main() {
  setUpSettingsTests();

  testWidgets('분류별로 값·출처를 보이고 운영 알림 안내를 단다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.allSettings);

    expect(find.text('관심사·정책'), findsOneWidget);
    expect(find.text('서버 (VM .env)'), findsOneWidget);
    expect(find.textContaining('운영 알림'), findsOneWidget);
    expect(find.text('#12'), findsOneWidget);
    expect(find.text('b21264b'), findsOneWidget);
    expect(
      find.descendant(
        of: _row('notify.daily_push_cap'),
        matching: find.text('앱 값'),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: _row('notify.daily_push_cap'),
        matching: find.text('20'),
      ),
      findsOneWidget,
    );
    expect(
      find.descendant(
        of: _row('scoring.threshold'),
        matching: find.text('앱 값'),
      ),
      findsNothing,
    );
  });

  testWidgets('앱 소유 행은 그 화면으로, YAML 행은 GitHub 편집 화면으로 간다', (tester) async {
    final launcher = _FakeLauncher();
    final original = UrlLauncherPlatform.instance;
    UrlLauncherPlatform.instance = launcher;
    addTearDown(() => UrlLauncherPlatform.instance = original);
    final (router, _) = await pumpSettingsApp(
      tester,
      at: AppRoutes.allSettings,
    );

    await tester.tap(_row('scoring.threshold'));
    await tester.pump();
    expect(launcher.launched, [
      'https://github.com/yeotaeho/trend/edit/main/config/rules.yaml',
    ]);

    await tester.tap(_row('notify.daily_push_cap'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.notifications);
  });
}
