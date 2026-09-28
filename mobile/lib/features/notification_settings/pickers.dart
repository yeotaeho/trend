// 05 값 피커 (디자인 없음) — 하단 시트에 CupertinoPicker 를 두고 `완료` 로 고른 값을 돌려준다.
import 'package:flutter/cupertino.dart';
import 'package:flutter/material.dart';

import '../../core/theme/app_colors.dart';
import '../../core/theme/app_spacing.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';

const double _itemExtent = 36;

/// [min]~[max] 정수 하나를 고른다. 닫으면 `null`.
Future<int?> showNumberPicker(
  BuildContext context, {
  required String title,
  required int initial,
  required int min,
  required int max,
  required String Function(int value) format,
}) {
  var selected = initial.clamp(min, max);
  return _showSheet<int>(
    context,
    title: title,
    result: () => selected,
    body: _Wheel(
      count: max - min + 1,
      initialItem: selected - min,
      label: (index) => format(min + index),
      onChanged: (index) => selected = min + index,
    ),
  );
}

/// 무음 시간의 시작·종료 시(0–23)를 고른다. 닫으면 `null`.
Future<(int start, int end)?> showHourRangePicker(
  BuildContext context, {
  required String title,
  required int start,
  required int end,
}) {
  var selectedStart = start;
  var selectedEnd = end;
  Widget column(String label, int initial, ValueChanged<int> onChanged) =>
      Expanded(
        child: Column(
          children: [
            Text(label, style: AppText.captionMd),
            Expanded(
              child: _Wheel(
                count: 24,
                initialItem: initial,
                label: formatHour,
                onChanged: onChanged,
              ),
            ),
          ],
        ),
      );
  return _showSheet<(int, int)>(
    context,
    title: title,
    result: () => (selectedStart, selectedEnd),
    body: Row(
      children: [
        column('시작', start, (hour) => selectedStart = hour),
        Text('–', style: AppText.rowTitle),
        column('종료', end, (hour) => selectedEnd = hour),
      ],
    ),
  );
}

/// `HH:00`.
String formatHour(int hour) => '${hour.toString().padLeft(2, '0')}:00';

Future<T?> _showSheet<T>(
  BuildContext context, {
  required String title,
  required T Function() result,
  required Widget body,
}) {
  return showModalBottomSheet<T>(
    context: context,
    useRootNavigator: true,
    backgroundColor: AppColors.surface,
    shape: const RoundedRectangleBorder(
      borderRadius: BorderRadius.vertical(top: Radius.circular(AppRadius.card)),
    ),
    builder: (context) => SafeArea(
      child: Column(
        mainAxisSize: MainAxisSize.min,
        children: [
          Padding(
            padding: const EdgeInsets.fromLTRB(20, 16, 20, 8),
            child: Row(
              mainAxisAlignment: MainAxisAlignment.spaceBetween,
              children: [
                Text(title, style: AppText.titleCard),
                AccentTextButton(
                  label: '완료',
                  onTap: () => Navigator.pop(context, result()),
                ),
              ],
            ),
          ),
          SizedBox(height: 216, child: body),
        ],
      ),
    ),
  );
}

class _Wheel extends StatefulWidget {
  const _Wheel({
    required this.count,
    required this.initialItem,
    required this.label,
    required this.onChanged,
  });

  final int count;
  final int initialItem;
  final String Function(int index) label;
  final ValueChanged<int> onChanged;

  @override
  State<_Wheel> createState() => _WheelState();
}

class _WheelState extends State<_Wheel> {
  late final FixedExtentScrollController _controller =
      FixedExtentScrollController(initialItem: widget.initialItem);

  @override
  void dispose() {
    _controller.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return CupertinoPicker(
      itemExtent: _itemExtent,
      scrollController: _controller,
      onSelectedItemChanged: widget.onChanged,
      children: [
        for (var index = 0; index < widget.count; index++)
          Center(child: Text(widget.label(index), style: AppText.rowTitle)),
      ],
    );
  }
}
