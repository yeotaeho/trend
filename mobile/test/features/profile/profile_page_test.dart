// 08 내 프로필 테스트 — fixture 샘플 문구, 카테고리 정렬·정규화, 기간 재조회, null 처리, 리포트 진입.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:go_router/go_router.dart';
import 'package:tech_radar/app/router.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/api/api_exception.dart';
import 'package:tech_radar/core/theme/app_colors.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';

Map<String, dynamic> _fixture(String name) =>
    jsonDecode(File('assets/fixtures/$name.json').readAsStringSync())
        as Map<String, dynamic>;

/// fixture JSON 을 돌려주고 `period_days` 호출을 기록한다.
class _FakeProfileRepository implements ProfileRepository {
  _FakeProfileRepository([Map<String, dynamic>? json])
    : json = json ?? _fixture('profile');

  final Map<String, dynamic> json;
  final List<int> periods = [];

  @override
  Future<Profile> profile({int periodDays = 14}) async {
    periods.add(periodDays);
    return Profile.fromJson({...json, 'period_days': periodDays});
  }

  @override
  Future<Report> report(String reportId) async =>
      Report.fromJson(_fixture('report_$reportId'));

  @override
  Future<Profile> updateDisplayName(String displayName) =>
      throw UnimplementedError();

  @override
  Future<CursorPage<ReportSummary>> reports({String? cursor, int? limit}) =>
      throw UnimplementedError();
}

class _FailingProfileRepository extends _FakeProfileRepository {
  @override
  Future<Profile> profile({int periodDays = 14}) async =>
      throw const ApiException('internal', '서버 오류가 발생했습니다.', status: 500);
}

/// 14일 조회는 성공하고 다른 기간은 실패한다.
class _FailingOtherPeriodRepository extends _FakeProfileRepository {
  @override
  Future<Profile> profile({int periodDays = 14}) async {
    if (periodDays == 14) return super.profile(periodDays: periodDays);
    throw const ApiException('internal', '서버 오류가 발생했습니다.', status: 500);
  }
}

Future<GoRouter> _pump(WidgetTester tester, ProfileRepository repo) async {
  tester.view.physicalSize = const Size(390 * 3, 1400 * 3);
  tester.view.devicePixelRatio = 3;
  addTearDown(tester.view.reset);
  final router = createRouter(initialLocation: AppRoutes.profile);
  addTearDown(router.dispose);
  await tester.pumpWidget(
    ProviderScope(
      overrides: [profileRepositoryProvider.overrideWithValue(repo)],
      retry: (retryCount, error) => null,
      child: MaterialApp.router(theme: buildAppTheme(), routerConfig: router),
    ),
  );
  await tester.pumpAndSettle();
  return router;
}

Color? _spanColor(WidgetTester tester, String text) =>
    tester.widget<Text>(find.text(text)).textSpan?.style?.color;

