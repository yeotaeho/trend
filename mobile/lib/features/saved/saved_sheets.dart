// 11 찜 시트·다이얼로그 — 정렬, 폴더 이동, 메모 편집, 폴더 이름(새 폴더·이름 변경), 폴더 관리 (모두 디자인 없음).
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
import 'saved_controller.dart';

/// 스낵바·다이얼로그에 보일 문장. 서버 오류는 `message` 를 그대로 쓴다 (계약 1.4).
String errorMessage(Object error) =>
    error is ApiException ? error.message : '요청을 처리하지 못했습니다.';

Future<T?> _showSheet<T>(
  BuildContext context, {
  required String title,
  required Widget child,
}) {
  return showModalBottomSheet<T>(
    context: context,
    useRootNavigator: true,
    isScrollControlled: true,
    backgroundColor: AppColors.canvas,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
    ),
    builder: (context) => _SheetFrame(title: title, child: child),
  );
}

class _SheetFrame extends StatelessWidget {
  const _SheetFrame({required this.title, required this.child});

  final String title;
  final Widget child;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(
        child: Column(
          mainAxisSize: MainAxisSize.min,
          crossAxisAlignment: CrossAxisAlignment.stretch,
          children: [
            Padding(
              padding: const EdgeInsets.fromLTRB(20, 20, 20, 12),
              child: Text(title, style: AppText.titleCard),
            ),
            Flexible(child: child),
            const SizedBox(height: 16),
          ],
        ),
      ),
    );
  }
}

/// 시트 안 행 목록 카드 (`4px 16px`).
class _RowCard extends StatelessWidget {
  const _RowCard({required this.children});

  final List<Widget> children;

  @override
  Widget build(BuildContext context) {
    return AppCard(
      padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
      gap: 0,
      children: children,
    );
  }
}

Widget _check(bool selected) => selected
    ? const AppIcon('check', size: 18, color: AppColors.primary)
    : const SizedBox.square(dimension: 18);

// ── 정렬 ──

Future<SavedSort?> showSortSheet(BuildContext context, SavedSort current) {
  return _showSheet(
    context,
    title: '정렬',
    child: Builder(
      builder: (context) => _RowCard(
        children: [
          for (final (i, sort) in SavedSort.values.indexed)
            SettingRow(
              title: sort.label,
              trailing: _check(sort == current),
              isLast: i == SavedSort.values.length - 1,
              onTap: () => Navigator.pop(context, sort),
            ),
        ],
      ),
    ),
  );
}

// ── 폴더 이동 ──

/// 폴더 이동 시트의 선택. [create] 면 새 폴더를 만들어 옮긴다.
class FolderPick {
  const FolderPick.folder(this.folder) : create = false;
  const FolderPick.create() : folder = null, create = true;

  /// `null` 이면 미분류.
  final FolderRef? folder;
  final bool create;
}

Future<FolderPick?> showFolderMoveSheet(
  BuildContext context, {
  required List<Folder> folders,
  required FolderRef? current,
}) {
  return _showSheet(
    context,
    title: '폴더 이동',
    child: Builder(
      builder: (context) {
        void pick(FolderPick value) => Navigator.pop(context, value);
        return SingleChildScrollView(
          child: _RowCard(
            children: [
              for (final folder in folders)
                SettingRow(
                  title: folder.name,
                  trailing: _check(folder.id == current?.id),
                  onTap: () => pick(FolderPick.folder(folder.ref)),
                ),
              SettingRow(
                title: '미분류',
                trailing: _check(current == null),
                onTap: () => pick(const FolderPick.folder(null)),
              ),
              SettingRow(
                title: '새 폴더',
                trailing: const AppIcon(
                  'plus',
                  size: 18,
                  color: AppColors.primary,
                ),
                isLast: true,
                onTap: () => pick(const FolderPick.create()),
              ),
            ],
          ),
        );
      },
    ),
  );
}

// ── 메모 ──

/// 저장하면 입력한 문장을, 닫으면 `null` 을 돌려준다. 빈 문장은 메모 삭제다.
Future<String?> showMemoSheet(
  BuildContext context, {
  required String? initial,
  required int maxLength,
}) {
  return _showSheet(
    context,
    title: '메모',
    child: _MemoEditor(initial: initial ?? '', maxLength: maxLength),
  );
}

