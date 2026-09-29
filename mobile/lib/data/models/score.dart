// 점수 결정 행의 breakdown — 07 근거 카드와 걸러진 항목 사유 줄이 같이 쓴다 (계약 3.2·4.2).
import 'package:json_annotation/json_annotation.dart';

part 'score.g.dart';

@JsonSerializable()
class ScoreBreakdown {
  const ScoreBreakdown({
    required this.total,
    required this.threshold,
    required this.components,
  });

  final double total;

  /// 통과선.
  final double threshold;

  /// `src`·`rel`·`hot`·`multi`·`fresh`·`kind` → 값. 서버 순서를 유지한다.
  final Map<String, double> components;

  factory ScoreBreakdown.fromJson(Map<String, dynamic> json) =>
      _$ScoreBreakdownFromJson(json);

  Map<String, dynamic> toJson() => _$ScoreBreakdownToJson(this);
}
