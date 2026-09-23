// 주간 리포트 상세 (디자인 없음) — 섹션마다 제목과 가로 스크롤 표, 숫자는 우정렬, null 은 `–`.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/format.dart';
import '../../core/theme/app_colors.dart';
import '../../core/theme/app_text.dart';
import '../../core/widgets/widgets.dart';
import '../../data/models/models.dart';
import 'profile_page.dart';
import 'profile_providers.dart';

class ReportPage extends ConsumerWidget {
  const ReportPage({super.key, required this.reportId});

  final String reportId;

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    final report = ref.watch(reportProvider(reportId));
    return Scaffold(
      appBar: const SubTopBar(title: '주간 리포트'),
      body: switch (report) {
        AsyncValue(isLoading: true) => const LoadingState(),
        AsyncValue(:final error?) => ErrorState(
          message: loadErrorMessage(error),
          onRetry: () => ref.invalidate(reportProvider(reportId)),
        ),
        AsyncValue(:final value?) => _ReportBody(report: value),
        _ => const LoadingState(),
      },
    );
  }
}

class _ReportBody extends StatelessWidget {
  const _ReportBody({required this.report});

  final Report report;

  @override
  Widget build(BuildContext context) {
    return ListView(
      padding: const EdgeInsets.only(bottom: 24),
      children: [
        Padding(
          padding: const EdgeInsets.fromLTRB(20, 4, 20, 0),
          child: Column(
            crossAxisAlignment: CrossAxisAlignment.start,
            spacing: 2,
            children: [
              Text(report.title, style: AppText.titleCard),
              Text(report.subtitle, style: AppText.captionMd),
              Text(
                '${report.periodStart} – ${report.periodEnd}',
                style: AppText.mono(AppText.captionMd),
              ),
            ],
          ),
        ),
        if (report.sections.isEmpty)
          const EmptyState(message: '리포트에 표가 없습니다.')
        else
          for (final section in report.sections) ...[
            SectionLabel(section.title),
            _SectionTable(section: section),
          ],
      ],
    );
  }
}

/// 셀 문자열. 정수는 그대로, 실수는 소수 2자리(음수는 U+2212), `null` 은 `–`.
String reportCell(Object? value) => switch (value) {
  null => '–',
  int() => '$value',
  double() => formatScore(value),
  _ => '$value',
};

class _SectionTable extends StatelessWidget {
  const _SectionTable({required this.section});

  final ReportSection section;

  static const EdgeInsets _cellPadding = EdgeInsets.symmetric(
    horizontal: 12,
    vertical: 8,
  );

  /// 값이 있는 셀이 모두 숫자인 열은 머리글까지 우정렬한다.
  bool _isNumericColumn(int column) {
    final values = [
      for (final row in section.rows)
        if (column < row.length && row[column] != null) row[column],
    ];
    return values.isNotEmpty && values.every((v) => v is num);
  }

  Widget _cell(String text, TextStyle style, {required bool right}) => Padding(
    padding: _cellPadding,
    child: Text(
      text,
      style: style,
      textAlign: right ? TextAlign.right : TextAlign.left,
    ),
  );

  @override
  Widget build(BuildContext context) {
    final columns = section.columns.length;
    final numeric = [for (var i = 0; i < columns; i++) _isNumericColumn(i)];
    final body = AppText.bodySm;
    return AppCard(
      padding: const EdgeInsets.symmetric(vertical: 4),
      children: [
        SingleChildScrollView(
          scrollDirection: Axis.horizontal,
          padding: const EdgeInsets.symmetric(horizontal: 4),
          child: Table(
            defaultColumnWidth: const IntrinsicColumnWidth(),
            border: const TableBorder(
              horizontalInside: BorderSide(color: AppColors.borderCard),
            ),
            children: [
              TableRow(
                children: [
                  for (var i = 0; i < columns; i++)
                    _cell(
                      section.columns[i],
                      AppText.mono(AppText.captionSmStrong),
                      right: numeric[i],
                    ),
                ],
              ),
              for (final row in section.rows)
                TableRow(
                  children: [
                    for (var i = 0; i < columns; i++)
                      _cell(
                        reportCell(i < row.length ? row[i] : null),
                        numeric[i] ? AppText.mono(body) : body,
                        right: numeric[i],
                      ),
                  ],
                ),
            ],
          ),
        ),
      ],
    );
  }
}
