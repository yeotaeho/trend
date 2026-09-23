// 설정 루트 프로바이더 — 하위 화면 요약(카테고리·push 상한·활성 소스), 표시 이름, 앱 버전.
import 'package:flutter_riverpod/flutter_riverpod.dart';
import 'package:package_info_plus/package_info_plus.dart';

import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

/// `GET /meta`. 앱이 떠 있는 동안 한 번 읽고 캐시한다.
final metaProvider = FutureProvider<Meta>(
  (ref) => ref.watch(metaRepositoryProvider).meta(),
);

/// `관심사` 보조 줄 — 선택한 카테고리 수와 taxonomy 전체 수.
final categorySummaryProvider = FutureProvider<({int selected, int total})>((
  ref,
) async {
  final interests = await ref.watch(settingsRepositoryProvider).interests();
  final meta = await ref.watch(metaProvider.future);
  return (
    selected: interests.selectedCategories.length,
    total: meta.taxonomy.length,
  );
});

/// `알림 설정` 보조 줄 — 하루 push 상한.
final pushCapSummaryProvider = FutureProvider<int>(
  (ref) async => (await ref.watch(settingsRepositoryProvider).notifications())
      .dailyPushCap,
);

/// `수집 소스` 보조 줄 — 켜진 소스 수와 전체 수.
final sourceSummaryProvider = FutureProvider<SourceStats>(
  (ref) async => (await ref.watch(sourceRepositoryProvider).sources()).stats,
);

/// `표시 이름` 행 값.
final displayNameProvider = FutureProvider<String>(
  (ref) async =>
      (await ref.watch(profileRepositoryProvider).profile()).user.displayName,
);

/// `앱 버전` 행 값 (`0.1.0`).
final appVersionProvider = FutureProvider<String>(
  (ref) async => (await PackageInfo.fromPlatform()).version,
);
