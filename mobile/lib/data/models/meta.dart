// 마스터 데이터·요약 모델 — GET /meta, 03 요약 줄 GET /stats/today, 기기 등록 응답 (계약 4.0·4.1·4.9).
import 'package:json_annotation/json_annotation.dart';

import '../../core/labels.dart';

part 'meta.g.dart';

/// 앱 기동 시 한 번 읽고 캐시한다.
@JsonSerializable()
class Meta {
  const Meta({
    required this.serverTime,
    required this.timezone,
    required this.taxonomy,
    required this.kinds,
    required this.limits,
    required this.resurfaceUnreadAfterDays,
  });

  final DateTime serverTime;
  final String timezone;

  /// `rules.policy.taxonomy` 순서. 라벨은 서버가 준다.
  final List<TaxonomyEntry> taxonomy;
  @JsonKey(unknownEnumValue: Kind.unknown)
  final List<Kind> kinds;
  final MetaLimits limits;
  final int resurfaceUnreadAfterDays;

  factory Meta.fromJson(Map<String, dynamic> json) => _$MetaFromJson(json);

  Map<String, dynamic> toJson() => _$MetaToJson(this);
}

@JsonSerializable()
class TaxonomyEntry {
  const TaxonomyEntry({required this.slug, required this.label});

  final String slug;
  final String label;

  factory TaxonomyEntry.fromJson(Map<String, dynamic> json) =>
      _$TaxonomyEntryFromJson(json);

  Map<String, dynamic> toJson() => _$TaxonomyEntryToJson(this);
}

@JsonSerializable()
class MetaLimits {
  const MetaLimits({
    required this.kindWeight,
    required this.dailyPushCap,
    required this.watchKeywordsMax,
    required this.folderNameMax,
    required this.memoMax,
  });

  final StepRange kindWeight;
  final IntRange dailyPushCap;
  final int watchKeywordsMax;
  final int folderNameMax;
  final int memoMax;

  factory MetaLimits.fromJson(Map<String, dynamic> json) =>
      _$MetaLimitsFromJson(json);

  Map<String, dynamic> toJson() => _$MetaLimitsToJson(this);
}

@JsonSerializable()
class StepRange {
  const StepRange({required this.min, required this.max, required this.step});

  final double min;
  final double max;
  final double step;

  factory StepRange.fromJson(Map<String, dynamic> json) =>
      _$StepRangeFromJson(json);

  Map<String, dynamic> toJson() => _$StepRangeToJson(this);
}

@JsonSerializable()
class IntRange {
  const IntRange({required this.min, required this.max});

  final int min;
  final int max;

  factory IntRange.fromJson(Map<String, dynamic> json) =>
      _$IntRangeFromJson(json);

  Map<String, dynamic> toJson() => _$IntRangeToJson(this);
}

/// `GET /stats/today` — 03 요약 줄.
@JsonSerializable()
class TodayStats {
  const TodayStats({
    required this.date,
    required this.timezone,
    required this.pushSentToday,
    required this.dailyPushCap,
    required this.windowHours,
    required this.collectedCount,
    required this.filteredCount,
  });

  /// `YYYY-MM-DD` (Asia/Seoul 달력일).
  final String date;
  final String timezone;
  final int pushSentToday;
  final int dailyPushCap;

  /// 수집·걸러짐 건수의 롤링 창.
  final int windowHours;
  final int collectedCount;
  final int filteredCount;

  factory TodayStats.fromJson(Map<String, dynamic> json) =>
      _$TodayStatsFromJson(json);

  Map<String, dynamic> toJson() => _$TodayStatsToJson(this);
}

/// `POST /devices` 응답.
@JsonSerializable()
class DeviceRegistration {
  const DeviceRegistration({
    required this.id,
    required this.platform,
    required this.registeredAt,
  });

  final String id;
  @JsonKey(unknownEnumValue: DevicePlatform.unknown)
  final DevicePlatform platform;
  final DateTime registeredAt;

  factory DeviceRegistration.fromJson(Map<String, dynamic> json) =>
      _$DeviceRegistrationFromJson(json);

  Map<String, dynamic> toJson() => _$DeviceRegistrationToJson(this);
}
