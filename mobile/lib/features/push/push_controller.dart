// 푸시 연동 — 기동·토큰 갱신 때 기기 등록, 알림 탭 딥링크, 포그라운드 스낵바와 피드 새로고침.
import 'dart:async';

import 'package:flutter/foundation.dart';
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../app/router.dart';
import '../../app/routes.dart';
import '../../core/labels.dart';
import '../../core/providers.dart';
import '../../core/snack.dart';
import '../../data/repositories/repository_providers.dart';
import '../feed/feed_providers.dart';
import 'push_messaging.dart';
import 'push_route.dart';

class PushController {
  PushController({
    required this.messaging,
    required this.registerToken,
    required this.open,
    required this.onForeground,
  });

  final PushMessaging messaging;
  final Future<void> Function(String token) registerToken;
  final void Function(PushMessage message) open;
  final void Function(PushMessage message) onForeground;

  final List<StreamSubscription<Object?>> _subscriptions = [];

  /// 스트림부터 구독해 준비 중에 온 갱신·탭을 놓치지 않는다.
  /// 단계마다 따로 실패를 삼켜, 권한 요청이 실패해도 딥링크와 등록은 진행한다.
  Future<void> start() async {
    _subscriptions.addAll([
      messaging.onTokenRefresh.listen(_register),
      messaging.onOpened.listen(open),
      messaging.onForeground.listen(onForeground),
    ]);
    await _attempt('권한·채널 준비', messaging.prepare);
    final initial = await _attempt('시작 메시지 조회', messaging.initialMessage);
    if (initial != null) open(initial);
    final token = await _attempt('토큰 조회', messaging.getToken);
    if (token != null) await _register(token);
  }

  Future<void> _register(String token) =>
      _attempt('기기 등록', () => registerToken(token));

  static Future<T?> _attempt<T>(
    String step,
    Future<T> Function() action,
  ) async {
    try {
      return await action();
    } catch (error) {
      debugPrint('push: $step 실패 — $error');
      return null;
    }
  }

  void dispose() {
    for (final subscription in _subscriptions) {
      subscription.cancel();
    }
  }
}

/// FCM 경계. Firebase 초기화에 성공했을 때만 main 이 채운다. null 이면 푸시를 쓰지 않는다.
final pushMessagingProvider = Provider<PushMessaging?>((ref) => null);

/// 앱 루트가 watch 해 기동 시 한 번 시작한다.
final pushControllerProvider = Provider<PushController?>((ref) {
  final messaging = ref.watch(pushMessagingProvider);
  if (messaging == null) return null;

  void openMessage(PushMessage message) {
    final route = pushRoute(message.data);
    final router = ref.read(routerProvider);
    route == AppRoutes.feed ? router.go(route) : router.push(route);
  }

  final controller = PushController(
    messaging: messaging,
    registerToken: (token) async {
      if (ref.read(useFixturesProvider)) {
        debugPrint('push: fixture 모드라 기기 등록을 건너뜁니다.');
        return;
      }
      await ref
          .read(deviceRepositoryProvider)
          .register(token: token, platform: _platform);
    },
    open: openMessage,
    onForeground: (message) {
      ref
        ..invalidate(feedProvider)
        ..invalidate(todayStatsProvider);
      ref.read(messengerKeyProvider).currentState
        ?..hideCurrentSnackBar()
        ..showSnackBar(
          SnackBar(
            content: Text(
              message.title ?? '새 알림이 도착했습니다.',
              maxLines: 2,
              overflow: TextOverflow.ellipsis,
            ),
            action: SnackBarAction(
              label: '보기',
              onPressed: () => openMessage(message),
            ),
          ),
        );
    },
  );
  unawaited(controller.start());
  ref.onDispose(controller.dispose);
  return controller;
});

DevicePlatform get _platform => defaultTargetPlatform == TargetPlatform.iOS
    ? DevicePlatform.ios
    : DevicePlatform.android;
