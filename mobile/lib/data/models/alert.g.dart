// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'alert.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Alert _$AlertFromJson(Map<String, dynamic> json) => Alert(
  id: json['id'] as String,
  sourceId: json['source_id'] as String,
  sourceName: json['source_name'] as String,
  sourceType: $enumDecode(
    _$SourceTypeEnumMap,
    json['source_type'],
    unknownValue: SourceType.unknown,
  ),
  deliveredAt: json['delivered_at'] == null
      ? null
      : DateTime.parse(json['delivered_at'] as String),
  deliveryMode: $enumDecodeNullable(
    _$DeliveryModeEnumMap,
    json['delivery_mode'],
    unknownValue: DeliveryMode.unknown,
  ),
  isExploration: json['is_exploration'] as bool,
  title: json['title'] as String,
  summary: json['summary'] as String? ?? '',
  categories:
      (json['categories'] as List<dynamic>?)
          ?.map((e) => e as String)
          .toList() ??
      [],
  tags:
      (json['tags'] as List<dynamic>?)?.map((e) => e as String).toList() ?? [],
  url: json['url'] as String,
  importance: (json['importance'] as num?)?.toInt(),
  isSaved: json['is_saved'] as bool,
  feedback: $enumDecodeNullable(
    _$FeedbackVerdictEnumMap,
    json['feedback'],
    unknownValue: FeedbackVerdict.unknown,
  ),
);

Map<String, dynamic> _$AlertToJson(Alert instance) => <String, dynamic>{
  'id': instance.id,
  'source_id': instance.sourceId,
  'source_name': instance.sourceName,
  'source_type': _$SourceTypeEnumMap[instance.sourceType]!,
  'delivered_at': instance.deliveredAt?.toIso8601String(),
  'delivery_mode': _$DeliveryModeEnumMap[instance.deliveryMode],
  'is_exploration': instance.isExploration,
  'title': instance.title,
  'summary': instance.summary,
  'categories': instance.categories,
  'tags': instance.tags,
  'url': instance.url,
  'importance': instance.importance,
  'is_saved': instance.isSaved,
  'feedback': _$FeedbackVerdictEnumMap[instance.feedback],
};

const _$SourceTypeEnumMap = {
  SourceType.rss: 'rss',
  SourceType.githubRelease: 'github_release',
  SourceType.youtube: 'youtube',
  SourceType.hackernews: 'hackernews',
  SourceType.hfPapers: 'hf_papers',
  SourceType.unknown: 'unknown',
};

const _$DeliveryModeEnumMap = {
  DeliveryMode.instant: 'instant',
  DeliveryMode.quiet: 'quiet',
  DeliveryMode.feedOnly: 'feed_only',
  DeliveryMode.experiment: 'experiment',
  DeliveryMode.unknown: 'unknown',
};

const _$FeedbackVerdictEnumMap = {
  FeedbackVerdict.useful: 'useful',
  FeedbackVerdict.notUseful: 'not_useful',
  FeedbackVerdict.unknown: 'unknown',
};

Rationale _$RationaleFromJson(Map<String, dynamic> json) => Rationale(
  score: json['score'] == null
      ? null
      : ScoreBreakdown.fromJson(json['score'] as Map<String, dynamic>),
  routing: $enumDecode(
    _$RoutingEnumMap,
    json['routing'],
    unknownValue: Routing.unknown,
  ),
  screening: json['screening'] == null
      ? null
      : Screening.fromJson(json['screening'] as Map<String, dynamic>),
  judgment: json['judgment'] == null
      ? null
      : Judgment.fromJson(json['judgment'] as Map<String, dynamic>),
  trustNoteSource: json['trust_note_source'] as String,
);

Map<String, dynamic> _$RationaleToJson(Rationale instance) => <String, dynamic>{
  'score': instance.score?.toJson(),
  'routing': _$RoutingEnumMap[instance.routing]!,
  'screening': instance.screening?.toJson(),
  'judgment': instance.judgment?.toJson(),
  'trust_note_source': instance.trustNoteSource,
};

