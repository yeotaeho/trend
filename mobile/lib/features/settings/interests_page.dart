// 04 관심사 — 프로필 문장·카테고리·키워드·kind 가중치를 로컬에서 고치고 헤더 `저장` 한 번으로 PUT 한다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/format.dart';
import '../../core/icons.dart';
import '../../core/labels.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';
import 'interests_draft.dart';
import 'settings_providers.dart';
import 'settings_sheets.dart';

class InterestsPage extends ConsumerStatefulWidget {
  const InterestsPage({super.key});

  @override
  ConsumerState<InterestsPage> createState() => _InterestsPageState();
}

class _InterestsPageState extends ConsumerState<InterestsPage> {
  InterestsDraft? _draft;
  Meta? _meta;
  Object? _loadError;
  bool _saving = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _loadError = null);
    try {
      final interests = await ref.read(settingsRepositoryProvider).interests();
      final meta = await ref.read(metaProvider.future);
      if (!mounted) return;
      setState(() {
        _meta = meta;
        _draft = _draftFrom(interests, meta);
      });
    } on Object catch (e) {
      if (mounted) setState(() => _loadError = e);
    }
  }

  InterestsDraft _draftFrom(InterestsSettings settings, Meta meta) =>
      InterestsDraft(
        settings,
        taxonomy: [for (final t in meta.taxonomy) t.slug],
        keywordsMax: meta.limits.watchKeywordsMax,
      );

  void _edit(void Function(InterestsDraft draft) change) =>
      setState(() => change(_draft!));

  void _snack(String message) => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));

  Future<void> _save() async {
    setState(() => _saving = true);
    try {
      final saved = await ref
          .read(settingsRepositoryProvider)
          .saveInterests(_draft!.toSettings());
      if (!mounted) return;
      setState(() => _draft = _draftFrom(saved, _meta!));
      ref.invalidate(categorySummaryProvider);
      _snack('저장했습니다.');
    } on ApiException catch (e) {
      if (mounted) _snack(e.message);
    } finally {
      if (mounted) setState(() => _saving = false);
    }
  }

  Future<void> _confirmLeave() async {
    final leave = await showConfirmDialog(
      context,
      title: '저장하지 않고 나갈까요?',
      message: '바꾼 내용이 사라집니다.',
      confirmLabel: '나가기',
    );
    if (leave && mounted) Navigator.of(context).pop();
  }

  Future<void> _editProfile() async {
    final draft = _draft!;
    final result = await showProfileEditSheet(
      context,
      selfDescription: draft.selfDescription,
      notInterested: draft.notInterested,
    );
    if (result == null) return;
    _edit((d) {
      d.selfDescription = result.selfDescription;
      d.notInterested = result.notInterested;
    });
  }

  Future<void> _addKeyword() => showTextInputDialog(
    context,
    title: '키워드 추가',
    hint: '스택·저장소 (owner/repo)',
    maxLength: InterestsDraft.keywordMaxLength,
    confirmLabel: '추가',
    onSubmit: (input) async {
      final error = _draft!.addKeyword(input);
      if (error == null) setState(() {});
      return error;
    },
  );

  Future<void> _removeKeyword(String keyword) async {
    final remove = await showConfirmDialog(
      context,
      title: '키워드 삭제',
      message: '‘$keyword’ 을(를) 목록에서 뺄까요?',
      confirmLabel: '삭제',
    );
    if (remove) _edit((d) => d.removeKeyword(keyword));
  }

  Future<void> _editWeight(Kind kind) async {
    final range = _meta!.limits.kindWeight;
    final value = await showWeightEditSheet(
      context,
      kind: kind,
      value: _draft!.weightOf(kind),
      range: range,
    );
    if (value != null) _edit((d) => d.setWeight(kind, value));
  }

  @override
  Widget build(BuildContext context) {
    final draft = _draft;
    return PopScope(
      canPop: !(draft?.isDirty ?? false),
      onPopInvokedWithResult: (didPop, _) {
        if (!didPop) _confirmLeave();
      },
      child: Scaffold(
        appBar: SubTopBar(
          title: '관심사',
          actions: [
            AccentTextButton(
              label: '저장',
              onTap: draft != null && draft.canSave && !_saving ? _save : null,
            ),
          ],
        ),
        body: switch ((draft, _loadError)) {
          (final InterestsDraft draft, _) => _body(draft),
          (_, final Object error) => ErrorState(
            message: error is ApiException ? error.message : '관심사를 불러오지 못했습니다.',
            onRetry: _load,
          ),
          _ => const LoadingState(),
        },
      ),
    );
  }

  Widget _body(InterestsDraft draft) {
    final taxonomy = _meta!.taxonomy;
    final selected = draft.selectedCategories.length;
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        const SectionLabel('나를 한 줄로 (선별 프롬프트에 그대로 들어갑니다)'),
        GestureDetector(
          onTap: _editProfile,
          behavior: HitTestBehavior.opaque,
          child: AppCard(
            children: [
              Text(draft.selfDescription, style: AppText.bodyProfile),
              Text('관심 없음: ${draft.notInterested}', style: AppText.captionMd),
            ],
          ),
        ),
        SectionLabel('카테고리 · $selected / ${taxonomy.length} 선택'),
        _TaxonomyGrid(
          taxonomy: taxonomy,
          isSelected: draft.isSelected,
          onToggle: (slug) => _edit((d) => d.toggleCategory(slug)),
        ),
        const SectionLabel('주목 스택 · 저장소'),
        Padding(
          padding: const EdgeInsets.symmetric(
            horizontal: AppSpacing.cardMargin,
          ),
          child: Wrap(
            spacing: AppSpacing.chipGap,
            runSpacing: AppSpacing.chipGap,
            children: [
              for (final keyword in draft.watchKeywords)
                GestureDetector(
                  key: ValueKey('keyword-$keyword'),
                  onLongPress: () => _removeKeyword(keyword),
                  child: AppChip(label: keyword),
                ),
              AppChip(label: '+ 추가', onTap: _addKeyword),
            ],
          ),
        ),
        const SectionLabel('변화 종류별 가중치 (kind)'),
        AppCard(
          padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
          gap: 0,
          children: [
            for (final (index, kind) in editableKinds.indexed)
              _KindWeightRow(
                kind: kind,
                weight: draft.weightOf(kind),
                isLast: index == editableKinds.length - 1,
                onTap: () => _editWeight(kind),
              ),
          ],
        ),
      ],
    );
  }
}

