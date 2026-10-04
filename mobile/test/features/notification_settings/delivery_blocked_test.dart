// 발송 막힘 사유 테스트 — 서버 notify/policy.py 와 같은 규칙(FCM 은 기기까지, 무음 20시간, 즉시 구간).
import 'dart:convert';
import 'dart:io';

import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/json_merge.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/features/notification_settings/delivery_blocked.dart';

NotificationSettings _settings([Map<String, Object?> patch = const {}]) {
  final json = jsonDecode(
    File('assets/fixtures/settings_notifications.json').readAsStringSync(),
  ) as Map<String, dynamic>;
  return NotificationSettings.fromJson(deepMerge(json, patch));
}

void main() {
  test('fixture 설정은 막힘이 없다', () {
    expect(deliveryBlocked(_settings()), isEmpty);
  });

  test('기기가 없는 FCM 만 남으면 보낼 채널이 없고 찜 재알림도 멈춘다', () {
    final settings = _settings({
      'channels': {
        'fcm': {'device_count': 0},
        'discord': {'enabled': false},
      },
    });

    expect(deliveryBlocked(settings), [
      DeliveryBlocked.noChannel,
      DeliveryBlocked.resurfaceOff,
    ]);
  });

  test('즉시 구간이 없거나 무음이 20시간 이상이면 막힌다', () {
    expect(
      deliveryBlocked(
        _settings({
          'delivery_by_importance': {'high': 'quiet'},
        }),
      ),
      [DeliveryBlocked.noInstant],
    );
    expect(
      deliveryBlocked(
        _settings({
          'quiet_hours': {'start': '23:00', 'end': '19:00'},
        }),
      ),
      [DeliveryBlocked.quietLong],
    );
    expect(
      deliveryBlocked(
        _settings({
          'quiet_hours': {'start': '01:00', 'end': '20:00'},
        }),
      ),
      isEmpty,
    );
  });
}
