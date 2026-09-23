// 스낵바 — 쓰기 실패 문구(ApiException.message)와 `준비 중` 안내를 한 줄로 띄운다.
import 'package:flutter/material.dart';
import 'package:flutter_riverpod/flutter_riverpod.dart';

import 'api/api_exception.dart';

/// 앱 루트 ScaffoldMessenger. context 없이 띄울 때(포그라운드 푸시) 쓴다.
final messengerKeyProvider = Provider<GlobalKey<ScaffoldMessengerState>>(
  (ref) => GlobalKey<ScaffoldMessengerState>(),
);

/// 오류를 사용자 문장으로. 서버 봉투가 있으면 그 `message` 를 그대로 쓴다.
String errorMessage(Object error) =>
    error is ApiException ? error.message : '알 수 없는 오류가 발생했습니다.';

void showSnack(BuildContext context, String message) {
  ScaffoldMessenger.of(context)
    ..hideCurrentSnackBar()
    ..showSnackBar(SnackBar(content: Text(message)));
}

/// [action] 이 실패하면 오류 문구를 스낵바로 보여 준다.
Future<void> runOrSnack(
  BuildContext context,
  Future<void> Function() action,
) async {
  try {
    await action();
  } catch (error) {
    if (context.mounted) showSnack(context, errorMessage(error));
  }
}
