// 프로필 모델 — 08 내 프로필(Profile)과 주간 리포트 목록·상세 (계약 4.8).
import 'package:json_annotation/json_annotation.dart';

import '../../core/labels.dart';

part 'profile.g.dart';

/// `GET /profile`.
@JsonSerializable()
class Profile {
  const Profile({
    required this.periodDays,
    required this.user,
    required this.stats,
    required this.categoryReactions,
    required this.learned,
    this.weeklyReportLatest,
  });

  /// 7 · 14 · 30.
  final int periodDays;
  final ProfileUser user;
  final ProfileStats stats;

  /// 합계 내림차순 상위 6.
  @JsonKey(defaultValue: <CategoryReaction>[])
  final List<CategoryReaction> categoryReactions;
  final Learned learned;

  /// 없으면 카드를 숨긴다.
  final ReportSummary? weeklyReportLatest;

  factory Profile.fromJson(Map<String, dynamic> json) =>
      _$ProfileFromJson(json);

  Map<String, dynamic> toJson() => _$ProfileToJson(this);
}

@JsonSerializable()
class ProfileUser {
  const ProfileUser({
    required this.displayName,
    required this.discordConnected,
    required this.onboardingDone,
    required this.onboardingTotal,
  });

  final String displayName;
  final bool discordConnected;

  /// **정적** 온보딩 진행도.
  final int onboardingDone;
  final int onboardingTotal;

  factory ProfileUser.fromJson(Map<String, dynamic> json) =>
      _$ProfileUserFromJson(json);

  Map<String, dynamic> toJson() => _$ProfileUserToJson(this);
}

@JsonSerializable()
class ProfileStats {
  const ProfileStats({
    required this.alertsReceived,
    required this.pushCount,
    required this.experimentCount,
    required this.usefulCount,
    required this.notUsefulCount,
    this.usefulRatio,
    required this.missedIssues,
  });

  final int alertsReceived;
  final int pushCount;
  final int experimentCount;
  final int usefulCount;
  final int notUsefulCount;

  /// 0~100 정수. 판정이 없으면 `null` (`–`).
  final int? usefulRatio;

  /// 기간 안에 복원한 걸러진 항목 수 (`직접 찾아본 건`).
  final int missedIssues;

  factory ProfileStats.fromJson(Map<String, dynamic> json) =>
      _$ProfileStatsFromJson(json);

  Map<String, dynamic> toJson() => _$ProfileStatsToJson(this);
}

@JsonSerializable()
class CategoryReaction {
  const CategoryReaction({
    required this.category,
    required this.useful,
    required this.notUseful,
    required this.total,
  });

  /// taxonomy slug.
  final String category;
  final int useful;
  final int notUseful;
  final int total;

  factory CategoryReaction.fromJson(Map<String, dynamic> json) =>
      _$CategoryReactionFromJson(json);

  Map<String, dynamic> toJson() => _$CategoryReactionToJson(this);
}

/// `학습된 취향`.
@JsonSerializable()
class Learned {
  const Learned({
    required this.kindPenalties,
    required this.sourceTrustChanges,
    required this.profileVectorLabels,
    required this.personalModelThreshold,
  });

  @JsonKey(defaultValue: <KindPenalty>[])
  final List<KindPenalty> kindPenalties;
  @JsonKey(defaultValue: <SourceTrustChange>[])
  final List<SourceTrustChange> sourceTrustChanges;
  final int profileVectorLabels;

  /// **정적** 50.
  final int personalModelThreshold;

  factory Learned.fromJson(Map<String, dynamic> json) =>
      _$LearnedFromJson(json);

  Map<String, dynamic> toJson() => _$LearnedToJson(this);
}

@JsonSerializable()
class KindPenalty {
  const KindPenalty({
    required this.kind,
    required this.weight,
    required this.notUseful,
    required this.total,
    required this.active,
  });

  @JsonKey(unknownEnumValue: Kind.unknown)
  final Kind kind;
  final double weight;
  final int notUseful;
  final int total;
  final bool active;

  factory KindPenalty.fromJson(Map<String, dynamic> json) =>
      _$KindPenaltyFromJson(json);

  Map<String, dynamic> toJson() => _$KindPenaltyToJson(this);
}

@JsonSerializable()
class SourceTrustChange {
  const SourceTrustChange({
    required this.sourceId,
    required this.sourceName,
    required this.from,
    required this.to,
  });

  final String sourceId;
  final String sourceName;
  final double from;
  final double to;

  factory SourceTrustChange.fromJson(Map<String, dynamic> json) =>
      _$SourceTrustChangeFromJson(json);

  Map<String, dynamic> toJson() => _$SourceTrustChangeToJson(this);
}

/// 주간 리포트 목록 한 줄. `weekly_report_latest` 에는 `created_at` 이 없다.
@JsonSerializable()
class ReportSummary {
  const ReportSummary({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.periodStart,
    required this.periodEnd,
    this.createdAt,
  });

  final String id;
  final String title;
  final String subtitle;

  /// `YYYY-MM-DD`.
  final String periodStart;
  final String periodEnd;
  final DateTime? createdAt;

  factory ReportSummary.fromJson(Map<String, dynamic> json) =>
      _$ReportSummaryFromJson(json);

  Map<String, dynamic> toJson() => _$ReportSummaryToJson(this);
}

/// `GET /reports/{id}` — 범용 표 묶음.
@JsonSerializable()
class Report {
  const Report({
    required this.id,
    required this.title,
    required this.subtitle,
    required this.periodStart,
    required this.periodEnd,
    required this.createdAt,
    required this.sections,
  });

  final String id;
  final String title;
  final String subtitle;
  final String periodStart;
  final String periodEnd;
  final DateTime createdAt;
  @JsonKey(defaultValue: <ReportSection>[])
  final List<ReportSection> sections;

  factory Report.fromJson(Map<String, dynamic> json) => _$ReportFromJson(json);

  Map<String, dynamic> toJson() => _$ReportToJson(this);
}

@JsonSerializable()
class ReportSection {
  const ReportSection({
    required this.key,
    required this.title,
    required this.columns,
    required this.rows,
  });

  /// `funnel`, `drop_reasons`, `by_source` … (`scripts/weekly_report.py` 표 순서).
  final String key;
  final String title;
  final List<String> columns;

  /// 셀 값은 문자열·숫자·`null`.
  final List<List<Object?>> rows;

  factory ReportSection.fromJson(Map<String, dynamic> json) =>
      _$ReportSectionFromJson(json);

  Map<String, dynamic> toJson() => _$ReportSectionToJson(this);
}
