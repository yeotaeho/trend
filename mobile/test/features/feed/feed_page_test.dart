// 03 피드 화면 테스트 — fixture 카드 3장 문구, 실험 헤더, 필터 칩, 낙관적 갱신 실패 롤백·스낵바.
import 'dart:async';

import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/api/api_exception.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/feed/feed_card.dart';

import '../../helpers.dart';

const _mcp =
    '[릴리즈] MCP Python SDK v2.2.0 — HTTP 리다이렉트·OAuth 검증 변경 (v2.2.0 · v1.30.0)';
const _beacon = 'BeaconKV: 장문 컨텍스트 KV 캐시 압축으로 추론 2.1배';
const _fable = '[모델] Claude 5 Fable — 컨텍스트 2배, 가격 동일';

Finder _card(String title) =>
    find.ancestor(of: find.text(title), matching: find.byType(FeedCard));

Finder _inCard(String title, Finder finder) =>
    find.descendant(of: _card(title), matching: finder);

FeedbackButton _feedbackButton(
  WidgetTester tester,
  String title,
  FeedbackVerdict verdict,
) => tester
    .widgetList<FeedbackButton>(_inCard(title, find.byType(FeedbackButton)))
    .firstWhere((b) => b.verdict == verdict);

Future<void> _tapChip(WidgetTester tester, String label) async {
  await tester.tap(
    find.descendant(of: find.byType(AppChip), matching: find.text(label)),
  );
  await tester.pumpAndSettle();
}

/// 쓰기를 [gate] 가 끝날 때까지 붙잡았다가 서버 오류로 실패시킨다.
class _FailingAlertRepository implements AlertRepository {
  _FailingAlertRepository(this._inner, this.gate);

  final AlertRepository _inner;
  final Completer<void> gate;

  Future<Never> _fail() async {
    await gate.future;
    throw const ApiException('server_error', '판정을 저장하지 못했습니다.', status: 500);
  }

  @override
  Future<AlertDetail> alert(String alertId) => _inner.alert(alertId);

  @override
  Future<RecentFeedback> recentFeedback({int? limit}) =>
      _inner.recentFeedback(limit: limit);

  @override
  Future<FeedbackResult> setFeedback(String alertId, FeedbackVerdict verdict) =>
      _fail();

  @override
  Future<void> clearFeedback(String alertId) => _fail();
}

class _FailingSavedRepository implements SavedRepository {
  @override
  Future<SavedItem> save(String alertId, {String? folderId}) async =>
      throw const ApiException('network', '서버에 연결할 수 없습니다.');

  @override
  dynamic noSuchMethod(Invocation invocation) => super.noSuchMethod(invocation);
}

