// 공통 위젯 테스트 — Chip·FeedbackButton 선택 색, Toggle on/off, 세그먼트 콜백, GateBar 구간 폭.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/core/theme/app_colors.dart';
import 'package:tech_radar/core/widgets/widgets.dart';

import '../../helpers.dart';

BoxDecoration _decorationOf(WidgetTester tester, Finder owner) {
  final container = tester.widget<Container>(
    find.descendant(of: owner, matching: find.byType(Container)).first,
  );
  return container.decoration! as BoxDecoration;
}

Color? _textColor(WidgetTester tester, String text) =>
    tester.widget<Text>(find.text(text)).style?.color;

void main() {
  group('AppChip', () {
    testWidgets('선택은 inverse 배경·흰 글자·같은 색 테두리', (tester) async {
      await pumpInApp(tester, const AppChip(label: '전체', selected: true));

      final decoration = _decorationOf(tester, find.byType(AppChip));
      expect(decoration.color, AppColors.textPrimary);
      expect((decoration.border! as Border).top.color, AppColors.textPrimary);
      expect(_textColor(tester, '전체'), AppColors.textInverse);
    });

    testWidgets('미선택은 흰 배경·#D9D5CC 테두리·secondary 글자', (tester) async {
      await pumpInApp(tester, const AppChip(label: '즉시'));

      final decoration = _decorationOf(tester, find.byType(AppChip));
      expect(decoration.color, AppColors.surface);
      expect((decoration.border! as Border).top.color, AppColors.borderControl);
      expect(_textColor(tester, '즉시'), AppColors.textSecondary);
    });

    testWidgets('탭하면 onTap 을 부른다', (tester) async {
      var taps = 0;
      await pumpInApp(tester, AppChip(label: '실험', onTap: () => taps++));
      await tester.tap(find.text('실험'));
      expect(taps, 1);
    });

    testWidgets('FolderChip 개수 색은 선택 #B8B4AB, 미선택 #8A877F, + 칩은 개수 없음', (
      tester,
    ) async {
      await pumpInApp(
        tester,
        const Row(
          mainAxisSize: MainAxisSize.min,
          children: [
            FolderChip(label: '전체', count: 23, selected: true),
            FolderChip(label: '나중에 읽기', count: 9),
            FolderChip(label: '+'),
          ],
        ),
      );

      expect(_textColor(tester, '23'), AppColors.chevron);
      expect(_textColor(tester, '9'), AppColors.textTertiary);
      expect(
        find.descendant(
          of: find.widgetWithText(FolderChip, '+'),
          matching: find.byType(Text),
        ),
        findsOneWidget,
      );
    });
  });

  group('FeedbackButton', () {
    testWidgets('선택은 #1C1B19 배경·테두리와 흰 글자', (tester) async {
      await pumpInApp(
        tester,
        const SizedBox(
          width: 160,
          child: FeedbackButton(
            verdict: FeedbackVerdict.useful,
            selected: true,
          ),
        ),
      );

      final decoration = _decorationOf(tester, find.byType(FeedbackButton));
      expect(decoration.color, AppColors.textPrimary);
      expect((decoration.border! as Border).top.color, AppColors.textPrimary);
      expect(_textColor(tester, '유용'), AppColors.textInverse);
    });

    testWidgets('미선택은 흰 배경·#D9D5CC 테두리·secondary 글자', (tester) async {
      await pumpInApp(
        tester,
        const SizedBox(
          width: 160,
          child: FeedbackButton(
            verdict: FeedbackVerdict.notUseful,
            selected: false,
          ),
        ),
      );

      final decoration = _decorationOf(tester, find.byType(FeedbackButton));
      expect(decoration.color, AppColors.surface);
      expect((decoration.border! as Border).top.color, AppColors.borderControl);
      expect(_textColor(tester, '불필요'), AppColors.textSecondary);
    });

    testWidgets('FeedbackButtons 는 선택된 쪽을 다시 누르면 해제(null)를 알린다', (
      tester,
    ) async {
      final changes = <FeedbackVerdict?>[];
      await pumpInApp(
        tester,
        SizedBox(
          width: 320,
          child: FeedbackButtons(
            value: FeedbackVerdict.useful,
            onChanged: changes.add,
          ),
        ),
      );

      await tester.tap(find.text('유용'));
      await tester.tap(find.text('불필요'));
      expect(changes, [null, FeedbackVerdict.notUseful]);
    });
  });

  group('AppToggle', () {
    Future<void> pumpToggle(WidgetTester tester, bool value) async {
      await pumpInApp(tester, AppToggle(value: value, onChanged: (_) {}));
      await tester.pumpAndSettle();
    }

    testWidgets('ON 은 #2D5BE3 트랙에 knob 오른쪽', (tester) async {
      await pumpToggle(tester, true);

      expect(tester.getSize(find.byType(AppToggle)), const Size(44, 26));
      final track = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );
      expect((track.decoration! as BoxDecoration).color, AppColors.primary);
      final align = tester.widget<AnimatedAlign>(find.byType(AnimatedAlign));
      expect(align.alignment, Alignment.centerRight);
    });

    testWidgets('OFF 는 #D6D2C9 트랙에 knob 왼쪽', (tester) async {
      await pumpToggle(tester, false);

      final track = tester.widget<AnimatedContainer>(
        find.byType(AnimatedContainer),
      );
      expect((track.decoration! as BoxDecoration).color, AppColors.controlOff);
      final align = tester.widget<AnimatedAlign>(find.byType(AnimatedAlign));
      expect(align.alignment, Alignment.centerLeft);
    });

    testWidgets('탭하면 반대 값을 알린다', (tester) async {
      bool? changed;
      await pumpInApp(
        tester,
        AppToggle(value: false, onChanged: (v) => changed = v),
      );
      await tester.tap(find.byType(AppToggle));
      expect(changed, isTrue);
    });

    testWidgets('ToggleRow 는 제목·보조 줄과 토글을 그리고 높이가 52 이상', (tester) async {
      await pumpInApp(
        tester,
        const SizedBox(
          width: 326,
          child: ToggleRow(
            title: 'Telegram 봇',
            subtitle: '연결 안 됨',
            value: false,
            isLast: true,
          ),
        ),
      );

      expect(find.text('Telegram 봇'), findsOneWidget);
      expect(find.text('연결 안 됨'), findsOneWidget);
      expect(find.byType(AppToggle), findsOneWidget);
      expect(
        tester.getSize(find.byType(SettingRow)).height,
        greaterThanOrEqualTo(52),
      );
    });
  });

  group('SegmentedControl', () {
    testWidgets('조각을 누르면 그 값으로 콜백하고 선택 조각만 primary 글자', (tester) async {
      FilteredView? changed;
      await pumpInApp(
        tester,
        SizedBox(
          width: 358,
          child: SegmentedControl<FilteredView>(
            values: FilteredView.values,
            selected: FilteredView.source,
            labelOf: (v) => v.label,
            onChanged: (v) => changed = v,
          ),
        ),
      );

      expect(_textColor(tester, '소스별'), AppColors.textPrimary);
      expect(_textColor(tester, '종류별'), AppColors.textTertiary);

      await tester.tap(find.text('관문별'));
      expect(changed, FilteredView.gate);
    });
  });

  group('GateBar', () {
    testWidgets('구간 폭은 건수 ÷ 합계에 비례한다', (tester) async {
      await pumpInApp(
        tester,
        const SizedBox(
          width: 300,
          child: GateBar(
            counts: {Gate.exclude: 1, Gate.dedup: 2, Gate.score: 3},
          ),
        ),
      );

      double width(Gate gate) => tester
          .getSize(find.byKey(ValueKey('gate-segment-${gate.value}')))
          .width;

      expect(width(Gate.exclude), moreOrLessEquals(50));
      expect(width(Gate.dedup), moreOrLessEquals(100));
      expect(width(Gate.score), moreOrLessEquals(150));
      expect(
        find.byKey(ValueKey('gate-segment-${Gate.judgment.value}')),
        findsNothing,
      );
    });

    testWidgets('범례는 다섯 관문을 늘 보여 주고 stale·cluster_dup 은 건수가 있을 때만', (
      tester,
    ) async {
      await pumpInApp(
        tester,
        const SizedBox(
          width: 358,
          child: GateBar(counts: {Gate.score: 3, Gate.stale: 2}),
        ),
      );

      expect(find.text('exclude 0'), findsOneWidget);
      expect(find.text('판정 0'), findsOneWidget);
      expect(find.text('오래됨 2'), findsOneWidget);
      expect(find.textContaining('클러스터'), findsNothing);
    });
  });

  group('ScoreBar', () {
    testWidgets('채움은 값 ÷ 0.5 비율이다', (tester) async {
      await pumpInApp(
        tester,
        const SizedBox(width: 300, child: ScoreBar(label: 'src', value: 0.10)),
      );

      // 트랙 폭 = 300 − 라벨 56 − 값 44 − 간격 10×2.
      expect(
        tester.getSize(find.byKey(const ValueKey('score-bar-fill'))).width,
        moreOrLessEquals(180 * 0.2),
      );
      expect(find.text('0.10'), findsOneWidget);
    });

    testWidgets('음수는 채움이 없고 값이 경고색이다', (tester) async {
      await pumpInApp(
        tester,
        const SizedBox(
          width: 300,
          child: ScoreBar(label: 'kind', value: -0.15),
        ),
      );

      expect(
        tester.getSize(find.byKey(const ValueKey('score-bar-fill'))).width,
        0,
      );
      expect(_textColor(tester, '−0.15'), AppColors.warn);
    });
  });

  group('배지', () {
    testWidgets('피드만 배지는 #EEF5EE / #3D7A4A', (tester) async {
      await pumpInApp(tester, const DeliveryBadge(DeliveryMode.feedOnly));

      final decoration = _decorationOf(tester, find.byType(DeliveryBadge));
      expect(decoration.color, AppColors.feedSoft);
      expect(_textColor(tester, '피드만'), AppColors.feed);
    });

    testWidgets('선별 탈락 태그는 #EAF0FC / #4A6FD0', (tester) async {
      await pumpInApp(tester, const StageTag(Gate.screening));

      final decoration = _decorationOf(tester, find.byType(StageTag));
      expect(decoration.color, AppColors.infoSoft);
      expect(_textColor(tester, '선별 탈락'), AppColors.info);
    });
  });
}
