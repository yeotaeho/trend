// 04 관심사 편집 상태 — GET 값 위의 로컬 변경을 들고 있다가 저장 때 PUT 본문 하나로 만든다.
import 'package:flutter/foundation.dart';

import '../../core/labels.dart';
import '../../data/models/models.dart';

/// 04 가 보여 주는 kind 가중치 6행 (디자인 순서). `news`·`other` 는 편집하지 않고 GET 값을 그대로 보낸다.
const List<Kind> editableKinds = [
  Kind.releaseMajor,
  Kind.releasePatch,
  Kind.technique,
  Kind.survey,
  Kind.tutorial,
  Kind.promo,
];

/// 가중치를 소수 2자리로 맞춘다 (서버도 저장 때 반올림한다).
double roundWeight(double value) => (value * 100).round() / 100;

class InterestsDraft {
  InterestsDraft(this.original, {required this.taxonomy, this.keywordsMax = 50})
    : selfDescription = original.profile.selfDescription,
      notInterested = original.profile.notInterested,
      _categories = {...original.selectedCategories},
      watchKeywords = [...original.watchKeywords],
      kindWeights = {...original.kindWeights};

  /// 마지막으로 읽거나 저장한 서버 값.
  final InterestsSettings original;

  /// `GET /meta` 의 taxonomy slug 순서. 선택 목록을 이 순서로 보낸다.
  final List<String> taxonomy;
  final int keywordsMax;

  static const int keywordMaxLength = 50;

  String selfDescription;
  String notInterested;
  final Set<String> _categories;
  final List<String> watchKeywords;

  /// 8개 kind 전부. 앱은 [editableKinds] 만 바꾼다.
  final Map<String, double> kindWeights;

  /// taxonomy 순서로 정렬한 선택 slug. taxonomy 에 없는 값은 뒤에 원래 순서로 둔다.
  List<String> get selectedCategories => [
    for (final slug in taxonomy)
      if (_categories.contains(slug)) slug,
    for (final slug in original.selectedCategories)
      if (_categories.contains(slug) && !taxonomy.contains(slug)) slug,
  ];

  bool isSelected(String slug) => _categories.contains(slug);

  void toggleCategory(String slug) {
    if (!_categories.remove(slug)) _categories.add(slug);
  }

  /// 앞뒤 공백을 떼고 추가한다. 추가하지 못하면 이유 문장을 돌려준다 (계약 4.3 검증과 같은 규칙).
  String? addKeyword(String input) {
    final keyword = input.trim();
    if (keyword.isEmpty) return '키워드를 입력하세요.';
    if (keyword.length > keywordMaxLength) {
      return '키워드는 $keywordMaxLength자 이하여야 합니다.';
    }
    final lower = keyword.toLowerCase();
    if (watchKeywords.any((k) => k.toLowerCase() == lower)) {
      return '이미 있는 키워드입니다.';
    }
    if (watchKeywords.length >= keywordsMax) {
      return '키워드는 최대 $keywordsMax개입니다.';
    }
    watchKeywords.add(keyword);
    return null;
  }

  void removeKeyword(String keyword) => watchKeywords.remove(keyword);

  double weightOf(Kind kind) => kindWeights[kind.value] ?? 0;

  void setWeight(Kind kind, double value) =>
      kindWeights[kind.value] = roundWeight(value);

  bool get isDirty {
    final base = original;
    return selfDescription != base.profile.selfDescription ||
        notInterested != base.profile.notInterested ||
        _categories.length != base.selectedCategories.length ||
        !_categories.containsAll(base.selectedCategories) ||
        !listEquals(watchKeywords, base.watchKeywords) ||
        kindWeights.entries.any(
          (e) =>
              roundWeight(e.value) != roundWeight(base.kindWeights[e.key] ?? 0),
        );
  }

  /// 헤더 `저장` 활성 조건 — 바꾼 것이 있고 카테고리가 1개 이상.
  bool get canSave => isDirty && _categories.isNotEmpty;

  /// `PUT /settings/interests` 본문.
  InterestsSettings toSettings() => InterestsSettings(
    profile: InterestsProfile(
      selfDescription: selfDescription,
      notInterested: notInterested,
    ),
    selectedCategories: selectedCategories,
    watchKeywords: [...watchKeywords],
    kindWeights: {...kindWeights},
  );
}
