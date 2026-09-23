// 앱 전역 프로바이더 — API 클라이언트와 fixture 모드 스위치.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api/api_client.dart';
import 'config.dart';

/// true 면 저장소가 fixture 구현을 쓴다 (`--dart-define=USE_FIXTURES`, 기본 true).
final useFixturesProvider = Provider<bool>((ref) => AppConfig.useFixtures);

final apiClientProvider = Provider<ApiClient>(
  (ref) => ApiClient(
    createDio(baseUrl: AppConfig.apiBaseUrl, token: AppConfig.apiToken),
  ),
);
