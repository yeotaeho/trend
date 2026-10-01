// 빌드 주입값 검사 — 설정 버전 줄의 연결 대상 표시와 실서버 릴리스 빌드 가드.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/config.dart';

void main() {
  group('connectionLabel', () {
    test('fixture 모드면 fixture', () {
      expect(
        connectionLabel(
          useFixtures: true,
          baseUrl: 'https://trend.yeotaeho.kr/api/v1',
        ),
        'fixture',
      );
    });

    test('실서버 모드면 API 호스트명', () {
      expect(
        connectionLabel(
          useFixtures: false,
          baseUrl: 'https://trend.yeotaeho.kr/api/v1',
        ),
        'trend.yeotaeho.kr',
      );
      expect(
        connectionLabel(
          useFixtures: false,
          baseUrl: 'http://localhost:8000/api/v1',
        ),
        'localhost',
      );
    });
  });

  group('releaseConfigProblem', () {
    test('fixture 모드는 검사하지 않는다', () {
      expect(
        releaseConfigProblem(
          useFixtures: true,
          baseUrl: 'http://localhost:8000/api/v1',
          token: '',
        ),
        isNull,
      );
    });

    test('https 주소와 토큰이 있으면 문제없다', () {
      expect(
        releaseConfigProblem(
          useFixtures: false,
          baseUrl: 'https://trend.yeotaeho.kr/api/v1',
          token: 'token',
        ),
        isNull,
      );
    });

    test('http 주소는 거부한다 — 토큰이 평문으로 나간다', () {
      expect(
        releaseConfigProblem(
          useFixtures: false,
          baseUrl: 'http://trend.yeotaeho.kr/api/v1',
          token: 'token',
        ),
        contains('https'),
      );
    });

    test('빈 토큰은 거부한다 — 모든 요청이 401 이다', () {
      expect(
        releaseConfigProblem(
          useFixtures: false,
          baseUrl: 'https://trend.yeotaeho.kr/api/v1',
          token: '',
        ),
        contains('APP_API_TOKEN'),
      );
    });
  });
}
