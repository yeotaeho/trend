// 푸시 딥링크 경로 변환 테스트 — `alert_id` 가 있으면 07, 없거나 비면 피드.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/app/routes.dart';
import 'package:tech_radar/features/push/push_route.dart';

void main() {
  test('alert 는 alert_id 로 07 을 연다', () {
    expect(
      pushRoute({
        'alert_id': '18342',
        'delivery_mode': 'instant',
        'type': 'alert',
      }),
      AppRoutes.alert('18342'),
    );
  });

  test('resurface 도 07 을 연다', () {
    expect(
      pushRoute({
        'alert_id': '18011',
        'delivery_mode': 'quiet',
        'type': 'resurface',
      }),
      AppRoutes.alert('18011'),
    );
  });

  test('alert_id 가 없거나 비었으면 피드', () {
    expect(pushRoute({}), AppRoutes.feed);
    expect(pushRoute({'type': 'alert'}), AppRoutes.feed);
    expect(pushRoute({'alert_id': ''}), AppRoutes.feed);
  });
}
