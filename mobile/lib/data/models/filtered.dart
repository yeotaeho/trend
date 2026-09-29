// 걸러진 항목 모델 — DroppedItem, 요약 카드, 그룹 목록, 복원 결과 (계약 3.2·4.6).
import 'package:json_annotation/json_annotation.dart';

import '../../core/labels.dart';
import 'alert.dart';
import 'score.dart';

part 'filtered.g.dart';

/// `gate_counts` ↔ `Map<Gate, int>`. 모르는 관문 키는 [Gate.unknown] 에 더해 합계를 지킨다.
class GateCountsConverter
    implements JsonConverter<Map<Gate, int>, Map<String, dynamic>> {
  const GateCountsConverter();

  @override
  Map<Gate, int> fromJson(Map<String, dynamic> json) {
    final counts = <Gate, int>{};
    for (final MapEntry(:key, :value) in json.entries) {
      final gate = Gate.values.firstWhere(
        (g) => g.value == key,
        orElse: () => Gate.unknown,
      );
      counts[gate] = (counts[gate] ?? 0) + (value as num).toInt();
    }
    return counts;
  }

  @override
  Map<String, dynamic> toJson(Map<Gate, int> counts) => {
    for (final MapEntry(:key, :value) in counts.entries) key.value: value,
  };
}

@JsonSerializable()
class DroppedItem {
  const DroppedItem({
    required this.id,
    required this.title,
    required this.url,
    required this.sourceId,
    required this.sourceName,
    required this.sourceType,
    required this.droppedGate,
    required this.droppedAt,
    this.relevance,
    this.kind,
    required this.topics,
    this.reason,
    this.score,
    required this.matchedKeywords,
    required this.explorationCandidate,
    required this.restored,
  });

  final String id;
  final String title;
  final String url;
  final String sourceId;
  final String sourceName;
  @JsonKey(unknownEnumValue: SourceType.unknown)
  final SourceType sourceType;
  @JsonKey(unknownEnumValue: Gate.unknown)
  final Gate droppedGate;
  final DateTime droppedAt;

  /// 선별 전에 떨어진 항목(`exclude`·`dedup`·`stale`)은 `relevance`·`kind`·`reason` 이 `null`.
  final double? relevance;
  @JsonKey(unknownEnumValue: Kind.unknown)
  final Kind? kind;
  @JsonKey(defaultValue: <String>[])
  final List<String> topics;
  final String? reason;

  /// 점수 전 탈락이면 `null`.
  final ScoreBreakdown? score;

  /// `exclude` 일 때 걸린 키워드.
  @JsonKey(defaultValue: <String>[])
  final List<String> matchedKeywords;
  final bool explorationCandidate;
  final bool restored;

  DroppedItem withRestored(bool value) => DroppedItem(
    id: id,
    title: title,
    url: url,
    sourceId: sourceId,
    sourceName: sourceName,
    sourceType: sourceType,
    droppedGate: droppedGate,
    droppedAt: droppedAt,
    relevance: relevance,
    kind: kind,
    topics: topics,
    reason: reason,
    score: score,
    matchedKeywords: matchedKeywords,
    explorationCandidate: explorationCandidate,
    restored: value,
  );

  factory DroppedItem.fromJson(Map<String, dynamic> json) =>
      _$DroppedItemFromJson(json);

  Map<String, dynamic> toJson() => _$DroppedItemToJson(this);
}

/// `GET /filtered/summary` — 09·10 요약 카드.
@JsonSerializable()
class FilteredSummary {
  const FilteredSummary({
    required this.windowHours,
    required this.filteredTotal,
    required this.collectedTotal,
    required this.gateCounts,
    required this.borderline,
    required this.unclassifiedCount,
  });

  final int windowHours;
  final int filteredTotal;
  final int collectedTotal;
  @GateCountsConverter()
  final Map<Gate, int> gateCounts;
  final Borderline borderline;

  /// kind 가 없는 항목 수 (`exclude`+`dedup`+`stale`).
  final int unclassifiedCount;

  factory FilteredSummary.fromJson(Map<String, dynamic> json) =>
      _$FilteredSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$FilteredSummaryToJson(this);
}

@JsonSerializable()
class Borderline {
  const Borderline({required this.count, required this.range});

