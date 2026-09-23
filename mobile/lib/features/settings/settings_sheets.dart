// 설정 편집 UI (디자인 없음) — 확인·텍스트 입력 다이얼로그, 04 프로필 편집 시트, kind 가중치 스테퍼 시트.
import 'package:flutter/material.dart';

import '../../core/format.dart';
import '../../core/labels.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';

/// 확인 다이얼로그. [confirmLabel] 을 누르면 true, 취소·바깥 탭이면 false.
Future<bool> showConfirmDialog(
  BuildContext context, {
  required String title,
  required String message,
  required String confirmLabel,
}) async {
  final result = await showDialog<bool>(
    context: context,
    builder: (context) => AlertDialog(
      backgroundColor: AppColors.surface,
      title: Text(title, style: AppText.titleCard),
      content: Text(message, style: AppText.bodyMd),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(false),
          child: Text('취소', style: AppText.labelStrong),
        ),
        TextButton(
          onPressed: () => Navigator.of(context).pop(true),
          child: Text(
            confirmLabel,
            style: AppText.labelStrong.copyWith(color: AppColors.primary),
          ),
        ),
      ],
    ),
  );
  return result ?? false;
}

/// 한 줄 입력 다이얼로그. [onSubmit] 이 오류 문장을 돌려주면 입력칸 아래에 보이고 닫지 않는다.
Future<void> showTextInputDialog(
  BuildContext context, {
  required String title,
  required String confirmLabel,
  required Future<String?> Function(String input) onSubmit,
  String initialValue = '',
  String? hint,
  int? maxLength,
}) {
  return showDialog<void>(
    context: context,
    builder: (context) => _TextInputDialog(
      title: title,
      confirmLabel: confirmLabel,
      onSubmit: onSubmit,
      initialValue: initialValue,
      hint: hint,
      maxLength: maxLength,
    ),
  );
}

class _TextInputDialog extends StatefulWidget {
  const _TextInputDialog({
    required this.title,
    required this.confirmLabel,
    required this.onSubmit,
    required this.initialValue,
    this.hint,
    this.maxLength,
  });

  final String title;
  final String confirmLabel;
  final Future<String?> Function(String input) onSubmit;
  final String initialValue;
  final String? hint;
  final int? maxLength;

  @override
  State<_TextInputDialog> createState() => _TextInputDialogState();
}

class _TextInputDialogState extends State<_TextInputDialog> {
  late final TextEditingController _controller = TextEditingController(
    text: widget.initialValue,
  );
  String? _error;
  bool _busy = false;

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  Future<void> _submit() async {
    setState(() => _busy = true);
    final error = await widget.onSubmit(_controller.text);
    if (!mounted) return;
    if (error == null) {
      Navigator.of(context).pop();
    } else {
      setState(() {
        _error = error;
        _busy = false;
      });
    }
  }

  @override
  Widget build(BuildContext context) {
    return AlertDialog(
      backgroundColor: AppColors.surface,
      title: Text(widget.title, style: AppText.titleCard),
      content: TextField(
        controller: _controller,
        autofocus: true,
        maxLength: widget.maxLength,
        style: AppText.rowTitle,
        onSubmitted: (_) => _busy ? null : _submit(),
        decoration: InputDecoration(hintText: widget.hint, errorText: _error),
      ),
      actions: [
        TextButton(
          onPressed: () => Navigator.of(context).pop(),
          child: Text('취소', style: AppText.labelStrong),
        ),
        TextButton(
          onPressed: _busy ? null : _submit,
          child: Text(
            widget.confirmLabel,
            style: AppText.labelStrong.copyWith(color: AppColors.primary),
          ),
        ),
      ],
    );
  }
}

/// 시트 틀 — 흰 배경 위쪽 반경 14, 제목 + 우측 `완료`.
Future<T?> _showSheet<T>(BuildContext context, WidgetBuilder builder) {
  return showModalBottomSheet<T>(
    context: context,
    isScrollControlled: true,
    useRootNavigator: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
    ),
    builder: (context) => Padding(
      padding: EdgeInsets.only(bottom: MediaQuery.viewInsetsOf(context).bottom),
      child: SafeArea(child: builder(context)),
    ),
  );
}

class _SheetHeader extends StatelessWidget {
  const _SheetHeader({required this.title, this.onDone});

  final String title;
  final VoidCallback? onDone;

  @override
  Widget build(BuildContext context) {
    return Row(
      mainAxisAlignment: MainAxisAlignment.spaceBetween,
      children: [
        Text(title, style: AppText.titleCard),
        AccentTextButton(label: '완료', onTap: onDone),
      ],
    );
  }
}

typedef ProfileEdit = ({String selfDescription, String notInterested});

/// 04 프로필 카드 편집. 자기소개 1~1000자, 관심 없음 0~500자 (계약 4.3). `완료` 하면 두 값을 돌려준다.
Future<ProfileEdit?> showProfileEditSheet(
  BuildContext context, {
  required String selfDescription,
  required String notInterested,
}) {
  return _showSheet(
    context,
    (context) => _ProfileEditSheet(
      selfDescription: selfDescription,
      notInterested: notInterested,
    ),
  );
}

class _ProfileEditSheet extends StatefulWidget {
  const _ProfileEditSheet({
    required this.selfDescription,
    required this.notInterested,
  });

