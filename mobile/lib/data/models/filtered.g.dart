// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'filtered.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

DroppedItem _$DroppedItemFromJson(Map<String, dynamic> json) => DroppedItem(
  id: json['id'] as String,
  title: json['title'] as String,
  url: json['url'] as String,
  sourceId: json['source_id'] as String,
  sourceName: json['source_name'] as String,
  sourceType: $enumDecode(
    _$SourceTypeEnumMap,
    json['source_type'],
    unknownValue: SourceType.unknown,
  ),
  droppedGate: $enumDecode(
    _$GateEnumMap,
    json['dropped_gate'],
    unknownValue: Gate.unknown,
  ),
  droppedAt: DateTime.parse(json['dropped_at'] as String),
  relevance: (json['relevance'] as num?)?.toDouble(),
  kind: $enumDecodeNullable(
    _$KindEnumMap,
    json['kind'],
    unknownValue: Kind.unknown,
  ),
  topics:
      (json['topics'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      [],
  reason: json['reason'] as String?,
  score: json['score'] == null
      ? null
      : ScoreBreakdown.fromJson(json['score'] as Map<String, dynamic>),
  matchedKeywords:
      (json['matched_keywords'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      [],
  explorationCandidate: json['exploration_candidate'] as bool,
  restored: json['restored'] as bool,
);

Map<String, dynamic> _$DroppedItemToJson(DroppedItem instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'url': instance.url,
      'source_id': instance.sourceId,
      'source_name': instance.sourceName,
      'source_type': _$SourceTypeEnumMap[instance.sourceType]!,
      'dropped_gate': _$GateEnumMap[instance.droppedGate]!,
      'dropped_at': instance.droppedAt.toIso8601String(),
      'relevance': instance.relevance,
      'kind': _$KindEnumMap[instance.kind],
      'topics': instance.topics,
      'reason': instance.reason,
      'score': instance.score?.toJson(),
      'matched_keywords': instance.matchedKeywords,
      'exploration_candidate': instance.explorationCandidate,
      'restored': instance.restored,
    };

const _$SourceTypeEnumMap = {
  SourceType.rss: 'rss',
  SourceType.githubRelease: 'github_release',
  SourceType.youtube: 'youtube',
  SourceType.hackernews: 'hackernews',
  SourceType.hfPapers: 'hf_papers',
  SourceType.unknown: 'unknown',
};

const _$GateEnumMap = {
  Gate.exclude: 'exclude',
  Gate.dedup: 'dedup',
  Gate.screening: 'screening',
  Gate.score: 'score',
  Gate.judgment: 'judgment',
  Gate.stale: 'stale',
  Gate.clusterDup: 'cluster_dup',
  Gate.unknown: 'unknown',
};

const _$KindEnumMap = {
  Kind.releaseMajor: 'release_major',
  Kind.releasePatch: 'release_patch',
  Kind.technique: 'technique',
  Kind.survey: 'survey',
  Kind.news: 'news',
  Kind.tutorial: 'tutorial',
  Kind.promo: 'promo',
  Kind.other: 'other',
  Kind.unknown: 'unknown',
};

FilteredSummary _$FilteredSummaryFromJson(Map<String, dynamic> json) =>
    FilteredSummary(
      windowHours: (json['window_hours'] as num).toInt(),
      filteredTotal: (json['filtered_total'] as num).toInt(),
      collectedTotal: (json['collected_total'] as num).toInt(),
      gateCounts: const GateCountsConverter().fromJson(
        json['gate_counts'] as Map<String, dynamic>,
      ),
      borderline: Borderline.fromJson(
        json['borderline'] as Map<String, dynamic>,
      ),
      unclassifiedCount: (json['unclassified_count'] as num).toInt(),
    );

Map<String, dynamic> _$FilteredSummaryToJson(FilteredSummary instance) =>
    <String, dynamic>{
      'window_hours': instance.windowHours,
      'filtered_total': instance.filteredTotal,
      'collected_total': instance.collectedTotal,
      'gate_counts': const GateCountsConverter().toJson(instance.gateCounts),
      'borderline': instance.borderline.toJson(),
      'unclassified_count': instance.unclassifiedCount,
    };

Borderline _$BorderlineFromJson(Map<String, dynamic> json) => Borderline(
  count: (json['count'] as num).toInt(),
  range: (json['range'] as List<dynamic>)
      .map((e) => (e as num).toDouble())
      .toList(),
);

Map<String, dynamic> _$BorderlineToJson(Borderline instance) =>
    <String, dynamic>{'count': instance.count, 'range': instance.range};

FilteredGroups _$FilteredGroupsFromJson(Map<String, dynamic> json) =>
    FilteredGroups(
      view: $enumDecode(_$FilteredViewEnumMap, json['view']),
      groups:
          (json['groups'] as List<dynamic>?)
              ?.map((e) => FilteredGroup.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );

Map<String, dynamic> _$FilteredGroupsToJson(FilteredGroups instance) =>
    <String, dynamic>{
      'view': _$FilteredViewEnumMap[instance.view]!,
      'groups': instance.groups.map((e) => e.toJson()).toList(),
    };

const _$FilteredViewEnumMap = {
  FilteredView.source: 'source',
  FilteredView.kind: 'kind',
  FilteredView.gate: 'gate',
};

FilteredGroup _$FilteredGroupFromJson(Map<String, dynamic> json) =>
    FilteredGroup(
      key: json['key'] as String,
      count: (json['count'] as num).toInt(),
      gateCounts: const GateCountsConverter().fromJson(
        json['gate_counts'] as Map<String, dynamic>,
      ),
      source: json['source'] == null
          ? null
          : GroupSource.fromJson(json['source'] as Map<String, dynamic>),
      kind: $enumDecodeNullable(
        _$KindEnumMap,
        json['kind'],
        unknownValue: Kind.unknown,
      ),
      gate: $enumDecodeNullable(
        _$GateEnumMap,
        json['gate'],
        unknownValue: Gate.unknown,
      ),
      lowRelevanceRatio: (json['low_relevance_ratio'] as num?)?.toDouble(),
      kindWeight: (json['kind_weight'] as num?)?.toDouble(),
      kindFeedback: json['kind_feedback'] == null
          ? null
          : KindFeedback.fromJson(
              json['kind_feedback'] as Map<String, dynamic>,
            ),
      penaltyActive: json['penalty_active'] as bool,
      borderlineCount: (json['borderline_count'] as num).toInt(),
      excludeKeywordHits: (json['exclude_keyword_hits'] as num).toInt(),
      preview:
          (json['preview'] as List<dynamic>?)
              ?.map((e) => DroppedItem.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
    );

Map<String, dynamic> _$FilteredGroupToJson(FilteredGroup instance) =>
    <String, dynamic>{
      'key': instance.key,
      'count': instance.count,
      'gate_counts': const GateCountsConverter().toJson(instance.gateCounts),
      'source': instance.source?.toJson(),
      'kind': _$KindEnumMap[instance.kind],
      'gate': _$GateEnumMap[instance.gate],
      'low_relevance_ratio': instance.lowRelevanceRatio,
      'kind_weight': instance.kindWeight,
      'kind_feedback': instance.kindFeedback?.toJson(),
      'penalty_active': instance.penaltyActive,
      'borderline_count': instance.borderlineCount,
      'exclude_keyword_hits': instance.excludeKeywordHits,
      'preview': instance.preview.map((e) => e.toJson()).toList(),
    };

GroupSource _$GroupSourceFromJson(Map<String, dynamic> json) => GroupSource(
  id: json['id'] as String,
  displayName: json['display_name'] as String,
  type: $enumDecode(
    _$SourceTypeEnumMap,
    json['type'],
    unknownValue: SourceType.unknown,
  ),
);

Map<String, dynamic> _$GroupSourceToJson(GroupSource instance) =>
    <String, dynamic>{
      'id': instance.id,
      'display_name': instance.displayName,
      'type': _$SourceTypeEnumMap[instance.type]!,
    };

KindFeedback _$KindFeedbackFromJson(Map<String, dynamic> json) => KindFeedback(
  notUseful: (json['not_useful'] as num).toInt(),
  total: (json['total'] as num).toInt(),
);

Map<String, dynamic> _$KindFeedbackToJson(KindFeedback instance) =>
    <String, dynamic>{
      'not_useful': instance.notUseful,
      'total': instance.total,
    };

RestoreResult _$RestoreResultFromJson(Map<String, dynamic> json) =>
    RestoreResult(
      itemId: json['item_id'] as String,
      restored: json['restored'] as bool,
      alert: Alert.fromJson(json['alert'] as Map<String, dynamic>),
    );

Map<String, dynamic> _$RestoreResultToJson(RestoreResult instance) =>
    <String, dynamic>{
      'item_id': instance.itemId,
      'restored': instance.restored,
      'alert': instance.alert.toJson(),
    };
