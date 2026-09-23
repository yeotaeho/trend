// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'profile.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Profile _$ProfileFromJson(Map<String, dynamic> json) => Profile(
  periodDays: (json['period_days'] as num).toInt(),
  user: ProfileUser.fromJson(json['user'] as Map<String, dynamic>),
  stats: ProfileStats.fromJson(json['stats'] as Map<String, dynamic>),
  categoryReactions:
      (json['category_reactions'] as List<dynamic>?)
          ?.map((e) => CategoryReaction.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [],
  learned: Learned.fromJson(json['learned'] as Map<String, dynamic>),
  weeklyReportLatest: json['weekly_report_latest'] == null
      ? null
      : ReportSummary.fromJson(
          json['weekly_report_latest'] as Map<String, dynamic>,
        ),
);

Map<String, dynamic> _$ProfileToJson(Profile instance) => <String, dynamic>{
  'period_days': instance.periodDays,
  'user': instance.user.toJson(),
  'stats': instance.stats.toJson(),
  'category_reactions': instance.categoryReactions
      .map((e) => e.toJson())
      .toList(),
  'learned': instance.learned.toJson(),
  'weekly_report_latest': instance.weeklyReportLatest?.toJson(),
};

ProfileUser _$ProfileUserFromJson(Map<String, dynamic> json) => ProfileUser(
  displayName: json['display_name'] as String,
  discordConnected: json['discord_connected'] as bool,
  onboardingDone: (json['onboarding_done'] as num).toInt(),
  onboardingTotal: (json['onboarding_total'] as num).toInt(),
);

Map<String, dynamic> _$ProfileUserToJson(ProfileUser instance) =>
    <String, dynamic>{
      'display_name': instance.displayName,
      'discord_connected': instance.discordConnected,
      'onboarding_done': instance.onboardingDone,
      'onboarding_total': instance.onboardingTotal,
    };

ProfileStats _$ProfileStatsFromJson(Map<String, dynamic> json) => ProfileStats(
  alertsReceived: (json['alerts_received'] as num).toInt(),
  pushCount: (json['push_count'] as num).toInt(),
  experimentCount: (json['experiment_count'] as num).toInt(),
  usefulCount: (json['useful_count'] as num).toInt(),
  notUsefulCount: (json['not_useful_count'] as num).toInt(),
  usefulRatio: (json['useful_ratio'] as num?)?.toInt(),
  missedIssues: (json['missed_issues'] as num).toInt(),
);

Map<String, dynamic> _$ProfileStatsToJson(ProfileStats instance) =>
    <String, dynamic>{
      'alerts_received': instance.alertsReceived,
      'push_count': instance.pushCount,
      'experiment_count': instance.experimentCount,
      'useful_count': instance.usefulCount,
      'not_useful_count': instance.notUsefulCount,
      'useful_ratio': instance.usefulRatio,
      'missed_issues': instance.missedIssues,
    };

CategoryReaction _$CategoryReactionFromJson(Map<String, dynamic> json) =>
    CategoryReaction(
      category: json['category'] as String,
      useful: (json['useful'] as num).toInt(),
      notUseful: (json['not_useful'] as num).toInt(),
      total: (json['total'] as num).toInt(),
    );

Map<String, dynamic> _$CategoryReactionToJson(CategoryReaction instance) =>
    <String, dynamic>{
      'category': instance.category,
      'useful': instance.useful,
      'not_useful': instance.notUseful,
      'total': instance.total,
    };