  final int count;

  /// [통과선 − 0.10, 통과선].
  final List<double> range;

  factory Borderline.fromJson(Map<String, dynamic> json) =>
      _$BorderlineFromJson(json);

  Map<String, dynamic> toJson() => _$BorderlineToJson(this);
}

/// `GET /filtered/groups` 응답.
@JsonSerializable()
class FilteredGroups {
  const FilteredGroups({required this.view, required this.groups});

  final FilteredView view;
  @JsonKey(defaultValue: <FilteredGroup>[])
  final List<FilteredGroup> groups;

  factory FilteredGroups.fromJson(Map<String, dynamic> json) =>
      _$FilteredGroupsFromJson(json);

  Map<String, dynamic> toJson() => _$FilteredGroupsToJson(this);
}

@JsonSerializable()
class FilteredGroup {
  const FilteredGroup({
    required this.key,
    required this.count,
    required this.gateCounts,
    this.source,
    this.kind,
    this.gate,
    this.lowRelevanceRatio,
    this.kindWeight,
    this.kindFeedback,
    required this.penaltyActive,
    required this.borderlineCount,
    required this.excludeKeywordHits,
    required this.preview,
  });

  /// 소스별은 소스 ID, 종류별은 kind 값 또는 [unclassifiedKey], 관문별은 gate 값.
  final String key;
  final int count;
  @GateCountsConverter()
  final Map<Gate, int> gateCounts;
  final GroupSource? source;
  @JsonKey(unknownEnumValue: Kind.unknown)
  final Kind? kind;
  @JsonKey(unknownEnumValue: Gate.unknown)
  final Gate? gate;
  final double? lowRelevanceRatio;
  final double? kindWeight;
  final KindFeedback? kindFeedback;
  final bool penaltyActive;
  final int borderlineCount;
  final int excludeKeywordHits;

  /// 최신 3건. 나머지는 `GET /filtered/items` 로 더 불러온다.
  @JsonKey(defaultValue: <DroppedItem>[])
  final List<DroppedItem> preview;

  static const String unclassifiedKey = 'unclassified';

  FilteredGroup withPreview(List<DroppedItem> value) => FilteredGroup(
    key: key,
    count: count,
    gateCounts: gateCounts,
    source: source,
    kind: kind,
    gate: gate,
    lowRelevanceRatio: lowRelevanceRatio,
    kindWeight: kindWeight,
    kindFeedback: kindFeedback,
    penaltyActive: penaltyActive,
    borderlineCount: borderlineCount,
    excludeKeywordHits: excludeKeywordHits,
    preview: value,
  );

  factory FilteredGroup.fromJson(Map<String, dynamic> json) =>
      _$FilteredGroupFromJson(json);

  Map<String, dynamic> toJson() => _$FilteredGroupToJson(this);
}

@JsonSerializable()
class GroupSource {
  const GroupSource({
    required this.id,
    required this.displayName,
    required this.type,
  });

  final String id;
  final String displayName;
  @JsonKey(unknownEnumValue: SourceType.unknown)
  final SourceType type;

  factory GroupSource.fromJson(Map<String, dynamic> json) =>
      _$GroupSourceFromJson(json);

  Map<String, dynamic> toJson() => _$GroupSourceToJson(this);
}

/// 최근 30일, 그 kind 로 선별된 항목에 붙은 판정 수.
@JsonSerializable()
class KindFeedback {
  const KindFeedback({required this.notUseful, required this.total});

  final int notUseful;
  final int total;

  factory KindFeedback.fromJson(Map<String, dynamic> json) =>
      _$KindFeedbackFromJson(json);

  Map<String, dynamic> toJson() => _$KindFeedbackToJson(this);
}

/// `POST /filtered/items/{id}/restore` 응답.
@JsonSerializable()
class RestoreResult {
  const RestoreResult({
    required this.itemId,
    required this.restored,
    required this.alert,
  });

  final String itemId;
  final bool restored;

  /// 피드에 올라간 알림 (`delivery_mode = feed_only`, `feedback = useful`).
  final Alert alert;

  factory RestoreResult.fromJson(Map<String, dynamic> json) =>
      _$RestoreResultFromJson(json);

  Map<String, dynamic> toJson() => _$RestoreResultToJson(this);
}
