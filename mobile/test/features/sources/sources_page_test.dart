// 06 수집 소스 테스트 — Stat·상태 줄 규칙·오류색, 토글 시 활성 소스 갱신·실패 되돌림, `+` 준비 중.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/api/api_exception.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/theme/app_colors.dart';
import 'package:tech_radar/core/theme/app_theme.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';
import 'package:tech_radar/data/repositories/repository_providers.dart';
import 'package:tech_radar/features/sources/sources_page.dart';

/// 조회는 fixture 로 하고 on/off 는 항상 실패한다.
class _FailingSources implements SourceRepository {
  _FailingSources(this._inner);

  final SourceRepository _inner;

  @override
  Future<SourcesResponse> sources() => _inner.sources();

  @override
  Future<Source> setEnabled(String sourceId, {required bool enabled}) async =>
      throw const ApiException('unavailable', 'DB 에 연결할 수 없습니다.', status: 503);
}

Future<SourceRepository> _pump(
  WidgetTester tester, {
  SourceRepository Function(SourceRepository fixture)? wrap,
}) async {
  tester.view.physicalSize = const Size(390, 1400);
  tester.view.devicePixelRatio = 1;
  addTearDown(tester.view.reset);

  final fixture = FixtureSourceRepository(FixtureStore(delay: Duration.zero));
  // rootBundle 은 fake async 밖에서만 끝나므로 fixture 를 먼저 읽어 둔다.
  await tester.runAsync(fixture.sources);
  final repository = wrap?.call(fixture) ?? fixture;
  await tester.pumpWidget(
    ProviderScope(
      overrides: [sourceRepositoryProvider.overrideWithValue(repository)],
      child: MaterialApp(theme: buildAppTheme(), home: const SourcesPage()),
    ),
  );
  await tester.pumpAndSettle();
  return fixture;
}

AppToggle _toggleOf(WidgetTester tester, String sourceId) => tester.widget(
  find.descendant(
    of: find.widgetWithText(SourceRow, sourceId),
    matching: find.byType(AppToggle),
  ),
);

Finder _stat(String text) => find.text(text, findRichText: true);

Source _source({
  int failures = 0,
  String? errorHint,
  String? lastError,
  double? calibrated,
  int? repoCount,
}) => Source(
  id: 'rss:test',
  displayName: 'Test',
  type: SourceType.rss,
  group: SourceGroup.blogRss,
  enabled: true,
  pollIntervalMin: 15,
  trust: calibrated ?? 0.5,
  trustBase: 0.5,
  trustCalibrated: calibrated,
  consecutiveFailures: failures,
  errorHint: errorHint,
  lastError: lastError,
  repoCount: repoCount,
);

void main() {
  testWidgets('Stat 3열·그룹 섹션·미착수 칩을 보여 준다', (tester) async {
    await _pump(tester);

    expect(_stat('9 / 10'), findsOneWidget);
    expect(_stat('612 건'), findsOneWidget);
    expect(_stat('41 / 60'), findsOneWidget);
    expect(find.text('기술 블로그 · RSS'), findsOneWidget);
    expect(find.text('논문 · 릴리즈 · 영상'), findsOneWidget);
    expect(find.text('커뮤니티'), findsNothing);
    expect(find.byType(SourceRow), findsNWidgets(7));
    expect(find.text('미착수'), findsOneWidget);
    for (final name in ['Reddit', 'GitHub Trending', 'X']) {
      expect(find.widgetWithText(AppChip, name), findsOneWidget);
    }
  });

  testWidgets('상태 줄이 계약 규칙대로 조합되고 실패는 오류색이다', (tester) async {
    await _pump(tester);

    final error = tester.widget<Text>(find.text('실패 5회 · 미러 확인 필요'));
    expect(error.style?.color, AppColors.error);
    expect(error.style?.fontWeight, FontWeight.w600);

    final calibrated = tester.widget<Text>(find.text('60분 · 보정 0.5 → 0.58'));
    expect(calibrated.style?.color, AppColors.textTertiary);
    expect(find.text('30분 · 저장소 10개'), findsOneWidget);
    expect(find.text('15분 · 보정 0.6 → 0.52'), findsOneWidget);
    expect(find.text('trust 1.0'), findsNWidgets(2));
    expect(find.text('trust 0.6'), findsNWidgets(2));
  });

  testWidgets('아이콘 타일은 종류별로 rss·github·youtube 다', (tester) async {
    await _pump(tester);

    AppIcon iconOf(String id) => tester.widget(
      find.descendant(
        of: find.widgetWithText(SourceRow, id),
        matching: find.byType(AppIcon),
      ),
    );
    expect(iconOf('rss:anthropic').name, 'rss');
    expect(iconOf('github_release:watchlist').name, 'github');
    expect(iconOf('youtube:jocoding').name, 'youtube');
  });

  testWidgets('토글하면 활성 소스 Stat 이 바뀌고 저장소에도 남는다', (tester) async {
    final fixture = await _pump(tester);

    await tester.tap(find.byWidget(_toggleOf(tester, 'rss:openai')));
    await tester.pumpAndSettle();
    expect(_toggleOf(tester, 'rss:openai').value, isFalse);
    expect(_stat('8 / 10'), findsOneWidget);

    await tester.tap(find.byWidget(_toggleOf(tester, 'youtube:codingapple')));
    await tester.pumpAndSettle();
    expect(_toggleOf(tester, 'youtube:codingapple').value, isTrue);
    expect(_stat('9 / 10'), findsOneWidget);

    final saved = await fixture.sources();
    expect(saved.stats.enabledCount, 9);
    expect(
      saved.sources.firstWhere((s) => s.id == 'rss:openai').enabled,
      false,
    );
  });

  testWidgets('저장에 실패하면 토글과 Stat 을 되돌리고 message 를 보여 준다', (tester) async {
    await _pump(tester, wrap: _FailingSources.new);

    await tester.tap(find.byWidget(_toggleOf(tester, 'rss:openai')));
    await tester.pumpAndSettle();

    expect(_toggleOf(tester, 'rss:openai').value, isTrue);
    expect(_stat('9 / 10'), findsOneWidget);
    expect(find.text('DB 에 연결할 수 없습니다.'), findsOneWidget);
  });

  testWidgets('헤더 + 는 준비 중 토스트를 띄운다', (tester) async {
    await _pump(tester);

    await tester.tap(find.bySemanticsLabel('소스 추가'));
    await tester.pump();

    expect(find.text('준비 중'), findsOneWidget);
  });

  group('sourceStatusLine', () {
    test('주기만 있으면 N분', () {
      expect(sourceStatusLine(_source()), (text: '15분', isError: false));
    });

    test('error_hint 가 없으면 last_error 앞 30자를 쓴다', () {
      final line = sourceStatusLine(
        _source(
          failures: 2,
          lastError: 'HTTPStatusError: 503 Service Unavailable',
        ),
      );
      expect(line, (
        text: '실패 2회 · HTTPStatusError: 503 Service U',
        isError: true,
      ));
    });

    test('조치 문구가 전혀 없으면 실패 횟수만', () {
      expect(sourceStatusLine(_source(failures: 1)), (
        text: '실패 1회',
        isError: true,
      ));
    });

    test('보정과 저장소 수를 차례로 붙인다', () {
      expect(sourceStatusLine(_source(calibrated: 0.5, repoCount: 3)), (
        text: '15분 · 보정 0.5 → 0.5 · 저장소 3개',
        isError: false,
      ));
    });
  });
}
