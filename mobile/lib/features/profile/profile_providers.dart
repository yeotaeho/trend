// 08 내 프로필 상태 — 선택한 기간(7·14·30일), 그 기간의 프로필 조회, 리포트 상세 조회.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../data/models/models.dart';
import '../../data/repositories/repository_providers.dart';

/// 기간 선택지 (계약 4.8 `period_days`).
const List<int> profilePeriods = [7, 14, 30];

class ProfilePeriod extends Notifier<int> {
  @override
  int build() => 14;

  void select(int days) => state = days;
}

final profilePeriodProvider = NotifierProvider<ProfilePeriod, int>(
  ProfilePeriod.new,
);

/// 기간이 바뀌면 `period_days` 쿼리로 다시 조회한다.
final profileProvider = FutureProvider<Profile>(
  (ref) => ref
      .watch(profileRepositoryProvider)
      .profile(periodDays: ref.watch(profilePeriodProvider)),
);

final reportProvider = FutureProvider.autoDispose.family<Report, String>(
  (ref, reportId) => ref.watch(profileRepositoryProvider).report(reportId),
);
