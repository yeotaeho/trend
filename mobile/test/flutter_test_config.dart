// 테스트 전역 설정 — google_fonts 가 테스트 중 네트워크로 폰트를 받지 않게 막는다.
import 'dart:async';

import 'package:google_fonts/google_fonts.dart';

Future<void> testExecutable(FutureOr<void> Function() testMain) async {
  GoogleFonts.config.allowRuntimeFetching = false;
  await testMain();
}