const _$RoutingEnumMap = {
  Routing.passed: 'passed',
  Routing.exploreSlot: 'explore_slot',
  Routing.restored: 'restored',
  Routing.dropped: 'dropped',
  Routing.clusterDup: 'cluster_dup',
  Routing.unknown: 'unknown',
};

Screening _$ScreeningFromJson(Map<String, dynamic> json) => Screening(
  relevance: (json['relevance'] as num).toDouble(),
  kind: $enumDecodeNullable(
    _$KindEnumMap,
    json['kind'],
    unknownValue: Kind.unknown,
  ),
  topics:
      (json['topics'] as List<dynamic>?)?.map((e) => e as String).toList() ??
      [],
  reason: json['reason'] as String?,
);

Map<String, dynamic> _$ScreeningToJson(Screening instance) => <String, dynamic>{
  'relevance': instance.relevance,
  'kind': _$KindEnumMap[instance.kind],
  'topics': instance.topics,
  'reason': instance.reason,
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

Judgment _$JudgmentFromJson(Map<String, dynamic> json) => Judgment(
  importance: (json['importance'] as num?)?.toInt(),
  worthNotifying: json['worth_notifying'] as bool,
  similarFeedback:
      (json['similar_feedback'] as List<dynamic>?)
          ?.map((e) => SimilarFeedback.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [],
);

Map<String, dynamic> _$JudgmentToJson(Judgment instance) => <String, dynamic>{
  'importance': instance.importance,
  'worth_notifying': instance.worthNotifying,
  'similar_feedback': instance.similarFeedback.map((e) => e.toJson()).toList(),
};

SimilarFeedback _$SimilarFeedbackFromJson(Map<String, dynamic> json) =>
    SimilarFeedback(
      alertId: json['alert_id'] as String,
      feedback: $enumDecode(
        _$FeedbackVerdictEnumMap,
        json['feedback'],
        unknownValue: FeedbackVerdict.unknown,
      ),
      title: json['title'] as String,
    );

Map<String, dynamic> _$SimilarFeedbackToJson(SimilarFeedback instance) =>
    <String, dynamic>{
      'alert_id': instance.alertId,
      'feedback': _$FeedbackVerdictEnumMap[instance.feedback]!,
      'title': instance.title,
    };

FeedbackResult _$FeedbackResultFromJson(Map<String, dynamic> json) =>
    FeedbackResult(
      alertId: json['alert_id'] as String,
      feedback: $enumDecode(
        _$FeedbackVerdictEnumMap,
        json['feedback'],
        unknownValue: FeedbackVerdict.unknown,
      ),
      updatedAt: DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$FeedbackResultToJson(FeedbackResult instance) =>
    <String, dynamic>{
      'alert_id': instance.alertId,
      'feedback': _$FeedbackVerdictEnumMap[instance.feedback]!,
      'updated_at': instance.updatedAt.toIso8601String(),
    };

RecentFeedback _$RecentFeedbackFromJson(Map<String, dynamic> json) =>
    RecentFeedback(
      todayCount: (json['today_count'] as num).toInt(),
      items:
          (json['items'] as List<dynamic>?)
              ?.map(
                (e) => RecentFeedbackItem.fromJson(e as Map<String, dynamic>),
              )
              .toList() ??
          [],
    );

Map<String, dynamic> _$RecentFeedbackToJson(RecentFeedback instance) =>
    <String, dynamic>{
      'today_count': instance.todayCount,
      'items': instance.items.map((e) => e.toJson()).toList(),
    };

RecentFeedbackItem _$RecentFeedbackItemFromJson(Map<String, dynamic> json) =>
    RecentFeedbackItem(
      alertId: json['alert_id'] as String,
      feedback: $enumDecode(
        _$FeedbackVerdictEnumMap,
        json['feedback'],
        unknownValue: FeedbackVerdict.unknown,
      ),
      title: json['title'] as String,
      createdAt: DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$RecentFeedbackItemToJson(RecentFeedbackItem instance) =>
    <String, dynamic>{
      'alert_id': instance.alertId,
      'feedback': _$FeedbackVerdictEnumMap[instance.feedback]!,
      'title': instance.title,
      'created_at': instance.createdAt.toIso8601String(),
    };
