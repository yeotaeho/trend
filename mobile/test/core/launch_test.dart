// 원문 링크 검사 — 외부 데이터인 원문 URL 가운데 웹 주소(http·https)만 앱 밖에서 연다.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/launch.dart';

void main() {
  test('http·https 주소는 연다', () {
    expect(isWebUrl('https://github.com/a/b/releases/tag/v1.0.0'), isTrue);
    expect(isWebUrl('http://example.com/post?id=1'), isTrue);
    expect(isWebUrl('HTTPS://EXAMPLE.COM'), isTrue);
  });

  test('다른 스킴과 호스트 없는 주소는 열지 않는다', () {
    for (final url in [
      'javascript:alert(1)',
      'intent://scan#Intent;scheme=zxing;end',
      'file:///sdcard/secret.txt',
      'mailto:a@example.com',
      'tel:010',
      'https://',
      '',
    ]) {
      expect(isWebUrl(url), isFalse, reason: url);
    }
  });
}
