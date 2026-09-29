// 앱 ThemeData — 라이트 전용 (다크 모드 디자인 없음), 리플 없이 토큰 색만 쓴다.
import 'package:flutter/material.dart';

import 'app_colors.dart';
import 'app_text.dart';

ThemeData buildAppTheme() {
  final colorScheme = ColorScheme.fromSeed(
    seedColor: AppColors.primary,
    primary: AppColors.primary,
    onPrimary: AppColors.textInverse,
    surface: AppColors.canvas,
    onSurface: AppColors.textPrimary,
    error: AppColors.error,
  );
  return ThemeData(
    useMaterial3: true,
    brightness: Brightness.light,
    colorScheme: colorScheme,
    scaffoldBackgroundColor: AppColors.canvas,
    splashFactory: NoSplash.splashFactory,
    highlightColor: Colors.transparent,
    dividerColor: AppColors.track,
    textTheme: TextTheme(
      bodyMedium: AppText.bodySm,
      bodyLarge: AppText.rowTitle,
      bodySmall: AppText.captionMd,
      titleLarge: AppText.titleRoot,
      titleMedium: AppText.titleSub,
      labelLarge: AppText.labelButton,
    ),
    snackBarTheme: SnackBarThemeData(
      backgroundColor: AppColors.textPrimary,
      contentTextStyle: AppText.bodySm.copyWith(color: AppColors.textInverse),
      behavior: SnackBarBehavior.floating,
    ),
  );
}
