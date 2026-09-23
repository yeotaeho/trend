// fixture 역직렬화 테스트 — assets/fixtures/*.json 이 모델로 읽히고 toJson 으로 되돌렸을 때 필드가 빠지지 않는다.
import 'dart:convert';
import 'dart:io';

import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:tech_radar/core/labels.dart';
import 'package:tech_radar/data/models/models.dart';

typedef _Json = Map<String, dynamic>;

Map<String, dynamic> _page<T>(
  _Json json,
  T Function(_Json) fromJson,
  _Json Function(T) toJson,
) => CursorPage.fromJson(
  json,
  (item) => fromJson(item as _Json),
).toJson((item) => toJson(item));

/// fixture 파일 → 모델을 거쳐 다시 JSON 으로.
final Map<String, _Json Function(_Json)> _roundTrips = {
  'alerts': (j) => _page(j, AlertDetail.fromJson, (d) => d.toJson()),
  'feed': (j) => _page(j, Alert.fromJson, (a) => a.toJson()),
  'feedback_recent': (j) => RecentFeedback.fromJson(j).toJson(),
  'filtered_groups_gate': (j) => FilteredGroups.fromJson(j).toJson(),
  'filtered_groups_kind': (j) => FilteredGroups.fromJson(j).toJson(),
  'filtered_groups_source': (j) => FilteredGroups.fromJson(j).toJson(),
  'filtered_items': (j) => _page(j, DroppedItem.fromJson, (d) => d.toJson()),
  'filtered_summary': (j) => FilteredSummary.fromJson(j).toJson(),
  'folders': (j) => FolderList.fromJson(j).toJson(),
  'meta': (j) => Meta.fromJson(j).toJson(),
  'profile': (j) => Profile.fromJson(j).toJson(),
  'report_12': (j) => Report.fromJson(j).toJson(),
  'reports': (j) => _page(j, ReportSummary.fromJson, (r) => r.toJson()),
  'saved': (j) => _page(j, SavedItem.fromJson, (s) => s.toJson()),
  'settings_interests': (j) => InterestsSettings.fromJson(j).toJson(),
  'settings_notifications': (j) => NotificationSettings.fromJson(j).toJson(),
  'sources': (j) => SourcesResponse.fromJson(j).toJson(),
  'stats_today': (j) => TodayStats.fromJson(j).toJson(),
};

/// 모델이 일부러 되돌려 보내지 않는 키 (`PUT` 본문에서 빠지는 서버 값).
const Map<String, Set<String>> _readOnlyKeys = {
  'settings_interests': {'updated_at'},
};

Future<_Json> _fixture(String name) async =>
    jsonDecode(await rootBundle.loadString('assets/fixtures/$name.json'))
        as _Json;

bool _isTimestamp(String value) =>
    RegExp(r'^\d{4}-\d{2}-\d{2}(T[\d:.]+(Z|[+-]\d{2}:\d{2})?)?$')
        .hasMatch(value);

