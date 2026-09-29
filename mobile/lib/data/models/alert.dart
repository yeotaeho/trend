// 알림 모델 — 피드 카드(Alert), 07 상세·근거(AlertDetail·Rationale), 판정 결과·최근 판정 (계약 3.1·4.1·4.2).
import 'package:json_annotation/json_annotation.dart';

import '../../core/labels.dart';
import 'score.dart';

part 'alert.g.dart';

@JsonSerializable()
class Alert {
  const Alert({
    required this.id,
    required this.sourceId,
    required this.sourceName,
    required this.sourceType,
    this.deliveredAt,
    this.deliveryMode,
    required this.isExploration,
    required this.title,
    required this.summary,
    required this.categories,
    required this.tags,
    required this.url,
    this.importance,
    required this.isSaved,
    this.feedback,
  });

  final String id;
  final String sourceId;
  final String sourceName;
  @JsonKey(unknownEnumValue: SourceType.unknown)
  final SourceType sourceType;

  /// 발송된 적 없는 항목(07 상세, `cluster_dup`)은 `null`.
  final DateTime? deliveredAt;
  @JsonKey(unknownEnumValue: DeliveryMode.unknown)
  final DeliveryMode? deliveryMode;
  final bool isExploration;

  /// 발송한 제목 (형제 버전 병기 포함).
  final String title;

  /// 요약이 없는 복원 항목은 원문 앞부분이거나 빈 문자열이다.
  @JsonKey(defaultValue: '')
  final String summary;

  /// 선별이 고른 taxonomy slug. 카드에 `#slug` 로 표시한다.
  @JsonKey(defaultValue: <String>[])
  final List<String> categories;
  @JsonKey(defaultValue: <String>[])
  final List<String> tags;
  final String url;
  final int? importance;
  final bool isSaved;
  @JsonKey(unknownEnumValue: FeedbackVerdict.unknown)
  final FeedbackVerdict? feedback;

  Alert withFeedback(FeedbackVerdict? value) => _copy(feedback: () => value);

  Alert withSaved(bool value) => _copy(isSaved: value);

  Alert _copy({bool? isSaved, FeedbackVerdict? Function()? feedback}) => Alert(
    id: id,
    sourceId: sourceId,
    sourceName: sourceName,
    sourceType: sourceType,
    deliveredAt: deliveredAt,
    deliveryMode: deliveryMode,
    isExploration: isExploration,
    title: title,
    summary: summary,
    categories: categories,
    tags: tags,
    url: url,
    importance: importance,
    isSaved: isSaved ?? this.isSaved,
    feedback: feedback == null ? this.feedback : feedback(),
  );

  factory Alert.fromJson(Map<String, dynamic> json) => _$AlertFromJson(json);

  Map<String, dynamic> toJson() => _$AlertToJson(this);
}

/// `GET /alerts/{id}` — [Alert] 필드 전체에 `rationale` 을 붙인 평평한 객체.
class AlertDetail {
  const AlertDetail({required this.alert, required this.rationale});

  final Alert alert;
  final Rationale rationale;

  factory AlertDetail.fromJson(Map<String, dynamic> json) => AlertDetail(
    alert: Alert.fromJson(json),
    rationale: Rationale.fromJson(json['rationale'] as Map<String, dynamic>),
  );

  Map<String, dynamic> toJson() => {
    ...alert.toJson(),
    'rationale': rationale.toJson(),
  };
}

/// 07 "이 알림이 온 이유".
@JsonSerializable()
class Rationale {
  const Rationale({
    this.score,
    required this.routing,
    this.screening,
    this.judgment,
    required this.trustNoteSource,
  });

  /// 점수 전 항목은 `null`.
  final ScoreBreakdown? score;
  @JsonKey(unknownEnumValue: Routing.unknown)
  final Routing routing;

  /// 선별 전 항목은 `null`.
  final Screening? screening;

