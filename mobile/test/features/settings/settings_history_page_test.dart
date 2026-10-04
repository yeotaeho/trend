// 설정 이력 화면 테스트 — 라벨과 이전 → 이후, 맨 위는 되돌리기 없음, 확인 뒤 되돌리면 이력이 한 줄 는다.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';

import 'harness.dart';

void main() {
  setUpSettingsTests();

  testWidgets('저장마다 라벨과 이전 → 이후를 보이고, 맨 위에는 되돌리기가 없다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.settingsHistory);

    expect(find.text('#12 · 앱 저장'), findsOneWidget);
    expect(find.text('하루 push 상한: 15 → 20'), findsOneWidget);
    expect(find.text('코딩애플 · 켜기: 켬 → 끔'), findsOneWidget);
    // 전체 설정에 라벨이 없는 키는 점 경로 그대로 보인다.
    expect(
      find.text('scoring.kind_weights.survey: −0.20 → −0.15'),
      findsOneWidget,
    );
    expect(find.byKey(const ValueKey('restore-12')), findsNothing);
    expect(find.byKey(const ValueKey('restore-11')), findsOneWidget);
  });

  testWidgets('이 버전으로 되돌리기는 확인 뒤 저장하고 이력이 한 줄 는다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.settingsHistory);

    await tester.tap(find.byKey(const ValueKey('restore-11')));
    await tester.pumpAndSettle();
    expect(find.text('#11 저장 뒤 상태로 되돌릴까요?'), findsOneWidget);
    await tester.tap(find.text('되돌리기'));
    await tester.pumpAndSettle();

    expect(find.text('되돌렸습니다.'), findsOneWidget);
    expect(find.text('#13 · 버전 되돌리기'), findsOneWidget);
    expect(find.text('#11 저장으로 되돌림'), findsOneWidget);
  });
}
