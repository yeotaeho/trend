// 오류 로그 — 프로바이더 실패와 쓰기 실패를 원인·스택과 함께 남긴다(안드로이드는 adb logcat -s flutter).
import 'package:flutter/foundation.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

/// 화면에는 '알 수 없는 오류' 한 줄만 보여도, 로그에는 원래 예외와 스택이 남게 한다.
void logError(String where, Object error, StackTrace stack) {
  debugPrint('[$where] $error\n$stack');
}

/// 조회 프로바이더가 실패할 때마다(401·연결 실패·파싱 오류 포함) 로그를 남긴다.
final class ErrorLogObserver extends ProviderObserver {
  const ErrorLogObserver();

  @override
  void providerDidFail(
    ProviderObserverContext context,
    Object error,
    StackTrace stackTrace,
  ) => logError('provider ${context.provider}', error, stackTrace);
}
