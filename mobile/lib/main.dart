// 앱 진입점 — 주입값을 검사하고 Firebase 를 띄워 푸시 경계를 넣은 뒤 ProviderScope 로 감싸 TechRadarApp 을 띄운다.
import 'package:flutter/foundation.dart';
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'core/config.dart';
import 'core/error_log.dart';
import 'features/push/push_controller.dart';
import 'features/push/push_messaging.dart';

Future<void> main() async {
  if (kReleaseMode) {
    final problem = releaseConfigProblem(
      useFixtures: AppConfig.useFixtures,
      baseUrl: AppConfig.apiBaseUrl,
      token: AppConfig.apiToken,
    );
    if (problem != null) throw StateError(problem);
  }
  WidgetsFlutterBinding.ensureInitialized();
  final messaging = await FirebasePushMessaging.initialize();
  runApp(
    ProviderScope(
      // 실패를 곧바로 보인다. 기본 재시도(최대 10회, 합계 약 38초)는 401·연결 실패를 스피너 뒤에 숨긴다.
      // 화면마다 '다시 시도' 와 당겨서 새로고침이 있다.
      retry: (retryCount, error) => null,
      observers: const [ErrorLogObserver()],
      overrides: [
        if (messaging != null)
          pushMessagingProvider.overrideWithValue(messaging),
      ],
      child: const TechRadarApp(),
    ),
  );
}
