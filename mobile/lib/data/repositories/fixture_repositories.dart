// Fixture* 저장소 — assets/fixtures/*.json 을 메모리 상태로 올려 두고 쓰기를 다음 조회에 반영한다.
import 'dart:convert';

import 'package:flutter/services.dart';

import '../../core/api/api_exception.dart';
import '../../core/json_merge.dart';
import '../../core/labels.dart';
import '../models/models.dart';
import 'repositories.dart';

typedef _Json = Map<String, dynamic>;

ApiException _notFound(String message) =>
    ApiException('not_found', message, status: 404);

ApiException _invalid(String message, String field) => ApiException(
  'validation_error',
  message,
  status: 422,
  details: {'field': field},
);

DateTime _now() => DateTime.now().toUtc();

/// 오프셋 문자열 커서로 자른다. 기본 20건 (계약 1.3).
CursorPage<T> _paginate<T>(List<T> all, String? cursor, int? limit) {
  final start = cursor == null ? 0 : int.tryParse(cursor);
  if (start == null || start < 0) {
    throw const ApiException('bad_request', '커서를 해석할 수 없습니다.', status: 400);
  }
  final end = (start + (limit ?? 20)).clamp(start, all.length);
  return CursorPage(
    items: all.sublist(start.clamp(0, all.length), end),
    nextCursor: end < all.length ? '$end' : null,
  );
}

Rationale _withRouting(Rationale r, Routing routing) => Rationale(
  score: r.score,
  routing: routing,
  screening: r.screening,
  judgment: r.judgment,
  trustNoteSource: r.trustNoteSource,
);

/// Fixture 저장소들이 함께 쓰는 메모리 상태. 첫 호출에 fixture 를 한 번 읽는다.
class FixtureStore {
  FixtureStore({this.delay = defaultDelay});

  static const Duration defaultDelay = Duration(milliseconds: 300);

  /// 매 호출 전에 기다리는 시간. 테스트는 [Duration.zero].
  final Duration delay;

  Future<void>? _loading;

  /// 읽기가 끝났으면 [_loading] 을 다시 기다리지 않는다. 위젯 테스트가 `runAsync` 로 미리
  /// 읽어 둔 Future 는 실제 존의 것이라, fake async 에서 기다리면 끝나지 않는다.
  bool _loaded = false;

  late Meta _meta;
  late TodayStats _todayStats;
  late List<Alert> _feed;
  late Map<String, AlertDetail> _details;
  late RecentFeedback _recent;
  late InterestsSettings _interests;
  late NotificationSettings _notifications;
  late SourcesResponse _sources;
  late FilteredSummary _summary;
  late Map<FilteredView, FilteredGroups> _groups;
  late List<DroppedItem> _dropped;
  late FolderList _folders;
  late List<SavedItem> _saved;
  late Profile _profile;
  late List<ReportSummary> _reports;
  late Map<String, Report> _reportDetails;
  final Map<String, DeviceRegistration> _devices = {};
  int _nextId = 1000;

  Future<T> _run<T>(T Function() body) async {
    if (!_loaded) await (_loading ??= _load());
    if (delay > Duration.zero) await Future<void>.delayed(delay);
    return body();
  }

  Future<_Json> _read(String name) async =>
      jsonDecode(await rootBundle.loadString('assets/fixtures/$name.json'))
          as _Json;

  Future<List<T>> _readPage<T>(String name, T Function(_Json) fromJson) async =>
      CursorPage.fromJson(
        await _read(name),
        (item) => fromJson(item as _Json),
      ).items;

  Future<void> _load() async {
    _meta = Meta.fromJson(await _read('meta'));
    _todayStats = TodayStats.fromJson(await _read('stats_today'));
    _feed = await _readPage('feed', Alert.fromJson);
    _details = {
      for (final d in await _readPage('alerts', AlertDetail.fromJson))
        d.alert.id: d,
    };
    _recent = RecentFeedback.fromJson(await _read('feedback_recent'));
    _interests = InterestsSettings.fromJson(await _read('settings_interests'));
    _notifications = NotificationSettings.fromJson(
      await _read('settings_notifications'),
    );
    _sources = SourcesResponse.fromJson(await _read('sources'));
    _summary = FilteredSummary.fromJson(await _read('filtered_summary'));
    _groups = {
      for (final view in FilteredView.values)
        view: FilteredGroups.fromJson(
          await _read('filtered_groups_${view.value}'),
        ),
    };
    _dropped = await _readPage('filtered_items', DroppedItem.fromJson);
    _folders = FolderList.fromJson(await _read('folders'));
    _saved = await _readPage('saved', SavedItem.fromJson);
    _profile = Profile.fromJson(await _read('profile'));
    _reports = await _readPage('reports', ReportSummary.fromJson);
    final report = Report.fromJson(await _read('report_12'));
    _reportDetails = {report.id: report};
    _loaded = true;
  }

