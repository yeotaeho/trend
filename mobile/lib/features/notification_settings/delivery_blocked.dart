// 발송 막힘 사유 — 서버 notify/policy.py 의 delivery_blocked 와 같은 규칙. 05 상태 줄과 저장 전 확인창이 쓴다.
import '../../core/labels.dart';
import '../../data/models/models.dart';

/// 무음이 이 시간 이상이면 quiet_long 이다 (서버 QUIET_LONG_HOURS).
const int quietLongHours = 20;

/// 저장 결과가 새로 만들면 저장 전에 묻는 사유. resurface_off 는 앱 푸시를 끄는 선택이라 묻지 않는다.
const Set<DeliveryBlocked> confirmBeforeSave = {
  DeliveryBlocked.noChannel,
  DeliveryBlocked.noInstant,
  DeliveryBlocked.quietLong,
};

/// [settings] 로는 알림이 막히는 사유. 없으면 빈 목록이다.
List<DeliveryBlocked> deliveryBlocked(NotificationSettings settings) {
  final channels = settings.channels;
  // FCM 은 연결 정보가 있어도 활성 기기가 없으면 보낼 곳이 없다.
  final fcm =
      channels.fcm.enabled &&
      channels.fcm.connected &&
      channels.fcm.deviceCount > 0;
  final usable =
      fcm ||
      (channels.discord.enabled && channels.discord.connected) ||
      (channels.telegram.enabled && channels.telegram.connected);
  final by = settings.deliveryByImportance;
  final quiet =
      (_hour(settings.quietHours.end) - _hour(settings.quietHours.start)) % 24;
  return [
    if (!usable) DeliveryBlocked.noChannel,
    if (![by.high, by.mid, by.low].contains(DeliveryChoice.instant))
      DeliveryBlocked.noInstant,
    if (quiet >= quietLongHours) DeliveryBlocked.quietLong,
    if (!fcm) DeliveryBlocked.resurfaceOff,
  ];
}

int _hour(String hhmm) => int.tryParse(hhmm.split(':').first) ?? 0;