void main() {
  testWidgets('fixture 로 08 샘플 문구를 모두 보여 준다', (tester) async {
    await _pump(tester, _FakeProfileRepository());

    // 제목과 탭 라벨.
    expect(find.text('내 프로필'), findsNWidgets(2));
    for (final text in [
      '최근 14일',
      '여',
      '여태호',
      'Discord 연결됨 · 온보딩 8/8 완료',
      '받은 알림',
      '61',
      'push 38 · 실험 9',
      '유용 비율',
      '64%',
      '👍 27 / 👎 15',
      '놓친 이슈',
      '1',
      '직접 찾아본 건',
      '반응한 카테고리 · 👍 / 👎',
      '학습된 취향',
      '서베이·전망 논문',
      '👎 4 / 4 → 자동 감점 중',
      'arXiv cs.CL 신뢰도',
      '0.50 → 0.58',
      'youtube:codingapple',
      '0.60 → 0.52',
      '프로필 벡터 라벨',
      '42건 (개인 모델 전환 50건)',
      '주간 리포트',
      '9월 2주차 리포트',
      'relevance 구간 × kind · 통과/탈락/👍/👎',
    ]) {
      expect(find.text(text), findsOneWidget, reason: text);
    }
    expect(_spanColor(tester, '👎 4 / 4 → 자동 감점 중'), AppColors.warn);
  });

  testWidgets('카테고리 6행은 합계 내림차순이고 최대 합계를 트랙 100% 로 둔다', (tester) async {
    final json = _fixture('profile');
    final reactions = (json['category_reactions'] as List).reversed.toList();
    await _pump(
      tester,
      _FakeProfileRepository({...json, 'category_reactions': reactions}),
    );

    final bars = tester.widgetList<StackedBar>(find.byType(StackedBar));
    expect(bars.map((b) => b.label), [
      'mcp-tooling',
      'llm-model',
      'inference-opt',
      'agent',
      'video',
      'dev-community',
    ]);
    expect(bars.map((b) => b.total), [14, 11, 9, 8, 6, 4]);
    final first = bars.first;
    expect(first.usefulFraction, closeTo(12 / 14, 1e-9));
    expect(first.notUsefulFraction, closeTo(2 / 14, 1e-9));
    final video = bars.elementAt(4);
    expect(video.usefulFraction, closeTo(1 / 14, 1e-9));
    expect(video.notUsefulFraction, closeTo(5 / 14, 1e-9));
  });

  testWidgets('기간을 바꾸면 period_days 로 다시 조회한다', (tester) async {
    final repo = _FakeProfileRepository();
    await _pump(tester, repo);
    expect(repo.periods, [14]);

    await tester.tap(find.text('최근 14일'));
    await tester.pumpAndSettle();
    expect(find.text('최근 7일'), findsOneWidget);
    expect(find.text('최근 30일'), findsOneWidget);

    await tester.tap(find.text('최근 30일'));
    await tester.pumpAndSettle();

    expect(repo.periods, [14, 30]);
    expect(find.text('최근 30일'), findsOneWidget);
    expect(find.text('최근 14일'), findsNothing);
  });

  testWidgets(
    'useful_ratio 가 null 이면 –, weekly_report_latest 가 null 이면 카드 숨김',
    (tester) async {
      final json = _fixture('profile');
      final stats = {
        ...json['stats'] as Map<String, dynamic>,
        'useful_ratio': null,
      };
      await _pump(
        tester,
        _FakeProfileRepository({
          ...json,
          'stats': stats,
          'weekly_report_latest': null,
        }),
      );

      expect(find.text('–'), findsOneWidget);
      expect(find.text('64%'), findsNothing);
      expect(find.text('주간 리포트'), findsNothing);
      expect(find.text('9월 2주차 리포트'), findsNothing);
    },
  );

  testWidgets('조회에 실패하면 오류 문구와 다시 시도를 보여 준다', (tester) async {
    await _pump(tester, _FailingProfileRepository());

    expect(find.text('서버 오류가 발생했습니다.'), findsOneWidget);
    expect(find.text('다시 시도'), findsOneWidget);
  });

  testWidgets('기간을 바꾼 재조회가 실패하면 이전 기간 숫자 대신 오류를 보여 준다', (tester) async {
    await _pump(tester, _FailingOtherPeriodRepository());
    expect(find.text('61'), findsOneWidget);

    await tester.tap(find.text('최근 14일'));
    await tester.pumpAndSettle();
    await tester.tap(find.text('최근 7일'));
    await tester.pumpAndSettle();

    expect(find.text('서버 오류가 발생했습니다.'), findsOneWidget);
    expect(find.text('61'), findsNothing);
    expect(find.text('최근 7일'), findsOneWidget);
  });

  testWidgets('주간 리포트 카드를 누르면 리포트 상세로 간다', (tester) async {
    final router = await _pump(tester, _FakeProfileRepository());

    await tester.tap(find.text('9월 2주차 리포트'));
    await tester.pumpAndSettle();

    expect(router.state.uri.path, AppRoutes.report('12'));
    expect(find.text('관문별 깔때기'), findsOneWidget);
    expect(find.byType(AppTabBar), findsOneWidget);
  });
}
