// Api* 저장소 — 계약 4 의 경로·쿼리·본문으로 dio 를 부르고 응답을 모델로 옮긴다.
import '../../core/api/api_client.dart';
import '../../core/labels.dart';
import '../models/models.dart';
import 'repositories.dart';

typedef _Json = Map<String, dynamic>;

/// 값이 `null` 인 키를 뺀다 — 쿼리는 서버 기본값을 쓰고, 본문은 보낸 키만 바뀐다.
Map<String, dynamic> _withoutNulls(Map<String, Object?> params) => {
  for (final MapEntry(:key, :value) in params.entries) key: ?value,
};

/// 경로 조각 — 소스 ID(`rss:anthropic`)·FCM 토큰은 URL 인코딩한다 (계약 1.2).
String _seg(String value) => Uri.encodeComponent(value);

CursorPage<T> _page<T>(Object? json, T Function(_Json json) fromJson) =>
    CursorPage.fromJson(json as _Json, (item) => fromJson(item as _Json));

class ApiFeedRepository implements FeedRepository {
  const ApiFeedRepository(this._api);

  final ApiClient _api;

  @override
  Future<TodayStats> todayStats() async =>
      TodayStats.fromJson(await _api.get('/stats/today') as _Json);

  @override
  Future<CursorPage<Alert>> feed({
    FeedFilter filter = FeedFilter.all,
    String? cursor,
    int? limit,
  }) async => _page(
    await _api.get(
      '/feed',
      query: _withoutNulls({
        'filter': filter.value,
        'cursor': cursor,
        'limit': limit,
      }),
    ),
    Alert.fromJson,
  );
}

class ApiAlertRepository implements AlertRepository {
  const ApiAlertRepository(this._api);

  final ApiClient _api;

  @override
  Future<AlertDetail> alert(String alertId) async =>
      AlertDetail.fromJson(await _api.get('/alerts/${_seg(alertId)}') as _Json);

  @override
  Future<FeedbackResult> setFeedback(
    String alertId,
    FeedbackVerdict verdict,
  ) async => FeedbackResult.fromJson(
    await _api.put(
      '/alerts/${_seg(alertId)}/feedback',
      body: {'verdict': verdict.value},
    ) as _Json,
  );

  @override
  Future<void> clearFeedback(String alertId) =>
      _api.delete('/alerts/${_seg(alertId)}/feedback');

  @override
  Future<RecentFeedback> recentFeedback({int? limit}) async =>
      RecentFeedback.fromJson(
        await _api.get(
          '/feedback/recent',
          query: _withoutNulls({'limit': limit}),
        ) as _Json,
      );
}

class ApiSettingsRepository implements SettingsRepository {
  const ApiSettingsRepository(this._api);

  final ApiClient _api;

  @override
  Future<InterestsSettings> interests() async => InterestsSettings.fromJson(
    await _api.get('/settings/interests') as _Json,
  );

  @override
  Future<InterestsSettings> saveInterests(InterestsSettings settings) async =>
      InterestsSettings.fromJson(
        await _api.put('/settings/interests', body: settings.toJson()) as _Json,
      );

  @override
  Future<NotificationSettings> notifications() async =>
      NotificationSettings.fromJson(
        await _api.get('/settings/notifications') as _Json,
      );

  @override
  Future<NotificationSettings> updateNotifications(
    Map<String, Object?> patch,
  ) async => NotificationSettings.fromJson(
    await _api.patch('/settings/notifications', body: patch) as _Json,
  );
}

class ApiSourceRepository implements SourceRepository {
  const ApiSourceRepository(this._api);

  final ApiClient _api;

  @override
  Future<SourcesResponse> sources() async =>
      SourcesResponse.fromJson(await _api.get('/sources') as _Json);

  @override
  Future<Source> setEnabled(String sourceId, {required bool enabled}) async =>
      Source.fromJson(
        await _api.patch(
          '/sources/${_seg(sourceId)}',
          body: {'enabled': enabled},
        ) as _Json,
      );
}

class ApiFilteredRepository implements FilteredRepository {
  const ApiFilteredRepository(this._api);

  final ApiClient _api;

  @override
  Future<FilteredSummary> summary({int? hours}) async =>
      FilteredSummary.fromJson(
        await _api.get(
          '/filtered/summary',
          query: _withoutNulls({'hours': hours}),
        ) as _Json,
      );

  @override
  Future<FilteredGroups> groups({
    FilteredView view = FilteredView.source,
    GroupSort sort = GroupSort.countDesc,
    int? hours,
  }) async => FilteredGroups.fromJson(
    await _api.get(
      '/filtered/groups',
      query: _withoutNulls({
        'view': view.value,
        'sort': sort.value,
        'hours': hours,
      }),
    ) as _Json,
  );

