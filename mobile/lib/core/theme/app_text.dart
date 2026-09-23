// 타이포그래피 토큰 — docs/design/tokens.md 스타일 표를 IBM Plex Sans KR TextStyle 로.
import 'package:flutter/painting.dart';
import 'package:google_fonts/google_fonts.dart';

import 'app_colors.dart';

abstract final class AppText {
  /// HTML 이 줄 높이를 지정하지 않은 스타일의 Flutter 값 (Figma 에서 잰 normal).
  static const double normalHeight = 1.4;

  static const List<String> _fallback = [
    'Apple SD Gothic Neo',
    'Malgun Gothic',
  ];

  static TextStyle _plex(
    double size,
    FontWeight weight, {
    Color color = AppColors.textPrimary,
    double height = normalHeight,
    double? letterSpacing,
  }) {
    return GoogleFonts.ibmPlexSansKr(
      fontSize: size,
      fontWeight: weight,
      color: color,
      height: height,
      letterSpacing: letterSpacing,
    ).copyWith(fontFamilyFallback: _fallback);
  }

  /// 코드·slug·수치용 고정폭 (`ui-monospace, Menlo, monospace`).
  static TextStyle mono(TextStyle base) => base.copyWith(
    fontFamily: 'Menlo',
    fontFamilyFallback: const ['Roboto Mono', 'monospace'],
  );

  static final TextStyle titleRoot = _plex(22, FontWeight.w700);
  static final TextStyle titleSub = _plex(18, FontWeight.w600);
  static final TextStyle titleDetail = _plex(17, FontWeight.w700);
  static final TextStyle titleCard = _plex(16, FontWeight.w600);
  static final TextStyle statValueLg = _plex(24, FontWeight.w700);
  static final TextStyle statValue = _plex(22, FontWeight.w700);
  static final TextStyle statSuffix = _plex(
    13,
    FontWeight.w500,
    color: AppColors.textTertiary,
  );
  static final TextStyle count = _plex(16, FontWeight.w700);
  static final TextStyle avatar = _plex(
    16,
    FontWeight.w700,
    color: AppColors.textInverse,
  );
  static final TextStyle rowTitle = _plex(15, FontWeight.w500);
  static final TextStyle summaryTitle = _plex(15, FontWeight.w600);
  static final TextStyle bodyMd = _plex(
    14,
    FontWeight.w400,
    color: AppColors.textSecondary,
  );
  static final TextStyle bodyProfile = _plex(14, FontWeight.w400, height: 1.6);
  static final TextStyle labelStrong = _plex(14, FontWeight.w600);
  static final TextStyle labelGroup = _plex(14, FontWeight.w500);
  static final TextStyle bodySummary = _plex(
    13.5,
    FontWeight.w400,
    color: AppColors.textSecondary,
    height: 1.55,
  );
  static final TextStyle bodyDropped = _plex(13.5, FontWeight.w500);
  static final TextStyle labelButton = _plex(13, FontWeight.w600);
  static final TextStyle labelChip = _plex(
    13,
    FontWeight.w500,
    color: AppColors.textSecondary,
  );
  static final TextStyle labelSegment = _plex(
    13,
    FontWeight.w600,
    color: AppColors.textTertiary,
  );
  static final TextStyle bodySm = _plex(13, FontWeight.w400);
  static final TextStyle captionMd = _plex(
    12,
    FontWeight.w400,
    color: AppColors.textTertiary,
  );
  static final TextStyle captionNote = _plex(
    12,
    FontWeight.w400,
    color: AppColors.textSecondary,
    height: 1.5,
  );
  static final TextStyle sectionLabel = _plex(
    12,
    FontWeight.w600,
    color: AppColors.textTertiary,
    letterSpacing: 12 * 0.04,
  );
  static final TextStyle captionStrong = _plex(
    12,
    FontWeight.w600,
    color: AppColors.primary,
  );
  static final TextStyle captionSm = _plex(
    11,
    FontWeight.w400,
    color: AppColors.textTertiary,
  );
  static final TextStyle captionSmStrong = _plex(
    11,
    FontWeight.w600,
    color: AppColors.textTertiary,
  );
  static final TextStyle slug = mono(captionSm);
  static final TextStyle badge = _plex(11, FontWeight.w600);
  static final TextStyle tabLabel = _plex(
    11,
    FontWeight.w500,
    color: AppColors.textTertiary,
  );
}
