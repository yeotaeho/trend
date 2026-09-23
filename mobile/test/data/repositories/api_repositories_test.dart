// Api* 저장소 테스트 — dio 모의 어댑터로 엔드포인트마다 메서드·경로·쿼리·본문과 응답 변환을 본다.
import 'dart:convert';
import 'dart:io';
import 'dart:typed_data';

import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/api/api_client.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/api_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';

typedef _Json = Map<String, dynamic>;

const _base = '/api/v1';

/// 요청을 기록하고 [body] 를 돌려주는 모의 어댑터. [body] 가 `null` 이면 빈 204.
class _Recorder implements HttpClientAdapter {
  Object? body;
  final List<RequestOptions> requests = [];

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    final body = this.body;
    if (body == null) return ResponseBody.fromString('', 204);
    return ResponseBody.fromString(
      jsonEncode(body),
      200,
      headers: {
        Headers.contentTypeHeader: [Headers.jsonContentType],
      },
    );
  }

  @override
  void close({bool force = false}) {}
}

_Json _fixture(String name) =>
    jsonDecode(File('assets/fixtures/$name.json').readAsStringSync()) as _Json;

_Json _first(String name, String key) =>
    (_fixture(name)[key] as List).first as _Json;

void main() {
  late _Recorder http;
  late ApiClient api;

  setUp(() {
    http = _Recorder();
    api = ApiClient(
      createDio(baseUrl: 'https://example.test$_base', token: 't')
        ..httpClientAdapter = http,
    );
  });

  /// 마지막 요청이 [method] [path] 이고 쿼리·본문이 정확히 같은지 본다.
  void expectSent(
    String method,
    String path, {
    Map<String, String> query = const {},
    Object? body,
  }) {
    final sent = http.requests.last;
    expect(sent.method, method);
    expect(sent.uri.path, '$_base$path');
    expect(sent.uri.queryParameters, query);
    expect(sent.data, body);
  }

  group('MetaRepository', () {
    test('GET /meta', () async {
      http.body = _fixture('meta');
      final meta = await ApiMetaRepository(api).meta();

      expectSent('GET', '/meta');
      expect(meta.timezone, 'Asia/Seoul');
    });
  });

  group('FeedRepository', () {
    late ApiFeedRepository repo;
    setUp(() => repo = ApiFeedRepository(api));

    test('GET /stats/today', () async {
      http.body = _fixture('stats_today');
      final stats = await repo.todayStats();

      expectSent('GET', '/stats/today');
      expect(stats.windowHours, 24);
    });

    test('GET /feed — 기본은 filter=all 만 보낸다', () async {
      http.body = _fixture('feed');
      final page = await repo.feed();

      expectSent('GET', '/feed', query: {'filter': 'all'});
      expect(page.items, isNotEmpty);
    });

    test('GET /feed — 필터·커서·개수', () async {
      http.body = {'items': <Object>[], 'next_cursor': null};
      await repo.feed(filter: FeedFilter.useful, cursor: 'abc', limit: 50);

      expectSent(
        'GET',
        '/feed',
        query: {'filter': 'useful', 'cursor': 'abc', 'limit': '50'},
      );
    });
  });

  group('AlertRepository', () {
    late ApiAlertRepository repo;
    setUp(() => repo = ApiAlertRepository(api));

    test('GET /alerts/{id}', () async {
      http.body = _first('alerts', 'items');
      final detail = await repo.alert('18342');

      expectSent('GET', '/alerts/18342');
      expect(detail.alert.id, '18342');
    });

    test('PUT /alerts/{id}/feedback', () async {
      http.body = {
        'alert_id': '18342',
        'feedback': 'not_useful',
        'updated_at': '2026-09-24T03:01:10Z',
      };
      final result = await repo.setFeedback('18342', FeedbackVerdict.notUseful);

      expectSent(
        'PUT',
        '/alerts/18342/feedback',
        body: {'verdict': 'not_useful'},
      );
      expect(result.feedback, FeedbackVerdict.notUseful);
    });

    test('DELETE /alerts/{id}/feedback — 204', () async {
      await repo.clearFeedback('18342');

      expectSent('DELETE', '/alerts/18342/feedback');
    });

    test('GET /feedback/recent — limit 이 없으면 쿼리 없음', () async {
      http.body = _fixture('feedback_recent');
      await repo.recentFeedback();
      expectSent('GET', '/feedback/recent');

      final recent = await repo.recentFeedback(limit: 5);
      expectSent('GET', '/feedback/recent', query: {'limit': '5'});
      expect(recent.items, isNotEmpty);
    });
  });

  group('SettingsRepository', () {
    late ApiSettingsRepository repo;
    setUp(() => repo = ApiSettingsRepository(api));

    test('GET /settings/interests', () async {
      http.body = _fixture('settings_interests');
      final settings = await repo.interests();

      expectSent('GET', '/settings/interests');
      expect(settings.selectedCategories, isNotEmpty);
    });

    test('PUT /settings/interests — 전체 객체를 본문으로', () async {
      final settings = InterestsSettings.fromJson(
        _fixture('settings_interests'),
      );
      http.body = _fixture('settings_interests');
      await repo.saveInterests(settings);

      expectSent('PUT', '/settings/interests', body: settings.toJson());
    });

    test('GET /settings/notifications', () async {
      http.body = _fixture('settings_notifications');
      final settings = await repo.notifications();

      expectSent('GET', '/settings/notifications');
      expect(settings.dailyPushCap, isPositive);
    });

    test('PATCH /settings/notifications — 바꿀 키만 보낸다', () async {
      const patch = {
        'channels': {
          'telegram': {'enabled': true},
        },
      };
      http.body = _fixture('settings_notifications');
      await repo.updateNotifications(patch);

      expectSent('PATCH', '/settings/notifications', body: patch);
    });
  });

  group('SourceRepository', () {
    late ApiSourceRepository repo;
    setUp(() => repo = ApiSourceRepository(api));

    test('GET /sources', () async {
      http.body = _fixture('sources');
      final response = await repo.sources();

      expectSent('GET', '/sources');
      expect(response.sources, isNotEmpty);
    });

    test('PATCH /sources/{id} — 소스 ID 는 URL 인코딩한다', () async {
      http.body = {..._first('sources', 'sources'), 'enabled': false};
      final source = await repo.setEnabled('rss:anthropic', enabled: false);

      expectSent('PATCH', '/sources/rss%3Aanthropic', body: {'enabled': false});
      expect(source.enabled, isFalse);
    });
  });

  group('FilteredRepository', () {
    late ApiFilteredRepository repo;
    setUp(() => repo = ApiFilteredRepository(api));

    test('GET /filtered/summary', () async {
      http.body = _fixture('filtered_summary');
      await repo.summary();
      expectSent('GET', '/filtered/summary');

      await repo.summary(hours: 48);
      expectSent('GET', '/filtered/summary', query: {'hours': '48'});
    });

    test('GET /filtered/groups — 기본은 source·count_desc', () async {
      http.body = _fixture('filtered_groups_source');
      final groups = await repo.groups();

      expectSent(
        'GET',
        '/filtered/groups',
        query: {'view': 'source', 'sort': 'count_desc'},
      );
      expect(groups.view, FilteredView.source);
    });

    test('GET /filtered/groups — 관문별·이름순·기간', () async {
      http.body = _fixture('filtered_groups_gate');
      await repo.groups(
        view: FilteredView.gate,
        sort: GroupSort.nameAsc,
        hours: 24,
      );

      expectSent(
        'GET',
        '/filtered/groups',
        query: {'view': 'gate', 'sort': 'name_asc', 'hours': '24'},
      );
    });

    test('GET /filtered/items', () async {
      http.body = _fixture('filtered_items');
      final page = await repo.items(
        view: FilteredView.kind,
        key: 'release_patch',
        cursor: 'c1',
        limit: 10,
      );

      expectSent(
        'GET',
        '/filtered/items',
        query: {
          'view': 'kind',
          'key': 'release_patch',
          'cursor': 'c1',
          'limit': '10',
        },
      );
      expect(page.items, isNotEmpty);
    });

    test('POST /filtered/items/{id}/restore — 본문 없음', () async {
      http.body = {
        'item_id': '18120',
        'restored': true,
        'alert': _first('feed', 'items'),
      };
      final result = await repo.restore('18120');

      expectSent('POST', '/filtered/items/18120/restore');
      expect(result.restored, isTrue);
    });

    test('DELETE /filtered/items/{id}/restore — 204', () async {
      await repo.cancelRestore('18120');

      expectSent('DELETE', '/filtered/items/18120/restore');
    });
  });

  group('SavedRepository', () {
    late ApiSavedRepository repo;
    setUp(() => repo = ApiSavedRepository(api));

    test('GET /folders', () async {
      http.body = _fixture('folders');
      final list = await repo.folders();

      expectSent('GET', '/folders');
      expect(list.folders, isNotEmpty);
    });

    test('POST /folders', () async {
      http.body = {..._first('folders', 'folders'), 'name': '논문'};
      final folder = await repo.createFolder('논문');

      expectSent('POST', '/folders', body: {'name': '논문'});
      expect(folder.name, '논문');
    });

    test('PATCH /folders/{id} — 준 필드만 보낸다', () async {
      http.body = _first('folders', 'folders');
      await repo.updateFolder('1', position: 2);
      expectSent('PATCH', '/folders/1', body: {'position': 2});

      await repo.updateFolder('1', name: '나중에');
      expectSent('PATCH', '/folders/1', body: {'name': '나중에'});
    });

    test('DELETE /folders/{id} — 204', () async {
      await repo.deleteFolder('1');

      expectSent('DELETE', '/folders/1');
    });

    test('GET /saved — 기본 쿼리', () async {
      http.body = _fixture('saved');
      final page = await repo.saved();

      expectSent(
        'GET',
        '/saved',
        query: {'unread_only': 'false', 'sort': 'saved_desc'},
      );
      expect(page.items, isNotEmpty);
    });

    test('GET /saved — 미분류·안 읽음·정렬·커서', () async {
      http.body = _fixture('saved');
      await repo.saved(
        folderId: SavedRepository.unfiled,
        unreadOnly: true,
        sort: SavedSort.deliveredDesc,
        cursor: 'c2',
        limit: 20,
      );

      expectSent(
        'GET',
        '/saved',
        query: {
          'folder_id': 'unfiled',
          'unread_only': 'true',
          'sort': 'delivered_desc',
          'cursor': 'c2',
          'limit': '20',
        },
      );
    });

    test('PUT /saved/{id} — 폴더가 없으면 빈 본문(미분류)', () async {
      http.body = _first('saved', 'items');
      final item = await repo.save('18342');
      expectSent('PUT', '/saved/18342', body: <String, dynamic>{});
      expect(item.alertId, '18342');

      await repo.save('18342', folderId: '2');
      expectSent('PUT', '/saved/18342', body: {'folder_id': '2'});
    });

    test('PATCH /saved/{id} — 미분류 이동은 folder_id: null 을 보낸다', () async {
      http.body = _first('saved', 'items');
      await repo.update('18342', SavedItemPatch.folder(null));
      expectSent('PATCH', '/saved/18342', body: {'folder_id': null});

      await repo.update('18342', SavedItemPatch.folder('2'));
      expectSent('PATCH', '/saved/18342', body: {'folder_id': '2'});
    });

    test('PATCH /saved/{id} — 메모·읽음', () async {
      http.body = _first('saved', 'items');
      await repo.update('18342', SavedItemPatch.memo('OAuth 확인'));
      expectSent('PATCH', '/saved/18342', body: {'memo': 'OAuth 확인'});

      await repo.update('18342', SavedItemPatch.memo(null));
      expectSent('PATCH', '/saved/18342', body: {'memo': null});

      await repo.update('18342', const SavedItemPatch.read());
      expectSent('PATCH', '/saved/18342', body: {'is_read': true});
    });

    test('DELETE /saved/{id} — 204', () async {
      await repo.unsave('18342');

      expectSent('DELETE', '/saved/18342');
    });
  });

  group('ProfileRepository', () {
    late ApiProfileRepository repo;
    setUp(() => repo = ApiProfileRepository(api));

    test('GET /profile — 기본 period_days=14', () async {
      http.body = _fixture('profile');
      final profile = await repo.profile();
      expectSent('GET', '/profile', query: {'period_days': '14'});
      expect(profile.periodDays, 14);

      await repo.profile(periodDays: 30);
      expectSent('GET', '/profile', query: {'period_days': '30'});
    });

    test('PATCH /profile — 표시 이름', () async {
      http.body = _fixture('profile');
      await repo.updateDisplayName('태호');

      expectSent('PATCH', '/profile', body: {'display_name': '태호'});
    });

    test('GET /reports', () async {
      http.body = _fixture('reports');
      final page = await repo.reports();
      expectSent('GET', '/reports');
      expect(page.items.single.id, '12');

      await repo.reports(cursor: 'c3', limit: 5);
      expectSent('GET', '/reports', query: {'cursor': 'c3', 'limit': '5'});
    });

    test('GET /reports/{id}', () async {
      http.body = _fixture('report_12');
      final report = await repo.report('12');

      expectSent('GET', '/reports/12');
      expect(report.sections, isNotEmpty);
    });
  });

  group('DeviceRepository', () {
    late ApiDeviceRepository repo;
    setUp(() => repo = ApiDeviceRepository(api));

    test('POST /devices — app_version 이 없으면 빼고 보낸다', () async {
      http.body = {
        'id': '3',
        'platform': 'android',
        'registered_at': '2026-09-24T03:00:00Z',
      };
      final registration = await repo.register(
        token: 'fcm-token',
        platform: DevicePlatform.android,
      );
      expectSent(
        'POST',
        '/devices',
        body: {'token': 'fcm-token', 'platform': 'android'},
      );
      expect(registration.platform, DevicePlatform.android);

      await repo.register(
        token: 'fcm-token',
        platform: DevicePlatform.ios,
        appVersion: '0.1.0',
      );
      expectSent(
        'POST',
        '/devices',
        body: {'token': 'fcm-token', 'platform': 'ios', 'app_version': '0.1.0'},
      );
    });

    test('DELETE /devices/{token} — 토큰은 URL 인코딩한다', () async {
      await repo.unregister('abc:APA91b/x+y');

      expectSent('DELETE', '/devices/abc%3AAPA91b%2Fx%2By');
    });
  });
}