/// [expected] 의 모든 키·값이 [actual] 에 같은 뜻으로 있는지 비교해 어긋난 경로를 모은다.
/// 시각 문자열은 같은 순간이면, 숫자는 값이 같으면 같다고 본다. 모델이 더한 키는 값이 null 일 때만 허용한다.
void _compare(
  Object? expected,
  Object? actual,
  String path,
  List<String> errors, {
  Set<String> skip = const {},
}) {
  if (expected is Map) {
    if (actual is! Map) {
      errors.add('$path: 객체가 아니다 ($actual)');
      return;
    }
    for (final key in expected.keys) {
      if (path == r'$' && skip.contains(key)) continue;
      if (!actual.containsKey(key)) {
        errors.add('$path.$key: 모델에서 빠졌다');
        continue;
      }
      _compare(expected[key], actual[key], '$path.$key', errors);
    }
    // 계약상 생략될 수 있는 키(`weekly_report_latest.created_at`)는 null 로 되돌아온다.
    for (final key in actual.keys) {
      if (!expected.containsKey(key) && actual[key] != null) {
        errors.add('$path.$key: fixture 에 없는 키다');
      }
    }
  } else if (expected is List) {
    if (actual is! List || actual.length != expected.length) {
      errors.add('$path: 목록 길이가 다르다 ($actual)');
      return;
    }
    for (var i = 0; i < expected.length; i++) {
      _compare(expected[i], actual[i], '$path[$i]', errors);
    }
  } else if (expected is num) {
    if (actual is! num || actual != expected) {
      errors.add('$path: $expected ≠ $actual');
    }
  } else if (expected is String && actual is String && _isTimestamp(expected)) {
    if (DateTime.parse(expected) != DateTime.parse(actual)) {
      errors.add('$path: $expected ≠ $actual');
    }
  } else if (expected != actual) {
    errors.add('$path: $expected ≠ $actual');
  }
}

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('assets/fixtures 의 모든 파일을 검사한다', () {
    final files = Directory('assets/fixtures')
        .listSync()
        .whereType<File>()
        .map((f) => f.uri.pathSegments.last)
        .where((name) => name.endsWith('.json'))
        .map((name) => name.substring(0, name.length - '.json'.length))
        .toSet();
    expect(files, _roundTrips.keys.toSet());
  });

  group('fixture 왕복', () {
    for (final MapEntry(key: name, value: roundTrip) in _roundTrips.entries) {
      test('$name.json — 필드 누락 없음', () async {
        final json = await _fixture(name);
        final errors = <String>[];
        _compare(
          json,
          roundTrip(json),
          r'$',
          errors,
          skip: _readOnlyKeys[name] ?? const {},
        );
        expect(errors, isEmpty);
      });
    }
  });

  group('null · [] 처리', () {
    const alertJson = {
      'id': '1',
      'source_id': 'rss:x',
      'source_name': 'X',
      'source_type': 'rss',
      'delivered_at': null,
      'delivery_mode': null,
      'is_exploration': false,
      'title': 't',
      'url': 'https://x.test',
      'importance': null,
      'is_saved': false,
      'feedback': null,
    };

    test('빠진 summary·categories·tags 는 빈 값이 된다', () {
      final alert = Alert.fromJson(alertJson);
      expect(alert.summary, '');
      expect(alert.categories, isEmpty);
      expect(alert.tags, isEmpty);
      expect(alert.deliveredAt, isNull);
      expect(alert.deliveryMode, isNull);
      expect(alert.feedback, isNull);
    });

    test('모르는 열거형 값은 unknown 으로 받는다', () {
      final alert = Alert.fromJson({
        ...alertJson,
        'source_type': 'mastodon',
        'delivery_mode': 'digest',
        'feedback': 'maybe',
      });
      expect(alert.sourceType, SourceType.unknown);
      expect(alert.deliveryMode, DeliveryMode.unknown);
      expect(alert.feedback, FeedbackVerdict.unknown);
    });

    test('모르는 관문 키는 gate_counts 의 unknown 에 더한다', () async {
      final json = await _fixture('filtered_summary');
      final summary = FilteredSummary.fromJson({
        ...json,
        'gate_counts': {'score': 3, 'future_a': 2, 'future_b': 1},
      });
      expect(summary.gateCounts, {Gate.score: 3, Gate.unknown: 3});
    });

    test('rationale 의 점수·선별·판정이 null 이어도 읽는다', () {
      final detail = AlertDetail.fromJson({
        ...alertJson,
        'rationale': {
          'score': null,
          'routing': 'dropped',
          'screening': null,
          'judgment': null,
          'trust_note_source': 'X',
        },
      });
      expect(detail.rationale.score, isNull);
      expect(detail.rationale.screening, isNull);
      expect(detail.rationale.judgment, isNull);
      expect(detail.rationale.routing, Routing.dropped);
    });

    test('리포트 셀은 문자열·숫자·불리언·null 을 그대로 받는다', () async {
      final report = Report.fromJson(await _fixture('report_12'));
      final funnel = report.sections.firstWhere((s) => s.key == 'funnel');
      expect(funnel.columns, ['stage', 'passed', 'reason', 'n']);
      expect(funnel.rows.first, ['llm', false, 'judge_false', 122]);
      expect(funnel.rows[1], ['llm', true, null, 118]);
    });

    test('빈 목록과 next_cursor null 은 마지막 빈 페이지다', () {
      final page = CursorPage<Alert>.fromJson({
        'items': <Object>[],
        'next_cursor': null,
      }, (item) => Alert.fromJson(item as _Json));
      expect(page.items, isEmpty);
      expect(page.hasMore, isFalse);
    });
  });
}
