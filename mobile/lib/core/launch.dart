// 외부 브라우저 열기 — 원문 URL 을 앱 밖에서 열고, 웹 주소가 아니거나 실패하면 스낵바로 알린다.
import 'package:flutter/widgets.dart';
import 'package:url_launcher/url_launcher.dart';

import 'snack.dart';

/// 원문 URL 은 서버를 거쳐 온 외부 데이터다. 웹 주소(http·https, 호스트 있음)만 연다.
/// `javascript:`·`intent:`·`file:` 같은 스킴은 다른 앱이나 기기 파일을 열 수 있다.
bool isWebUrl(String url) {
  final uri = Uri.tryParse(url);
  return uri != null &&
      (uri.scheme == 'http' || uri.scheme == 'https') &&
      uri.host.isNotEmpty;
}

Future<void> openExternal(
  BuildContext context,
  String url, {
  String failMessage = '원문을 열 수 없습니다.',
}) async {
  var opened = false;
  if (isWebUrl(url)) {
    try {
      opened = await launchUrl(
        Uri.parse(url),
        mode: LaunchMode.externalApplication,
      );
    } catch (_) {
      opened = false;
    }
  }
  if (!opened && context.mounted) showSnack(context, failMessage);
}