void main() {
  testWidgets('fixture 카드 3장이 디자인 샘플 문구대로 보이고 2번 카드만 실험 헤더다', (tester) async {
    await pumpRouterApp(tester);

    expect(find.text('오늘'), findsOneWidget);
    expect(find.text('오늘 push 4 / 15'), findsOneWidget);
    expect(find.text('걸러짐 571건 보기 ›'), findsOneWidget);
    expect(find.byType(FeedCard), findsNWidgets(3));

    final samples = {
      _mcp: (
        'GitHub Releases · 42분 전',
        '즉시',
        '스트리밍 HTTP 클라이언트의 리다이렉트 처리와 OAuth 토큰 검증이 바뀐 보안 릴리즈. v1.30.0에 백포트됨.',
        ['#mcp-tooling', '#python-backend'],
      ),
      _beacon: (
        'arXiv cs.CL · 3시간 전',
        '실험',
        '고정 비콘 토큰에 문맥을 요약 저장해 KV 캐시를 8배 줄이고 품질 손실 1% 이내. 코드 공개.',
        ['#inference-opt'],
      ),
      _fable: (
        'Anthropic · 5시간 전',
        '즉시',
        '새 최상위 모델. 툴 사용과 장문 추론 벤치마크 갱신, API 가격은 이전 세대와 동일.',
        ['#llm-model'],
      ),
    };
    for (final MapEntry(key: title, value: (meta, badge, summary, tags))
        in samples.entries) {
      expect(_inCard(title, find.text(meta)), findsOneWidget, reason: title);
      expect(_inCard(title, find.text(badge)), findsOneWidget, reason: title);
      expect(_inCard(title, find.text(summary)), findsOneWidget, reason: title);
      for (final tag in tags) {
        expect(_inCard(title, find.text(tag)), findsOneWidget, reason: tag);
      }
    }

    expect(find.text('실험 · 경계 항목'), findsOneWidget);
    expect(_inCard(_beacon, find.text('실험 · 경계 항목')), findsOneWidget);

    // 1번 카드는 찜됨·유용 선택, 나머지는 둘 다 아님.
    expect(
      tester.widget<BookmarkButton>(_inCard(_mcp, find.byType(BookmarkButton))),
      isA<BookmarkButton>().having((b) => b.saved, 'saved', true),
    );
    expect(
      _feedbackButton(tester, _mcp, FeedbackVerdict.useful).selected,
      true,
    );
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.useful).selected,
      false,
    );
  });

  testWidgets('필터 실험은 1장, 👍 유용은 1장, 전체로 돌아오면 3장', (tester) async {
    await pumpRouterApp(tester);

    await _tapChip(tester, '실험');
    expect(find.byType(FeedCard), findsOneWidget);
    expect(find.text(_beacon), findsOneWidget);

    await _tapChip(tester, '👍 유용');
    expect(find.byType(FeedCard), findsOneWidget);
    expect(find.text(_mcp), findsOneWidget);

    await _tapChip(tester, '전체');
    expect(find.byType(FeedCard), findsNWidgets(3));
  });

  testWidgets('결과가 없는 필터는 빈 상태 문구와 걸러짐 링크를 보인다', (tester) async {
    await pumpRouterApp(tester);

    await _tapChip(tester, '조용히');

    expect(find.byType(FeedCard), findsNothing);
    expect(find.text('오늘 받은 알림이 없습니다'), findsOneWidget);
    expect(find.text('걸러짐 571건 보기 ›'), findsNWidgets(2));
  });

  testWidgets('유용·불필요는 상호배타이고 다시 누르면 해제된다', (tester) async {
    await pumpRouterApp(tester);

    await tester.tap(_inCard(_fable, find.text('유용')));
    await tester.pumpAndSettle();
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.useful).selected,
      true,
    );

    await tester.tap(_inCard(_fable, find.text('불필요')));
    await tester.pumpAndSettle();
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.useful).selected,
      false,
    );
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.notUseful).selected,
      true,
    );

    await tester.tap(_inCard(_fable, find.text('불필요')));
    await tester.pumpAndSettle();
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.notUseful).selected,
      false,
    );
  });

  testWidgets('판정 저장이 실패하면 버튼이 롤백되고 스낵바에 message 가 보인다', (tester) async {
    final gate = Completer<void>();
    await pumpRouterApp(
      tester,
      extra: [
        alertRepositoryProvider.overrideWith(
          (ref) => _FailingAlertRepository(
            FixtureAlertRepository(ref.watch(fixtureStoreProvider)),
            gate,
          ),
        ),
      ],
    );

    await tester.tap(_inCard(_fable, find.text('유용')));
    await tester.pump();
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.useful).selected,
      true,
      reason: '낙관적 갱신',
    );

    gate.complete();
    await tester.pumpAndSettle();
    expect(
      _feedbackButton(tester, _fable, FeedbackVerdict.useful).selected,
      false,
    );
    expect(find.text('판정을 저장하지 못했습니다.'), findsOneWidget);
  });

  testWidgets('찜 저장이 실패하면 찜 아이콘이 롤백되고 스낵바가 뜬다', (tester) async {
    await pumpRouterApp(
      tester,
      extra: [
        savedRepositoryProvider.overrideWithValue(_FailingSavedRepository()),
      ],
    );

    await tester.tap(_inCard(_fable, find.byType(BookmarkButton)));
    await tester.pumpAndSettle();

    expect(
      tester
          .widget<BookmarkButton>(_inCard(_fable, find.byType(BookmarkButton)))
          .saved,
      false,
    );
    expect(find.text('서버에 연결할 수 없습니다.'), findsOneWidget);
  });

  testWidgets('검색·벨은 준비 중 안내, 걸러짐 링크는 09 로 간다', (tester) async {
    final router = await pumpRouterApp(tester);

    await tester.tap(
      find.byWidgetPredicate((w) => w is AppIcon && w.name == 'search'),
    );
    await tester.pumpAndSettle();
    expect(find.text('준비 중'), findsOneWidget);

    await tester.tap(find.text('걸러짐 571건 보기 ›'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.filtered);
    expect(router.state.uri.queryParameters['view'], 'source');
  });
}
