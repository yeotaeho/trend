// 푸시 딥링크 — 메시지 `data` 를 열 경로로 바꾼다 (`alert_id` 가 있으면 07, 없으면 피드).
import '../../app/routes.dart';

/// 계약 4.9 페이로드의 `data`. `type` 이 `alert`·`resurface` 어느 쪽이든 `alert_id` 로 07 을 연다.
String pushRoute(Map<String, Object?> data) {
  final alertId = data['alert_id'];
  if (alertId is String && alertId.isNotEmpty) return AppRoutes.alert(alertId);
  return AppRoutes.feed;
}
