// 빌드 시 주입값 — --dart-define 로 받는 API 주소·토큰·fixture 모드.
abstract final class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  static const String apiToken = String.fromEnvironment('APP_API_TOKEN');
  static const bool useFixtures = bool.fromEnvironment(
    'USE_FIXTURES',
    defaultValue: true,
  );
}
