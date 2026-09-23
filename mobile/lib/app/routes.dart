// 라우트 경로 상수 — 4탭 루트와 하위 화면, 탭바 없는 07 상세.
abstract final class AppRoutes {
  /// 03 피드 (탭 1).
  static const String feed = '/feed';

  /// 09·10 걸러진 항목. 쿼리 `view` = `source`·`kind`·`gate`.
  static const String filtered = '/feed/filtered';

  /// 11 찜 (탭 2).
  static const String saved = '/saved';

  /// 설정 루트 (탭 3, 디자인 없음).
  static const String settings = '/settings';
  static const String interests = '/settings/interests';
  static const String notifications = '/settings/notifications';
  static const String sources = '/settings/sources';

  /// 08 내 프로필 (탭 4).
  static const String profile = '/profile';

  /// 주간 리포트 상세 (디자인 없음).
  static String report(String reportId) => '/profile/reports/$reportId';

  /// 07 피드백 · 판정 근거. 루트 네비게이터에 올라가 탭바가 없다.
  static String alert(String alertId) => '/alerts/$alertId';
}
