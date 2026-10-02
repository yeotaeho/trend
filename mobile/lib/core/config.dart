// 빌드 시 주입값 — --dart-define 로 받는 API 주소·토큰·fixture 모드와 그 검사.
abstract final class AppConfig {
  static const String apiBaseUrl = String.fromEnvironment(
    'API_BASE_URL',
    defaultValue: 'http://localhost:8000/api/v1',
  );
  static const String apiToken = String.fromEnvironment('APP_API_TOKEN');

  /// 주소(`API_BASE_URL`)를 주면 실서버, 안 주면 fixture 가 기본이다.
  /// `USE_FIXTURES` 를 직접 주면 그 값이 이긴다.
  static const bool useFixtures = bool.fromEnvironment(
    'USE_FIXTURES',
    defaultValue: !bool.hasEnvironment('API_BASE_URL'),
  );
}

/// 설정 화면 버전 줄에 붙이는 연결 대상 — fixture 모드면 `fixture`, 아니면 API 호스트명.
/// 주소가 깨졌으면 받은 문자열을 그대로 보여 오타를 화면에서 찾게 한다.
String connectionLabel({required bool useFixtures, required String baseUrl}) {
  if (useFixtures) return 'fixture';
  final host = Uri.tryParse(baseUrl)?.host ?? '';
  return host.isEmpty ? baseUrl : host;
}

/// 실서버 릴리스 빌드에 빠진 주입값. 문제없으면 null 이다.
///
/// http 주소면 토큰이 평문으로 나가고, 308 리다이렉트에서 Authorization 이 떨어져 401 이 된다.
/// 토큰이 비면 서버가 모든 요청을 401 로 막는다.
String? releaseConfigProblem({
  required bool useFixtures,
  required String baseUrl,
  required String token,
}) {
  if (useFixtures) return null;
  final uri = Uri.tryParse(baseUrl);
  if (uri == null || uri.scheme != 'https' || uri.host.isEmpty) {
    return 'API_BASE_URL 이 호스트가 있는 https 주소가 아니다: $baseUrl';
  }
  if (token.isEmpty) return 'APP_API_TOKEN 이 비어 있다';
  return null;
}
