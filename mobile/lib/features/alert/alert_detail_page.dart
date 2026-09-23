// 07 피드백 · 판정 근거 화면 — 요약 카드·근거 카드(점수 바)·판정 버튼·안내 카드·최근 판정.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/routes.dart';
import '../../core/format.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/launch.dart';
import '../../core/providers.dart';
import '../../core/snack.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import 'alert_providers.dart';

class AlertDetailPage extends ConsumerWidget {
  const AlertDetailPage({super.key, required this.alertId});

  final String alertId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final detail = ref.watch(alertDetailProvider(alertId));
    final url = detail.value?.alert.url;
    return Scaffold(
      appBar: SubTopBar(
        title: '피드백',
        actions: [
          if (url != null)
            Semantics(
              button: true,
              label: '원문',
              child: GestureDetector(
                onTap: () => openExternal(context, url),
                behavior: HitTestBehavior.opaque,
                child: const AppIcon(
                  'external',
                  size: 22,
                  color: AppColors.textPrimary,
                ),
              ),
            ),
        ],
      ),
      body: detail.when(
        loading: () => const LoadingState(),
        error: (error, _) => ErrorState(
          message: errorMessage(error),
          onRetry: () => ref.invalidate(alertDetailProvider(alertId)),
        ),
        data: (detail) => _Body(detail: detail),
      ),
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.detail});

  final AlertDetail detail;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final alert = detail.alert;
    final user = watchAlertUserState(ref, alert);
    return SingleChildScrollView(
      padding: EdgeInsets.only(
        top: 4,
        bottom: 24 + MediaQuery.paddingOf(context).bottom,
      ),
      child: Column(
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: 12,
        children: [
          _SummaryCard(alert: alert),
          const SectionLabel('이 알림이 온 이유'),
          _RationaleCard(rationale: detail.rationale),
          const SectionLabel('당신의 판정'),
          Padding(
            padding: const EdgeInsets.symmetric(horizontal: 16),
            child: FeedbackButtons(
              value: user.feedback,
              onChanged: (verdict) => runOrSnack(
                context,
                () => ref
                    .read(alertUserStatesProvider.notifier)
                    .setFeedback(alert, verdict),
              ),
            ),
          ),
          _TrustNoteCard(source: detail.rationale.trustNoteSource),
          const _RecentFeedback(),
        ],
      ),
    );
  }
}

class _SummaryCard extends ConsumerWidget {
  const _SummaryCard({required this.alert});

  final Alert alert;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final deliveredAt = alert.deliveredAt;
    final meta = [
      alert.sourceName,
      if (deliveredAt != null)
        relativeTime(deliveredAt, now: ref.watch(clockProvider)()),
    ].join(' · ');
    return AppCard(
      children: [
        Row(
          spacing: 8,
          children: [
            Expanded(child: Text(meta, style: AppText.captionMd)),
            if (alert.deliveryMode case final mode?) DeliveryBadge(mode),
          ],
        ),
        Text(alert.title, style: AppText.titleDetail),
        if (alert.summary.isNotEmpty)
          Text(alert.summary, style: AppText.bodySummary),
      ],
    );
  }
}

/// 점수/통과선·routing 라벨·점수 바·선별·판정 근거 두 줄.
class _RationaleCard extends StatelessWidget {
  const _RationaleCard({required this.rationale});

  /// 디자인의 네 행. `hot`·`multi` 는 0 이 아닐 때만 더한다 (계약 4.2).
  static const Set<String> _alwaysShown = {'src', 'rel', 'fresh', 'kind'};

  final Rationale rationale;

