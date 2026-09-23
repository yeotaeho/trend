// 09·10 걸러진 항목 화면 테스트 — fixture 저장소로 그룹 순서·펼침·보기 전환·정렬·더 보기·복원·빈 상태를 본다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/providers.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/filtered/drop_group_card.dart';
import 'package:tech_radar/features/filtered/filtered_page.dart';

Future<void> _pump(
  WidgetTester tester, {
  FixtureStore? store,
  FilteredRepository? repository,
  FilteredView initialView = FilteredView.source,
}) async {
  // 긴 목록이 한 화면에 다 그려지게 세로로 늘린다.
  tester.view.physicalSize = const Size(390, 3200);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);
  // fixture 는 rootBundle 을 실제 비동기로 읽으므로 실제 존에서 미리 올려 둔다.
  final fixtures = store ?? FixtureStore(delay: Duration.zero);
  await tester.runAsync(() => FixtureMetaRepository(fixtures).meta());
  await tester.pumpWidget(
    ProviderScope(
      overrides: [
        useFixturesProvider.overrideWithValue(true),
        fixtureStoreProvider.overrideWithValue(fixtures),
        if (repository != null)
          filteredRepositoryProvider.overrideWithValue(repository),
      ],
      child: MaterialApp(
        theme: buildAppTheme(),
        home: FilteredPage(initialView: initialView),
      ),
    ),
  );
  await _settle(tester);
}

/// 저장소 호출은 실제 존에서 끝난 로딩 Future 를 기다리므로, 실제 비동기를 잠깐씩 돌려
/// 응답을 넘긴 뒤 프레임을 정리한다.
Future<void> _settle(WidgetTester tester) async {
  for (var i = 0; i < 3; i++) {
    await tester.runAsync(() => Future<void>.delayed(Duration.zero));
    await tester.pump();
  }
  await tester.pumpAndSettle();
}

/// 피드 저장소 조회도 같은 이유로 실제 존에서 돌린다.
Future<List<String>> _feedIds(WidgetTester tester, FixtureStore store) async {
  final page = await tester.runAsync(() => FixtureFeedRepository(store).feed());
  return page!.items.map((a) => a.id).toList();
}

Finder _group(String key) => find.byKey(ValueKey('drop-group-$key'));

List<DropGroupCard> _cards(WidgetTester tester) =>
    tester.widgetList<DropGroupCard>(find.byType(DropGroupCard)).toList();

List<String> _titles(WidgetTester tester) =>
    _cards(tester).map((c) => c.title).toList();

Iterable<String> _rowTitles(WidgetTester tester, Finder group) => tester
    .widgetList<DroppedItemRow>(
      find.descendant(of: group, matching: find.byType(DroppedItemRow)),
    )
    .map((r) => r.item.title);

Future<void> _tapText(WidgetTester tester, String text) async {
  await tester.tap(find.text(text));
  await _settle(tester);
}

RestoreButton _restoreOf(WidgetTester tester, String title) =>
    tester.widget<RestoreButton>(
      find.descendant(
        of: find.widgetWithText(DroppedItemRow, title),
        matching: find.byType(RestoreButton),
      ),
    );

