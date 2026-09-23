// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'meta.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

Meta _$MetaFromJson(Map<String, dynamic> json) => Meta(
  serverTime: DateTime.parse(json['server_time'] as String),
  timezone: json['timezone'] as String,
  taxonomy: (json['taxonomy'] as List<dynamic>)
      .map((e) => TaxonomyEntry.fromJson(e as Map<String, dynamic>))
      .toList(),
  kinds: (json['kinds'] as List<dynamic>)
      .map((e) => $enumDecode(_$KindEnumMap, e, unknownValue: Kind.unknown))
      .toList(),
  limits: MetaLimits.fromJson(json['limits'] as Map<String, dynamic>),
  resurfaceUnreadAfterDays: (json['resurface_unread_after_days'] as num)
      .toInt(),
);

Map<String, dynamic> _$MetaToJson(Meta instance) => <String, dynamic>{
  'server_time': instance.serverTime.toIso8601String(),
  'timezone': instance.timezone,
  'taxonomy': instance.taxonomy.map((e) => e.toJson()).toList(),
  'kinds': instance.kinds.map((e) => _$KindEnumMap[e]!).toList(),
  'limits': instance.limits.toJson(),
  'resurface_unread_after_days': instance.resurfaceUnreadAfterDays,
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

TaxonomyEntry _$TaxonomyEntryFromJson(Map<String, dynamic> json) =>
    TaxonomyEntry(slug: json['slug'] as String, label: json['label'] as String);

Map<String, dynamic> _$TaxonomyEntryToJson(TaxonomyEntry instance) =>
    <String, dynamic>{'slug': instance.slug, 'label': instance.label};

MetaLimits _$MetaLimitsFromJson(Map<String, dynamic> json) => MetaLimits(
  kindWeight: StepRange.fromJson(json['kind_weight'] as Map<String, dynamic>),
  dailyPushCap: IntRange.fromJson(
    json['daily_push_cap'] as Map<String, dynamic>,
  ),
  watchKeywordsMax: (json['watch_keywords_max'] as num).toInt(),
  folderNameMax: (json['folder_name_max'] as num).toInt(),
  memoMax: (json['memo_max'] as num).toInt(),
);

Map<String, dynamic> _$MetaLimitsToJson(MetaLimits instance) =>
    <String, dynamic>{
      'kind_weight': instance.kindWeight.toJson(),
      'daily_push_cap': instance.dailyPushCap.toJson(),
      'watch_keywords_max': instance.watchKeywordsMax,
      'folder_name_max': instance.folderNameMax,
      'memo_max': instance.memoMax,
    };

StepRange _$StepRangeFromJson(Map<String, dynamic> json) => StepRange(
  min: (json['min'] as num).toDouble(),
  max: (json['max'] as num).toDouble(),
  step: (json['step'] as num).toDouble(),
);

Map<String, dynamic> _$StepRangeToJson(StepRange instance) => <String, dynamic>{
  'min': instance.min,
  'max': instance.max,
  'step': instance.step,
};

IntRange _$IntRangeFromJson(Map<String, dynamic> json) => IntRange(
  min: (json['min'] as num).toInt(),
  max: (json['max'] as num).toInt(),
);

Map<String, dynamic> _$IntRangeToJson(IntRange instance) => <String, dynamic>{
  'min': instance.min,
  'max': instance.max,
};

TodayStats _$TodayStatsFromJson(Map<String, dynamic> json) => TodayStats(
  date: json['date'] as String,
  timezone: json['timezone'] as String,
  pushSentToday: (json['push_sent_today'] as num).toInt(),
  dailyPushCap: (json['daily_push_cap'] as num).toInt(),
  windowHours: (json['window_hours'] as num).toInt(),
  collectedCount: (json['collected_count'] as num).toInt(),
  filteredCount: (json['filtered_count'] as num).toInt(),
);

Map<String, dynamic> _$TodayStatsToJson(TodayStats instance) =>
    <String, dynamic>{
      'date': instance.date,
      'timezone': instance.timezone,
      'push_sent_today': instance.pushSentToday,
      'daily_push_cap': instance.dailyPushCap,
      'window_hours': instance.windowHours,
      'collected_count': instance.collectedCount,
      'filtered_count': instance.filteredCount,
    };

DeviceRegistration _$DeviceRegistrationFromJson(Map<String, dynamic> json) =>
    DeviceRegistration(
      id: json['id'] as String,
      platform: $enumDecode(
        _$DevicePlatformEnumMap,
        json['platform'],
        unknownValue: DevicePlatform.unknown,
      ),
      registeredAt: DateTime.parse(json['registered_at'] as String),
    );

Map<String, dynamic> _$DeviceRegistrationToJson(DeviceRegistration instance) =>
    <String, dynamic>{
      'id': instance.id,
      'platform': _$DevicePlatformEnumMap[instance.platform]!,
      'registered_at': instance.registeredAt.toIso8601String(),
    };

const _$DevicePlatformEnumMap = {
  DevicePlatform.android: 'android',
  DevicePlatform.ios: 'ios',
  DevicePlatform.unknown: 'unknown',
};
