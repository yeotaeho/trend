// 디자인 색 토큰 — docs/design/tokens.md 색상 표를 그대로 옮긴 상수.
import 'package:flutter/painting.dart';

abstract final class AppColors {
  static const Color canvas = Color(0xFFF5F4F0);
  static const Color surface = Color(0xFFFFFFFF);
  static const Color subtle = Color(0xFFF0EEE9);
  static const Color segmentedTrack = Color(0xFFEBE8E1);
  static const Color track = Color(0xFFEFECE6);

  static const Color borderCard = Color(0xFFE5E2DB);
  static const Color borderControl = Color(0xFFD9D5CC);
  static const Color controlOff = Color(0xFFD6D2C9);
  static const Color chevron = Color(0xFFB8B4AB);

  static const Color textPrimary = Color(0xFF1C1B19);
  static const Color textSecondary = Color(0xFF55524B);
  static const Color textMuted = Color(0xFF6B6862);
  static const Color textTertiary = Color(0xFF8A877F);
  static const Color textInverse = Color(0xFFFFFFFF);

  static const Color primary = Color(0xFF2D5BE3);
  static const Color primarySoft = Color(0xFFE8EEFC);
  static const Color primaryMuted = Color(0xFF9FB4EA);
  static const Color info = Color(0xFF4A6FD0);
  static const Color infoSoft = Color(0xFFEAF0FC);
  static const Color warn = Color(0xFFB5651D);
  static const Color warnSoft = Color(0xFFFDF1E2);
  static const Color warnMuted = Color(0xFFE0A373);
  static const Color feed = Color(0xFF3D7A4A);
  static const Color feedSoft = Color(0xFFEEF5EE);
  static const Color error = Color(0xFFC2410C);

  static const Color gateExclude = Color(0xFFB8B4AB);
  static const Color gateDedup = Color(0xFFD6D2C9);
  static const Color gateScreening = Color(0xFF9FB4EA);
  static const Color gateScore = Color(0xFF2D5BE3);
  static const Color gateJudgment = Color(0xFFB5651D);
  // 계약 2 `gate` 표의 권장값 — 디자인에 없던 두 관문.
  static const Color gateStale = Color(0xFFCFCBC2);
  static const Color gateClusterDup = Color(0xFFE0A373);

  static const Color segmentShadow = Color(0x14000000);
}
