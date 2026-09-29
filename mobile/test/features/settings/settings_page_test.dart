// 설정 루트 위젯 테스트 — 하위 화면 요약·표시 이름 PATCH·앱 버전, 관심사 저장 뒤 요약 갱신.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/widgets/widgets.dart';

import 'harness.dart';

void main() {
  setUpSettingsTests();

  testWidgets('카드 행 세 줄에 요약, 표시 이름과 앱 버전을 보여 준다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.settings);

    expect(find.text('설정'), findsWidgets);
    expect(find.text('카테고리 8/12'), findsOneWidget);
    expect(find.text('하루 push 상한 15건'), findsOneWidget);
    expect(find.text('활성 소스 9/10'), findsOneWidget);
    expect(find.widgetWithText(ValueRow, '여태호'), findsOneWidget);
    expect(find.text('0.1.0'), findsOneWidget);
  });

  testWidgets('행을 누르면 하위 화면으로 간다', (tester) async {
    final (router, _) = await pumpSettingsApp(tester, at: AppRoutes.settings);

    await tester.tap(find.text('수집 소스'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.sources);
  });

  testWidgets('표시 이름을 바꾸면 PATCH 뒤 행 값이 바뀌고 빈 이름은 막는다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.settings);

    await tester.tap(find.text('여태호'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), '   ');
    await tester.tap(find.widgetWithText(TextButton, '저장'));
    await tester.pumpAndSettle();
    expect(find.text('표시 이름을 입력하세요.'), findsOneWidget);

    await tester.enterText(find.byType(TextField), ' 태호 ');
    await tester.tap(find.widgetWithText(TextButton, '저장'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(find.widgetWithText(ValueRow, '태호'), findsOneWidget);
  });

  testWidgets('관심사를 저장하고 돌아오면 카테고리 요약이 갱신된다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.settings);

    await tester.tap(find.text('관심사'));
    await tester.pumpAndSettle();
    await tester.tap(find.byKey(const ValueKey('taxonomy-rag-retrieval')));
    await tester.pump();
    await tester.tap(find.widgetWithText(AccentTextButton, '저장'));
    await tester.pumpAndSettle();
    await tester.tap(
      find.byWidgetPredicate((w) => w is AppIcon && w.name == 'back'),
    );
    await tester.pumpAndSettle();

    expect(find.text('카테고리 9/12'), findsOneWidget);
  });
}