  final String selfDescription;
  final String notInterested;

  @override
  State<_ProfileEditSheet> createState() => _ProfileEditSheetState();
}

class _ProfileEditSheetState extends State<_ProfileEditSheet> {
  late final TextEditingController _self = TextEditingController(
    text: widget.selfDescription,
  );
  late final TextEditingController _not = TextEditingController(
    text: widget.notInterested,
  );

  @override
  void initState() {
    super.initState();
    _self.addListener(() => setState(() {}));
  }

  @override
  void dispose() {
    _self.dispose();
    _not.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 16),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: 12,
        children: [
          _SheetHeader(
            title: '나를 한 줄로',
            onDone: _self.text.trim().isEmpty
                ? null
                : () => Navigator.of(context).pop((
                    selfDescription: _self.text.trim(),
                    notInterested: _not.text.trim(),
                  )),
          ),
          TextField(
            key: const ValueKey('self-description'),
            controller: _self,
            autofocus: true,
            minLines: 3,
            maxLines: 6,
            maxLength: 1000,
            style: AppText.bodyProfile,
            decoration: const InputDecoration(labelText: '자기소개'),
          ),
          TextField(
            key: const ValueKey('not-interested'),
            controller: _not,
            minLines: 1,
            maxLines: 3,
            maxLength: 500,
            style: AppText.bodyProfile,
            decoration: const InputDecoration(labelText: '관심 없음'),
          ),
        ],
      ),
    );
  }
}

/// kind 가중치 스테퍼. [range] 안에서 [StepRange.step] 단위로 움직이고 `완료` 하면 값을 돌려준다.
Future<double?> showWeightEditSheet(
  BuildContext context, {
  required Kind kind,
  required double value,
  required StepRange range,
}) {
  return _showSheet(
    context,
    (context) => _WeightEditSheet(kind: kind, value: value, range: range),
  );
}

class _WeightEditSheet extends StatefulWidget {
  const _WeightEditSheet({
    required this.kind,
    required this.value,
    required this.range,
  });

  final Kind kind;
  final double value;
  final StepRange range;

  @override
  State<_WeightEditSheet> createState() => _WeightEditSheetState();
}

class _WeightEditSheetState extends State<_WeightEditSheet> {
  // 부동소수 누적 오차를 피하려고 0.01 단위 정수로 센다.
  late int _cents = _toCents(widget.value);
  late final int _min = _toCents(widget.range.min);
  late final int _max = _toCents(widget.range.max);
  late final int _step = _toCents(widget.range.step);

  static int _toCents(double value) => (value * 100).round();

  void _move(int direction) =>
      setState(() => _cents = (_cents + direction * _step).clamp(_min, _max));

  @override
  Widget build(BuildContext context) {
    final value = _cents / 100;
    return Padding(
      padding: const EdgeInsets.fromLTRB(20, 16, 20, 24),
      child: Column(
        mainAxisSize: MainAxisSize.min,
        crossAxisAlignment: CrossAxisAlignment.stretch,
        spacing: 16,
        children: [
          _SheetHeader(
            title: widget.kind.label,
            onDone: () => Navigator.of(context).pop(value),
          ),
          Row(
            mainAxisAlignment: MainAxisAlignment.center,
            spacing: 24,
            children: [
              _StepButton(
                key: const ValueKey('weight-down'),
                label: minusSign,
                semanticLabel: '낮추기',
                onTap: _cents > _min ? () => _move(-1) : null,
              ),
              SizedBox(
                width: 96,
                child: Text(
                  formatSignedScore(value),
                  key: const ValueKey('weight-value'),
                  textAlign: TextAlign.center,
                  style: AppText.mono(AppText.statValue).copyWith(
                    color: _cents < 0 ? AppColors.warn : AppColors.textPrimary,
                  ),
                ),
              ),
              _StepButton(
                key: const ValueKey('weight-up'),
                label: '+',
                semanticLabel: '올리기',
                onTap: _cents < _max ? () => _move(1) : null,
              ),
            ],
          ),
          Text(
            '${widget.kind.value} · ${formatSignedScore(widget.range.min)} ~ '
            '${formatSignedScore(widget.range.max)}, '
            '${widget.range.step.toStringAsFixed(2)} 단위',
            textAlign: TextAlign.center,
            style: AppText.captionMd,
          ),
        ],
      ),
    );
  }
}

class _StepButton extends StatelessWidget {
  const _StepButton({
    super.key,
    required this.label,
    required this.semanticLabel,
    this.onTap,
  });

  final String label;
  final String semanticLabel;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    final enabled = onTap != null;
    return Semantics(
      button: true,
      enabled: enabled,
      label: semanticLabel,
      child: GestureDetector(
        onTap: onTap,
        behavior: HitTestBehavior.opaque,
        child: Container(
          width: 44,
          height: 44,
          alignment: Alignment.center,
          decoration: BoxDecoration(
            color: AppColors.surface,
            border: Border.all(color: AppColors.borderControl),
            borderRadius: BorderRadius.circular(AppRadius.button),
          ),
          child: Text(
            label,
            style: AppText.mono(AppText.titleSub).copyWith(
              color: enabled ? AppColors.textPrimary : AppColors.controlOff,
            ),
          ),
        ),
      ),
    );
  }
}