  // ── 알림 ──

  /// 피드·상세에 있는 알림. 걸러진 항목뿐이면 그 줄로 상세를 만들어 둔다 (`routing = dropped`).
  AlertDetail _detail(String id) {
    final known = _details[id];
    if (known != null) return known;
    final inFeed = _feed.where((a) => a.id == id).firstOrNull;
    final dropped = _dropped.where((d) => d.id == id).firstOrNull;
    if (inFeed == null && dropped == null) {
      throw _notFound('알림을 찾을 수 없습니다.');
    }
    final detail = dropped == null
        ? AlertDetail(
            alert: inFeed!,
            rationale: Rationale(
              routing: Routing.passed,
              trustNoteSource: inFeed.sourceName,
            ),
          )
        : _fromDropped(dropped);
    return _details[id] = detail;
  }

  AlertDetail _fromDropped(DroppedItem d) => AlertDetail(
    alert: Alert(
      id: d.id,
      sourceId: d.sourceId,
      sourceName: d.sourceName,
      sourceType: d.sourceType,
      isExploration: false,
      title: d.title,
      summary: '',
      categories: d.topics,
      tags: const [],
      url: d.url,
      isSaved: _saved.any((s) => s.alertId == d.id),
    ),
    rationale: Rationale(
      score: d.score,
      routing: d.droppedGate == Gate.clusterDup
          ? Routing.clusterDup
          : Routing.dropped,
      screening: d.relevance == null
          ? null
          : Screening(
              relevance: d.relevance!,
              kind: d.kind,
              topics: d.topics,
              reason: d.reason,
            ),
      trustNoteSource: d.sourceName,
    ),
  );

  /// 피드 카드와 상세 양쪽의 같은 알림을 바꾼다. 없는 곳은 건너뛴다.
  void _updateAlert(String id, Alert Function(Alert) change) {
    for (var i = 0; i < _feed.length; i++) {
      if (_feed[i].id == id) _feed[i] = change(_feed[i]);
    }
    final detail = _details[id];
    if (detail != null) {
      _details[id] = AlertDetail(
        alert: change(detail.alert),
        rationale: detail.rationale,
      );
    }
  }

  FeedbackResult _setVerdict(String id, FeedbackVerdict verdict) {
    final alert = _detail(id).alert;
    final now = _now();
    _updateAlert(id, (a) => a.withFeedback(verdict));
    _recent = RecentFeedback(
      todayCount: _recent.todayCount + (alert.feedback == null ? 1 : 0),
      items: [
        RecentFeedbackItem(
          alertId: id,
          feedback: verdict,
          title: alert.title,
          createdAt: now,
        ),
        ..._recent.items.where((i) => i.alertId != id),
      ],
    );
    return FeedbackResult(alertId: id, feedback: verdict, updatedAt: now);
  }

  void _clearVerdict(String id) {
    if (_detail(id).alert.feedback == null) return;
    _updateAlert(id, (a) => a.withFeedback(null));
    _recent = RecentFeedback(
      todayCount: (_recent.todayCount - 1).clamp(0, _recent.todayCount),
      items: _recent.items.where((i) => i.alertId != id).toList(),
    );
  }

  // ── 걸러진 항목 ──

  void _setRestored(String id, bool restored) {
    DroppedItem mark(DroppedItem d) =>
        d.id == id ? d.withRestored(restored) : d;
    _dropped = _dropped.map(mark).toList();
    for (final groups in _groups.values) {
      for (var i = 0; i < groups.groups.length; i++) {
        final g = groups.groups[i];
        groups.groups[i] = g.withPreview(g.preview.map(mark).toList());
      }
    }
  }

  // ── 찜 ──

  FolderRef _folderRef(String folderId) {
    final folder = _folders.folders.where((f) => f.id == folderId).firstOrNull;
    if (folder == null) throw _notFound('폴더를 찾을 수 없습니다.');
    return folder.ref;
  }

