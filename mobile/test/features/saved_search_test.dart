// 11 찜 검색 — 🔍 로 연 입력이 제목으로 목록을 좁히고, 결과가 없으면 안내하고, 취소하면 전체로 돌아온다.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/features/saved/saved_card.dart';

import '../helpers.dart';

void main() {
  testWidgets('찜 검색은 제목으로 좁히고, 결과가 없으면 안내하고, 취소하면 전체로 돌아온다', (tester) async {
    await pumpRouterApp(tester, at: AppRoutes.saved);
    expect(find.byType(SavedCard), findsNWidgets(4));

    await tester.tap(find.bySemanticsLabel('검색'));
    await tester.pumpAndSettle();
    await submitSearch(tester, 'claude'); // 대소문자 무시
    expect(find.byType(SavedCard), findsNWidgets(2));
    expect(find.textContaining('Claude 5 Fable'), findsOneWidget);
    expect(find.textContaining('Claude Code 서브에이전트'), findsOneWidget);

    await submitSearch(tester, '없는 검색어');
    expect(find.byType(SavedCard), findsNothing);
    expect(find.text('검색 결과가 없습니다.'), findsOneWidget);

    await tester.tap(find.text('취소'));
    await tester.pumpAndSettle();
    expect(find.byType(TextField), findsNothing);
    expect(find.byType(SavedCard), findsNWidgets(4));
  });
}
