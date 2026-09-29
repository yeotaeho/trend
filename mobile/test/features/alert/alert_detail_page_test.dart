// 07 판정 근거 화면 테스트 — 03 과 판정 상태 공유, 점수 바 채움·음수 경고색, 근거·안내·최근 판정.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/theme/app_colors.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/alert/alert_detail_page.dart';
import 'package:tech_radar/features/feed/feed_card.dart';

import '../../helpers.dart';

const _fable = '[모델] Claude 5 Fable — 컨텍스트 2배, 가격 동일';

FeedbackButton _button(WidgetTester tester, Finder scope, FeedbackVerdict v) =>
    tester
        .widgetList<FeedbackButton>(
          find.descendant(of: scope, matching: find.byType(FeedbackButton)),
        )
        .firstWhere((b) => b.verdict == v);

Finder get _detail => find.byType(AlertDetailPage);

Finder get _fableCard =>
    find.ancestor(of: find.text(_fable), matching: find.byType(FeedCard));

Finder _scoreBar(String label) =>
    find.byWidgetPredicate((w) => w is ScoreBar && w.label == label);

/// 채움 폭 ÷ 트랙 폭.
double _fillRatio(WidgetTester tester, String label) {
  final fill = find.descendant(
    of: _scoreBar(label),
    matching: find.byKey(const ValueKey('score-bar-fill')),
  );
  final track = find.ancestor(of: fill, matching: find.byType(Container)).first;
  return tester.getSize(fill).width / tester.getSize(track).width;
}

/// BeaconKV 상세의 점수만 바꿔 돌려준다.
class _ScoreAlertRepository implements AlertRepository {
  _ScoreAlertRepository(this._inner, this.components);

  final AlertRepository _inner;
  final Map<String, double> components;

  @override
  Future<AlertDetail> alert(String alertId) async {
    final detail = await _inner.alert(alertId);
    final r = detail.rationale;
    return AlertDetail(
      alert: detail.alert,
      rationale: Rationale(
        score: ScoreBreakdown(
          total: r.score!.total,
          threshold: r.score!.threshold,
          components: components,
        ),
        routing: r.routing,
        screening: r.screening,
        judgment: r.judgment,
        trustNoteSource: r.trustNoteSource,
      ),
    );
  }

  @override
  Future<RecentFeedback> recentFeedback({int? limit}) =>
      _inner.recentFeedback(limit: limit);

  @override
  Future<FeedbackResult> setFeedback(String alertId, FeedbackVerdict verdict) =>
      _inner.setFeedback(alertId, verdict);

  @override
  Future<void> clearFeedback(String alertId) => _inner.clearFeedback(alertId);
}

