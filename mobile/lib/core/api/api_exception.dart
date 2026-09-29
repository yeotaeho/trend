// API 오류 — 계약 1.4 오류 봉투를 code·message·status 로 옮긴 예외.
import 'package:dio/dio.dart';

class ApiException implements Exception {
  const ApiException(this.code, this.message, {this.status, this.details});

  /// 서버 봉투가 없을 때 (연결 실패·시간 초과).
  static const String network = 'network';

  /// 봉투 형식이 아닌 응답.
  static const String unknown = 'unknown';

  /// 계약 1.4 `code` (`unauthorized`, `not_found`, `validation_error` …).
  final String code;

  /// 사람이 읽는 한국어 문장. 스낵바에 그대로 보여 줘도 된다.
  final String message;

  final int? status;
  final Map<String, dynamic>? details;

  factory ApiException.fromDio(DioException error) {
    final response = error.response;
    if (response == null) {
      return const ApiException(network, '서버에 연결할 수 없습니다.');
    }
    final status = response.statusCode;
    final data = response.data;
    if (data is Map && data['error'] is Map) {
      final body = data['error'] as Map;
      return ApiException(
        body['code'] as String? ?? unknown,
        body['message'] as String? ?? '알 수 없는 오류가 발생했습니다.',
        status: status,
        details: (body['details'] as Map?)?.cast<String, dynamic>(),
      );
    }
    return ApiException(unknown, '알 수 없는 오류가 발생했습니다.', status: status);
  }

  @override
  String toString() => 'ApiException($code, $status): $message';
}
