// 수집 소스 모델 — Source 한 줄과 06 화면 응답(Stat·LLM 예산·미착수) (계약 3.4·4.5).
import 'package:json_annotation/json_annotation.dart';

import '../../core/labels.dart';

part 'source.g.dart';

@JsonSerializable()
class Source {
  const Source({
    required this.id,
    required this.displayName,
    required this.type,
    required this.group,
    required this.enabled,
    required this.pollIntervalMin,
    required this.trust,
    required this.trustBase,
    this.trustCalibrated,
    required this.consecutiveFailures,
    this.errorHint,
    this.lastError,
    this.lastPolledAt,
    this.repoCount,
  });

  /// `sources.name` (`rss:anthropic`).
  final String id;
  final String displayName;
  @JsonKey(unknownEnumValue: SourceType.unknown)
  final SourceType type;
  @JsonKey(unknownEnumValue: SourceGroup.unknown)
  final SourceGroup group;
  final bool enabled;
  final int pollIntervalMin;

  /// `trust_calibrated ?? trust_base`.
  final double trust;
  final double trustBase;

  /// 미보정이면 `null` (상태 줄의 `보정 a → b` 는 이 값이 있을 때만).
  final double? trustCalibrated;
  final int consecutiveFailures;
  final String? errorHint;
  final String? lastError;
  final DateTime? lastPolledAt;

  /// `github_release` 의 저장소 수, 그 밖은 `null`.
  final int? repoCount;

  Source withEnabled(bool value) => Source(
    id: id,
    displayName: displayName,
    type: type,
    group: group,
    enabled: value,
    pollIntervalMin: pollIntervalMin,
    trust: trust,
    trustBase: trustBase,
    trustCalibrated: trustCalibrated,
    consecutiveFailures: consecutiveFailures,
    errorHint: errorHint,
    lastError: lastError,
    lastPolledAt: lastPolledAt,
    repoCount: repoCount,
  );

  factory Source.fromJson(Map<String, dynamic> json) => _$SourceFromJson(json);

  Map<String, dynamic> toJson() => _$SourceToJson(this);
}

/// `GET /sources`.
@JsonSerializable()
class SourcesResponse {
  const SourcesResponse({
    required this.stats,
    required this.sources,
    required this.plannedSources,
  });

  final SourceStats stats;

  /// `sources.yaml` 순서. 앱은 `group` 으로 섹션을 나눈다.
  @JsonKey(defaultValue: <Source>[])
  final List<Source> sources;

  /// **정적** 미착수 소스 이름.
  @JsonKey(defaultValue: <String>[])
  final List<String> plannedSources;

  factory SourcesResponse.fromJson(Map<String, dynamic> json) =>
      _$SourcesResponseFromJson(json);

  Map<String, dynamic> toJson() => _$SourcesResponseToJson(this);
}

@JsonSerializable()
class SourceStats {
  const SourceStats({
    required this.enabledCount,
    required this.total,
    required this.windowHours,
    required this.itemsCollected,
    required this.llmBudget,
  });

  final int enabledCount;
  final int total;
  final int windowHours;
  final int itemsCollected;
  final LlmBudget llmBudget;

  SourceStats withEnabledCount(int value) => SourceStats(
    enabledCount: value,
    total: total,
    windowHours: windowHours,
    itemsCollected: itemsCollected,
    llmBudget: llmBudget,
  );

  factory SourceStats.fromJson(Map<String, dynamic> json) =>
      _$SourceStatsFromJson(json);

  Map<String, dynamic> toJson() => _$SourceStatsToJson(this);
}

/// 오늘(달력일) LLM 예산. 06 Stat `LLM 예산` 은 [triage] 다.
@JsonSerializable()
class LlmBudget {
  const LlmBudget({
    required this.triage,
    required this.judge,
    required this.explore,
  });

  final BudgetUsage triage;
  final BudgetUsage judge;
  final BudgetUsage explore;

  factory LlmBudget.fromJson(Map<String, dynamic> json) =>
      _$LlmBudgetFromJson(json);

  Map<String, dynamic> toJson() => _$LlmBudgetToJson(this);
}

@JsonSerializable()
class BudgetUsage {
  const BudgetUsage({required this.used, required this.cap});

  final int used;
  final int cap;

  factory BudgetUsage.fromJson(Map<String, dynamic> json) =>
      _$BudgetUsageFromJson(json);

  Map<String, dynamic> toJson() => _$BudgetUsageToJson(this);
}