  /// 판정 전 항목은 `null`.
  final Judgment? judgment;

  /// 안내 카드 문장에 넣을 소스 표시명.
  final String trustNoteSource;

  factory Rationale.fromJson(Map<String, dynamic> json) =>
      _$RationaleFromJson(json);

  Map<String, dynamic> toJson() => _$RationaleToJson(this);
}

@JsonSerializable()
class Screening {
  const Screening({
    required this.relevance,
    this.kind,
    required this.topics,
    this.reason,
  });

  final double relevance;
  @JsonKey(unknownEnumValue: Kind.unknown)
  final Kind? kind;

  /// 화면에는 쓰지 않는다. `topics` 가 없는 옛 결정 행은 `[]`.
  @JsonKey(defaultValue: <String>[])
  final List<String> topics;
  final String? reason;

  factory Screening.fromJson(Map<String, dynamic> json) =>
      _$ScreeningFromJson(json);

  Map<String, dynamic> toJson() => _$ScreeningToJson(this);
}

@JsonSerializable()
class Judgment {
  const Judgment({
    this.importance,
    required this.worthNotifying,
    required this.similarFeedback,
  });

  final int? importance;
  final bool worthNotifying;

  /// 판정 프롬프트에 넣은 최근접 피드백 사례. 화면은 첫 건만 쓴다.
  @JsonKey(defaultValue: <SimilarFeedback>[])
  final List<SimilarFeedback> similarFeedback;

  factory Judgment.fromJson(Map<String, dynamic> json) =>
      _$JudgmentFromJson(json);

  Map<String, dynamic> toJson() => _$JudgmentToJson(this);
}

@JsonSerializable()
class SimilarFeedback {
  const SimilarFeedback({
    required this.alertId,
    required this.feedback,
    required this.title,
  });

  final String alertId;
  @JsonKey(unknownEnumValue: FeedbackVerdict.unknown)
  final FeedbackVerdict feedback;
  final String title;

  factory SimilarFeedback.fromJson(Map<String, dynamic> json) =>
      _$SimilarFeedbackFromJson(json);

  Map<String, dynamic> toJson() => _$SimilarFeedbackToJson(this);
}

/// `PUT /alerts/{id}/feedback` 응답.
@JsonSerializable()
class FeedbackResult {
  const FeedbackResult({
    required this.alertId,
    required this.feedback,
    required this.updatedAt,
  });

  final String alertId;
  @JsonKey(unknownEnumValue: FeedbackVerdict.unknown)
  final FeedbackVerdict feedback;
  final DateTime updatedAt;

  factory FeedbackResult.fromJson(Map<String, dynamic> json) =>
      _$FeedbackResultFromJson(json);

  Map<String, dynamic> toJson() => _$FeedbackResultToJson(this);
}

/// `GET /feedback/recent` — 오늘 판정 수와 기간 무관 최근 N건.
@JsonSerializable()
class RecentFeedback {
  const RecentFeedback({required this.todayCount, required this.items});

  final int todayCount;
  @JsonKey(defaultValue: <RecentFeedbackItem>[])
  final List<RecentFeedbackItem> items;

  factory RecentFeedback.fromJson(Map<String, dynamic> json) =>
      _$RecentFeedbackFromJson(json);

  Map<String, dynamic> toJson() => _$RecentFeedbackToJson(this);
}

@JsonSerializable()
class RecentFeedbackItem {
  const RecentFeedbackItem({
    required this.alertId,
    required this.feedback,
    required this.title,
    required this.createdAt,
  });

  final String alertId;
  @JsonKey(unknownEnumValue: FeedbackVerdict.unknown)
  final FeedbackVerdict feedback;
  final String title;
  final DateTime createdAt;

  factory RecentFeedbackItem.fromJson(Map<String, dynamic> json) =>
      _$RecentFeedbackItemFromJson(json);

  Map<String, dynamic> toJson() => _$RecentFeedbackItemToJson(this);
}