  @override
  Widget build(BuildContext context) {
    final score = rationale.score;
    final components = score?.components ?? const <String, double>{};
    final rows = [
      for (final MapEntry(:key, :value) in components.entries)
        if (_alwaysShown.contains(key) || value != 0) (key, value),
      if (score != null)
        for (final key in _alwaysShown)
          if (!components.containsKey(key)) (key, 0.0),
    ];
    final reasons = _reasonSpans(rationale);
    return AppCard(
      children: [
        Row(
          crossAxisAlignment: CrossAxisAlignment.baseline,
          textBaseline: TextBaseline.alphabetic,
          spacing: 8,
          children: [
            Expanded(
              child: score == null
                  ? const SizedBox.shrink()
                  : Text.rich(
                      TextSpan(
                        text: '점수 ${formatScore(score.total)} ',
                        style: AppText.labelButton,
                        children: [
                          TextSpan(
                            text: '/ 통과선 ${formatScore(score.threshold)}',
                            style: AppText.labelButton.copyWith(
                              fontWeight: FontWeight.w500,
                              color: AppColors.textTertiary,
                            ),
                          ),
                        ],
                      ),
                    ),
            ),
            Text(
              rationale.routing.label,
              style: AppText.captionStrong.copyWith(color: AppColors.warn),
            ),
          ],
        ),
        for (final (label, value) in rows) ScoreBar(label: label, value: value),
        if (reasons.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 4),
            child: Text.rich(TextSpan(children: reasons), style: _reasonStyle),
          ),
      ],
    );
  }

  static final TextStyle _reasonStyle = AppText.captionMd.copyWith(
    color: AppColors.textMuted,
    height: 1.55,
  );

  /// `선별: relevance 0.83 · kind technique — "…"` 와
  /// `판정: importance 4 · 유사 피드백 👍 "…"`. 없는 결정은 줄을 빼고, 없는 값은 조각을 뺀다.
  static List<InlineSpan> _reasonSpans(Rationale rationale) {
    final lines = <List<InlineSpan>>[];
    if (rationale.screening case final s?) {
      lines.add([
        TextSpan(text: '선별: relevance ${formatScore(s.relevance)}'),
        if (s.kind case final kind?) ...[
          const TextSpan(text: ' · kind '),
          TextSpan(text: kind.value, style: AppText.mono(_reasonStyle)),
        ],
        if (s.reason case final reason? when reason.isNotEmpty)
          TextSpan(text: ' — "$reason"'),
      ]);
    }
    if (rationale.judgment case final j?) {
      final similar = j.similarFeedback.firstOrNull;
      final parts = [
        if (j.importance case final importance?) 'importance $importance',
        if (similar != null)
          '유사 피드백 '
              '${similar.feedback == FeedbackVerdict.notUseful ? '👎' : '👍'} '
              '"${similar.title}"',
      ];
      if (parts.isNotEmpty) {
        lines.add([TextSpan(text: '판정: ${parts.join(' · ')}')]);
      }
    }
    return [
      for (final (index, line) in lines.indexed) ...[
        if (index > 0) const TextSpan(text: '\n'),
        ...line,
      ],
    ];
  }
}

class _TrustNoteCard extends StatelessWidget {
  const _TrustNoteCard({required this.source});

  final String source;

  @override
  Widget build(BuildContext context) {
    final style = AppText.captionMd.copyWith(height: 1.6);
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 12),
      children: [
        Text.rich(
          TextSpan(
            children: [
              const TextSpan(text: '👍는 다음 선별·판정에 사례로 들어가고 '),
              TextSpan(text: source, style: AppText.mono(style)),
              const TextSpan(
                text: '의 신뢰도를 보정합니다. Discord에서 누른 리액션과 자동으로 합쳐집니다.',
              ),
            ],
          ),
          style: style,
        ),
      ],
    );
  }
}

/// `최근 판정 · 오늘 N건` + 행 목록. 행을 누르면 그 알림의 07 을 연다.
class _RecentFeedback extends ConsumerWidget {
  const _RecentFeedback();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final recent = ref.watch(recentFeedbackProvider).value;
    if (recent == null) return const SizedBox.shrink();
    final now = ref.watch(clockProvider)();
    return Column(
      crossAxisAlignment: CrossAxisAlignment.stretch,
      spacing: 12,
      children: [
        SectionLabel('최근 판정 · 오늘 ${recent.todayCount}건'),
        if (recent.items.isNotEmpty)
          AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            gap: 0,
            children: [
              for (final (index, item) in recent.items.indexed)
                _RecentRow(
                  item: item,
                  now: now,
                  isLast: index == recent.items.length - 1,
                ),
            ],
          ),
      ],
    );
  }
}

class _RecentRow extends StatelessWidget {
  const _RecentRow({
    required this.item,
    required this.now,
    required this.isLast,
  });

  final RecentFeedbackItem item;
  final DateTime now;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    final useful = item.feedback != FeedbackVerdict.notUseful;
    return GestureDetector(
      onTap: () => context.push(AppRoutes.alert(item.alertId)),
      behavior: HitTestBehavior.opaque,
      child: Container(
        padding: const EdgeInsets.symmetric(vertical: 6),
        decoration: isLast
            ? null
            : const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.track)),
              ),
        child: Row(
          spacing: 10,
          children: [
            AppIcon(
              useful ? 'thumbup' : 'thumbdown',
              size: 16,
              color: useful ? AppColors.primary : AppColors.warn,
            ),
            Expanded(
              child: Text(
                item.title,
                maxLines: 1,
                overflow: TextOverflow.ellipsis,
                style: AppText.bodySm,
              ),
            ),
            Text(
              relativeTime(item.createdAt, now: now, suffix: false),
              style: AppText.captionSm,
            ),
          ],
        ),
      ),
    );
  }
}
