// 주간 리포트 상세 테스트 — 섹션 8개, null 셀 `–`, 숫자 우정렬, 셀 문자열 형식.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/profile/report_page.dart';

Future<void> _pump(WidgetTester tester, String reportId) async {
  tester.view.physicalSize = const Size(390 * 3, 4000 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        fixtureStoreProvider.overrideWithValue(
          FixtureStore(delay: Duration.zero),
        ),
      ],
      retry: (retryCount, error) => null,
      child: MaterialApp(
        theme: buildAppTheme(),
        home: ReportPage(reportId: reportId),
      ),
    ),
  );
  await tester.pumpAndSettle();
}

void main() {
  // 앞 테스트의 가짜 시간 영역에서 만든 asset 캐시 Future 는 다음 테스트에서 완료되지 않는다.
  setUp(rootBundle.clear);

  testWidgets('fixture 리포트의 섹션 8개를 제목과 표로 보여 준다', (tester) async {
    await _pump(tester, '12');

    expect(find.text('9월 2주차 리포트'), findsOneWidget);
    expect(find.text('2026-09-07 – 2026-09-13'), findsOneWidget);
    for (final title in [
      '관문별 깔때기',
      '탈락 사유',
      '소스별 발송·👍·👎·정밀도',
      'importance 별 정밀도',
      '점수 구간',
      '선별 보정 (relevance 구간 × kind)',
      '낮은 relevance 표본',
      'trust 보정',
    ]) {
      expect(find.text(title), findsOneWidget, reason: title);
    }
    expect(find.byType(Table), findsNWidgets(8));
  });

  testWidgets('null 셀은 – 이고 숫자 열은 우정렬이다', (tester) async {
    await _pump(tester, '12');

    // funnel 5 + by_source 3 + low_relevance_samples 1.
    expect(find.text('–'), findsNWidgets(9));
    expect(tester.widget<Text>(find.text('3620')).textAlign, TextAlign.right);
    expect(tester.widget<Text>(find.text('n')).textAlign, TextAlign.right);
    expect(
      tester.widget<Text>(find.text('judge_false').first).textAlign,
      TextAlign.left,
    );
    expect(find.text('−0.08'), findsOneWidget);
    expect(find.text('true'), findsNWidgets(4));
  });

  testWidgets('없는 리포트면 오류 문구를 보여 준다', (tester) async {
    await _pump(tester, '999');

    expect(find.text('리포트를 찾을 수 없습니다.'), findsOneWidget);
  });

  test('reportCell — 정수·실수 2자리·음수 U+2212·null·문자열·불리언', () {
    expect(reportCell(3620), '3620');
    expect(reportCell(0.5), '0.50');
    expect(reportCell(1.0), '1.00');
    expect(reportCell(-0.08), '−0.08');
    expect(reportCell(null), '–');
    expect(reportCell('0.55+'), '0.55+');
    expect(reportCell(false), 'false');
  });
}
