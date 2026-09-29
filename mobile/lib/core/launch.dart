// 외부 브라우저 열기 — 원문 URL 을 앱 밖에서 열고, 실패하면 스낵바로 알린다.
import 'package:flutter/widgets.dart';
import 'package:url_launcher/url_launcher.dart';

import 'snack.dart';

Future<void> openExternal(BuildContext context, String url) async {
  final uri = Uri.tryParse(url);
  var opened = false;
  if (uri != null) {
    try {
      opened = await launchUrl(uri, mode: LaunchMode.externalApplication);
    } catch (_) {
      opened = false;
    }
  }
  if (!opened && context.mounted) showSnack(context, '원문을 열 수 없습니다.');
}
