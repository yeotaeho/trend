// 앱 진입점 — ProviderScope 로 감싸 TechRadarApp 을 띄운다.
import 'package:flutter/widgets.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'app/app.dart';

void main() {
  runApp(const ProviderScope(child: TechRadarApp()));
}