class _MemoEditor extends StatefulWidget {
  const _MemoEditor({required this.initial, required this.maxLength});

  final String initial;
  final int maxLength;

  @override
  State<_MemoEditor> createState() => _MemoEditorState();
}

class _MemoEditorState extends State<_MemoEditor> {
  late final _controller = TextEditingController(text: widget.initial);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.symmetric(horizontal: AppSpacing.cardMargin),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: 12,
        children: [
          TextField(
            controller: _controller,
            autofocus: true,
            minLines: 3,
            maxLines: 6,
            maxLength: widget.maxLength,
            style: AppText.bodySm,
            decoration: _inputDecoration(hint: '메모를 남겨 두세요. 비우면 메모가 지워집니다.'),
          ),
          Align(
            alignment: Alignment.centerRight,
            child: AccentTextButton(
              label: '저장',
              onTap: () => Navigator.pop(context, _controller.text),
            ),
          ),
        ],
      ),
    );
  }
}

// ── 폴더 이름 ──

/// 새 폴더·이름 변경 다이얼로그. [submit] 이 끝나야 닫히고, 실패하면 (이름 중복 409 등)
/// 오류 문장을 입력칸 아래에 보인 채 머문다. 취소하면 `null`.
Future<T?> showFolderNameDialog<T>(
  BuildContext context, {
  required String title,
  required int maxLength,
  required Future<T> Function(String name) submit,
  String initial = '',
}) {
  return showDialog<T>(
    context: context,
    useRootNavigator: true,
    builder: (context) => _FolderNameDialog<T>(
      title: title,
      initial: initial,
      maxLength: maxLength,
      submit: submit,
    ),
  );
}

class _FolderNameDialog<T> extends StatefulWidget {
  const _FolderNameDialog({
    required this.title,
    required this.initial,
    required this.maxLength,
    required this.submit,
  });

  final String title;
  final String initial;
  final int maxLength;
  final Future<T> Function(String name) submit;

  @override
  State<_FolderNameDialog<T>> createState() => _FolderNameDialogState<T>();
}

class _FolderNameDialogState<T> extends State<_FolderNameDialog<T>> {
  late final _controller = TextEditingController(text: widget.initial);
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  String get _name => _controller.text.trim();

  bool get _valid => _name.isNotEmpty && _name.length <= widget.maxLength;

  Future<void> _submit() async {
    if (!_valid || _busy) return;
    setState(() {
      _busy = true;
      _error = null;
    });
    try {
      final result = await widget.submit(_name);
      if (mounted) Navigator.pop(context, result);
    } catch (e) {
      if (mounted) {
        setState(() {
          _busy = false;
          _error = errorMessage(e);
        });
      }
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      title: Text(widget.title, style: AppText.titleCard),
      content: TextField(
        controller: _controller,
        autofocus: true,
        maxLength: widget.maxLength,
        style: AppText.bodySm,
        textInputAction: TextInputAction.done,
        onChanged: (_) => setState(() => _error = null),
        onSubmitted: (_) => _submit(),
        decoration: _inputDecoration(
          hint: '폴더 이름 (1~${widget.maxLength}자)',
          error: _error,
        ),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context),
          child: Text(
            '취소',
            style: AppText.labelStrong.copyWith(color: AppColors.textTertiary),
          ),
        ),
        AccentTextButton(label: '확인', onTap: _valid && !_busy ? _submit : null),
      ],
    );
  }
}

InputDecoration _inputDecoration({required String hint, String? error}) {
  OutlineInputBorder border(Color color) => OutlineInputBorder(
    borderRadius: BorderRadius.circular(AppRadius.button),
    borderSide: BorderSide(color: color),
  );
  return InputDecoration(
    hintText: hint,
    hintStyle: AppText.bodySm.copyWith(color: AppColors.textTertiary),
    errorText: error,
    errorStyle: AppText.captionMd.copyWith(color: AppColors.error),
    counterStyle: AppText.captionSm,
    filled: true,
    fillColor: AppColors.surface,
    contentPadding: const EdgeInsets.symmetric(horizontal: 12, vertical: 10),
    enabledBorder: border(AppColors.borderControl),
    focusedBorder: border(AppColors.primary),
    errorBorder: border(AppColors.error),
    focusedErrorBorder: border(AppColors.error),
  );
}

// ── 폴더 관리 (더보기) ──

