// 토글·설정 행 — 44×26 Toggle, ToggleRow·ValueRow (min-height 52, 행 사이 1px 구분선).
import 'package:flutter/widgets.dart';

import '../icons.dart';
import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';

const Duration _toggleDuration = Duration(milliseconds: 150);

class AppToggle extends StatelessWidget {
  const AppToggle({super.key, required this.value, this.onChanged});

  final bool value;
  final ValueChanged<bool>? onChanged;

  @override
  Widget build(BuildContext context) {
    return Semantics(
      toggled: value,
      enabled: onChanged != null,
      child: GestureDetector(
        onTap: onChanged == null ? null : () => onChanged!(!value),
        child: AnimatedContainer(
          duration: _toggleDuration,
          width: 44,
          height: 26,
          padding: const EdgeInsets.all(2),
          decoration: BoxDecoration(
            color: value ? AppColors.primary : AppColors.controlOff,
            borderRadius: BorderRadius.circular(AppRadius.toggleTrack),
          ),
          child: AnimatedAlign(
            duration: _toggleDuration,
            alignment: value ? Alignment.centerRight : Alignment.centerLeft,
            child: Container(
              width: 22,
              height: 22,
              decoration: BoxDecoration(
                color: AppColors.surface,
                borderRadius: BorderRadius.circular(AppRadius.toggleKnob),
              ),
            ),
          ),
        ),
      ),
    );
  }
}

/// 설정 행 틀. 좌 제목(15/500)·보조 줄(12 tertiary), 우 [trailing].
class SettingRow extends StatelessWidget {
  const SettingRow({
    super.key,
    required this.title,
    required this.trailing,
    this.subtitle,
    this.isLast = false,
    this.onTap,
  });

  final String title;
  final String? subtitle;
  final Widget trailing;

  /// 마지막 행은 아래 구분선이 없다.
  final bool isLast;
  final VoidCallback? onTap;

  @override
  Widget build(BuildContext context) {
    return GestureDetector(
      onTap: onTap,
      behavior: HitTestBehavior.opaque,
      child: Container(
        constraints: const BoxConstraints(minHeight: AppSpacing.rowMinHeight),
        padding: const EdgeInsets.symmetric(vertical: AppSpacing.rowPaddingV),
        decoration: isLast
            ? null
            : const BoxDecoration(
                border: Border(bottom: BorderSide(color: AppColors.track)),
              ),
        child: Row(
          spacing: 12,
          children: [
            Expanded(
              child: Column(
                crossAxisAlignment: CrossAxisAlignment.start,
                mainAxisSize: MainAxisSize.min,
                children: [
                  Text(title, style: AppText.rowTitle),
                  if (subtitle != null)
                    Padding(
                      padding: const EdgeInsets.only(top: 2),
                      child: Text(subtitle!, style: AppText.captionMd),
                    ),
                ],
              ),
            ),
            trailing,
          ],
        ),
      ),
    );
  }
}

class ToggleRow extends StatelessWidget {
  const ToggleRow({
    super.key,
    required this.title,
    required this.value,
    this.onChanged,
    this.subtitle,
    this.isLast = false,
  });

  final String title;
  final String? subtitle;
  final bool value;
  final ValueChanged<bool>? onChanged;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return SettingRow(
      title: title,
      subtitle: subtitle,
      isLast: isLast,
      trailing: AppToggle(value: value, onChanged: onChanged),
    );
  }
}

/// 값(14 secondary) + chevron 16 행. 탭하면 편집·이동한다.
class ValueRow extends StatelessWidget {
  const ValueRow({
    super.key,
    required this.title,
    required this.value,
    this.onTap,
    this.subtitle,
    this.isLast = false,
  });

  final String title;
  final String? subtitle;
  final String value;
  final VoidCallback? onTap;
  final bool isLast;

  @override
  Widget build(BuildContext context) {
    return SettingRow(
      title: title,
      subtitle: subtitle,
      isLast: isLast,
      onTap: onTap,
      trailing: Row(
        mainAxisSize: MainAxisSize.min,
        spacing: 6,
        children: [
          Text(value, style: AppText.bodyMd),
          const AppIcon('chev', size: 16, color: AppColors.chevron),
        ],
      ),
    );
  }
}
