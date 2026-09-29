// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'score.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

ScoreBreakdown _$ScoreBreakdownFromJson(Map<String, dynamic> json) =>
    ScoreBreakdown(
      total: (json['total'] as num).toDouble(),
      threshold: (json['threshold'] as num).toDouble(),
      components: (json['components'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, (e as num).toDouble()),
      ),
    );

Map<String, dynamic> _$ScoreBreakdownToJson(ScoreBreakdown instance) =>
    <String, dynamic>{
      'total': instance.total,
      'threshold': instance.threshold,
      'components': instance.components,
    };
