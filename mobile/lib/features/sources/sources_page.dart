// 06 수집 소스 화면 — Stat 3열, 그룹별 SourceRow(상태 줄·trust·토글), 미착수 칩. `+` 는 준비 중.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import 'sources_controller.dart';

/// `last_error` 로 조치 문구를 대신할 때 앞에서 자르는 길이 (계약 3.4).
const int _lastErrorLength = 30;

class SourcesPage extends ConsumerWidget {
  const SourcesPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final sources = ref.watch(sourcesProvider);
    return Scaffold(
      appBar: SubTopBar(
        title: '수집 소스',
        actions: [
          Semantics(
            button: true,
            label: '소스 추가',
            child: GestureDetector(
              onTap: () =>
                  ScaffoldMessenger.of(context)
                      .showSnackBar(const SnackBar(content: Text('준비 중'))),
              behavior: HitTestBehavior.opaque,
              child: const AppIcon(
                'plus',
                size: 22,
                color: AppColors.textPrimary,
              ),
            ),
          ),
        ],
      ),
      body: switch (sources) {
        AsyncData(:final value) => _Body(response: value),
        AsyncError(:final error) => ErrorState(
          message: error is ApiException ? error.message : '소스를 불러오지 못했습니다.',
          onRetry: () => ref.invalidate(sourcesProvider),
        ),
        _ => const LoadingState(),
      },
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.response});

  final SourcesResponse response;

  Future<void> _toggle(
    BuildContext context,
    WidgetRef ref,
    Source source,
    bool enabled,
  ) async {
    final messenger = ScaffoldMessenger.of(context);
    try {
      await ref
          .read(sourcesProvider.notifier)
          .setEnabled(source.id, enabled: enabled);
    } on ApiException catch (error) {
      messenger.showSnackBar(SnackBar(content: Text(error.message)));
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final stats = response.stats;
    final triage = stats.llmBudget.triage;
    final groups = [
      for (final group in SourceGroup.values)
        (
          group,
          [
            for (final s in response.sources)
              if (s.group == group) s,
          ],
        ),
    ];
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(16, 8, 16, 4),
          child: Row(
            spacing: 12,
            children: [
              Expanded(
                child: StatCard(
                  size: StatCardSize.compact,
                  label: '활성 소스',
                  value: '${stats.enabledCount}',
                  suffix: ' / ${stats.total}',
                ),
              ),
              Expanded(
                child: StatCard(
                  size: StatCardSize.compact,
                  label: '오늘 수집',
                  value: '${stats.itemsCollected}',
                  suffix: ' 건',
                ),
              ),
              Expanded(
                child: StatCard(
                  size: StatCardSize.compact,
                  label: 'LLM 예산',
                  value: '${triage.used}',
                  suffix: ' / ${triage.cap}',
                ),
              ),
            ],
          ),
        ),
        for (final (group, sources) in groups)
          if (sources.isNotEmpty) ...[
            SectionLabel(group.label),
            AppCard(
              padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 2),
              gap: 0,
              children: [
                for (final (index, source) in sources.indexed)
                  SourceRow(
                    source: source,
                    isLast: index == sources.length - 1,
                    onChanged: (enabled) =>
                        _toggle(context, ref, source, enabled),
                  ),
              ],
            ),
          ],
        if (response.plannedSources.isNotEmpty) ...[
          const SectionLabel('미착수'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: Wrap(
              spacing: AppSpacing.chipGap,
              runSpacing: AppSpacing.chipGap,
              children: [
                for (final name in response.plannedSources)
                  AppChip(label: name),
              ],
            ),
          ),
        ],
      ],
    );
  }
}

/// 소스 한 줄 — 아이콘 타일, ID(mono)와 상태 줄, `trust x.x`, 토글.
class SourceRow extends StatelessWidget {
  const SourceRow({
    super.key,
    required this.source,
    required this.onChanged,
    this.isLast = false,
  });

  final Source source;
  final ValueChanged<bool> onChanged;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final status = sourceStatusLine(source);
    return Container(
      padding: const EdgeInsets.symmetric(vertical: 12),
      decoration: isLast
          ? null
          : const BoxDecoration(
              border: Border(bottom: BorderSide(color: AppColors.track)),
            ),
      child: Row(
        spacing: 12,
        children: [
          Container(
            width: 36,
            height: 36,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.subtle,
              borderRadius: BorderRadius.circular(AppRadius.button),
            ),
            child: AppIcon(
              sourceIcon(source.type),
              size: 18,
              color: AppColors.textSecondary,
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              mainAxisSize: MainAxisSize.min,
              children: [
                // 긴 ID(`github_release:watchlist`)가 중간에서 줄바꿈되지 않게 한 줄로 줄인다.
                FittedBox(
                  fit: BoxFit.scaleDown,
                  alignment: Alignment.centerLeft,
                  child: Text(
                    source.id,
                    style: AppText.mono(AppText.labelStrong),
                  ),
                ),
                Text(
                  status.text,
                  style: status.isError
                      ? AppText.captionSmStrong.copyWith(color: AppColors.error)
                      : AppText.captionSm,
                ),
              ],
            ),
          ),
          Text(
            'trust ${source.trust.toStringAsFixed(1)}',
            style: AppText.mono(AppText.captionMd),
          ),
          AppToggle(value: source.enabled, onChanged: onChanged),
        ],
      ),
    );
  }
}

/// 아이콘 타일 이름. 디자인에 아이콘이 없는 소스 종류는 `rss` 로 그린다.
String sourceIcon(SourceType type) => switch (type) {
  SourceType.githubRelease => 'github',
  SourceType.youtube => 'youtube',
  SourceType.rss ||
  SourceType.hackernews ||
  SourceType.hfPapers ||
  SourceType.unknown => 'rss',
};

/// 상태 줄. `{주기}` 뒤에 `보정 {base} → {calibrated}` · `저장소 {n}개` 를 붙이고,
/// 실패가 있으면 `실패 {n}회 · {조치}` 로 바꾼다 (오류색). 조치는 `error_hint`,
/// 없으면 `last_error` 앞 30자다.
({String text, bool isError}) sourceStatusLine(Source source) {
  if (source.consecutiveFailures > 0) {
    final lastError = source.lastError;
    final hint =
        source.errorHint ??
        (lastError != null && lastError.length > _lastErrorLength
            ? lastError.substring(0, _lastErrorLength)
            : lastError);
    return (
      text: ['실패 ${source.consecutiveFailures}회', ?hint].join(' · '),
      isError: true,
    );
  }
  final calibrated = source.trustCalibrated;
  final repoCount = source.repoCount;
  return (
    text: [
      '${source.pollIntervalMin}분',
      if (calibrated != null)
        '보정 ${_trustValue(source.trustBase)} → ${_trustValue(calibrated)}',
      if (repoCount != null) '저장소 $repoCount개',
    ].join(' · '),
    isError: false,
  );
}

/// 2자리에서 끝의 0 하나를 뗀다 (`0.50` → `0.5`, `1.00` → `1.0`, `0.58`).
String _trustValue(double value) {
  final fixed = value.toStringAsFixed(2);
  return fixed.endsWith('0') ? fixed.substring(0, fixed.length - 1) : fixed;
}
