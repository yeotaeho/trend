// 입력 공통 — 시트와 목록 검색 줄이 같이 쓰는 입력 장식, 🔍 로 여는 목록 검색 입력.
import 'package:flutter/material.dart';
import 'package:flutter/services.dart';

import '../theme/app_colors.dart';
import '../theme/app_spacing.dart';
import '../theme/app_text.dart';
import 'buttons.dart';

/// 흰 바탕, 테두리 1px, 포커스 때 주색. 오류가 있으면 오류색 테두리와 문구.
InputDecoration appInputDecoration({required String hint, String? error}) {
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

/// 목록 검색 줄(디자인 없음). 키보드의 검색으로 제출하고 `취소` 로 닫는다.
/// 제출한 글자는 앞뒤 공백을 떼고 비면 `null` 로 알린다. 서버 상한(계약 4.1, 100자)보다 길게 받지 않는다.
class SearchField extends StatelessWidget {
  const SearchField({
    super.key,
    required this.onSubmitted,
    required this.onCancel,
  });

  static const int maxLength = 100;

  final ValueChanged<String?> onSubmitted;
  final VoidCallback onCancel;

  @override
  Widget build(BuildContext context) {
    return Padding(
      padding: const EdgeInsets.fromLTRB(16, 4, 16, 8),
      child: Row(
        spacing: 12,
        children: [
          Expanded(
            child: TextField(
              autofocus: true,
              textInputAction: TextInputAction.search,
              inputFormatters: [LengthLimitingTextInputFormatter(maxLength)],
              style: AppText.bodySm,
              decoration: appInputDecoration(hint: '제목·요약 검색'),
              onSubmitted: (text) {
                final q = text.trim();
                onSubmitted(q.isEmpty ? null : q);
              },
            ),
          ),
          AccentTextButton(label: '취소', onTap: onCancel),
        ],
      ),
    );
  }
}
