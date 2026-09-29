// 저장소 인터페이스 — 화면이 쓰는 계약 4 의 호출. 구현은 Api*(dio)·Fixture*(메모리) 둘이다.
import '../../core/labels.dart';
import '../models/models.dart';

/// 03 피드.
abstract interface class FeedRepository {
  Future<TodayStats> todayStats();

  Future<CursorPage<Alert>> feed({
    FeedFilter filter = FeedFilter.all,
    String? cursor,
    int? limit,
  });
}

/// 07 상세·근거와 판정 (03 피드 카드의 판정 버튼도 여기로).
abstract interface class AlertRepository {
  Future<AlertDetail> alert(String alertId);

  Future<FeedbackResult> setFeedback(String alertId, FeedbackVerdict verdict);

  Future<void> clearFeedback(String alertId);

  Future<RecentFeedback> recentFeedback({int? limit});
}

/// 04 관심사 · 05 알림 설정.
abstract interface class SettingsRepository {
  Future<InterestsSettings> interests();

  /// 명시 저장 (`PUT` 전체 교체). 저장 후 GET 과 같은 객체를 돌려준다.
  Future<InterestsSettings> saveInterests(InterestsSettings settings);

  Future<NotificationSettings> notifications();

  /// 즉시 저장 (`PATCH`). [patch] 는 바꿀 키만 담은 중첩 맵이다
  /// (`{"channels": {"telegram": {"enabled": true}}}`).
  Future<NotificationSettings> updateNotifications(Map<String, Object?> patch);
}

/// 06 수집 소스.
abstract interface class SourceRepository {
  Future<SourcesResponse> sources();

  Future<Source> setEnabled(String sourceId, {required bool enabled});
}

/// 09 · 10 걸러진 항목.
abstract interface class FilteredRepository {
  Future<FilteredSummary> summary({int? hours});

  Future<FilteredGroups> groups({
    FilteredView view = FilteredView.source,
    GroupSort sort = GroupSort.countDesc,
    int? hours,
  });

  Future<CursorPage<DroppedItem>> items({
    required FilteredView view,
    required String key,
    int? hours,
    String? cursor,
    int? limit,
  });

  Future<RestoreResult> restore(String itemId);

  Future<void> cancelRestore(String itemId);
}

/// 11 찜 — 폴더와 찜.
abstract interface class SavedRepository {
  /// [saved] 의 `folderId` 로 미분류만 고를 때 쓰는 값.
  static const String unfiled = 'unfiled';

  Future<FolderList> folders();

  Future<Folder> createFolder(String name);

  Future<Folder> updateFolder(String folderId, {String? name, int? position});

  Future<void> deleteFolder(String folderId);

  /// [folderId] 가 없으면 전체, [unfiled] 면 미분류만.
  Future<CursorPage<SavedItem>> saved({
    String? folderId,
    bool unreadOnly = false,
    SavedSort sort = SavedSort.savedDesc,
    String? cursor,
    int? limit,
  });

  /// 찜 추가 (`PUT`). [folderId] 가 없으면 미분류이고, 이미 찜했으면 폴더를 바꾸지 않는다.
  Future<SavedItem> save(String alertId, {String? folderId});

  Future<SavedItem> update(String alertId, SavedItemPatch patch);

  Future<void> unsave(String alertId);
}

/// `PATCH /saved/{alert_id}` 본문. 계약 예시처럼 한 번에 한 가지만 바꾼다.
class SavedItemPatch {
  const SavedItemPatch._(this.body);

  /// [folderId] 가 `null` 이면 미분류로 옮긴다.
  SavedItemPatch.folder(String? folderId) : this._({'folder_id': folderId});

  /// `null` 이나 빈 문자열이면 메모를 지운다.
  SavedItemPatch.memo(String? memo) : this._({'memo': memo});

  const SavedItemPatch.read() : this._(const {'is_read': true});

  final Map<String, Object?> body;
}

/// 08 내 프로필 · 주간 리포트.
abstract interface class ProfileRepository {
  Future<Profile> profile({int periodDays = 14});

  Future<Profile> updateDisplayName(String displayName);

  Future<CursorPage<ReportSummary>> reports({String? cursor, int? limit});

  Future<Report> report(String reportId);
}

abstract interface class MetaRepository {
  Future<Meta> meta();
}

/// FCM 기기 등록.
abstract interface class DeviceRepository {
  Future<DeviceRegistration> register({
    required String token,
    required DevicePlatform platform,
    String? appVersion,
  });

  Future<void> unregister(String token);
}
