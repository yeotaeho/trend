// 설정 이력 (디자인 없음) — 저장마다 남은 이력과 바뀐 키, `이 버전으로 되돌리기`(POST /settings/revisions/{id}/restore).
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/api/api_exception.dart';
import '../../core/format.dart';
import '../../core/labels.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';
import 'settings_sheets.dart';

class SettingsHistoryPage extends ConsumerStatefulWidget {
  const SettingsHistoryPage({super.key});

  @override
  ConsumerState<SettingsHistoryPage> createState() =>
      _SettingsHistoryPageState();
}

class _SettingsHistoryPageState extends ConsumerState<SettingsHistoryPage> {
  List<SettingsRevision>? _items;
  String? _next;

  /// 점 경로 → 한국어 라벨 (GET /settings). 못 읽으면 키를 그대로 보인다.
  Map<String, String> _labels = const {};
  Object? _error;
  bool _busy = false;

  @override
  void initState() {
    super.initState();
    _load();
  }

  Future<void> _load() async {
    setState(() => _error = null);
    final repository = ref.read(settingsHistoryRepositoryProvider);
    try {
      final page = await repository.revisions();
      final overview = await repository.overview();
      if (!mounted) return;
      setState(() {
        _items = page.items;
        _next = page.nextCursor;
        _labels = {for (final item in overview.items) item.key: item.label};
      });
    } on Object catch (e) {
      if (mounted) setState(() => _error = e);
    }
  }

  Future<void> _more() async {
    setState(() => _busy = true);
    try {
      final page = await ref
          .read(settingsHistoryRepositoryProvider)
          .revisions(cursor: _next);
      if (!mounted) return;
      setState(() {
        _items = [...?_items, ...page.items];
        _next = page.nextCursor;
      });
    } on ApiException catch (e) {
      if (mounted) _snack(e.message);
    } finally {
      if (mounted) setState(() => _busy = false);
    }
  }

  void _snack(String message) => ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));

  Future<void> _restore(SettingsRevision revision) async {
    final ok = await showConfirmDialog(
      context,
      title: '#${revision.id} 저장 뒤 상태로 되돌릴까요?',
      message:
          '앱 설정만 되돌립니다. 이미 걸러진 항목(FILTERED_OUT), 피드로만 닫힌 항목, '
          '이미 매긴 점수는 돌아오지 않습니다.',
      confirmLabel: '되돌리기',
    );
    if (!ok || !mounted) return;
    final RevisionRestore result;
    try {
      result = await ref
          .read(settingsHistoryRepositoryProvider)
          .restoreRevision(revision.id);
    } on ApiException catch (e) {
      if (mounted) _snack(e.message);
      return;
    }
    if (!mounted) return;
    _snack(
      result.dropped.isEmpty
          ? '되돌렸습니다.'
          : '되돌렸습니다. 지금은 바꿀 수 없는 키는 뺐습니다: ${result.dropped.join(', ')}',
    );
    await _load();
  }

  @override
  Widget build(BuildContext context) {
    final items = _items;
    return Scaffold(
      appBar: const SubTopBar(title: '설정 이력'),
      body: switch ((items, _error)) {
        (final List<SettingsRevision> items, _) when items.isEmpty =>
          const EmptyState(message: '아직 저장한 설정이 없습니다.'),
        (final List<SettingsRevision> items, _) => ListView(
          padding: const EdgeInsets.only(top: 8, bottom: 24),
          children: [
            for (final (index, revision) in items.indexed)
              _RevisionCard(
                revision: revision,
                labels: _labels,
                // 맨 위는 지금 상태라 되돌릴 것이 없다.
                onRestore: index == 0 ? null : () => _restore(revision),
              ),
            if (_next != null)
              Center(
                child: AccentTextButton(
                  label: '더 보기',
                  onTap: _busy ? null : _more,
                ),
              ),
          ],
        ),
        (_, final Object error) => ErrorState(
          message: error is ApiException ? error.message : '이력을 불러오지 못했습니다.',
          onRetry: _load,
        ),
        _ => const LoadingState(),
      },
    );
  }
}

/// 저장 한 건 — `#id · 길`, 시각, 메모, 바뀐 키(이전 → 이후), `이 버전으로 되돌리기`.
class _RevisionCard extends StatelessWidget {
  const _RevisionCard({
    required this.revision,
    required this.labels,
    this.onRestore,
  });

  final SettingsRevision revision;
  final Map<String, String> labels;
  final VoidCallback? onRestore;

  @override
  Widget build(BuildContext context) {
    final onRestore = this.onRestore;
    return AppCard(
      key: ValueKey('revision-${revision.id}'),
      children: [
        Row(
          children: [
            Expanded(
              child: Text(
                '#${revision.id} · ${revisionOriginLabel(revision.origin)}',
                style: AppText.labelStrong,
              ),
            ),
            Text(relativeTime(revision.createdAt), style: AppText.captionMd),
          ],
        ),
        if (revision.note case final note?)
          Text(note, style: AppText.captionMd),
        if (revision.changes.isEmpty)
          Text('바뀐 값 없음', style: AppText.captionMd)
        else
          for (final change in revision.changes)
            Text(
              '${labels[change.key] ?? change.key}: '
              '${formatSettingValue(change.old)} → ${formatSettingValue(change.newValue)}',
              style: AppText.bodyMd,
            ),
        if (onRestore != null)
          Align(
            alignment: Alignment.centerRight,
            child: AccentTextButton(
              key: ValueKey('restore-${revision.id}'),
              label: '이 버전으로 되돌리기',
              onTap: onRestore,
            ),
          ),
      ],
    );
  }
}
