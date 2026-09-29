// 03 FeedCard — 실험 헤더·메타·제목·요약·#slug 태그와 원문·찜·유용/불필요 액션 행.
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/routes.dart';
import '../../core/format.dart';
import '../../core/icons.dart';
import '../../core/launch.dart';
import '../../core/providers.dart';
import '../../core/snack.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import '../alert/alert_providers.dart';

class FeedCard extends ConsumerWidget {
  const FeedCard({super.key, required this.alert});

  final Alert alert;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final user = watchAlertUserState(ref, alert);
    final actions = ref.read(alertUserStatesProvider.notifier);
    final deliveredAt = alert.deliveredAt;
    final meta = [
      alert.sourceName,
      if (deliveredAt != null)
        relativeTime(deliveredAt, now: ref.watch(clockProvider)()),
    ].join(' · ');

    return AppCard(
      gap: 10,
      children: [
        if (alert.isExploration)
          Row(
            spacing: 6,
            children: [
              const AppIcon('flask', size: 14, color: AppColors.warn),
              Text(
                '실험 · 경계 항목',
                style: AppText.captionStrong.copyWith(color: AppColors.warn),
              ),
            ],
          ),
        Row(
          spacing: 8,
          children: [
            Expanded(child: Text(meta, style: AppText.captionMd)),
            if (alert.deliveryMode case final mode?) DeliveryBadge(mode),
          ],
        ),
        GestureDetector(
          onTap: () => context.push(AppRoutes.alert(alert.id)),
          behavior: HitTestBehavior.opaque,
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.stretch,
            spacing: 10,
            children: [
              Text(alert.title, style: AppText.titleCard),
              if (alert.summary.isNotEmpty)
                Text(alert.summary, style: AppText.bodySummary),
            ],
          ),
        ),
        if (alert.categories.isNotEmpty)
          Wrap(
            spacing: 8,
            runSpacing: 4,
            children: [
              for (final slug in alert.categories)
                Text(
                  '#$slug',
                  style: AppText.captionMd.copyWith(color: AppColors.primary),
                ),
            ],
          ),
        Row(
          spacing: 8,
          children: [
            OpenButton(
              label: '원문',
              onTap: () => openExternal(context, alert.url),
            ),
            BookmarkButton(
              saved: user.isSaved,
              onTap: () => runOrSnack(
                context,
                () => actions.setSaved(alert, saved: !user.isSaved),
              ),
            ),
            Expanded(
              child: FeedbackButtons(
                value: user.feedback,
                onChanged: (verdict) => runOrSnack(
                  context,
                  () => actions.setFeedback(alert, verdict),
                ),
              ),
            ),
          ],
        ),
      ],
    );
  }
}
