// 전체 설정 (디자인 없음) — GET /settings 를 분류별 읽기 전용 색인으로. 앱 소유는 04·05·06 으로, YAML 소유는 GitHub 로 간다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/routes.dart';
import '../../core/api/api_exception.dart';
import '../../core/format.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/launch.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

final settingsOverviewProvider = FutureProvider.autoDispose<SettingsOverview>(
  (ref) => ref.watch(settingsHistoryRepositoryProvider).overview(),
);

const EdgeInsets _rowCardPadding = EdgeInsets.symmetric(
  horizontal: 16,
  vertical: 4,
);

class AllSettingsPage extends ConsumerWidget {
  const AllSettingsPage({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final overview = ref.watch(settingsOverviewProvider);
    return Scaffold(
      appBar: const SubTopBar(title: '전체 설정'),
      body: switch (overview) {
        AsyncData(:final value) => _Body(overview: value),
        AsyncError(:final error) => ErrorState(
          message: error is ApiException ? error.message : '설정을 불러오지 못했습니다.',
          onRetry: () => ref.invalidate(settingsOverviewProvider),
        ),
        _ => const LoadingState(),
      },
    );
  }
}

class _Body extends ConsumerWidget {
  const _Body({required this.overview});

  final SettingsOverview overview;

  /// 앱 소유 키는 그 키를 고치는 화면으로, YAML 소유 키는 GitHub 편집 화면으로 간다. 서버 키는 VM 에서만 바꾼다.
  Future<void> _open(
    BuildContext context,
    WidgetRef ref,
    SettingItem item,
  ) async {
    if (item.owner == 'app') {
      final route = switch (item.category) {
        'notify' => AppRoutes.notifications,
        'sources' => AppRoutes.sources,
        _ => AppRoutes.interests,
      };
      await context.push(route);
      // 그 화면에서 바꾼 값을 다시 읽는다.
      if (context.mounted) ref.invalidate(settingsOverviewProvider);
    } else if (item.editUrl case final url?) {
      await openExternal(context, url, failMessage: '편집 화면을 열 수 없습니다.');
    }
  }

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final blocked = [
      for (final reason in DeliveryBlocked.values)
        if (overview.deliveryBlocked.contains(reason.value)) reason,
    ];
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        if (blocked.isNotEmpty)
          Padding(
            padding: const EdgeInsets.only(top: 12),
            child: AppCard(
              children: [
                for (final reason in blocked)
                  Text(
                    reason.label,
                    style: AppText.captionMd.copyWith(color: AppColors.warn),
                  ),
              ],
            ),
          ),
        const SizedBox(height: 8),
        AppCard(
          padding: _rowCardPadding,
          gap: 0,
          children: [
            SettingRow(
              title: '마지막 저장',
              trailing: Text(
                overview.revision == null ? '없음' : '#${overview.revision}',
                style: AppText.mono(AppText.bodyMd),
              ),
            ),
            SettingRow(
              title: '배포 커밋',
              trailing: Text(switch (overview.gitSha) {
                null => '로컬',
                final sha when sha.length > 7 => sha.substring(0, 7),
                final sha => sha,
              }, style: AppText.mono(AppText.bodyMd)),
            ),
            ValueRow(
              title: '설정 이력',
              subtitle: '저장 기록과 버전 되돌리기',
              value: '',
              isLast: true,
              onTap: () => context.push(AppRoutes.settingsHistory),
            ),
          ],
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 12, 20, 0),
          child: Text(
            '운영 알림(장애·예산 소진)은 이 설정과 상관없이 항상 디스코드로 갑니다.',
            style: AppText.captionMd,
          ),
        ),
        for (final category in SettingCategory.values)
          ..._section(context, ref, category),
      ],
    );
  }

  List<Widget> _section(
    BuildContext context,
    WidgetRef ref,
    SettingCategory category,
  ) {
    final items = [
      for (final item in overview.items)
        if (item.category == category.value) item,
    ];
    if (items.isEmpty) return const [];
    return [
      SectionLabel(category.label),
      AppCard(
        padding: _rowCardPadding,
        gap: 0,
        children: [
          for (final (index, item) in items.indexed)
            _ItemRow(
              item: item,
              isLast: index == items.length - 1,
              onTap: item.owner == 'server'
                  ? null
                  : () => _open(context, ref, item),
            ),
        ],
      ),
    ];
  }
}

/// 키 한 줄 — 라벨, 반영 시점·기본값, 앱 값 배지와 값.
class _ItemRow extends StatelessWidget {
  const _ItemRow({required this.item, required this.isLast, this.onTap});

  final SettingItem item;
  final bool isLast;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final app = item.source == 'app';
    final subtitle = [
      settingApplyLabel(item.apply),
      if (app) '기본 ${formatSettingValue(item.defaultValue)}',
      if (item.defaultChanged) '앱 값이 바뀐 기본값을 가림',
    ].join(' · ');
    return SettingRow(
      key: ValueKey('setting-${item.key}'),
      title: item.label,
      subtitle: subtitle,
      isLast: isLast,
      onTap: onTap,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        spacing: 6,
        children: [
          if (app)
            const AppBadge(
              label: '앱 값',
              background: AppColors.primarySoft,
              foreground: AppColors.primary,
            ),
          ConstrainedBox(
            constraints: const BoxConstraints(maxWidth: 120),
            child: Text(
              formatSettingValue(item.value),
              style: AppText.bodyMd,
              overflow: TextOverflow.ellipsis,
            ),
          ),
          if (onTap != null)
            const AppIcon('chev', size: 16, color: AppColors.chevron),
        ],
      ),
    );
  }
}