Learned _$LearnedFromJson(Map<String, dynamic> json) => Learned(
  kindPenalties:
      (json['kind_penalties'] as List<dynamic>?)
          ?.map((e) => KindPenalty.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [],
  sourceTrustChanges:
      (json['source_trust_changes'] as List<dynamic>?)
          ?.map((e) => SourceTrustChange.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [],
  profileVectorLabels: (json['profile_vector_labels'] as num).toInt(),
  personalModelThreshold: (json['personal_model_threshold'] as num).toInt(),
);

Map<String, dynamic> _$LearnedToJson(Learned instance) => <String, dynamic>{
  'kind_penalties': instance.kindPenalties.map((e) => e.toJson()).toList(),
  'source_trust_changes': instance.sourceTrustChanges
      .map((e) => e.toJson())
      .toList(),
  'profile_vector_labels': instance.profileVectorLabels,
  'personal_model_threshold': instance.personalModelThreshold,
};

KindPenalty _$KindPenaltyFromJson(Map<String, dynamic> json) => KindPenalty(
  kind: $enumDecode(_$KindEnumMap, json['kind'], unknownValue: Kind.unknown),
  weight: (json['weight'] as num).toDouble(),
  notUseful: (json['not_useful'] as num).toInt(),
  total: (json['total'] as num).toInt(),
  active: json['active'] as bool,
);

Map<String, dynamic> _$KindPenaltyToJson(KindPenalty instance) =>
    <String, dynamic>{
      'kind': _$KindEnumMap[instance.kind]!,
      'weight': instance.weight,
      'not_useful': instance.notUseful,
      'total': instance.total,
      'active': instance.active,
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

SourceTrustChange _$SourceTrustChangeFromJson(Map<String, dynamic> json) =>
    SourceTrustChange(
      sourceId: json['source_id'] as String,
      sourceName: json['source_name'] as String,
      from: (json['from'] as num).toDouble(),
      to: (json['to'] as num).toDouble(),
    );

Map<String, dynamic> _$SourceTrustChangeToJson(SourceTrustChange instance) =>
    <String, dynamic>{
      'source_id': instance.sourceId,
      'source_name': instance.sourceName,
      'from': instance.from,
      'to': instance.to,
    };

ReportSummary _$ReportSummaryFromJson(Map<String, dynamic> json) =>
    ReportSummary(
      id: json['id'] as String,
      title: json['title'] as String,
      subtitle: json['subtitle'] as String,
      periodStart: json['period_start'] as String,
      periodEnd: json['period_end'] as String,
      createdAt: json['created_at'] == null
          ? null
          : DateTime.parse(json['created_at'] as String),
    );

Map<String, dynamic> _$ReportSummaryToJson(ReportSummary instance) =>
    <String, dynamic>{
      'id': instance.id,
      'title': instance.title,
      'subtitle': instance.subtitle,
      'period_start': instance.periodStart,
      'period_end': instance.periodEnd,
      'created_at': instance.createdAt?.toIso8601String(),
    };

Report _$ReportFromJson(Map<String, dynamic> json) => Report(
  id: json['id'] as String,
  title: json['title'] as String,
  subtitle: json['subtitle'] as String,
  periodStart: json['period_start'] as String,
  periodEnd: json['period_end'] as String,
  createdAt: DateTime.parse(json['created_at'] as String),
  sections:
      (json['sections'] as List<dynamic>?)
          ?.map((e) => ReportSection.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [],
);

Map<String, dynamic> _$ReportToJson(Report instance) => <String, dynamic>{
  'id': instance.id,
  'title': instance.title,
  'subtitle': instance.subtitle,
  'period_start': instance.periodStart,
  'period_end': instance.periodEnd,
  'created_at': instance.createdAt.toIso8601String(),
  'sections': instance.sections.map((e) => e.toJson()).toList(),
};

ReportSection _$ReportSectionFromJson(
  Map<String, dynamic> json,
) => ReportSection(
  key: json['key'] as String,
  title: json['title'] as String,
  columns: (json['columns'] as List<dynamic>).map((e) => e as String).toList(),
  rows: (json['rows'] as List<dynamic>).map((e) => e as List<dynamic>).toList(),
);

Map<String, dynamic> _$ReportSectionToJson(ReportSection instance) =>
    <String, dynamic>{
      'key': instance.key,
      'title': instance.title,
      'columns': instance.columns,
      'rows': instance.rows,
    };