  /// 폴더(없으면 미분류) 개수를 더한다. [total] 이면 `전체`·`안 읽음` 칩도 같이.
  void _count(
    String? folderId, {
    required int count,
    required int unread,
    bool total = false,
  }) {
    _folders = FolderList(
      totalCount: _folders.totalCount + (total ? count : 0),
      unreadCount: _folders.unreadCount + (total ? unread : 0),
      unfiledCount: _folders.unfiledCount + (folderId == null ? count : 0),
      folders: [
        for (final f in _folders.folders)
          f.id == folderId
              ? f.copyWith(
                  count: f.count + count,
                  unreadCount: f.unreadCount + unread,
                )
              : f,
      ],
    );
  }

  int _savedIndex(String alertId) =>
      _saved.indexWhere((s) => s.alertId == alertId);

  void _moveSaved(int index, FolderRef? folder) {
    final item = _saved[index];
    final unread = item.isRead ? 0 : 1;
    _count(item.folder?.id, count: -1, unread: -unread);
    _count(folder?.id, count: 1, unread: unread);
    _saved[index] = item.copyWith(folder: () => folder);
  }

  String _folderName(String name, {String? exceptId}) {
    final trimmed = name.trim();
    if (trimmed.isEmpty || trimmed.length > _meta.limits.folderNameMax) {
      throw _invalid('폴더 이름은 1~${_meta.limits.folderNameMax}자여야 합니다.', 'name');
    }
    if (_folders.folders.any((f) => f.name == trimmed && f.id != exceptId)) {
      throw const ApiException('conflict', '같은 이름의 폴더가 있습니다.', status: 409);
    }
    return trimmed;
  }

  void _replaceFolders(List<Folder> folders) {
    _folders = FolderList(
      totalCount: _folders.totalCount,
      unreadCount: _folders.unreadCount,
      unfiledCount: _folders.unfiledCount,
      folders: [for (final (i, f) in folders.indexed) f.copyWith(position: i)],
    );
  }
}

class FixtureFeedRepository implements FeedRepository {
  const FixtureFeedRepository(this._s);

  final FixtureStore _s;

  @override
  Future<TodayStats> todayStats() => _s._run(() => _s._todayStats);

  @override
  Future<CursorPage<Alert>> feed({
    FeedFilter filter = FeedFilter.all,
    String? cursor,
    int? limit,
  }) => _s._run(() {
    bool keep(Alert a) => switch (filter) {
      FeedFilter.all => true,
      FeedFilter.instant => a.deliveryMode == DeliveryMode.instant,
      FeedFilter.quiet => a.deliveryMode == DeliveryMode.quiet,
      FeedFilter.experiment => a.deliveryMode == DeliveryMode.experiment,
      FeedFilter.useful => a.feedback == FeedbackVerdict.useful,
    };
    final items = _s._feed.where(keep).toList()
      ..sort((a, b) => b.deliveredAt!.compareTo(a.deliveredAt!));
    return _paginate(items, cursor, limit);
  });
}

class FixtureAlertRepository implements AlertRepository {
  const FixtureAlertRepository(this._s);

  final FixtureStore _s;

  @override
  Future<AlertDetail> alert(String alertId) =>
      _s._run(() => _s._detail(alertId));

  @override
  Future<FeedbackResult> setFeedback(String alertId, FeedbackVerdict verdict) =>
      _s._run(() => _s._setVerdict(alertId, verdict));

  @override
  Future<void> clearFeedback(String alertId) =>
      _s._run(() => _s._clearVerdict(alertId));

  @override
  Future<RecentFeedback> recentFeedback({int? limit}) => _s._run(
    () => RecentFeedback(
      todayCount: _s._recent.todayCount,
      items: _s._recent.items.take(limit ?? 5).toList(),
    ),
  );
}

class FixtureSettingsRepository implements SettingsRepository {
  const FixtureSettingsRepository(this._s);

  final FixtureStore _s;

  @override
  Future<InterestsSettings> interests() => _s._run(() => _s._interests);

  @override
  Future<InterestsSettings> saveInterests(InterestsSettings settings) =>
      _s._run(() {
        if (settings.selectedCategories.isEmpty) {
          throw _invalid(
            'selected_categories 는 1개 이상이어야 합니다.',
            'selected_categories',
          );
        }
        return _s._interests = InterestsSettings(
          profile: settings.profile,
          selectedCategories: settings.selectedCategories,
          watchKeywords: settings.watchKeywords,
          kindWeights: {..._s._interests.kindWeights, ...settings.kindWeights},
          updatedAt: _now(),
        );
      });

