// 표시 형식 — 상대시간(N분 전·N시간 전·어제·M월 d일)과 점수 2자리·유니코드 − 부호.

/// 유니코드 마이너스 (U+2212). 하이픈 대신 쓴다.
const String minusSign = '−';

/// 알림 시각을 상대시간으로 바꾼다.
///
/// 1시간 미만은 `N분 전`(최소 1분), 24시간 미만은 `N시간 전`, 그보다 오래되면
/// 달력 기준 어제는 `어제`, 그 전은 `M월 d일`. [suffix] 가 false 면 ` 전` 을 뗀다
/// (07 최근 판정의 `42분`).
String relativeTime(DateTime at, {DateTime? now, bool suffix = true}) {
  final local = at.toLocal();
  final current = (now ?? DateTime.now()).toLocal();
  final diff = current.difference(local);
  final ago = suffix ? ' 전' : '';

  if (diff.inMinutes < 60) {
    final minutes = diff.inMinutes < 1 ? 1 : diff.inMinutes;
    return '$minutes분$ago';
  }
  if (diff.inHours < 24) {
    return '${diff.inHours}시간$ago';
  }
  final today = DateTime(current.year, current.month, current.day);
  final day = DateTime(local.year, local.month, local.day);
  if (today.difference(day).inDays == 1) {
    return '어제';
  }
  return '${local.month}월 ${local.day}일';
}

/// 점수 2자리. 음수는 `−0.15` 처럼 U+2212 를 붙인다.
String formatScore(double value) => _signed(value, positive: '');

/// 부호를 항상 붙인 점수 2자리 (`+0.00`, `−0.15`). 04 kind 가중치용.
String formatSignedScore(double value) => _signed(value, positive: '+');

String _signed(double value, {required String positive}) {
  final digits = value.abs().toStringAsFixed(2);
  final isNegative = value < 0 && digits != '0.00';
  return '${isNegative ? minusSign : positive}$digits';
}