void main() {
  testWidgets('03 에서 유용 → 07 에서도 선택, 07 에서 해제 → 뒤로 가면 03 도 해제', (tester) async {
    await pumpRouterApp(tester);

    await tester.tap(
      find.descendant(of: _fableCard, matching: find.text('유용')),
    );
    await tester.pumpAndSettle();
    expect(_button(tester, _fableCard, FeedbackVerdict.useful).selected, true);

    await tester.tap(find.text(_fable));
    await tester.pumpAndSettle();
    expect(_detail, findsOneWidget);
    expect(_button(tester, _detail, FeedbackVerdict.useful).selected, true);

    await tester.tap(find.descendant(of: _detail, matching: find.text('유용')));
    await tester.pumpAndSettle();
    expect(_button(tester, _detail, FeedbackVerdict.useful).selected, false);

    await tester.tap(
      find.byWidgetPredicate((w) => w is AppIcon && w.name == 'back'),
    );
    await tester.pumpAndSettle();
    expect(_detail, findsNothing);
    expect(_button(tester, _fableCard, FeedbackVerdict.useful).selected, false);
  });

  testWidgets('BeaconKV 근거 — 점수·routing 라벨·바 4행·근거 두 줄·안내·최근 판정', (
    tester,
  ) async {
    await pumpRouterApp(tester, at: AppRoutes.alert('18301'));

    expect(find.text('피드백'), findsOneWidget);
    expect(find.text('arXiv cs.CL · 3시간 전'), findsOneWidget);
    expect(find.text('실험'), findsOneWidget);
    expect(find.text('BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배'), findsOneWidget);
    expect(find.text('이 알림이 온 이유'), findsOneWidget);
    expect(find.text('점수 0.43 / 통과선 0.45', findRichText: true), findsOneWidget);
    expect(find.text('경계 → 탐색 슬롯'), findsOneWidget);

    // hot·multi 가 0 이면 디자인의 네 행만.
    expect(
      tester.widgetList<ScoreBar>(find.byType(ScoreBar)).map((b) => b.label),
      ['src', 'rel', 'fresh', 'kind'],
    );
    expect(_fillRatio(tester, 'src'), closeTo(0.2, 1e-9));
    expect(_fillRatio(tester, 'rel'), closeTo(0.5, 1e-9));

    expect(
      find.text(
        '선별: relevance 0.83 · kind technique — "KV 캐시 압축의 구체 기법과 수치, 코드 공개"\n'
        '판정: importance 4 · 유사 피드백 👍 "PagedAttention v2 — 페이지 단위 KV 캐시 재사용"',
        findRichText: true,
      ),
      findsOneWidget,
    );
    expect(
      find.text(
        '👍는 다음 선별·판정에 사례로 들어가고 arXiv cs.CL의 신뢰도를 보정합니다. '
        'Discord에서 누른 리액션과 자동으로 합쳐집니다.',
        findRichText: true,
      ),
      findsOneWidget,
    );

    expect(find.text('최근 판정 · 오늘 3건'), findsOneWidget);
    expect(find.text('MCP Python SDK v2.2.0 — HTTP 리다이렉트…'), findsOneWidget);
    expect(find.text('42분'), findsOneWidget);
    expect(find.text('SDLC 에이전트 서베이 — 2026 상반기 동향'), findsOneWidget);
    // 09:10Z 판정은 고정 시각 03:00Z 에서 24시간이 안 돼 `N시간` 이다.
    expect(find.text('17시간'), findsOneWidget);
  });

  testWidgets('kind 가 음수면 값이 경고색이고 채움이 없다. 0 아닌 hot·multi 는 행을 더한다', (
    tester,
  ) async {
    await pumpRouterApp(
      tester,
      at: AppRoutes.alert('18301'),
      extra: [
        alertRepositoryProvider.overrideWith(
          (ref) => _ScoreAlertRepository(
            FixtureAlertRepository(ref.watch(fixtureStoreProvider)),
            const {
              'src': 0.10,
              'rel': 0.25,
              'hot': 0.0,
              'multi': 0.05,
              'fresh': 0.10,
              'kind': -0.15,
            },
          ),
        ),
      ],
    );

    expect(
      tester.widgetList<ScoreBar>(find.byType(ScoreBar)).map((b) => b.label),
      ['src', 'rel', 'multi', 'fresh', 'kind'],
    );
    final kindValue = tester.widget<Text>(
      find.descendant(of: _scoreBar('kind'), matching: find.text('−0.15')),
    );
    expect(kindValue.style?.color, AppColors.warn);
    expect(_fillRatio(tester, 'kind'), 0);
    expect(_fillRatio(tester, 'src'), closeTo(0.2, 1e-9));
  });

  testWidgets('최근 판정 행을 누르면 그 알림의 07 을 연다', (tester) async {
    final router = await pumpRouterApp(tester, at: AppRoutes.alert('18301'));

    await tester.tap(find.text('SDLC 에이전트 서베이 — 2026 상반기 동향'));
    await tester.pumpAndSettle();

    expect(router.state.uri.path, AppRoutes.alert('18011'));
    expect(find.text('arXiv cs.SE · 18시간 전'), findsOneWidget);
    expect(find.text('조용히'), findsOneWidget);
  });

  testWidgets('07 에서 판정을 바꾸면 최근 판정 목록과 오늘 건수가 갱신된다', (tester) async {
    await pumpRouterApp(tester, at: AppRoutes.alert('18301'));

    await tester.tap(find.descendant(of: _detail, matching: find.text('불필요')));
    await tester.pumpAndSettle();

    expect(find.text('최근 판정 · 오늘 4건'), findsOneWidget);
    expect(find.text('BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배'), findsNWidgets(2));
  });
}