  @override
  Future<NotificationSettings> notifications() =>
      _s._run(() => _s._notifications);

  @override
  Future<NotificationSettings> updateNotifications(
    Map<String, Object?> patch,
  ) => _s._run(() {
    final current = _s._notifications.toJson();
    final channels = patch['channels'];
    if (channels is Map) {
      for (final MapEntry(:key, :value) in channels.entries) {
        final channel = (current['channels'] as _Json)[key] as _Json?;
        if (value is Map &&
            value['enabled'] == true &&
            channel?['connected'] == false) {
          throw const ApiException(
            'channel_not_connected',
            '연결 정보가 없는 채널은 켤 수 없습니다.',
            status: 409,
          );
        }
      }
    }
    return _s._notifications = NotificationSettings.fromJson({
      ...deepMerge(current, patch),
      'updated_at': _now().toIso8601String(),
    });
  });
}

class FixtureSourceRepository implements SourceRepository {
  const FixtureSourceRepository(this._s);

  final FixtureStore _s;

  @override
  Future<SourcesResponse> sources() => _s._run(() => _s._sources);

  @override
  Future<Source> setEnabled(String sourceId, {required bool enabled}) =>
      _s._run(() {
        final sources = _s._sources.sources;
        final i = sources.indexWhere((s) => s.id == sourceId);
        if (i < 0) throw _notFound('소스를 찾을 수 없습니다.');
        final before = sources[i].enabled;
        final updated = sources[i].withEnabled(enabled);
        final stats = _s._sources.stats;
        final delta = (enabled ? 1 : 0) - (before ? 1 : 0);
        _s._sources = SourcesResponse(
          stats: stats.withEnabledCount(stats.enabledCount + delta),
          sources: [...sources]..[i] = updated,
          plannedSources: _s._sources.plannedSources,
        );
        return updated;
      });
}

class FixtureFilteredRepository implements FilteredRepository {
  const FixtureFilteredRepository(this._s);

  final FixtureStore _s;

  @override
  Future<FilteredSummary> summary({int? hours}) => _s._run(() => _s._summary);

  @override
  Future<FilteredGroups> groups({
    FilteredView view = FilteredView.source,
    GroupSort sort = GroupSort.countDesc,
    int? hours,
  }) => _s._run(() {
    String name(FilteredGroup g) =>
        g.source?.displayName ?? g.kind?.label ?? g.gate?.label ?? g.key;
    int rank(FilteredGroup g) => g.key == FilteredGroup.unclassifiedKey ? 1 : 0;
    final groups = [..._s._groups[view]!.groups]
      ..sort((a, b) {
        final last = rank(a).compareTo(rank(b));
        if (last != 0) return last;
        return switch (sort) {
          GroupSort.countDesc => b.count.compareTo(a.count),
          GroupSort.nameAsc => name(a).compareTo(name(b)),
        };
      });
    return FilteredGroups(view: view, groups: groups);
  });

  @override
  Future<CursorPage<DroppedItem>> items({
    required FilteredView view,
    required String key,
    int? hours,
    String? cursor,
    int? limit,
  }) => _s._run(() {
    bool inGroup(DroppedItem d) => switch (view) {
      FilteredView.source => d.sourceId == key,
      FilteredView.kind =>
        (d.kind?.value ?? FilteredGroup.unclassifiedKey) == key,
      FilteredView.gate => d.droppedGate.value == key,
    };
    final items = _s._dropped.where(inGroup).toList()
      ..sort((a, b) => b.droppedAt.compareTo(a.droppedAt));
    return _paginate(items, cursor, limit);
  });

  @override
  Future<RestoreResult> restore(String itemId) => _s._run(() {
    final item = _s._dropped.where((d) => d.id == itemId).firstOrNull;
    if (item == null) throw _notFound('걸러진 항목을 찾을 수 없습니다.');
    if (!item.restored) {
      final detail = _s._detail(itemId);
      final base = detail.alert;
      final alert = Alert(
        id: base.id,
        sourceId: base.sourceId,
        sourceName: base.sourceName,
        sourceType: base.sourceType,
        deliveredAt: _now(),
        deliveryMode: DeliveryMode.feedOnly,
        isExploration: false,
        title: base.title,
        summary: base.summary,
        categories: base.categories,
        tags: base.tags,
        url: base.url,
        importance: base.importance,
        isSaved: base.isSaved,
        feedback: base.feedback,
      );
      _s._details[itemId] = AlertDetail(
        alert: alert,
        rationale: _withRouting(detail.rationale, Routing.restored),
      );
      _s._feed
        ..removeWhere((a) => a.id == itemId)
        ..insert(0, alert);
      _s._setRestored(itemId, true);
      _s._setVerdict(itemId, FeedbackVerdict.useful);
    }
    return RestoreResult(
      itemId: itemId,
      restored: true,
      alert: _s._detail(itemId).alert,
    );
  });

