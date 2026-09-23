// 막대 — 07 점수 바(값 ÷ 0.5), 08 👍/👎 누적 바, 09·10 관문 GateBar + 범례.
import 'package:flutter/widgets.dart';

import '../format.dart';
import '../labels.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

/// 점수 성분 한 행. 채움 폭은 `값 ÷ [fullScale]` 비율이고 0 이하는 채움이 없다.
class ScoreBar extends StatelessWidget {
  const ScoreBar({
    super.key,
    required this.label,
    required this.value,
    this.fullScale = 0.5,
  });

  final String label;
  final double value;
  final double fullScale;

  double get fillFraction =>
      value <= 0 ? 0 : (value / fullScale).clamp(0.0, 1.0);

  @override
  Widget build(BuildContext context) {
    final base = AppText.captionMd;
    return Row(
      spacing: 10,
      children: [
        SizedBox(width: 56, child: Text(label, style: AppText.mono(base))),
        Expanded(
          child: Container(
            height: 8,
            decoration: BoxDecoration(
              color: AppColors.track,
              borderRadius: BorderRadius.circular(AppRadius.scoreBar),
            ),
            alignment: Alignment.centerLeft,
            child: FractionallySizedBox(
              widthFactor: fillFraction,
              heightFactor: 1,
              child: Container(
                key: const ValueKey('score-bar-fill'),
                decoration: BoxDecoration(
                  color: AppColors.primary,
                  borderRadius: BorderRadius.circular(AppRadius.scoreBar),
                ),
              ),
            ),
          ),
        ),
        SizedBox(
          width: 44,
          child: Text(
            formatScore(value),
            textAlign: TextAlign.right,
            style: AppText.mono(base).copyWith(
              color: value < 0 ? AppColors.warn : AppColors.textSecondary,
            ),
          ),
        ),
      ],
    );
  }
}

/// 08 카테고리 반응 한 행. 👍·👎 구간 폭은 트랙 폭 대비 비율(0–1)이다.
class StackedBar extends StatelessWidget {
  const StackedBar({
    super.key,
    required this.label,
    required this.usefulFraction,
    required this.notUsefulFraction,
    required this.total,
  });

  final String label;
  final double usefulFraction;
  final double notUsefulFraction;
  final int total;

  @override
  Widget build(BuildContext context) {
    return Row(
      spacing: 10,
      children: [
        SizedBox(
          width: 92,
          child: Text(
            label,
            overflow: TextOverflow.ellipsis,
            style: AppText.captionMd.copyWith(color: AppColors.textSecondary),
          ),
        ),
        Expanded(
          child: ClipRRect(
            borderRadius: BorderRadius.circular(AppRadius.stackedBar),
            child: Container(
              height: 10,
              color: AppColors.track,
              child: LayoutBuilder(
                builder: (context, constraints) {
                  final width = constraints.maxWidth;
                  final useful = usefulFraction.clamp(0.0, 1.0);
                  final notUseful = notUsefulFraction.clamp(0.0, 1.0 - useful);
                  return Row(
                    children: [
                      Container(
                        width: width * useful,
                        color: AppColors.primary,
                      ),
                      Container(
                        width: width * notUseful,
                        color: AppColors.warnMuted,
                      ),
                    ],
                  );
                },
              ),
            ),
          ),
        ),
        SizedBox(
          width: 28,
          child: Text(
            '$total',
            textAlign: TextAlign.right,
            style: AppText.mono(AppText.captionMd),
          ),
        ),
      ],
    );
  }
}

extension GateColor on Gate {
  Color get color => switch (this) {
    Gate.exclude => AppColors.gateExclude,
    Gate.dedup => AppColors.gateDedup,
    Gate.screening => AppColors.gateScreening,
    Gate.score => AppColors.gateScore,
    Gate.judgment => AppColors.gateJudgment,
    Gate.stale => AppColors.gateStale,
    Gate.clusterDup => AppColors.gateClusterDup,
  };
}

/// 관문별 탈락 건수 막대. 구간 폭 = 건수 ÷ 합계, 순서는 [Gate] 선언 순서.
///
/// 범례는 디자인의 다섯 관문을 항상 보여 주고, 디자인에 없던 `stale`·`cluster_dup`
/// 은 건수가 있을 때만 보여 준다.
class GateBar extends StatelessWidget {
  const GateBar({super.key, required this.counts});

  final Map<Gate, int> counts;

  static const Set<Gate> _optionalInLegend = {Gate.stale, Gate.clusterDup};

  @override
  Widget build(BuildContext context) {
    final segments = [
      for (final gate in Gate.values)
        if ((counts[gate] ?? 0) > 0) gate,
    ];
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      mainAxisSize: MainAxisSize.min,
      spacing: 10,
      children: [
        ClipRRect(
          borderRadius: BorderRadius.circular(AppRadius.stackedBar),
          child: Container(
            height: 10,
            color: AppColors.track,
            child: Row(
              children: [
                for (final gate in segments)
                  Expanded(
                    key: ValueKey('gate-segment-${gate.value}'),
                    flex: counts[gate]!,
                    child: ColoredBox(color: gate.color),
                  ),
              ],
            ),
          ),
        ),
        Wrap(
          spacing: 10,
          runSpacing: 10,
          children: [
            for (final gate in Gate.values)
              if (!_optionalInLegend.contains(gate) || (counts[gate] ?? 0) > 0)
                _LegendItem(gate: gate, count: counts[gate] ?? 0),
          ],
        ),
      ],
    );
  }
}

class _LegendItem extends StatelessWidget {
  const _LegendItem({required this.gate, required this.count});

  final Gate gate;
  final int count;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisSize: MainAxisSize.min,
      spacing: 4,
      children: [
        Container(
          width: 8,
          height: 8,
          decoration: BoxDecoration(
            color: gate.color,
            borderRadius: BorderRadius.circular(AppRadius.legendDot),
          ),
        ),
        Text('${gate.label} $count', style: AppText.captionSm),
      ],
    );
  }
}
