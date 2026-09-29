// FCM 경계 — 권한·Android 알림 채널 준비와 토큰·메시지 스트림. 테스트는 가짜 구현으로 바꾼다.
import 'package:firebase_core/firebase_core.dart';
import 'package:firebase_messaging/firebase_messaging.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter_local_notifications/flutter_local_notifications.dart';

/// 받은 푸시에서 앱이 쓰는 부분. [data] 는 계약 4.9 페이로드의 `data` 다.
class PushMessage {
  const PushMessage({this.title, this.data = const {}});

  final String? title;
  final Map<String, Object?> data;
}

abstract interface class PushMessaging {
  /// 알림 권한을 묻고 Android 채널을 만든다.
  Future<void> prepare();

  Future<String?> getToken();

  Stream<String> get onTokenRefresh;

  /// 앱이 앞에 있을 때 받은 메시지. 시스템 알림은 뜨지 않는다.
  Stream<PushMessage> get onForeground;

  /// 백그라운드에서 알림을 눌러 앱이 앞으로 왔을 때.
  Stream<PushMessage> get onOpened;

  /// 종료 상태에서 알림을 눌러 앱이 켜졌으면 그 메시지.
  Future<PushMessage?> initialMessage();
}

/// 서버가 `android.notification.channel_id` 로 고르는 채널 (계약 4.9).
const instantChannel = AndroidNotificationChannel(
  'instant',
  '즉시 알림',
  description: '중요한 알림을 소리와 함께 바로 알립니다.',
  importance: Importance.high,
);

const quietChannel = AndroidNotificationChannel(
  'quiet',
  '조용한 알림',
  description: '덜 급한 알림과 재알림을 소리 없이 알림 창에 둡니다.',
  importance: Importance.low,
  playSound: false,
  enableVibration: false,
);

class FirebasePushMessaging implements PushMessaging {
  FirebasePushMessaging._(this._fm);

  final FirebaseMessaging _fm;

  /// Firebase 를 띄운다. 설정 파일(`google-services.json`·`GoogleService-Info.plist`)이
  /// 없으면 실패하고 null 이다. 그때 앱은 푸시 없이 동작한다.
  static Future<FirebasePushMessaging?> initialize() async {
    try {
      await Firebase.initializeApp();
    } catch (error) {
      debugPrint('push: Firebase 초기화 실패로 푸시를 끕니다 — $error');
      return null;
    }
    return FirebasePushMessaging._(FirebaseMessaging.instance);
  }

  @override
  Future<void> prepare() async {
    await _fm.requestPermission();
    final android = FlutterLocalNotificationsPlugin()
        .resolvePlatformSpecificImplementation<
          AndroidFlutterLocalNotificationsPlugin
        >();
    await android?.createNotificationChannel(instantChannel);
    await android?.createNotificationChannel(quietChannel);
  }

  @override
  Future<String?> getToken() => _fm.getToken();

  @override
  Stream<String> get onTokenRefresh => _fm.onTokenRefresh;

  @override
  Stream<PushMessage> get onForeground => FirebaseMessaging.onMessage.map(_map);

  @override
  Stream<PushMessage> get onOpened =>
      FirebaseMessaging.onMessageOpenedApp.map(_map);

  @override
  Future<PushMessage?> initialMessage() async {
    final message = await _fm.getInitialMessage();
    return message == null ? null : _map(message);
  }

  static PushMessage _map(RemoteMessage message) =>
      PushMessage(title: message.notification?.title, data: message.data);
}