  @override
  Future<void> cancelRestore(String itemId) => _s._run(() {
    final item = _s._dropped.where((d) => d.id == itemId).firstOrNull;
    if (item == null || !item.restored) return;
    _s._clearVerdict(itemId);
    _s._feed.removeWhere((a) => a.id == itemId);
    final detail = _s._details[itemId]!;
    _s._details[itemId] = AlertDetail(
      alert: detail.alert,
      rationale: _withRouting(
        detail.rationale,
        item.droppedGate == Gate.clusterDup
            ? Routing.clusterDup
            : Routing.dropped,
      ),
    );
    _s._setRestored(itemId, false);
  });
}

class FixtureSavedRepository implements SavedRepository {
  const FixtureSavedRepository(this._s);

  final FixtureStore _s;

  @override
  Future<FolderList> folders() => _s._run(() => _s._folders);

  @override
  Future<Folder> createFolder(String name) => _s._run(() {
    final folder = Folder(
      id: '${_s._nextId++}',
      name: _s._folderName(name),
      count: 0,
      unreadCount: 0,
      position: _s._folders.folders.length,
    );
    _s._replaceFolders([..._s._folders.folders, folder]);
    return folder;
  });

  @override
  Future<Folder> updateFolder(String folderId, {String? name, int? position}) =>
      _s._run(() {
        _s._folderRef(folderId);
        final folders = [..._s._folders.folders];
        final i = folders.indexWhere((f) => f.id == folderId);
        var folder = folders.removeAt(i);
        if (name != null) {
          folder = folder.copyWith(
            name: _s._folderName(name, exceptId: folderId),
          );
          for (var j = 0; j < _s._saved.length; j++) {
            if (_s._saved[j].folder?.id == folderId) {
              _s._saved[j] = _s._saved[j].copyWith(folder: () => folder.ref);
            }
          }
        }
        folders.insert((position ?? i).clamp(0, folders.length), folder);
        _s._replaceFolders(folders);
        return _s._folders.folders.firstWhere((f) => f.id == folderId);
      });

  @override
  Future<void> deleteFolder(String folderId) => _s._run(() {
    final folder = _s._folders.folders
        .where((f) => f.id == folderId)
        .firstOrNull;
    if (folder == null) throw _notFound('폴더를 찾을 수 없습니다.');
    for (var i = 0; i < _s._saved.length; i++) {
      if (_s._saved[i].folder?.id == folderId) {
        _s._saved[i] = _s._saved[i].copyWith(folder: () => null);
      }
    }
    _s._count(null, count: folder.count, unread: 0);
    _s._replaceFolders(
      _s._folders.folders.where((f) => f.id != folderId).toList(),
    );
  });

  @override
  Future<CursorPage<SavedItem>> saved({
    String? folderId,
    bool unreadOnly = false,
    SavedSort sort = SavedSort.savedDesc,
    String? cursor,
    int? limit,
  }) => _s._run(() {
    bool keep(SavedItem s) =>
        (folderId == null ||
            (folderId == SavedRepository.unfiled
                ? s.folder == null
                : s.folder?.id == folderId)) &&
        (!unreadOnly || !s.isRead);
    final epoch = DateTime.utc(0);
    final items = _s._saved.where(keep).toList()
      ..sort(
        (a, b) => switch (sort) {
          SavedSort.savedDesc => b.savedAt.compareTo(a.savedAt),
          SavedSort.savedAsc => a.savedAt.compareTo(b.savedAt),
          SavedSort.deliveredDesc => (b.deliveredAt ?? epoch).compareTo(
            a.deliveredAt ?? epoch,
          ),
        },
      );
    return _paginate(items, cursor, limit);
  });

