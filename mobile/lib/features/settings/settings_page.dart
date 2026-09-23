// 설정 루트 (디자인 없음) — 하위 화면 세 줄과 요약, 표시 이름 편집(PATCH /profile), 앱 버전.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:go_router/go_router.dart';

import '../../app/routes.dart';
import '../../core/api/api_exception.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/repositories/repository_providers.dart';
import 'settings_providers.dart';
import 'settings_sheets.dart';

/// 요약을 아직 못 읽었거나 실패했을 때의 값.
const String _missing = '–';

class SettingsPage extends ConsumerWidget {
  const SettingsPage({super.key});

  static const int displayNameMaxLength = 20;

  /// 하위 화면에서 돌아오면 그 화면이 바꾼 값을 다시 읽는다.
  Future<void> _open(
    BuildContext context,
    WidgetRef ref,
    String location,
  ) async {
    await context.push(location);
    ref
      ..invalidate(categorySummaryProvider)
      ..invalidate(pushCapSummaryProvider)
      ..invalidate(sourceSummaryProvider);
  }

  Future<void> _editDisplayName(
    BuildContext context,
    WidgetRef ref,
    String current,
  ) => showTextInputDialog(
    context,
    title: '표시 이름',
    initialValue: current,
    maxLength: displayNameMaxLength,
    confirmLabel: '저장',
    onSubmit: (input) async {
      final name = input.trim();
      if (name.isEmpty) return '표시 이름을 입력하세요.';
      try {
        await ref.read(profileRepositoryProvider).updateDisplayName(name);
      } on ApiException catch (e) {
        return e.message;
      }
      ref.invalidate(displayNameProvider);
      return null;
    },
  );

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final categories = ref.watch(categorySummaryProvider).value;
    final pushCap = ref.watch(pushCapSummaryProvider).value;
    final sources = ref.watch(sourceSummaryProvider).value;
    final displayName = ref.watch(displayNameProvider).value;
    final version = ref.watch(appVersionProvider).value;

    return Scaffold(
      appBar: const RootTopBar(title: '설정'),
      body: ListView(
        padding: const EdgeInsets.only(top: 8, bottom: 24),
        children: [
          AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            gap: 0,
            children: [
              ValueRow(
                title: '관심사',
                subtitle: categories == null
                    ? null
                    : '카테고리 ${categories.selected}/${categories.total}',
                value: '',
                onTap: () => _open(context, ref, AppRoutes.interests),
              ),
              ValueRow(
                title: '알림 설정',
                subtitle: pushCap == null ? null : '하루 push 상한 $pushCap건',
                value: '',
                onTap: () => _open(context, ref, AppRoutes.notifications),
              ),
              ValueRow(
                title: '수집 소스',
                subtitle: sources == null
                    ? null
                    : '활성 소스 ${sources.enabledCount}/${sources.total}',
                value: '',
                isLast: true,
                onTap: () => _open(context, ref, AppRoutes.sources),
              ),
            ],
          ),
          const SectionLabel('계정'),
          AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            gap: 0,
            children: [
              ValueRow(
                title: '표시 이름',
                value: displayName ?? _missing,
                isLast: true,
                onTap: displayName == null
                    ? null
                    : () => _editDisplayName(context, ref, displayName),
              ),
            ],
          ),
          const SectionLabel('앱 정보'),
          AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            gap: 0,
            children: [
              SettingRow(
                title: '앱 버전',
                isLast: true,
                trailing: Text(
                  version ?? _missing,
                  style: AppText.mono(AppText.bodyMd),
                ),
              ),
            ],
          ),
        ],
      ),
    );
  }
}
