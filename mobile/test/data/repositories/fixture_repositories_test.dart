// Fixture 저장소 쓰기 테스트 — 판정·찜·복원·설정 변경이 다음 조회에 반영되는지 본다.
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/api/api_exception.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/data/models/models.dart';
import 'package:tech_radar/data/repositories/fixture_repositories.dart';
import 'package:tech_radar/data/repositories/repositories.dart';

Matcher _apiError(String code, int status) => throwsA(
  isA<ApiException>()
      .having((e) => e.code, 'code', code)
      .having((e) => e.status, 'status', status),
);

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  late FixtureStore store;
  late FixtureFeedRepository feed;
  late FixtureAlertRepository alerts;
  late FixtureSavedRepository saved;
  late FixtureFilteredRepository filtered;
  late FixtureSettingsRepository settings;
  late FixtureSourceRepository sources;
  late FixtureProfileRepository profile;

  setUp(() {
    store = FixtureStore(delay: Duration.zero);
    feed = FixtureFeedRepository(store);
    alerts = FixtureAlertRepository(store);
    saved = FixtureSavedRepository(store);
    filtered = FixtureFilteredRepository(store);
    settings = FixtureSettingsRepository(store);
    sources = FixtureSourceRepository(store);
    profile = FixtureProfileRepository(store);
  });

  Future<Alert> feedAlert(String id) async =>
      (await feed.feed()).items.firstWhere((a) => a.id == id);

  Future<SavedItem> savedItem(String alertId) async =>
      (await saved.saved()).items.firstWhere((s) => s.alertId == alertId);

  Future<Folder> folder(String id) async =>
      (await saved.folders()).folders.firstWhere((f) => f.id == id);

  test('기본 지연은 300ms 다', () {
    expect(FixtureStore().delay, const Duration(milliseconds: 300));
  });

  group('판정 PUT/DELETE', () {
    test('새 판정은 피드·상세·최근 판정·유용 칩에 보인다', () async {
      await alerts.setFeedback('18301', FeedbackVerdict.useful);

      expect((await feedAlert('18301')).feedback, FeedbackVerdict.useful);
      expect(
        (await alerts.alert('18301')).alert.feedback,
        FeedbackVerdict.useful,
      );
      final useful = await feed.feed(filter: FeedFilter.useful);
      expect(useful.items.map((a) => a.id), containsAll(['18301', '18342']));
      final recent = await alerts.recentFeedback();
      expect(recent.todayCount, 4);
      expect(recent.items.first.alertId, '18301');
    });

    test('판정을 바꾸면 오늘 개수는 그대로이고 최근 줄은 하나다', () async {
      await alerts.setFeedback('18342', FeedbackVerdict.notUseful);

      expect((await feedAlert('18342')).feedback, FeedbackVerdict.notUseful);
      final recent = await alerts.recentFeedback();
      expect(recent.todayCount, 3);
      expect(recent.items.where((i) => i.alertId == '18342'), hasLength(1));
      expect(recent.items.first.feedback, FeedbackVerdict.notUseful);
    });

    test('해제하면 판정이 사라지고 최근 판정에서도 빠진다', () async {
      await alerts.clearFeedback('18342');

      expect((await feedAlert('18342')).feedback, isNull);
      expect((await alerts.alert('18342')).alert.feedback, isNull);
      final useful = await feed.feed(filter: FeedFilter.useful);
      expect(useful.items.map((a) => a.id), isNot(contains('18342')));
      final recent = await alerts.recentFeedback();
      expect(recent.todayCount, 2);
      expect(recent.items.map((i) => i.alertId), isNot(contains('18342')));
    });

    test('없는 알림은 404', () async {
      await expectLater(
        alerts.setFeedback('nope', FeedbackVerdict.useful),
        _apiError('not_found', 404),
      );
    });
  });

  group('찜', () {
    test('추가하면 미분류 맨 앞에 오고 칩 개수와 피드 찜 표시가 바뀐다', () async {
      await saved.save('18301');

      final all = await saved.saved();
      expect(all.items.first.alertId, '18301');
      expect(all.items.first.folder, isNull);
      expect(all.items.first.isRead, isFalse);
      final unfiled = await saved.saved(folderId: SavedRepository.unfiled);
      expect(unfiled.items.map((s) => s.alertId), contains('18301'));
      final folders = await saved.folders();
      expect(folders.totalCount, 24);
      expect(folders.unreadCount, 8);
      expect(folders.unfiledCount, 4);
      expect((await feedAlert('18301')).isSaved, isTrue);
    });

    test('폴더를 주고 추가하면 그 폴더 개수가 늘어난다', () async {
      await saved.save('18290', folderId: '1');

      expect((await savedItem('18290')).folder?.id, '1');
      final f = await folder('1');
      expect(f.count, 10);
      expect(f.unreadCount, 5);
      expect((await saved.folders()).unfiledCount, 3);
    });

    test('이미 찜한 알림을 폴더 없이 다시 찜하면 폴더를 바꾸지 않는다', () async {
      await saved.save('17811');

      expect((await savedItem('17811')).folder?.id, '1');
      expect((await saved.folders()).totalCount, 23);
    });

    test('폴더 이동은 양쪽 개수와 폴더별 목록에 반영된다', () async {
      await saved.update('17811', SavedItemPatch.folder('2'));

      expect((await folder('1')).count, 8);
      expect((await folder('1')).unreadCount, 3);
      expect((await folder('2')).count, 7);
      expect((await folder('2')).unreadCount, 3);
      final inTwo = await saved.saved(folderId: '2');
      expect(inTwo.items.map((s) => s.alertId), contains('17811'));

      await saved.update('17811', SavedItemPatch.folder(null));

      expect((await savedItem('17811')).folder, isNull);
      expect((await folder('2')).count, 6);
      expect((await saved.folders()).unfiledCount, 4);
    });

    test('메모를 쓰고, 빈 문자열이면 지운다', () async {
      await saved.update('17811', SavedItemPatch.memo('OAuth 부분 확인'));
      expect((await savedItem('17811')).memo, 'OAuth 부분 확인');

      await saved.update('17811', SavedItemPatch.memo(''));
      expect((await savedItem('17811')).memo, isNull);
    });

    test('메모가 500자를 넘으면 422', () async {
      await expectLater(
        saved.update('17811', SavedItemPatch.memo('가' * 501)),
        _apiError('validation_error', 422),
      );
    });

    test('읽음 처리는 read_at 을 채우고 안 읽음 개수를 줄인다', () async {
      await saved.update('17811', const SavedItemPatch.read());

      final item = await savedItem('17811');
      expect(item.isRead, isTrue);
      expect(item.readAt, isNotNull);
      expect((await saved.folders()).unreadCount, 6);
      expect((await folder('1')).unreadCount, 3);
      final unread = await saved.saved(unreadOnly: true);
      expect(unread.items.map((s) => s.alertId), isNot(contains('17811')));
    });

    test('해제하면 목록·개수·피드 찜 표시에서 빠진다', () async {
      await saved.unsave('18342');

      final all = await saved.saved();
      expect(all.items.map((s) => s.alertId), isNot(contains('18342')));
      expect((await saved.folders()).totalCount, 22);
      expect((await folder('2')).count, 5);
      expect((await feedAlert('18342')).isSaved, isFalse);
    });

    test('새 폴더는 맨 뒤에 붙고 같은 이름은 409', () async {
      final created = await saved.createFolder('  리팩터링 아이디어 ');

      expect(created.name, '리팩터링 아이디어');
      final folders = (await saved.folders()).folders;
      expect(folders.last.id, created.id);
      expect(folders.last.position, 3);
      await expectLater(
        saved.createFolder('적용해보기'),
        _apiError('conflict', 409),
      );
    });

    test('폴더를 지우면 안의 찜은 미분류가 된다', () async {
      await saved.deleteFolder('1');

      final folders = await saved.folders();
      expect(folders.folders.map((f) => f.id), isNot(contains('1')));
      expect(folders.unfiledCount, 12);
      expect((await savedItem('17811')).folder, isNull);
    });
  });

  group('복원', () {
    // 피드 순서는 delivered_at(복원 시각 = 지금)이라 fixture 시각과 시계에 따라 달라서 위치는 보지 않는다.
    test('복원하면 피드에 feed_only·유용으로 오르고 근거는 restored 다', () async {
      final result = await filtered.restore('18107');

      expect(result.restored, isTrue);
      expect(result.alert.deliveryMode, DeliveryMode.feedOnly);
      expect(result.alert.feedback, FeedbackVerdict.useful);
      final restored = await feedAlert('18107');
      expect(restored.deliveryMode, DeliveryMode.feedOnly);
      expect(restored.feedback, FeedbackVerdict.useful);
      final detail = await alerts.alert('18107');
      expect(detail.rationale.routing, Routing.restored);
      final items = await filtered.items(view: FilteredView.gate, key: 'score');
      expect(items.items.firstWhere((d) => d.id == '18107').restored, isTrue);
      final groups = await filtered.groups(view: FilteredView.kind);
      final survey = groups.groups.firstWhere((g) => g.key == 'survey');
      expect(
        survey.preview.firstWhere((d) => d.id == '18107').restored,
        isTrue,
      );
      expect((await alerts.recentFeedback()).items.first.alertId, '18107');
    });

    test('두 번 복원해도 피드에 한 번만 오른다', () async {
      await filtered.restore('18107');
      await filtered.restore('18107');

      final ids = (await feed.feed()).items.map((a) => a.id);
      expect(ids.where((id) => id == '18107'), hasLength(1));
    });

    test('복원 취소는 피드에서 내리고 판정·표시를 되돌린다', () async {
      await filtered.restore('18107');
      await filtered.cancelRestore('18107');

      final ids = (await feed.feed()).items.map((a) => a.id);
      expect(ids, isNot(contains('18107')));
      final detail = await alerts.alert('18107');
      expect(detail.rationale.routing, Routing.dropped);
      expect(detail.alert.feedback, isNull);
      final items = await filtered.items(view: FilteredView.gate, key: 'score');
      expect(items.items.firstWhere((d) => d.id == '18107').restored, isFalse);
    });

    test('cluster_dup 항목은 취소하면 cluster_dup 근거로 돌아간다', () async {
      await filtered.restore('18336');
      expect((await alerts.alert('18336')).rationale.routing, Routing.restored);

      await filtered.cancelRestore('18336');
      expect(
        (await alerts.alert('18336')).rationale.routing,
        Routing.clusterDup,
      );
    });

    test('걸러진 항목이 아니면 404', () async {
      await expectLater(filtered.restore('18342'), _apiError('not_found', 404));
    });
  });

  group('설정', () {
    test('알림 설정 PATCH 는 보낸 키만 바꾸고 다음 조회에 보인다', () async {
      await settings.updateNotifications({
        'daily_push_cap': 10,
        'quiet_hours': {'start': '22:00'},
        'channels': {
          'discord': {'enabled': false},
        },
      });

      final n = await settings.notifications();
      expect(n.dailyPushCap, 10);
      expect(n.quietHours.start, '22:00');
      expect(n.quietHours.end, '08:00');
      expect(n.channels.discord.enabled, isFalse);
      expect(n.channels.discord.connected, isTrue);
      expect(n.channels.discord.channelName, '#trend-alerts');
      expect(n.channels.fcm.enabled, isTrue);
      expect(n.updatedAt!.isAfter(DateTime.utc(2026, 9, 20, 11)), isTrue);
    });

    test('연결 안 된 채널을 켜면 409 이고 설정은 그대로다', () async {
      await expectLater(
        settings.updateNotifications({
          'channels': {
            'telegram': {'enabled': true},
          },
        }),
        _apiError('channel_not_connected', 409),
      );
      expect((await settings.notifications()).channels.telegram.enabled, false);
    });

    test('관심사 PUT 은 다음 조회에 그대로 보인다', () async {
      final before = await settings.interests();
      await settings.saveInterests(
        InterestsSettings(
          profile: before.profile,
          selectedCategories: const ['agent', 'mcp-tooling'],
          watchKeywords: const ['claude'],
          kindWeights: const {'survey': -0.2},
        ),
      );

      final after = await settings.interests();
      expect(after.selectedCategories, ['agent', 'mcp-tooling']);
      expect(after.watchKeywords, ['claude']);
      expect(after.kindWeights['survey'], -0.2);
      expect(after.kindWeights['promo'], before.kindWeights['promo']);
      expect(after.updatedAt, isNotNull);
    });

    test('카테고리가 비면 422', () async {
      final before = await settings.interests();
      await expectLater(
        settings.saveInterests(
          InterestsSettings(
            profile: before.profile,
            selectedCategories: const [],
            watchKeywords: before.watchKeywords,
            kindWeights: before.kindWeights,
          ),
        ),
        _apiError('validation_error', 422),
      );
    });

    test('소스 on/off 는 목록과 켜진 개수에 반영된다', () async {
      await sources.setEnabled('youtube:codingapple', enabled: true);

      final after = await sources.sources();
      expect(
        after.sources.firstWhere((s) => s.id == 'youtube:codingapple').enabled,
        isTrue,
      );
      expect(after.stats.enabledCount, 10);
    });

    test('표시 이름 PATCH 는 다음 프로필 조회에 보인다', () async {
      await profile.updateDisplayName(' 태호 ');

      expect((await profile.profile()).user.displayName, '태호');
    });
  });
}
