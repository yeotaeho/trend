// dio 클라이언트 — 베어러 토큰 인터셉터, 15초 타임아웃, 오류 봉투 → ApiException 변환.
import 'package:dio/dio.dart';

import 'api_exception.dart';

const Duration apiTimeout = Duration(seconds: 15);

/// 모든 요청에 `Authorization: Bearer <APP_API_TOKEN>` 을 붙인다 (계약 1.1).
class AuthInterceptor extends Interceptor {
  AuthInterceptor(this.token);

  final String token;

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (token.isNotEmpty) {
      options.headers['Authorization'] = 'Bearer $token';
    }
    handler.next(options);
  }
}

/// 실패한 응답의 오류 봉투(계약 1.4)를 `DioException.error` 의 [ApiException] 으로 바꾼다.
class ErrorEnvelopeInterceptor extends Interceptor {
  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    handler.next(err.copyWith(error: ApiException.fromDio(err)));
  }
}

Dio createDio({required String baseUrl, required String token}) {
  return Dio(
    BaseOptions(
      baseUrl: baseUrl,
      connectTimeout: apiTimeout,
      receiveTimeout: apiTimeout,
      sendTimeout: apiTimeout,
      contentType: Headers.jsonContentType,
      responseType: ResponseType.json,
    ),
  )..interceptors.addAll([AuthInterceptor(token), ErrorEnvelopeInterceptor()]);
}

/// 저장소가 쓰는 얇은 래퍼. 실패는 항상 [ApiException] 으로 던진다.
class ApiClient {
  ApiClient(this.dio);

  final Dio dio;

  Future<dynamic> get(String path, {Map<String, dynamic>? query}) =>
      _send('GET', path, query: query);

  Future<dynamic> post(String path, {Object? body}) =>
      _send('POST', path, body: body);

  Future<dynamic> put(String path, {Object? body}) =>
      _send('PUT', path, body: body);

  Future<dynamic> patch(String path, {Object? body}) =>
      _send('PATCH', path, body: body);

  Future<dynamic> delete(String path) => _send('DELETE', path);

  Future<dynamic> _send(
    String method,
    String path, {
    Map<String, dynamic>? query,
    Object? body,
  }) async {
    try {
      final response = await dio.request<dynamic>(
        path,
        data: body,
        queryParameters: query,
        options: Options(method: method),
      );
      return response.data;
    } on DioException catch (e) {
      final error = e.error;
      throw error is ApiException ? error : ApiException.fromDio(e);
    }
  }
}
