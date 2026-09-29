// 04 편집 상태 단위 테스트 — 더티 판정, taxonomy 순서, 키워드 검증, 가중치 반올림.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/features/settings/interests_draft.dart';

InterestsDraft _draft({List<String> keywords = const ['claude', 'uv']}) =>
    InterestsDraft(
      InterestsSettings(
        profile: const InterestsProfile(
          selfDescription: '개발자.',
          notInterested: '채용',
        ),
        selectedCategories: const ['agent', 'llm-model'],
        watchKeywords: keywords,
        kindWeights: const {'survey': -0.15, 'news': 0.1, 'other': 0},
      ),
      taxonomy: const ['llm-model', 'agent', 'rag-retrieval'],
      keywordsMax: 3,
    );

void main() {
  test('처음에는 더티가 아니고 되돌리면 다시 깨끗하다', () {
    final draft = _draft();
    expect(draft.isDirty, isFalse);

    draft.toggleCategory('agent');
    expect(draft.isDirty, isTrue);
    draft.toggleCategory('agent');
    expect(draft.isDirty, isFalse);

    draft.setWeight(Kind.survey, -0.1);
    expect(draft.isDirty, isTrue);
    draft.setWeight(Kind.survey, -0.15);
    expect(draft.isDirty, isFalse);
  });

  test('선택 목록은 taxonomy 순서로 보내고 카테고리 0개면 저장 불가', () {
    final draft = _draft()..toggleCategory('rag-retrieval');
    expect(draft.toSettings().selectedCategories, [
      'llm-model',
      'agent',
      'rag-retrieval',
    ]);

    draft
      ..toggleCategory('rag-retrieval')
      ..toggleCategory('agent')
      ..toggleCategory('llm-model');
    expect(draft.isDirty, isTrue);
    expect(draft.canSave, isFalse);
  });

  test('키워드는 공백을 떼고 대소문자 무시 중복·길이·개수를 검사한다', () {
    final draft = _draft();
    expect(draft.addKeyword('   '), '키워드를 입력하세요.');
    expect(draft.addKeyword('CLAUDE'), '이미 있는 키워드입니다.');
    expect(draft.addKeyword('a' * 51), '키워드는 50자 이하여야 합니다.');
    expect(draft.addKeyword(' anthropics/* '), isNull);
    expect(draft.watchKeywords, ['claude', 'uv', 'anthropics/*']);
    expect(draft.addKeyword('mcp'), '키워드는 최대 3개입니다.');

    draft.removeKeyword('uv');
    expect(draft.watchKeywords, ['claude', 'anthropics/*']);
  });

  test('가중치는 소수 2자리로 맞추고 편집하지 않는 kind 는 그대로 보낸다', () {
    final draft = _draft()..setWeight(Kind.promo, -0.1 - 0.2);
    final weights = draft.toSettings().kindWeights;
    expect(weights['promo'], -0.3);
    expect(weights['news'], 0.1);
    expect(weights['other'], 0);
    expect(draft.weightOf(Kind.technique), 0);
  });
}
