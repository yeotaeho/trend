// 앱 전역 프로바이더 — API 클라이언트, fixture 모드 스위치, 시계.
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

/// 지금 시각. 상대시간 표시가 쓰고, 테스트는 고정 시각으로 덮어쓴다.
final clockProvider = Provider<DateTime Function()>((ref) => DateTime.now);
