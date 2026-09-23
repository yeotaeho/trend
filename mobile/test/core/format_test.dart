// format.dart 단위 테스트 — 상대시간 경계(59분·23시간·어제)와 점수 부호.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/format.dart';

void main() {
  group('relativeTime', () {
    final now = DateTime(2026, 9, 24, 10, 0);

    String ago(Duration d, {bool suffix = true}) =>
        relativeTime(now.subtract(d), now: now, suffix: suffix);

    test('1분 미만은 1분 전', () {
      expect(ago(const Duration(seconds: 30)), '1분 전');
    });

    test('59분까지는 분 단위', () {
      expect(ago(const Duration(minutes: 59, seconds: 59)), '59분 전');
    });

    test('60분부터 시간 단위', () {
      expect(ago(const Duration(minutes: 60)), '1시간 전');
    });

    test('23시간 59분까지는 시간 단위', () {
      expect(ago(const Duration(hours: 23, minutes: 59)), '23시간 전');
    });

    test('24시간이 지나고 달력상 어제면 어제', () {
      expect(ago(const Duration(hours: 24)), '어제');
      expect(relativeTime(DateTime(2026, 9, 23, 0, 5), now: now), '어제');
    });

    test('자정 직후라도 24시간 안이면 시간 단위', () {
      final earlyMorning = DateTime(2026, 9, 24, 0, 30);
      expect(
        relativeTime(DateTime(2026, 9, 23, 23, 0), now: earlyMorning),
        '1시간 전',
      );
    });

    test('그제부터는 M월 d일', () {
      expect(relativeTime(DateTime(2026, 9, 22, 23, 0), now: now), '9월 22일');
    });

    test('suffix 가 false 면 전 을 뗀다', () {
      expect(ago(const Duration(minutes: 42), suffix: false), '42분');
    });

    test('UTC 시각은 로컬로 바꿔 계산한다', () {
      final utcNow = now.toUtc();
      expect(
        relativeTime(utcNow.subtract(const Duration(minutes: 5)), now: now),
        '5분 전',
      );
    });
  });

  group('formatScore', () {
    test('2자리로 반올림한다', () {
      expect(formatScore(0.4123), '0.41');
      expect(formatScore(0), '0.00');
    });

    test('음수는 유니코드 마이너스를 쓴다', () {
      expect(formatScore(-0.15), '${minusSign}0.15');
      expect(formatScore(-0.15).codeUnitAt(0), 0x2212);
    });

    test('반올림해서 0 이 되는 음수는 부호를 붙이지 않는다', () {
      expect(formatScore(-0.001), '0.00');
    });
  });

  group('formatSignedScore', () {
    test('양수와 0 은 + 를 붙인다', () {
      expect(formatSignedScore(0.25), '+0.25');
      expect(formatSignedScore(0), '+0.00');
    });

    test('음수는 유니코드 마이너스', () {
      expect(formatSignedScore(-0.3), '${minusSign}0.30');
    });
  });
}
