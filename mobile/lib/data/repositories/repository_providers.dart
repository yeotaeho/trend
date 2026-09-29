// 저장소 프로바이더 — useFixturesProvider 로 Fixture*(메모리)·Api*(dio) 구현을 고른다.
import 'package:flutter_riverpod/flutter_riverpod.dart';

import '../../core/providers.dart';
import '../../core/api/api_client.dart';
import 'api_repositories.dart';
import 'fixture_repositories.dart';
import 'repositories.dart';

/// Fixture 저장소들이 함께 쓰는 메모리 상태. 쓰기가 다른 화면의 다음 조회에 보인다.
final fixtureStoreProvider = Provider<FixtureStore>((ref) => FixtureStore());

T _pick<T>(
  Ref ref,
  T Function(FixtureStore store) fixture,
  T Function(ApiClient api) api,
) => ref.watch(useFixturesProvider)
    ? fixture(ref.watch(fixtureStoreProvider))
    : api(ref.watch(apiClientProvider));

final feedRepositoryProvider = Provider<FeedRepository>(
  (ref) => _pick(ref, FixtureFeedRepository.new, ApiFeedRepository.new),
);

final alertRepositoryProvider = Provider<AlertRepository>(
  (ref) => _pick(ref, FixtureAlertRepository.new, ApiAlertRepository.new),
);

final settingsRepositoryProvider = Provider<SettingsRepository>(
  (ref) => _pick(ref, FixtureSettingsRepository.new, ApiSettingsRepository.new),
);

final sourceRepositoryProvider = Provider<SourceRepository>(
  (ref) => _pick(ref, FixtureSourceRepository.new, ApiSourceRepository.new),
);

final filteredRepositoryProvider = Provider<FilteredRepository>(
  (ref) => _pick(ref, FixtureFilteredRepository.new, ApiFilteredRepository.new),
);

final savedRepositoryProvider = Provider<SavedRepository>(
  (ref) => _pick(ref, FixtureSavedRepository.new, ApiSavedRepository.new),
);

final profileRepositoryProvider = Provider<ProfileRepository>(
  (ref) => _pick(ref, FixtureProfileRepository.new, ApiProfileRepository.new),
);

final metaRepositoryProvider = Provider<MetaRepository>(
  (ref) => _pick(ref, FixtureMetaRepository.new, ApiMetaRepository.new),
);

final deviceRepositoryProvider = Provider<DeviceRepository>(
  (ref) => _pick(ref, FixtureDeviceRepository.new, ApiDeviceRepository.new),
);
