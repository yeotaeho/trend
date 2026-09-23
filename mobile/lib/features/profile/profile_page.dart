// 08 내 프로필 — 기간 선택, 사용자 행, Stat 3열, 카테고리 👍/👎 누적 바, 학습된 취향, 주간 리포트 카드.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/routes.dart';
import '../../core/api/api_exception.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import 'profile_providers.dart';

/// 조회 실패 문구. [ApiException] 이 아니면 고정 문장.
String loadErrorMessage(Object error) =>
    error is ApiException ? error.message : '불러오지 못했습니다.';

class ProfilePage extends ConsumerWidget {
  const ProfilePage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final profile = ref.watch(profileProvider);
    return Scaffold(
      appBar: RootTopBar(
        title: '내 프로필',
        actions: [_PeriodButton(days: ref.watch(profilePeriodProvider))],
      ),
      // 기간을 바꿔 다시 조회하는 동안에는 이전 값을 그대로 보여 준다.
      body: switch (profile) {
        AsyncValue(:final value?) => _ProfileBody(profile: value),
        AsyncValue(:final error?) => ErrorState(
          message: loadErrorMessage(error),
          onRetry: () => ref.invalidate(profileProvider),
        ),
        _ => const LoadingState(),
      },
    );
  }
}

class _PeriodButton extends ConsumerWidget {
  const _PeriodButton({required this.days});

  final int days;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () async {
          final picked = await showModalBottomSheet<int>(
            context: context,
            backgroundColor: AppColors.surface,
            builder: (context) => _PeriodSheet(selected: days),
          );
          if (picked != null) {
            ref.read(profilePeriodProvider.notifier).select(picked);
          }
        },
        child: Text(
          '최근 $days일',
          style: AppText.bodySm.copyWith(color: AppColors.textTertiary),
        ),
      ),
    );
  }
}

class _PeriodSheet extends StatelessWidget {
  const _PeriodSheet({required this.selected});

  final int selected;

  @override
  Widget build(BuildContext context) {
    return SafeArea(
      child: Padding(
        padding: const EdgeInsets.symmetric(vertical: 8),
        child: Column(
          mainAxisSize: MainAxisSize.min,
          children: [
            for (final days in profilePeriods)
              InkWell(
                onTap: () => Navigator.pop(context, days),
                child: Padding(
                  padding: const EdgeInsets.symmetric(
                    horizontal: AppSpacing.textMargin,
                    vertical: 14,
                  ),
                  child: Row(
                    children: [
                      Expanded(
                        child: Text('최근 $days일', style: AppText.rowTitle),
                      ),
                      if (days == selected)
                        const AppIcon(
                          'check',
                          size: 18,
                          color: AppColors.primary,
                        ),
                    ],
                  ),
                ),
              ),
          ],
        ),
      ),
    );
  }
}

class _ProfileBody extends StatelessWidget {
  const _ProfileBody({required this.profile});

  final Profile profile;

  @override
  Widget build(BuildContext context) {
    final report = profile.weeklyReportLatest;
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        _UserRow(user: profile.user),
        _StatRow(stats: profile.stats),
        const SectionLabel('반응한 카테고리 · 👍 / 👎'),
        _CategoryCard(reactions: profile.categoryReactions),
        const SectionLabel('학습된 취향'),
        _LearnedCard(learned: profile.learned),
        if (report != null) ...[
          const SectionLabel('주간 리포트'),
          _ReportCard(report: report),
        ],
      ],
    );
  }
}

class _UserRow extends StatelessWidget {
  const _UserRow({required this.user});

  final ProfileUser user;

  @override
  Widget build(BuildContext context) {
    final discord = user.discordConnected ? 'Discord 연결됨' : 'Discord 연결 안 됨';
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 4, 20, 12),
      child: Row(
        spacing: 12,
        children: [
          Container(
            width: 44,
            height: 44,
            alignment: Alignment.center,
            decoration: BoxDecoration(
              color: AppColors.textPrimary,
              borderRadius: BorderRadius.circular(AppRadius.avatar),
            ),
            child: Text(
              user.displayName.characters.firstOrNull ?? '',
              style: AppText.avatar,
            ),
          ),
          Expanded(
            child: Column(
              crossAxisAlignment: CrossAxisAlignment.start,
              children: [
                Text(user.displayName, style: AppText.summaryTitle),
                Text(
                  '$discord · 온보딩 ${user.onboardingDone}/${user.onboardingTotal} 완료',
                  style: AppText.captionMd,
                ),
              ],
            ),
          ),
        ],
      ),
    );
  }
}

class _StatRow extends StatelessWidget {
  const _StatRow({required this.stats});

  final ProfileStats stats;

