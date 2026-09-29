// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'source.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Source _$SourceFromJson(Map<String, dynamic> json) => Source(
  id: json['id'] as String,
  displayName: json['display_name'] as String,
  type: $enumDecode(
    _$SourceTypeEnumMap,
    json['type'],
    unknownValue: SourceType.unknown,
  ),
  group: $enumDecode(
    _$SourceGroupEnumMap,
    json['group'],
    unknownValue: SourceGroup.unknown,
  ),
  enabled: json['enabled'] as bool,
  pollIntervalMin: (json['poll_interval_min'] as num).toInt(),
  trust: (json['trust'] as num).toDouble(),
  trustBase: (json['trust_base'] as num).toDouble(),
  trustCalibrated: (json['trust_calibrated'] as num?)?.toDouble(),
  consecutiveFailures: (json['consecutive_failures'] as num).toInt(),
  errorHint: json['error_hint'] as String?,
  lastError: json['last_error'] as String?,
  lastPolledAt: json['last_polled_at'] == null
      ? null
      : DateTime.parse(json['last_polled_at'] as String),
  repoCount: (json['repo_count'] as num?)?.toInt(),
);

Map<String, dynamic> _$SourceToJson(Source instance) => <String, dynamic>{
  'id': instance.id,
  'display_name': instance.displayName,
  'type': _$SourceTypeEnumMap[instance.type]!,
  'group': _$SourceGroupEnumMap[instance.group]!,
  'enabled': instance.enabled,
  'poll_interval_min': instance.pollIntervalMin,
  'trust': instance.trust,
  'trust_base': instance.trustBase,
  'trust_calibrated': instance.trustCalibrated,
  'consecutive_failures': instance.consecutiveFailures,
  'error_hint': instance.errorHint,
  'last_error': instance.lastError,
  'last_polled_at': instance.lastPolledAt?.toIso8601String(),
  'repo_count': instance.repoCount,
};

const _$SourceTypeEnumMap = {
  SourceType.rss: 'rss',
  SourceType.githubRelease: 'github_release',
  SourceType.youtube: 'youtube',
  SourceType.hackernews: 'hackernews',
  SourceType.hfPapers: 'hf_papers',
  SourceType.unknown: 'unknown',
};

const _$SourceGroupEnumMap = {
  SourceGroup.blogRss: 'blog_rss',
  SourceGroup.paperReleaseVideo: 'paper_release_video',
  SourceGroup.community: 'community',
  SourceGroup.unknown: 'unknown',
};

SourcesResponse _$SourcesResponseFromJson(Map<String, dynamic> json) =>
    SourcesResponse(
      stats: SourceStats.fromJson(json['stats'] as Map<String, dynamic>),
      sources:
          (json['sources'] as List<dynamic>?)
              ?.map((e) => Source.fromJson(e as Map<String, dynamic>))
              .toList() ??
          [],
      plannedSources:
          (json['planned_sources'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
    );

Map<String, dynamic> _$SourcesResponseToJson(SourcesResponse instance) =>
    <String, dynamic>{
      'stats': instance.stats.toJson(),
      'sources': instance.sources.map((e) => e.toJson()).toList(),
      'planned_sources': instance.plannedSources,
    };

SourceStats _$SourceStatsFromJson(Map<String, dynamic> json) => SourceStats(
  enabledCount: (json['enabled_count'] as num).toInt(),
  total: (json['total'] as num).toInt(),
  windowHours: (json['window_hours'] as num).toInt(),
  itemsCollected: (json['items_collected'] as num).toInt(),
  llmBudget: LlmBudget.fromJson(json['llm_budget'] as Map<String, dynamic>),
);

Map<String, dynamic> _$SourceStatsToJson(SourceStats instance) =>
    <String, dynamic>{
      'enabled_count': instance.enabledCount,
      'total': instance.total,
      'window_hours': instance.windowHours,
      'items_collected': instance.itemsCollected,
      'llm_budget': instance.llmBudget.toJson(),
    };

LlmBudget _$LlmBudgetFromJson(Map<String, dynamic> json) => LlmBudget(
  triage: BudgetUsage.fromJson(json['triage'] as Map<String, dynamic>),
  judge: BudgetUsage.fromJson(json['judge'] as Map<String, dynamic>),
  explore: BudgetUsage.fromJson(json['explore'] as Map<String, dynamic>),
);

Map<String, dynamic> _$LlmBudgetToJson(LlmBudget instance) => <String, dynamic>{
  'triage': instance.triage.toJson(),
  'judge': instance.judge.toJson(),
  'explore': instance.explore.toJson(),
};

BudgetUsage _$BudgetUsageFromJson(Map<String, dynamic> json) => BudgetUsage(
  used: (json['used'] as num).toInt(),
  cap: (json['cap'] as num).toInt(),
);

Map<String, dynamic> _$BudgetUsageToJson(BudgetUsage instance) =>
    <String, dynamic>{'used': instance.used, 'cap': instance.cap};