  @override
  Future<CursorPage<DroppedItem>> items({
    required FilteredView view,
    required String key,
    int? hours,
    String? cursor,
    int? limit,
  }) async => _page(
    await _api.get(
      '/filtered/items',
      query: _withoutNulls({
        'view': view.value,
        'key': key,
        'hours': hours,
        'cursor': cursor,
        'limit': limit,
      }),
    ),
    DroppedItem.fromJson,
  );

  @override
  Future<RestoreResult> restore(String itemId) async => RestoreResult.fromJson(
    await _api.post('/filtered/items/${_seg(itemId)}/restore') as _Json,
  );

  @override
  Future<void> cancelRestore(String itemId) =>
      _api.delete('/filtered/items/${_seg(itemId)}/restore');
}

class ApiSavedRepository implements SavedRepository {
  const ApiSavedRepository(this._api);

  final ApiClient _api;

  @override
  Future<FolderList> folders() async =>
      FolderList.fromJson(await _api.get('/folders') as _Json);

  @override
  Future<Folder> createFolder(String name) async => Folder.fromJson(
    await _api.post('/folders', body: {'name': name}) as _Json,
  );

  @override
  Future<Folder> updateFolder(
    String folderId, {
    String? name,
    int? position,
  }) async => Folder.fromJson(
    await _api.patch(
      '/folders/${_seg(folderId)}',
      body: _withoutNulls({'name': name, 'position': position}),
    ) as _Json,
  );

  @override
  Future<void> deleteFolder(String folderId) =>
      _api.delete('/folders/${_seg(folderId)}');

  @override
  Future<CursorPage<SavedItem>> saved({
    String? folderId,
    bool unreadOnly = false,
    SavedSort sort = SavedSort.savedDesc,
    String? cursor,
    int? limit,
  }) async => _page(
    await _api.get(
      '/saved',
      query: _withoutNulls({
        'folder_id': folderId,
        'unread_only': unreadOnly,
        'sort': sort.value,
        'cursor': cursor,
        'limit': limit,
      }),
    ),
    SavedItem.fromJson,
  );

  @override
  Future<SavedItem> save(String alertId, {String? folderId}) async =>
      SavedItem.fromJson(
        await _api.put(
          '/saved/${_seg(alertId)}',
          body: _withoutNulls({'folder_id': folderId}),
        ) as _Json,
      );

  @override
  Future<SavedItem> update(String alertId, SavedItemPatch patch) async =>
      SavedItem.fromJson(
        await _api.patch('/saved/${_seg(alertId)}', body: patch.body) as _Json,
      );

  @override
  Future<void> unsave(String alertId) => _api.delete('/saved/${_seg(alertId)}');
}

class ApiProfileRepository implements ProfileRepository {
  const ApiProfileRepository(this._api);

  final ApiClient _api;

  @override
  Future<Profile> profile({int periodDays = 14}) async => Profile.fromJson(
    await _api.get('/profile', query: {'period_days': periodDays}) as _Json,
  );

  @override
  Future<Profile> updateDisplayName(String displayName) async =>
      Profile.fromJson(
        await _api.patch('/profile', body: {'display_name': displayName})
            as _Json,
      );

  @override
  Future<CursorPage<ReportSummary>> reports({
    String? cursor,
    int? limit,
  }) async => _page(
    await _api.get(
      '/reports',
      query: _withoutNulls({'cursor': cursor, 'limit': limit}),
    ),
    ReportSummary.fromJson,
  );

  @override
  Future<Report> report(String reportId) async =>
      Report.fromJson(await _api.get('/reports/${_seg(reportId)}') as _Json);
}

class ApiMetaRepository implements MetaRepository {
  const ApiMetaRepository(this._api);

  final ApiClient _api;

  @override
  Future<Meta> meta() async => Meta.fromJson(await _api.get('/meta') as _Json);
}

class ApiDeviceRepository implements DeviceRepository {
  const ApiDeviceRepository(this._api);

  final ApiClient _api;

  @override
  Future<DeviceRegistration> register({
    required String token,
    required DevicePlatform platform,
    String? appVersion,
  }) async => DeviceRegistration.fromJson(
    await _api.post(
      '/devices',
      body: _withoutNulls({
        'token': token,
        'platform': platform.value,
        'app_version': appVersion,
      }),
    ) as _Json,
  );

  @override
  Future<void> unregister(String token) =>
      _api.delete('/devices/${_seg(token)}');
}