  @override
  Future<SavedItem> save(String alertId, {String? folderId}) => _s._run(() {
    final folder = folderId == null ? null : _s._folderRef(folderId);
    final existing = _s._savedIndex(alertId);
    if (existing >= 0) {
      if (folderId != null) _s._moveSaved(existing, folder);
      return _s._saved[existing];
    }
    final alert = _s._detail(alertId).alert;
    final item = SavedItem(
      alertId: alertId,
      sourceName: alert.sourceName,
      title: alert.title,
      url: alert.url,
      deliveredAt: alert.deliveredAt,
      savedAt: _now(),
      folder: folder,
      isRead: false,
    );
    _s._saved.insert(0, item);
    _s._count(folder?.id, count: 1, unread: 1, total: true);
    _s._updateAlert(alertId, (a) => a.withSaved(true));
    return item;
  });

  @override
  Future<SavedItem> update(String alertId, SavedItemPatch patch) => _s._run(() {
    final i = _s._savedIndex(alertId);
    if (i < 0) throw _notFound('찜을 찾을 수 없습니다.');
    final body = patch.body;
    if (body.containsKey('folder_id')) {
      final folderId = body['folder_id'] as String?;
      _s._moveSaved(i, folderId == null ? null : _s._folderRef(folderId));
    }
    if (body.containsKey('memo')) {
      final memo = body['memo'] as String?;
      if (memo != null && memo.length > _s._meta.limits.memoMax) {
        throw _invalid('메모는 ${_s._meta.limits.memoMax}자 이하여야 합니다.', 'memo');
      }
      _s._saved[i] = _s._saved[i].copyWith(
        memo: () => memo == null || memo.isEmpty ? null : memo,
      );
    }
    if (body['is_read'] == true && !_s._saved[i].isRead) {
      _s._count(_s._saved[i].folder?.id, count: 0, unread: -1, total: true);
      _s._saved[i] = _s._saved[i].copyWith(isRead: true, readAt: () => _now());
    }
    return _s._saved[i];
  });

  @override
  Future<void> unsave(String alertId) => _s._run(() {
    final i = _s._savedIndex(alertId);
    if (i < 0) return;
    final item = _s._saved.removeAt(i);
    _s._count(
      item.folder?.id,
      count: -1,
      unread: item.isRead ? 0 : -1,
      total: true,
    );
    _s._updateAlert(alertId, (a) => a.withSaved(false));
  });
}

class FixtureProfileRepository implements ProfileRepository {
  const FixtureProfileRepository(this._s);

  final FixtureStore _s;

  Profile _with({int? periodDays, ProfileUser? user}) {
    final p = _s._profile;
    return Profile(
      periodDays: periodDays ?? p.periodDays,
      user: user ?? p.user,
      stats: p.stats,
      categoryReactions: p.categoryReactions,
      learned: p.learned,
      weeklyReportLatest: p.weeklyReportLatest,
    );
  }

  @override
  Future<Profile> profile({int periodDays = 14}) =>
      _s._run(() => _with(periodDays: periodDays));

  @override
  Future<Profile> updateDisplayName(String displayName) => _s._run(() {
    final name = displayName.trim();
    if (name.isEmpty || name.length > 20) {
      throw _invalid('표시 이름은 1~20자여야 합니다.', 'display_name');
    }
    final user = _s._profile.user;
    return _s._profile = _with(
      user: ProfileUser(
        displayName: name,
        discordConnected: user.discordConnected,
        onboardingDone: user.onboardingDone,
        onboardingTotal: user.onboardingTotal,
      ),
    );
  });

  @override
  Future<CursorPage<ReportSummary>> reports({String? cursor, int? limit}) =>
      _s._run(() => _paginate(_s._reports, cursor, limit));

  @override
  Future<Report> report(String reportId) => _s._run(
    () => _s._reportDetails[reportId] ?? (throw _notFound('리포트를 찾을 수 없습니다.')),
  );
}

class FixtureMetaRepository implements MetaRepository {
  const FixtureMetaRepository(this._s);

  final FixtureStore _s;

  @override
  Future<Meta> meta() => _s._run(() => _s._meta);
}

class FixtureDeviceRepository implements DeviceRepository {
  const FixtureDeviceRepository(this._s);

  final FixtureStore _s;

  @override
  Future<DeviceRegistration> register({
    required String token,
    required DevicePlatform platform,
    String? appVersion,
  }) => _s._run(
    () => _s._devices[token] ??= DeviceRegistration(
      id: '${_s._nextId++}',
      platform: platform,
      registeredAt: _now(),
    ),
  );

  @override
  Future<void> unregister(String token) => _s._run(() {
    _s._devices.remove(token);
  });
}
