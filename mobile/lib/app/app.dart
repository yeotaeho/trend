// 앱 루트 — MaterialApp.router 에 테마와 go_router 를 붙이고 푸시 연동을 시작한다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../core/snack.dart';
import '../core/theme/app_theme.dart';
import '../features/push/push_controller.dart';
import 'router.dart';

class TechRadarApp extends ConsumerWidget {
  const TechRadarApp({super.key});

  @override
  Widget build(BuildContext context, WidgetRef ref) {
    ref.watch(pushControllerProvider);
    return MaterialApp.router(
      title: '기술 파악',
      debugShowCheckedModeBanner: false,
      theme: buildAppTheme(),
      scaffoldMessengerKey: ref.watch(messengerKeyProvider),
      routerConfig: ref.watch(routerProvider),
    );
  }
}
