// 04 관심사 위젯 테스트 — fixture 표시, 셀 토글·저장 활성, PUT 본문, 422 문구, 더티 뒤로가기, 편집 시트·다이얼로그.
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/core/api/api_exception.dart';
import 'package:tech_radar/core/icons.dart';
import 'package:tech_radar/core/theme/app_colors.dart';
import 'package:tech_radar/core/widgets/widgets.dart';
import 'package:tech_radar/features/settings/interests_draft.dart';

import 'harness.dart';

Finder _cell(String slug) => find.byKey(ValueKey('taxonomy-$slug'));

AccentTextButton _saveButton(WidgetTester tester) => tester
    .widget<AccentTextButton>(find.widgetWithText(AccentTextButton, '저장'));

Color? _textColor(WidgetTester tester, Finder finder) =>
    tester.widget<Text>(finder).style?.color;

Finder _weightIn(String kind, String text) => find.descendant(
  of: find.byKey(ValueKey('kind-$kind')),
  matching: find.text(text),
);

Future<void> _tapBack(WidgetTester tester) async {
  await tester.tap(
    find.byWidgetPredicate((w) => w is AppIcon && w.name == 'back'),
  );
  await tester.pumpAndSettle();
}

void main() {
  setUpSettingsTests();

  testWidgets('fixture 로 8/12 선택, 키워드 7개 이상, 가중치 6행과 음수 경고색', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.interests);

    expect(find.text('나를 한 줄로 (선별 프롬프트에 그대로 들어갑니다)'), findsOneWidget);
    expect(find.textContaining('AI 시스템 개발자.'), findsOneWidget);
    expect(find.text('관심 없음: 채용·홍보·입문 튜토리얼·개발과 무관한 금융 콘텐츠'), findsOneWidget);
    expect(find.text('카테고리 · 8 / 12 선택'), findsOneWidget);
    expect(find.text('새 모델·벤치마크'), findsOneWidget);
    expect(find.text('llm-model'), findsOneWidget);

    for (final keyword in [
      'claude',
      'mcp',
      'langgraph',
      'fastapi',
      'pydantic',
      'next.js',
      'uv',
    ]) {
      expect(find.widgetWithText(AppChip, keyword), findsOneWidget);
    }
    expect(find.widgetWithText(AppChip, '+ 추가'), findsOneWidget);

    for (final kind in editableKinds) {
      expect(find.byKey(ValueKey('kind-${kind.value}')), findsOneWidget);
    }
    expect(find.text('news'), findsNothing);
    expect(find.text('other'), findsNothing);

    for (final (kind, text) in [
      ('survey', '−0.15'),
      ('tutorial', '−0.05'),
      ('promo', '−0.30'),
    ]) {
      expect(_textColor(tester, _weightIn(kind, text)), AppColors.warn);
    }
    expect(
      _textColor(tester, _weightIn('release_major', '+0.00')),
      AppColors.textSecondary,
    );

    expect(_saveButton(tester).onTap, isNull, reason: '변경 없음');
  });

  testWidgets('셀 탭으로 카운트가 늘고 줄며, 전부 해제하면 저장이 비활성', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.interests);

    await tester.tap(_cell('rag-retrieval'));
    await tester.pump();
    expect(find.text('카테고리 · 9 / 12 선택'), findsOneWidget);
    expect(_saveButton(tester).onTap, isNotNull);

    await tester.tap(_cell('rag-retrieval'));
    await tester.tap(_cell('agent'));
    await tester.pump();
    expect(find.text('카테고리 · 7 / 12 선택'), findsOneWidget);

    for (final slug in [
      'llm-model',
      'mcp-tooling',
      'inference-opt',
      'python-backend',
      'web-frontend',
      'dev-community',
      'video',
    ]) {
      await tester.tap(_cell(slug));
    }
    await tester.pump();
    expect(find.text('카테고리 · 0 / 12 선택'), findsOneWidget);
    expect(_saveButton(tester).onTap, isNull, reason: '카테고리 0개');
  });

  testWidgets('저장하면 PUT 본문이 로컬 상태와 같고 news·other 는 GET 값 그대로', (tester) async {
    final (_, settings) = await pumpSettingsApp(
      tester,
      at: AppRoutes.interests,
    );
    final before = await settings.interests();

    await tester.tap(_cell('rag-retrieval'));
    await tester.tap(_cell('video'));
    await tester.pump();
    await tester.tap(find.widgetWithText(AccentTextButton, '저장'));
    await tester.pumpAndSettle();

    expect(settings.savedBodies, [
      {
        'profile': before.profile.toJson(),
        'selected_categories': [
          'llm-model',
          'agent',
          'mcp-tooling',
          'inference-opt',
          'rag-retrieval',
          'python-backend',
          'web-frontend',
          'dev-community',
        ],
        'watch_keywords': before.watchKeywords,
        'kind_weights': before.kindWeights,
      },
    ]);
    final weights = settings.savedBodies.single['kind_weights'] as Map;
    expect(weights['news'], before.kindWeights['news']);
    expect(weights['other'], before.kindWeights['other']);
    expect(find.text('저장했습니다.'), findsOneWidget);
    expect(_saveButton(tester).onTap, isNull, reason: '저장 뒤에는 변경 없음');
  });

  testWidgets('422 응답이면 message 를 보여 주고 편집 상태를 유지한다', (tester) async {
    final (_, settings) = await pumpSettingsApp(
      tester,
      at: AppRoutes.interests,
    );
    settings.saveError = const ApiException(
      'validation_error',
      'kind_weights 값은 −0.50 ~ +0.50 이어야 합니다.',
      status: 422,
    );

    await tester.tap(_cell('rag-retrieval'));
    await tester.pump();
    await tester.tap(find.widgetWithText(AccentTextButton, '저장'));
    await tester.pumpAndSettle();

    expect(find.text('kind_weights 값은 −0.50 ~ +0.50 이어야 합니다.'), findsOneWidget);
    expect(find.text('카테고리 · 9 / 12 선택'), findsOneWidget);
    expect(_saveButton(tester).onTap, isNotNull);
  });

  testWidgets('더티 상태에서 뒤로가기 → 확인 다이얼로그, 취소하면 머문다', (tester) async {
    final (router, _) = await pumpSettingsApp(tester, at: AppRoutes.interests);

    await tester.tap(_cell('rag-retrieval'));
    await tester.pump();
    await _tapBack(tester);

    expect(find.text('저장하지 않고 나갈까요?'), findsOneWidget);
    await tester.tap(find.text('취소'));
    await tester.pumpAndSettle();
    expect(find.text('저장하지 않고 나갈까요?'), findsNothing);
    expect(router.state.uri.path, AppRoutes.interests);
    expect(find.text('카테고리 · 9 / 12 선택'), findsOneWidget);

    await _tapBack(tester);
    await tester.tap(find.text('나가기'));
    await tester.pumpAndSettle();
    expect(router.state.uri.path, AppRoutes.settings);
  });

  testWidgets('변경이 없으면 뒤로가기에 다이얼로그가 없다', (tester) async {
    final (router, _) = await pumpSettingsApp(tester, at: AppRoutes.interests);

    await _tapBack(tester);

    expect(find.text('저장하지 않고 나갈까요?'), findsNothing);
    expect(router.state.uri.path, AppRoutes.settings);
  });

  testWidgets('가중치 시트 스테퍼는 0.05 단위로 움직이고 범위 끝에서 멈춘다', (tester) async {
    final (_, settings) = await pumpSettingsApp(
      tester,
      at: AppRoutes.interests,
    );

    await tester.tap(find.byKey(const ValueKey('kind-survey')));
    await tester.pumpAndSettle();
    expect(find.byKey(const ValueKey('weight-value')), findsOneWidget);
    expect(find.text('−0.15'), findsWidgets);
    await tester.tap(find.byKey(const ValueKey('weight-up')));
    await tester.pump();
    expect(
      tester.widget<Text>(find.byKey(const ValueKey('weight-value'))).data,
      '−0.10',
    );
    await tester.tap(find.widgetWithText(AccentTextButton, '완료'));
    await tester.pumpAndSettle();
    expect(_textColor(tester, _weightIn('survey', '−0.10')), AppColors.warn);

    await tester.tap(find.byKey(const ValueKey('kind-release_major')));
    await tester.pumpAndSettle();
    for (var i = 0; i < 12; i++) {
      await tester.tap(find.byKey(const ValueKey('weight-up')));
    }
    await tester.pump();
    expect(
      tester.widget<Text>(find.byKey(const ValueKey('weight-value'))).data,
      '+0.50',
    );
    final upButton = tester.widget<GestureDetector>(
      find.descendant(
        of: find.byKey(const ValueKey('weight-up')),
        matching: find.byType(GestureDetector),
      ),
    );
    expect(upButton.onTap, isNull, reason: '상한 +0.50');
    await tester.tap(find.widgetWithText(AccentTextButton, '완료'));
    await tester.pumpAndSettle();
    expect(_weightIn('release_major', '+0.50'), findsOneWidget);

    await tester.tap(find.widgetWithText(AccentTextButton, '저장'));
    await tester.pumpAndSettle();
    final weights = settings.savedBodies.single['kind_weights'] as Map;
    expect(weights['survey'], -0.1);
    expect(weights['release_major'], 0.5);
  });

  testWidgets('키워드 추가 다이얼로그는 중복을 막고, 길게 눌러 삭제를 확인한다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.interests);

    await tester.tap(find.widgetWithText(AppChip, '+ 추가'));
    await tester.pumpAndSettle();
    await tester.enterText(find.byType(TextField), 'Claude');
    await tester.tap(find.text('추가'));
    await tester.pumpAndSettle();
    expect(find.text('이미 있는 키워드입니다.'), findsOneWidget);

    await tester.enterText(find.byType(TextField), '  langchain ');
    await tester.tap(find.text('추가'));
    await tester.pumpAndSettle();
    expect(find.byType(AlertDialog), findsNothing);
    expect(find.widgetWithText(AppChip, 'langchain'), findsOneWidget);
    expect(_saveButton(tester).onTap, isNotNull);

    await tester.longPress(find.widgetWithText(AppChip, 'mcp'));
    await tester.pumpAndSettle();
    expect(find.text('키워드 삭제'), findsOneWidget);
    await tester.tap(find.text('삭제'));
    await tester.pumpAndSettle();
    expect(find.widgetWithText(AppChip, 'mcp'), findsNothing);
  });

  testWidgets('프로필 카드를 탭하면 두 필드 편집 시트가 열리고 완료하면 카드에 반영된다', (tester) async {
    await pumpSettingsApp(tester, at: AppRoutes.interests);

    await tester.tap(find.textContaining('AI 시스템 개발자.'));
    await tester.pumpAndSettle();
    await tester.enterText(
      find.byKey(const ValueKey('self-description')),
      '백엔드 개발자.',
    );
    await tester.enterText(find.byKey(const ValueKey('not-interested')), '채용');
    await tester.tap(find.widgetWithText(AccentTextButton, '완료'));
    await tester.pumpAndSettle();

    expect(find.text('백엔드 개발자.'), findsOneWidget);
    expect(find.text('관심 없음: 채용'), findsOneWidget);
    expect(_saveButton(tester).onTap, isNotNull);
  });
}
