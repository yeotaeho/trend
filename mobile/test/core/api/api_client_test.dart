// dio 클라이언트 테스트 — 베어러 헤더 부착과 오류 봉투 → ApiException 변환 (모의 어댑터).
import 'dart:convert';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/api/api_client.dart';
import 'package:tech_radar/core/api/api_exception.dart';

/// 요청을 기록하고 정해 둔 응답을 돌려주는 모의 어댑터.
class _FakeAdapter implements HttpClientAdapter {
  _FakeAdapter(this.status, this.body);

  final int status;
  final Object body;
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    return ResponseBody.fromString(
      jsonEncode(body),
      status,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

/// 연결 실패를 흉내 내는 어댑터.
class _OfflineAdapter implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) {
    throw DioException.connectionError(
      requestOptions: options,
      reason: 'offline',
    );
  }

  @override
  void close({bool force = false}) {}
}

ApiClient _client(HttpClientAdapter adapter, {String token = 'secret'}) {
  final dio = createDio(baseUrl: 'https://example.test/api/v1', token: token)
    ..httpClientAdapter = adapter;
  return ApiClient(dio);
}

void main() {
  test('기본 옵션은 타임아웃 15초', () {
    final dio = createDio(baseUrl: 'https://example.test/api/v1', token: 't');
    expect(dio.options.connectTimeout, const Duration(seconds: 15));
    expect(dio.options.receiveTimeout, const Duration(seconds: 15));
    expect(dio.options.sendTimeout, const Duration(seconds: 15));
  });

  test('모든 요청에 Authorization: Bearer 토큰을 붙인다', () async {
    final adapter = _FakeAdapter(200, {'ok': true});
    final data = await _client(adapter).get('/meta');

    expect(data, {'ok': true});
    expect(adapter.requests.single.headers['Authorization'], 'Bearer secret');
    expect(adapter.requests.single.uri.path, '/api/v1/meta');
  });

  test('토큰이 비어 있으면 Authorization 을 붙이지 않는다', () async {
    final adapter = _FakeAdapter(200, {'ok': true});
    await _client(adapter, token: '').get('/meta');

    expect(
      adapter.requests.single.headers.containsKey('Authorization'),
      isFalse,
    );
  });

  test('401 오류 봉투는 ApiException(unauthorized) 로 바뀐다', () async {
    final adapter = _FakeAdapter(401, {
      'error': {'code': 'unauthorized', 'message': '인증 토큰이 올바르지 않습니다.'},
    });

    await expectLater(
      _client(adapter).get('/meta'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', 'unauthorized')
            .having((e) => e.status, 'status', 401)
            .having((e) => e.message, 'message', '인증 토큰이 올바르지 않습니다.'),
      ),
    );
  });

  test('details 도 옮긴다', () async {
    final adapter = _FakeAdapter(422, {
      'error': {
        'code': 'validation_error',
        'message': 'selected_categories 는 1개 이상이어야 합니다.',
        'details': {'field': 'selected_categories'},
      },
    });

    await expectLater(
      _client(adapter).put('/settings/interests', body: {}),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', 'validation_error')
            .having((e) => e.details, 'details', {
              'field': 'selected_categories',
            }),
      ),
    );
  });

  test('봉투가 아닌 오류 응답은 unknown', () async {
    final adapter = _FakeAdapter(500, 'boom');

    await expectLater(
      _client(adapter).get('/meta'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', ApiException.unknown)
            .having((e) => e.status, 'status', 500),
      ),
    );
  });

  test('응답이 없으면 network', () async {
    await expectLater(
      _client(_OfflineAdapter()).get('/meta'),
      throwsA(
        isA<ApiException>()
            .having((e) => e.code, 'code', ApiException.network)
            .having((e) => e.status, 'status', isNull),
      ),
    );
  });
}
