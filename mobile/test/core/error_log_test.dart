// 오류 로그 — 실패한 프로바이더와 runOrSnack 이 문구로 바꾼 예외가 원인과 함께 로그에 남는지.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/error_log.dart';
import 'package:tech_radar/core/snack.dart';

/// [body] 동안 debugPrint 출력을 모은다. 위젯 테스트는 끝나기 전에 원래 함수로 되돌려야 한다.
Future<List<String>> _captureLogs(Future<void> Function() body) async {
  final logs = <String>[];
  final original = debugPrint;
  debugPrint = (message, {wrapWidth}) => logs.add(message ?? '');
  try {
    await body();
  } finally {
    debugPrint = original;
  }
  return logs;
}

void main() {
  test('실패한 프로바이더는 오류와 스택을 로그에 남긴다', () async {
    final failing = FutureProvider<int>((ref) => throw StateError('boom'));
    final container = ProviderContainer(
      observers: const [ErrorLogObserver()],
      retry: (retryCount, error) => null,
    );
    addTearDown(container.dispose);

    final logs = await _captureLogs(() async {
      await expectLater(
        container.read(failing.future),
        throwsA(isA<StateError>()),
      );
    });

    expect(logs.join('\n'), contains('boom'));
  });

  testWidgets('runOrSnack 은 문구를 띄우고, 삼킨 예외는 로그에 남긴다', (tester) async {
    await tester.pumpWidget(
      MaterialApp(
        home: Scaffold(
          body: Builder(
            builder: (context) => TextButton(
              onPressed: () => runOrSnack(
                context,
                () async => throw const FormatException('bad json'),
              ),
              child: const Text('저장'),
            ),
          ),
        ),
      ),
    );

    final logs = await _captureLogs(() async {
      await tester.tap(find.text('저장'));
      await tester.pump();
    });

    expect(find.text('알 수 없는 오류가 발생했습니다.'), findsOneWidget);
    expect(logs.join('\n'), contains('bad json'));
  });
}
