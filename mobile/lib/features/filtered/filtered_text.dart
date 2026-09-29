// 걸러진 항목 문구 조합 — 그룹 제목·요약 줄, 사유 줄, 요약 카드 안내 (계약 3.2·4.6 의 클라이언트 몫).
import '../../core/format.dart';
import '../../core/labels.dart';
import '../../data/models/models.dart';

/// 소스별 요약의 `선별 relevance 0.5 미만` 기준 (계약 4.6, 백엔드 `screening_relevance_floor` 기본값).
const double lowRelevanceRatioFloor = 0.5;

const String _sep = ' · ';

/// relevance 는 끝자리 0 을 뗀 2자리 (`0.3`, `0.62`).
String formatRelevance(double value) {
  final fixed = value.toStringAsFixed(2);
  return fixed.endsWith('0') ? fixed.substring(0, fixed.length - 1) : fixed;
}

/// `0.35–0.45`.
String formatRange(List<double> range) => range.length == 2
    ? '${formatScore(range[0])}–${formatScore(range[1])}'
    : '';

/// 0 이 아닌 관문 건수를 [Gate] 순서로 (`중복 9 · 선별 11 · 점수 3`).
String gateCountsLine(Map<Gate, int> counts) => [
  for (final gate in Gate.values)
    if ((counts[gate] ?? 0) > 0) '${gate.label} ${counts[gate]}',
].join(_sep);

String groupTitle(FilteredGroup group, FilteredView view) => switch (view) {
  FilteredView.source => group.source?.id ?? group.key,
  FilteredView.kind =>
    group.key == FilteredGroup.unclassifiedKey
        ? '미분류 (exclude·중복)'
        : '${group.key} · ${(group.kind ?? Kind.unknown).label}',
  FilteredView.gate => (group.gate ?? Gate.unknown).label,
};

/// 그룹 헤더 둘째 줄. [borderlineRange] 는 요약 카드의 `borderline.range`.
String groupSummary(
  FilteredGroup group,
  FilteredView view, {
  required List<double> borderlineRange,
}) => switch (view) {
  FilteredView.source => _sourceSummary(group),
  FilteredView.kind => _kindSummary(group, borderlineRange),
  FilteredView.gate => _gateSummary(group),
};

String _sourceSummary(FilteredGroup group) {
  final ratio = group.lowRelevanceRatio;
  if (ratio != null && ratio >= lowRelevanceRatioFloor) {
    return '선별 relevance ${formatRelevance(lowRelevanceRatioFloor)} 미만 '
        '${(ratio * 100).round()}%';
  }
  return gateCountsLine(group.gateCounts);
}

/// 계약에 규칙이 없는 kind(감점·경계·키워드·클러스터 모두 없음)는 소스별 규칙으로 채운다.
String _kindSummary(FilteredGroup group, List<double> borderlineRange) {
  if (group.key == FilteredGroup.unclassifiedKey) return '선별 전 탈락 — kind 없음';
  final weight = group.kindWeight;
  final feedback = group.kindFeedback;
  final clusterDup = group.gateCounts[Gate.clusterDup] ?? 0;
  final parts = [
    if (weight != null && weight < 0) '감점 ${formatScore(weight)}',
    if (feedback != null && feedback.total > 0)
      '불필요 ${feedback.notUseful}/${feedback.total}'
          '${group.penaltyActive ? ' → 감점 유지 중' : ''}',
    if (group.borderlineCount > 0)
      '점수 경계(${formatRange(borderlineRange)}) ${group.borderlineCount}건',
    if (group.excludeKeywordHits > 0) 'exclude 키워드 ${group.excludeKeywordHits}',
    if (clusterDup > 0) '${Gate.clusterDup.label} $clusterDup',
  ];
  return parts.isEmpty ? _sourceSummary(group) : parts.join(_sep);
}

/// 관문별(디자인 없음) — `preview` 에 많이 나온 소스 2개. preview 는 최신 3건뿐이라
/// 소스별 전체 건수를 알 수 없어 이름만 쓴다.
String _gateSummary(FilteredGroup group) {
  final counts = <String, int>{};
  for (final item in group.preview) {
    counts[item.sourceName] = (counts[item.sourceName] ?? 0) + 1;
  }
  final names = counts.keys.toList()
    ..sort((a, b) => counts[b]!.compareTo(counts[a]!));
  return names.take(2).join(_sep);
}

/// 탈락 태그 옆 사유 줄 (계약 3.2).
String reasonLine(
  DroppedItem item,
  FilteredView view,
) => switch (item.droppedGate) {
  Gate.screening => [
    if (item.relevance != null) 'relevance ${formatRelevance(item.relevance!)}',
    // 종류별 보기는 그룹 제목이 kind 라 사유 줄에서 뺀다.
    if (view != FilteredView.kind && item.kind != null) item.kind!.value,
    if (item.reason != null) '"${item.reason}"',
  ].join(_sep),
  Gate.score => _scoreLine(item, view),
  Gate.exclude =>
    item.matchedKeywords.isEmpty
        ? 'exclude 키워드'
        : '키워드 ${item.matchedKeywords.join(', ')}',
  Gate.dedup => '같은 이슈 중복',
  Gate.stale => '72시간 지난 항목',
  Gate.judgment => '판정 false',
  Gate.clusterDup => '같은 이슈 하루 1건 → 앞 알림에 병기',
  Gate.unknown => item.reason ?? '',
};

String _scoreLine(DroppedItem item, FilteredView view) {
  final score = item.score;
  if (score == null) return '';
  final total = formatScore(score.total);
  if (item.explorationCandidate) return '$total$_sep경계 → 내일 탐색 슬롯 후보';
  if (view == FilteredView.kind) return '$total$_sep${item.sourceName}';
  final components = [
    for (final MapEntry(:key, :value) in score.components.entries)
      if (formatScore(value) != '0.00') '$key ${formatScore(value)}',
  ];
  return components.isEmpty ? total : '$total (${components.join(_sep)})';
}

/// 요약 카드 하단 안내. 관문별은 디자인이 없어 소스별 문구를 쓴다.
String summaryNote(FilteredSummary summary, FilteredView view) =>
    switch (view) {
      FilteredView.kind =>
        'kind는 선별 단계 출력이라 exclude·중복 탈락 '
            '${summary.unclassifiedCount}건은 "미분류"로 묶입니다.',
      FilteredView.source || FilteredView.gate =>
        '점수 탈락 중 경계(${formatRange(summary.borderline.range)}) '
            '${summary.borderline.count}건 · 탐색 슬롯 후보',
    };
