// AppIcon 테스트 — 26개 이름을 모두 그리고, 알 수 없는 이름은 assert 로 막는다.
import 'package:flutter/material.dart';
import 'package:flutter_svg/flutter_svg.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/icons.dart';

import '../helpers.dart';

void main() {
  test('디자인 아이콘은 26종이다', () {
    expect(appIconPaths, hasLength(26));
  });

  test('공통 래퍼는 viewBox 24·선 굵기 1.8·둥근 끝과 지정 색을 쓴다', () {
    final svg = appIconSvg('back', const Color(0xFF2D5BE3));
    expect(svg, contains('viewBox="0 0 24 24"'));
    expect(svg, contains('stroke-width="1.8"'));
    expect(svg, contains('stroke-linecap="round"'));
    expect(svg, contains('stroke-linejoin="round"'));
    expect(svg, contains('stroke="#2d5be3"'));
  });

  test('bookmarkfill 의 currentColor 채움은 선 색으로 바뀐다', () {
    final svg = appIconSvg('bookmarkfill', const Color(0xFF2D5BE3));
    expect(svg, isNot(contains('currentColor')));
    expect(svg, contains('fill="#2d5be3"'));
  });

  for (final name in appIconPaths.keys) {
    testWidgets('$name 을 그린다', (tester) async {
      await tester.runAsync(
        () => vg.loadPicture(
          SvgStringLoader(appIconSvg(name, Colors.black)),
          null,
        ),
      );
      await pumpInApp(tester, AppIcon(name, size: 22));
      await tester.pumpAndSettle();

      expect(tester.takeException(), isNull);
      final picture = tester.widget<SvgPicture>(find.byType(SvgPicture));
      expect(picture.width, 22);
      expect(picture.height, 22);
    });
  }

  testWidgets('알 수 없는 이름은 assert 한다', (tester) async {
    await pumpInApp(tester, const AppIcon('nope'));
    expect(tester.takeException(), isA<AssertionError>());
  });
}