Future<void> showFolderManageSheet(BuildContext context) {
  return _showSheet(context, title: '폴더 관리', child: const _FolderManager());
}

/// 이름 변경·삭제·순서 (길게 눌러 끌기). 칩과 같은 상태를 보므로 바꾸면 바로 반영된다.
class _FolderManager extends ConsumerWidget {
  const _FolderManager();

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final s = ref.watch(savedControllerProvider).value;
    if (s == null) return const LoadingState();
    final controller = ref.read(savedControllerProvider.notifier);
    final folders = s.folders.folders;

    void fail(Object e) =>
        ScaffoldMessenger.of(context)
            .showSnackBar(SnackBar(content: Text(errorMessage(e))));

    Future<void> rename(Folder folder) => showFolderNameDialog<void>(
      context,
      title: '이름 변경',
      initial: folder.name,
      maxLength: s.meta.limits.folderNameMax,
      submit: (name) => controller.renameFolder(folder.id, name),
    );

    Future<void> delete(Folder folder) async {
      final ok = await showDialog<bool>(
        context: context,
        useRootNavigator: true,
        builder: (context) => _DeleteFolderDialog(folder: folder),
      );
      if (ok != true) return;
      try {
        await controller.deleteFolder(folder.id);
      } catch (e) {
        if (context.mounted) fail(e);
      }
    }

    if (folders.isEmpty) {
      return const Padding(
        padding: EdgeInsets.symmetric(vertical: 24),
        child: EmptyState(message: '폴더가 없습니다.'),
      );
    }
    return Column(
      mainAxisSize: MainAxisSize.min,
      crossAxisAlignment: CrossAxisAlignment.stretch,
      children: [
        Flexible(
          child: AppCard(
            padding: const EdgeInsets.symmetric(horizontal: 16, vertical: 4),
            gap: 0,
            children: [
              Flexible(
                child: ReorderableListView(
                  shrinkWrap: true,
                  buildDefaultDragHandles: false,
                  onReorderItem: (from, to) async {
                    try {
                      await controller.moveFolder(folders[from].id, to);
                    } catch (e) {
                      if (context.mounted) fail(e);
                    }
                  },
                  children: [
                    for (final (i, folder) in folders.indexed)
                      ReorderableDelayedDragStartListener(
                        key: ValueKey(folder.id),
                        index: i,
                        child: ColoredBox(
                          color: AppColors.surface,
                          child: SettingRow(
                            title: folder.name,
                            subtitle: '찜 ${folder.count}',
                            isLast: i == folders.length - 1,
                            trailing: Row(
                              mainAxisSize: MainAxisSize.min,
                              spacing: 16,
                              children: [
                                _TextAction(
                                  label: '이름 변경',
                                  onTap: () => rename(folder),
                                ),
                                _TextAction(
                                  label: '삭제',
                                  color: AppColors.error,
                                  onTap: () => delete(folder),
                                ),
                              ],
                            ),
                          ),
                        ),
                      ),
                  ],
                ),
              ),
            ],
          ),
        ),
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 8, 20, 0),
          child: Text('길게 눌러 끌면 순서가 바뀝니다.', style: AppText.captionMd),
        ),
      ],
    );
  }
}

class _TextAction extends StatelessWidget {
  const _TextAction({
    required this.label,
    required this.onTap,
    this.color = AppColors.textSecondary,
  });

  final String label;
  final VoidCallback onTap;
  final Color color;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Text(label, style: AppText.labelButton.copyWith(color: color)),
    );
  }
}

class _DeleteFolderDialog extends StatelessWidget {
  const _DeleteFolderDialog({required this.folder});

  final Folder folder;

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.surface,
      shape: RoundedRectangleBorder(
        borderRadius: BorderRadius.circular(AppRadius.card),
      ),
      title: Text('폴더 삭제', style: AppText.titleCard),
      content: Text(
        '‘${folder.name}’ 폴더를 삭제할까요? 안의 찜 ${folder.count}개는 미분류로 남습니다.',
        style: AppText.bodyMd,
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.pop(context, false),
          child: Text(
            '취소',
            style: AppText.labelStrong.copyWith(color: AppColors.textTertiary),
          ),
        ),
        TextButton(
          onPressed: () => Navigator.pop(context, true),
          child: Text(
            '삭제',
            style: AppText.labelStrong.copyWith(color: AppColors.error),
          ),
        ),
      ],
    );
  }
}
