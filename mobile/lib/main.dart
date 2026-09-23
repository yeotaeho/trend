// 앱 진입점 — Firebase 를 띄워 푸시 경계를 넣고 ProviderScope 로 감싸 TechRadarApp 을 띄운다.
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';
import 'features/push/push_controller.dart';
import 'features/push/push_messaging.dart';

Future<void> main() async {
  WidgetsFlutterBinding.ensureInitialized();
  final messaging = await FirebasePushMessaging.initialize();
  runApp(
    ProviderScope(
      overrides: [
        if (messaging != null)
          pushMessagingProvider.overrideWithValue(messaging),
      ],
      child: const TechRadarApp(),
    ),
  );
}
