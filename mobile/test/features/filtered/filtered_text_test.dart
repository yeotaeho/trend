// 걸러진 항목 문구 조합 테스트 — fixture 그룹·항목으로 요약 줄·사유 줄이 계약 4.6·3.2 규칙과 디자인 문구를 따르는지 본다.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/features/filtered/filtered_text.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FixtureFilteredRepository repo;
  late FilteredSummary summary;

  setUp(() async {
    repo = FixtureFilteredRepository(FixtureStore(delay: Duration.zero));
    summary = await repo.summary();
  });

  Future<Map<String, String>> summaries(FilteredView view) async {
    final groups = (await repo.groups(view: view)).groups;
    return {
      for (final g in groups)
        groupTitle(g, view): groupSummary(
          g,
          view,
          borderlineRange: summary.borderline.range,
        ),
    };
  }

  /// fixture 항목 — 관문별 목록을 차례로 뒤진다.
  Future<DroppedItem> item(String id) async {
    for (final gate in Gate.values) {
      final page = await repo.items(view: FilteredView.gate, key: gate.value);
      final found = page.items.where((d) => d.id == id).firstOrNull;
      if (found != null) return found;
    }
    throw StateError('fixture 에 $id 가 없습니다.');
  }

  test('소스별 요약 — relevance 비율이 0.5 이상이면 비율, 아니면 관문 건수', () async {
    expect(await summaries(FilteredView.source), {
      'rss:arxiv-cs-ai': '선별 relevance 0.5 미만 71%',
      'rss:arxiv-cs-cl': '선별 relevance 0.5 미만 64%',
      'rss:huggingface': '중복 9 · 선별 11 · 점수 3',
      'youtube:jocoding': '중복 4 · 판정 10',
      'github_release:watchlist': '중복 8 · 판정 3 · 클러스터 하루 1건 1',
      'rss:vercel': 'exclude 2 · 선별 5',
    });
  });

  test('종류별 요약 — 감점·판정 수·경계·키워드·클러스터, 규칙 없는 kind 는 소스별 규칙', () async {
    expect(await summaries(FilteredView.kind), {
      'survey · 서베이·전망': '감점 −0.15 · 불필요 4/4 → 감점 유지 중',
      'technique · 기법·논문': '점수 경계(0.35–0.45) 154건',
      'other · 기타': '선별 relevance 0.5 미만 83%',
      'release_patch · 패치 릴리즈': '클러스터 하루 1건 1',
      'tutorial · 튜토리얼': '감점 −0.05',
      'promo · 홍보·구인': '감점 −0.30 · exclude 키워드 2',
      '미분류 (exclude·중복)': '선별 전 탈락 — kind 없음',
    });
  });

  test('관문별 요약 — gate 라벨 제목과 preview 에 많이 나온 소스 2개', () async {
    final result = await summaries(FilteredView.gate);
    expect(result['선별'], 'arXiv cs.CL · arXiv cs.AI');
    expect(result['클러스터 하루 1건'], 'GitHub Releases');
  });

  test('사유 줄 — 선별·점수·탐색 후보는 디자인 문구와 같다', () async {
    expect(
      reasonLine(await item('18120'), FilteredView.source),
      'relevance 0.3 · survey · "관심 스택과 무관한 도메인 서베이"',
    );
    expect(
      reasonLine(await item('18093'), FilteredView.source),
      '0.41 (src 0.10 · rel 0.24 · kind −0.15)',
    );
    expect(
      reasonLine(await item('18131'), FilteredView.source),
      '0.43 · 경계 → 내일 탐색 슬롯 후보',
    );
  });

  test('사유 줄 — 종류별은 점수 괄호 대신 소스명, 선별은 kind 를 뺀다', () async {
    expect(
      reasonLine(await item('18107'), FilteredView.kind),
      '0.41 · arXiv cs.SE',
    );
    expect(
      reasonLine(await item('18077'), FilteredView.kind),
      'relevance 0.4 · "수치 없는 포지션 논문"',
    );
    expect(
      reasonLine(await item('18131'), FilteredView.kind),
      '0.43 · 경계 → 내일 탐색 슬롯 후보',
    );
  });

  test('사유 줄 — exclude·중복·판정·클러스터 고정 문구', () async {
    expect(
      reasonLine(await item('18112'), FilteredView.source),
      '키워드 sponsored',
    );
    expect(reasonLine(await item('18140'), FilteredView.source), '같은 이슈 중복');
    expect(reasonLine(await item('18101'), FilteredView.source), '판정 false');
    expect(
      reasonLine(await item('18336'), FilteredView.source),
      '같은 이슈 하루 1건 → 앞 알림에 병기',
    );
  });

  test('빈 값 — 걸린 키워드가 없으면 exclude 키워드, 판정 0건이면 불필요 줄을 뺀다', () async {
    final exclude = await item('18112');
    expect(
      reasonLine(
        DroppedItem.fromJson({...exclude.toJson(), 'matched_keywords': []}),
        FilteredView.source,
      ),
      'exclude 키워드',
    );
    const group = FilteredGroup(
      key: 'news',
      count: 3,
      gateCounts: {Gate.score: 3},
      kind: Kind.news,
      kindWeight: -0.1,
      kindFeedback: KindFeedback(notUseful: 0, total: 0),
      penaltyActive: true,
      borderlineCount: 0,
      excludeKeywordHits: 0,
      preview: [],
    );
    expect(
      groupSummary(
        group,
        FilteredView.kind,
        borderlineRange: const [0.35, 0.45],
      ),
      '감점 −0.10',
    );
  });

  test('요약 카드 안내 — 소스별·관문별은 경계, 종류별은 미분류 건수', () {
    expect(
      summaryNote(summary, FilteredView.source),
      '점수 탈락 중 경계(0.35–0.45) 154건 · 탐색 슬롯 후보',
    );
    expect(
      summaryNote(summary, FilteredView.kind),
      'kind는 선별 단계 출력이라 exclude·중복 탈락 67건은 "미분류"로 묶입니다.',
    );
  });

  test('relevance 는 끝자리 0 을 뗀다', () {
    expect(formatRelevance(0.3), '0.3');
    expect(formatRelevance(0.62), '0.62');
    expect(formatRelevance(0.5), '0.5');
  });
}