  @override
  Widget build(BuildContext context) {
    final ratio = stats.usefulRatio;
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.cardMargin),
      child: IntrinsicHeight(
        child: Row(
          crossAxisAlignment: CrossAxisAlignment.stretch,
          spacing: 10,
          children: [
            Expanded(
              child: StatCard(
                label: '받은 알림',
                value: '${stats.alertsReceived}',
                caption:
                    'push ${stats.pushCount} · 실험 ${stats.experimentCount}',
              ),
            ),
            Expanded(
              child: StatCard(
                label: '유용 비율',
                value: ratio == null ? '–' : '$ratio%',
                caption: '👍 ${stats.usefulCount} / 👎 ${stats.notUsefulCount}',
              ),
            ),
            Expanded(
              child: StatCard(
                label: '놓친 이슈',
                value: '${stats.missedIssues}',
                caption: '직접 찾아본 건',
              ),
            ),
          ],
        ),
      ),
    );
  }
}

/// 합계 내림차순. 가장 큰 합계가 트랙 100% 이고 👍·👎 는 그 합계 대비 개수 비율이다.
class _CategoryCard extends StatelessWidget {
  const _CategoryCard({required this.reactions});

  final List<CategoryReaction> reactions;

  @override
  Widget build(BuildContext context) {
    final rows = [...reactions]..sort((a, b) => b.total.compareTo(a.total));
    final maxTotal = rows.isEmpty ? 0 : rows.first.total;
    double fraction(int count) => maxTotal == 0 ? 0 : count / maxTotal;
    return AppCard(
      gap: 10,
      children: [
        if (rows.isEmpty)
          Text('기간 안에 판정한 항목이 없습니다.', style: AppText.captionMd)
        else
          for (final row in rows)
            StackedBar(
              label: row.category,
              usefulFraction: fraction(row.useful),
              notUsefulFraction: fraction(row.notUseful),
              total: row.total,
            ),
      ],
    );
  }
}

class _LearnedCard extends StatelessWidget {
  const _LearnedCard({required this.learned});

  final Learned learned;

  static final TextStyle _value = AppText.bodySm.copyWith(
    fontWeight: FontWeight.w600,
  );

  /// 디자인 문구 `서베이·전망 논문` — survey 만 대상(논문)을 붙이고 나머지는 kind 라벨 그대로.
  static String _penaltyLabel(Kind kind) =>
      kind == Kind.survey ? '${kind.label} 논문' : kind.label;

  /// 표시명이 따로 있으면 `arXiv cs.CL 신뢰도`, id 그대로면 `youtube:codingapple` (디자인 문구).
  static String _trustLabel(SourceTrustChange change) =>
      change.sourceName == change.sourceId
      ? change.sourceName
      : '${change.sourceName} 신뢰도';

  @override
  Widget build(BuildContext context) {
    return AppCard(
      gap: 10,
      children: [
        for (final penalty in learned.kindPenalties)
          _LearnedRow(
            label: _penaltyLabel(penalty.kind),
            value: TextSpan(
              text:
                  '👎 ${penalty.notUseful} / ${penalty.total}'
                  '${penalty.active ? ' → 자동 감점 중' : ''}',
              style: penalty.active
                  ? _value.copyWith(color: AppColors.warn)
                  : _value,
            ),
          ),
        for (final change in learned.sourceTrustChanges)
          _LearnedRow(
            label: _trustLabel(change),
            value: TextSpan(
              text:
                  '${change.from.toStringAsFixed(2)} → '
                  '${change.to.toStringAsFixed(2)}',
              style: AppText.mono(_value),
            ),
          ),
        _LearnedRow(
          label: '프로필 벡터 라벨',
          value: TextSpan(
            text: '${learned.profileVectorLabels}건 ',
            style: _value,
            children: [
              TextSpan(
                text: '(개인 모델 전환 ${learned.personalModelThreshold}건)',
                style: _value.copyWith(
                  fontWeight: FontWeight.w500,
                  color: AppColors.textTertiary,
                ),
              ),
            ],
          ),
        ),
      ],
    );
  }
}

class _LearnedRow extends StatelessWidget {
  const _LearnedRow({required this.label, required this.value});

  final String label;
  final InlineSpan value;

  @override
  Widget build(BuildContext context) {
    return Row(
      spacing: 12,
      children: [
        Expanded(
          child: Text(
            label,
            style: AppText.bodySm.copyWith(color: AppColors.textSecondary),
          ),
        ),
        Text.rich(value, textAlign: TextAlign.right),
      ],
    );
  }
}

class _ReportCard extends StatelessWidget {
  const _ReportCard({required this.report});

  final ReportSummary report;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      child: GestureDetector(
        behavior: HitTestBehavior.opaque,
        onTap: () => context.go(AppRoutes.report(report.id)),
        child: AppCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 14),
          children: [
            Row(
              children: [
                Expanded(
                  child: Column(
                    crossAxisAlignment: CrossAxisAlignment.start,
                    children: [
                      Text(report.title, style: AppText.labelStrong),
                      Text(report.subtitle, style: AppText.captionMd),
                    ],
                  ),
                ),
                const AppIcon('chev', size: 18, color: AppColors.chevron),
              ],
            ),
          ],
        ),
      ),
    );
  }
}