/// 2열 격자. 한 줄의 두 셀은 높이를 맞춘다 (CSS grid 의 stretch).
class _TaxonomyGrid extends StatelessWidget {
  const _TaxonomyGrid({
    required this.taxonomy,
    required this.isSelected,
    required this.onToggle,
  });

  final List<TaxonomyEntry> taxonomy;
  final bool Function(String slug) isSelected;
  final ValueChanged<String> onToggle;

  @override
  Widget build(BuildContext context) {
    Widget cell(TaxonomyEntry entry) => TaxonomyCell(
      entry: entry,
      selected: isSelected(entry.slug),
      onTap: () => onToggle(entry.slug),
    );
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.cardMargin),
      child: Column(
        spacing: 8,
        children: [
          for (var i = 0; i < taxonomy.length; i += 2)
            IntrinsicHeight(
              child: Row(
                crossAxisAlignment: CrossAxisAlignment.stretch,
                spacing: 8,
                children: [
                  Expanded(child: cell(taxonomy[i])),
                  Expanded(
                    child: i + 1 < taxonomy.length
                        ? cell(taxonomy[i + 1])
                        : const SizedBox.shrink(),
                  ),
                ],
              ),
            ),
        ],
      ),
    );
  }
}

/// 택소노미 셀 — 라벨 14/600 + slug 11 mono, 우측 18×18 체크 원.
class TaxonomyCell extends StatelessWidget {
  const TaxonomyCell({
    super.key,
    required this.entry,
    required this.selected,
    this.onTap,
  });

  final TaxonomyEntry entry;
  final bool selected;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      button: true,
      selected: selected,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          key: ValueKey('taxonomy-${entry.slug}'),
          padding: const EdgeInsets.symmetric(horizontal: 14, vertical: 12),
          decoration: BoxDecoration(
            color: selected ? AppColors.textPrimary : AppColors.surface,
            border: Border.all(
              color: selected ? AppColors.textPrimary : AppColors.borderControl,
            ),
            borderRadius: BorderRadius.circular(AppRadius.taxonomyCell),
          ),
          child: Row(
            spacing: 8,
            children: [
              Expanded(
                child: Column(
                  crossAxisAlignment: CrossAxisAlignment.start,
                  mainAxisAlignment: MainAxisAlignment.center,
                  children: [
                    Text(
                      entry.label,
                      style: AppText.labelStrong.copyWith(
                        color: selected
                            ? AppColors.textInverse
                            : AppColors.textPrimary,
                      ),
                    ),
                    Text(
                      entry.slug,
                      style: AppText.slug.copyWith(
                        color: selected
                            ? AppColors.chevron
                            : AppColors.textTertiary,
                      ),
                    ),
                  ],
                ),
              ),
              Container(
                width: 18,
                height: 18,
                alignment: Alignment.center,
                decoration: BoxDecoration(
                  color: selected ? AppColors.primary : null,
                  border: selected
                      ? null
                      : Border.all(color: AppColors.borderControl, width: 1.5),
                  borderRadius: BorderRadius.circular(AppRadius.checkCircle),
                ),
                child: selected
                    ? const AppIcon(
                        'check',
                        size: 12,
                        color: AppColors.textInverse,
                      )
                    : null,
              ),
            ],
          ),
        ),
      ),
    );
  }
}

/// kind 가중치 행 — 값 14 mono (음수 경고색) + chevron.
class _KindWeightRow extends StatelessWidget {
  const _KindWeightRow({
    required this.kind,
    required this.weight,
    required this.isLast,
    required this.onTap,
  });

  final Kind kind;
  final double weight;
  final bool isLast;
  final VoidCallback onTap;

  @override
  Widget build(BuildContext context) {
    return SettingRow(
      key: ValueKey('kind-${kind.value}'),
      title: kind.label,
      subtitle: kind.value,
      isLast: isLast,
      onTap: onTap,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        spacing: 6,
        children: [
          Text(
            formatSignedScore(weight),
            style: AppText.mono(AppText.bodyMd).copyWith(
              color: roundWeight(weight) < 0
                  ? AppColors.warn
                  : AppColors.textSecondary,
            ),
          ),
          const AppIcon('chev', size: 16, color: AppColors.chevron),
        ],
      ),
    );
  }
}