void main() {
  testWidgets('09 — 요약 카드, 그룹 6개 순서·건수·요약, 첫 그룹만 펼침', (tester) async {
    await _pump(tester);

    expect(find.text('걸러진 항목'), findsOneWidget);
    expect(
      find.text('오늘 걸러짐 571 / 수집 612', findRichText: true),
      findsOneWidget,
    );
    expect(find.text('최근 24시간'), findsOneWidget);
    expect(find.text('점수 탈락 중 경계(0.35–0.45) 154건 · 탐색 슬롯 후보'), findsOneWidget);
    expect(find.text('소스별 · 많은 순'), findsOneWidget);

    expect(_titles(tester), [
      'rss:arxiv-cs-ai',
      'rss:arxiv-cs-cl',
      'rss:huggingface',
      'youtube:jocoding',
      'github_release:watchlist',
      'rss:vercel',
    ]);
    expect(_cards(tester).map((c) => c.count), [312, 198, 23, 14, 12, 7]);
    expect(_cards(tester).map((c) => c.icon), [
      'rss',
      'rss',
      'rss',
      'youtube',
      'github',
      'rss',
    ]);
    expect(find.text('선별 relevance 0.5 미만 71%'), findsOneWidget);
    expect(find.text('중복 9 · 선별 11 · 점수 3'), findsOneWidget);

    expect(_cards(tester).map((c) => c.expanded), [
      true,
      false,
      false,
      false,
      false,
      false,
    ]);
    expect(_rowTitles(tester, _group('rss:arxiv-cs-ai')), [
      'LLM 기반 자율주행 의사결정 프레임워크 제안',
      'Survey of Agentic Software Engineering, 2026H1',
      'Beacon-style KV compaction for 1M-token context',
    ]);
    expect(
      find.text('relevance 0.3 · survey · "관심 스택과 무관한 도메인 서베이"'),
      findsOneWidget,
    );
    expect(
      find.text('0.41 (src 0.10 · rel 0.24 · kind −0.15)'),
      findsOneWidget,
    );
    expect(find.text('0.43 · 경계 → 내일 탐색 슬롯 후보'), findsOneWidget);
    expect(find.text('선별 탈락'), findsOneWidget);
    expect(find.text('점수 탈락'), findsNWidgets(2));
  });

  testWidgets('종류별 — 미분류가 마지막, 합계 571, 아이콘 타일 없음', (tester) async {
    await _pump(tester);
    await _tapText(tester, '종류별');

    expect(find.text('종류별 · 많은 순'), findsOneWidget);
    expect(
      find.text('kind는 선별 단계 출력이라 exclude·중복 탈락 67건은 "미분류"로 묶입니다.'),
      findsOneWidget,
    );
    final titles = _titles(tester);
    expect(titles.first, 'survey · 서베이·전망');
    expect(titles.last, '미분류 (exclude·중복)');
    expect(titles, hasLength(7));
    expect(_cards(tester).fold<int>(0, (sum, c) => sum + c.count), 571);
    expect(_cards(tester).every((c) => c.icon == null), isTrue);

    expect(_rowTitles(tester, _group('survey')), [
      'Survey of Agentic Software Engineering, 2026H1',
      'LLM Evaluation: A Position Paper',
    ]);
    expect(find.text('0.41 · arXiv cs.SE'), findsOneWidget);
    expect(find.text('relevance 0.4 · "수치 없는 포지션 논문"'), findsOneWidget);
  });

  testWidgets('그룹 펼침 상태는 보기를 바꾸면 초기화된다', (tester) async {
    await _pump(tester);
    await _tapText(tester, 'rss:arxiv-cs-ai');
    await _tapText(tester, 'rss:huggingface');
    expect(_cards(tester).map((c) => c.expanded).toList(), [
      false,
      false,
      true,
      false,
      false,
      false,
    ]);
    expect(
      find.descendant(
        of: _group('rss:huggingface'),
        matching: find.byWidgetPredicate(
          (w) => w is AppIcon && w.name == 'chevd',
        ),
      ),
      findsOneWidget,
    );

    await _tapText(tester, '종류별');
    await _tapText(tester, '소스별');

    expect(_cards(tester).map((c) => c.expanded).toList(), [
      true,
      false,
      false,
      false,
      false,
      false,
    ]);
  });

  testWidgets('섹션 라벨을 누르면 이름순 ↔ 많은 순으로 바뀐다', (tester) async {
    await _pump(tester);
    await _tapText(tester, '소스별 · 많은 순');

    expect(find.text('소스별 · 이름순'), findsOneWidget);
    expect(_titles(tester).first, isNot('rss:arxiv-cs-ai'));

    await _tapText(tester, '소스별 · 이름순');
    expect(_titles(tester).first, 'rss:arxiv-cs-ai');
  });

  testWidgets('더 보기는 목록 API 로 나머지를 불러오고 끝이면 사라진다', (tester) async {
    await _pump(tester);
    expect(find.text('더 보기'), findsOneWidget);

    await _tapText(tester, '더 보기');

    expect(find.text('더 보기'), findsNothing);
    expect(_rowTitles(tester, _group('rss:arxiv-cs-ai')), hasLength(3));
  });

  testWidgets('복원 탭 → 선택 상태·스낵바, 피드 첫 항목이 그 항목, 다시 탭하면 취소', (tester) async {
    final store = FixtureStore(delay: Duration.zero);
    await _pump(tester, store: store);
    const title = 'LLM 기반 자율주행 의사결정 프레임워크 제안';
    expect(_restoreOf(tester, title).restored, isFalse);

    await tester.tap(
      find.descendant(
        of: find.widgetWithText(DroppedItemRow, title),
        matching: find.byType(RestoreButton),
      ),
    );
    await _settle(tester);

    expect(_restoreOf(tester, title).restored, isTrue);
    expect(find.text('피드에 추가했습니다'), findsOneWidget);
    expect((await _feedIds(tester, store)).first, '18120');

    await tester.tap(
      find.descendant(
        of: find.widgetWithText(DroppedItemRow, title),
        matching: find.byType(RestoreButton),
      ),
    );
    await _settle(tester);

    expect(_restoreOf(tester, title).restored, isFalse);
    expect(await _feedIds(tester, store), isNot(contains('18120')));
  });

  testWidgets('cluster_dup — GateBar 일곱째 구간, release_patch 요약, 관문별 그룹과 복원', (
    tester,
  ) async {
    final store = FixtureStore(delay: Duration.zero);
    await _pump(tester, store: store);
    expect(
      find.byKey(const ValueKey('gate-segment-cluster_dup')),
      findsOneWidget,
    );
    expect(find.text('클러스터 하루 1건 1'), findsOneWidget);
    expect(find.text('오래됨 0'), findsNothing);

    await _tapText(tester, '종류별');
    expect(
      find.descendant(
        of: _group('release_patch'),
        matching: find.text('클러스터 하루 1건 1'),
      ),
      findsOneWidget,
    );

    await _tapText(tester, '관문별');
    await tester.tap(
      find.descendant(
        of: _group('cluster_dup'),
        matching: find.text('클러스터 하루 1건'),
      ),
    );
    await _settle(tester);

    final row = find.ancestor(
      of: find.textContaining('[릴리즈] MCP Python SDK v1.30.0'),
      matching: find.byType(DroppedItemRow),
    );
    expect(row, findsOneWidget);
    expect(
      find.descendant(of: row, matching: find.byType(StageTag)),
      findsOneWidget,
    );
    expect(
      tester
          .widget<StageTag>(
            find.descendant(of: row, matching: find.byType(StageTag)),
          )
          .gate
          .tagLabel,
      '클러스터 하루 1건',
    );
    expect(
      find.descendant(of: row, matching: find.text('같은 이슈 하루 1건 → 앞 알림에 병기')),
      findsOneWidget,
    );

    await tester.tap(
      find.descendant(of: row, matching: find.byType(RestoreButton)),
    );
    await _settle(tester);

    expect(
      tester
          .widget<RestoreButton>(
            find.descendant(of: row, matching: find.byType(RestoreButton)),
          )
          .restored,
      isTrue,
    );
    expect((await _feedIds(tester, store)).first, '18336');
  });

  testWidgets('검색 아이콘은 준비 중 스낵바', (tester) async {
    await _pump(tester);
    await tester.tap(
      find.byWidgetPredicate((w) => w is AppIcon && w.name == 'search'),
    );
    await tester.pump();

    expect(find.text('준비 중'), findsOneWidget);
  });

  testWidgets('걸러짐 0건이면 GateBar·그룹 없이 빈 상태 문구', (tester) async {
    await _pump(tester, repository: _EmptyFilteredRepository());

    expect(find.text('오늘 걸러진 항목이 없습니다'), findsOneWidget);
    expect(find.byType(GateBar), findsNothing);
    expect(find.byType(DropGroupCard), findsNothing);
    expect(find.text('소스별 · 많은 순'), findsNothing);
  });
}

class _EmptyFilteredRepository extends Fake implements FilteredRepository {
  @override
  Future<FilteredSummary> summary({int? hours}) async => const FilteredSummary(
    windowHours: 24,
    filteredTotal: 0,
    collectedTotal: 40,
    gateCounts: {},
    borderline: Borderline(count: 0, range: [0.35, 0.45]),
    unclassifiedCount: 0,
  );
}
