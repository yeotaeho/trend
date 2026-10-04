// 설정 모델 — 04 관심사·05 알림 설정·전체 설정(SettingsOverview)·저장 이력(SettingsRevision).
import 'package:json_annotation/json_annotation.dart';

import '../../core/labels.dart';

part 'settings.g.dart';

/// `GET·PUT /settings/interests`. [toJson] 은 PUT 본문이라 `updated_at` 을 넣지 않는다.
@JsonSerializable()
class InterestsSettings {
  const InterestsSettings({
    required this.profile,
    required this.selectedCategories,
    required this.watchKeywords,
    required this.kindWeights,
    this.updatedAt,
    this.overridden = const <String>[],
  });

  final InterestsProfile profile;

  /// taxonomy slug. 1개 이상.
  final List<String> selectedCategories;

  /// `focus_stack` + `focus_repos`. `/` 를 포함한 값은 저장소다.
  @JsonKey(defaultValue: <String>[])
  final List<String> watchKeywords;

  /// kind 값 → 가중치. 앱이 편집하지 않는 `news`·`other` 와 모르는 kind 도 그대로 되돌려 보내도록
  /// 문자열 키로 둔다.
  final Map<String, double> kindWeights;

  /// 한 번도 저장하지 않았으면 `null`.
  @JsonKey(includeToJson: false)
  final DateTime? updatedAt;

  /// 앱 값이 있는 키(`policy.categories`·`scoring.kind_weights.survey` 같은 점 경로). PUT 본문에는
  /// 넣지 않는다. 서버가 모르는 키라며 422 를 낸다.
  @JsonKey(includeToJson: false, defaultValue: <String>[])
  final List<String> overridden;

  factory InterestsSettings.fromJson(Map<String, dynamic> json) =>
      _$InterestsSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$InterestsSettingsToJson(this);
}

@JsonSerializable()
class InterestsProfile {
  const InterestsProfile({
    required this.selfDescription,
    required this.notInterested,
  });

  final String selfDescription;
  final String notInterested;

  factory InterestsProfile.fromJson(Map<String, dynamic> json) =>
      _$InterestsProfileFromJson(json);

  Map<String, dynamic> toJson() => _$InterestsProfileToJson(this);
}

/// `GET /settings/notifications`. 저장은 바꿀 키만 담은 PATCH 다.
@JsonSerializable()
class NotificationSettings {
  const NotificationSettings({
    required this.channels,
    required this.dailyPushCap,
    required this.quietHours,
    required this.dedupeSameIssueDaily,
    required this.deliveryByImportance,
    required this.explorationSlot,
    this.updatedAt,
    this.clusterDailyCap = 1,
    this.resurfaceAfterDays = 7,
    this.overridden = const <String>[],
  });

  final NotifyChannels channels;
  final int dailyPushCap;
  final QuietHours quietHours;

  /// `같은 이슈 하루 N건` (`cluster_daily_cap > 0`).
  final bool dedupeSameIssueDaily;

  /// 같은 이슈 하루 상한 N (유효값, 0 = 끔). 읽기 전용.
  @JsonKey(defaultValue: 1)
  final int clusterDailyCap;

  final DeliveryByImportance deliveryByImportance;
  final ExplorationSlot explorationSlot;

  /// 읽지 않은 찜을 다시 알리는 날수. 한도는 `/meta` 의 `limits.resurface_after_days`.
  @JsonKey(defaultValue: 7)
  final int resurfaceAfterDays;

  final DateTime? updatedAt;

  /// 앱 값이 있는 `notify.*` 키. 읽기 전용.
  @JsonKey(defaultValue: <String>[])
  final List<String> overridden;

  factory NotificationSettings.fromJson(Map<String, dynamic> json) =>
      _$NotificationSettingsFromJson(json);

  Map<String, dynamic> toJson() => _$NotificationSettingsToJson(this);
}

@JsonSerializable()
class NotifyChannels {
  const NotifyChannels({
    required this.fcm,
    required this.discord,
    required this.telegram,
  });

  final FcmChannel fcm;
  final DiscordChannel discord;
  final TelegramChannel telegram;

  factory NotifyChannels.fromJson(Map<String, dynamic> json) =>
      _$NotifyChannelsFromJson(json);

  Map<String, dynamic> toJson() => _$NotifyChannelsToJson(this);
}

@JsonSerializable()
class FcmChannel {
  const FcmChannel({
    required this.enabled,
    required this.connected,
    required this.deviceCount,
  });

  final bool enabled;
  final bool connected;

  /// 0 이면 보조 줄에 `등록된 기기 없음`.
  final int deviceCount;

  factory FcmChannel.fromJson(Map<String, dynamic> json) =>
      _$FcmChannelFromJson(json);

  Map<String, dynamic> toJson() => _$FcmChannelToJson(this);
}

@JsonSerializable()
class DiscordChannel {
  const DiscordChannel({
    required this.enabled,
    required this.connected,
    this.channelName,
    required this.reactionSync,
  });

  final bool enabled;
  final bool connected;

  /// 표시 전용 (`#trend-alerts`).
  final String? channelName;
  final bool reactionSync;

  factory DiscordChannel.fromJson(Map<String, dynamic> json) =>
      _$DiscordChannelFromJson(json);

  Map<String, dynamic> toJson() => _$DiscordChannelToJson(this);
}

@JsonSerializable()
class TelegramChannel {
  const TelegramChannel({required this.enabled, required this.connected});

  final bool enabled;

  /// `false` 면 보조 줄 `연결 안 됨`.
  final bool connected;

  factory TelegramChannel.fromJson(Map<String, dynamic> json) =>
      _$TelegramChannelFromJson(json);

  Map<String, dynamic> toJson() => _$TelegramChannelToJson(this);
}

@JsonSerializable()
class QuietHours {
  const QuietHours({
    required this.start,
    required this.end,
    required this.timezone,
  });

  /// `HH:mm` (분은 항상 00). 같은 값이면 무음 없음.
  final String start;
  final String end;

  /// 읽기 전용 IANA 시간대.
  final String timezone;

  factory QuietHours.fromJson(Map<String, dynamic> json) =>
      _$QuietHoursFromJson(json);

  Map<String, dynamic> toJson() => _$QuietHoursToJson(this);
}

@JsonSerializable()
class DeliveryByImportance {
  const DeliveryByImportance({
    required this.high,
    required this.mid,
    required this.low,
  });

  @JsonKey(unknownEnumValue: DeliveryChoice.unknown)
  final DeliveryChoice high;
  @JsonKey(unknownEnumValue: DeliveryChoice.unknown)
  final DeliveryChoice mid;
  @JsonKey(unknownEnumValue: DeliveryChoice.unknown)
  final DeliveryChoice low;

  factory DeliveryByImportance.fromJson(Map<String, dynamic> json) =>
      _$DeliveryByImportanceFromJson(json);

  Map<String, dynamic> toJson() => _$DeliveryByImportanceToJson(this);
}

@JsonSerializable()
class ExplorationSlot {
  const ExplorationSlot({required this.enabled, required this.dailyLimit});

  final bool enabled;

  /// **정적** 1.
  final int dailyLimit;

  factory ExplorationSlot.fromJson(Map<String, dynamic> json) =>
      _$ExplorationSlotFromJson(json);

  Map<String, dynamic> toJson() => _$ExplorationSlotToJson(this);
}

/// `GET /settings` — 모든 설정 키와 출처·주인(계약 4.0). 화면은 #36 에서 붙인다.
@JsonSerializable()
class SettingsOverview {
  const SettingsOverview({
    required this.revision,
    required this.gitSha,
    required this.deliveryBlocked,
    required this.items,
  });

  /// 마지막 저장 이력 id. 저장한 적이 없으면 `null`.
  final String? revision;

  /// 배포한 커밋. 로컬 서버는 `null`.
  final String? gitSha;

  /// 알림이 막히는 사유 — `no_channel`·`no_instant`·`quiet_long`·`resurface_off`.
  final List<String> deliveryBlocked;

  final List<SettingItem> items;

  factory SettingsOverview.fromJson(Map<String, dynamic> json) =>
      _$SettingsOverviewFromJson(json);

  Map<String, dynamic> toJson() => _$SettingsOverviewToJson(this);
}

/// 설정 키 하나. `owner` 가 `app` 인 키만 앱에서 바꾼다.
@JsonSerializable()
class SettingItem {
  const SettingItem({
    required this.key,
    required this.label,
    required this.category,
    required this.value,
    required this.defaultValue,
    required this.source,
    required this.owner,
    required this.apply,
    required this.defaultChanged,
    required this.editUrl,
  });

  /// 점 경로(`notify.daily_push_cap`). 첫 마디가 [category] 다.
  final String key;
  final String label;
  final String category;

  /// 유효값. 숫자·문자열·불리언·목록·객체 가운데 하나다.
  final Object? value;

  @JsonKey(name: 'default')
  final Object? defaultValue;

  /// `default` 또는 `app`.
  final String source;

  /// `app`·`yaml`·`server`.
  final String owner;

  /// `next_job`·`deploy`·`restart`.
  final String apply;

  final bool defaultChanged;

  /// YAML 편집 주소. `server` 는 `null`.
  final String? editUrl;

  factory SettingItem.fromJson(Map<String, dynamic> json) =>
      _$SettingItemFromJson(json);

  Map<String, dynamic> toJson() => _$SettingItemToJson(this);
}

/// 저장 이력 한 건에서 유효값이 바뀐 키 하나. [defaultValue] 는 저장 때의 YAML 값이다.
@JsonSerializable()
class SettingChange {
  const SettingChange({
    required this.key,
    required this.old,
    required this.newValue,
    required this.defaultValue,
  });

  final String key;
  final Object? old;

  @JsonKey(name: 'new')
  final Object? newValue;

  @JsonKey(name: 'default')
  final Object? defaultValue;

  factory SettingChange.fromJson(Map<String, dynamic> json) =>
      _$SettingChangeFromJson(json);

  Map<String, dynamic> toJson() => _$SettingChangeToJson(this);
}

/// `GET /settings/revisions` 한 줄. 저장마다 한 행이고 지우지 않는다.
@JsonSerializable()
class SettingsRevision {
  const SettingsRevision({
    required this.id,
    required this.origin,
    required this.note,
    required this.changes,
    required this.createdAt,
  });

  final String id;

  /// `app`·`reset`·`restore`·`script`.
  final String origin;
  final String? note;
  final List<SettingChange> changes;
  final DateTime createdAt;

  factory SettingsRevision.fromJson(Map<String, dynamic> json) =>
      _$SettingsRevisionFromJson(json);

  Map<String, dynamic> toJson() => _$SettingsRevisionToJson(this);
}

/// `POST /settings/revisions/{id}/restore` — 되돌린 저장(새 이력 행)과 지금 모델에 맞지 않아 버린 키.
@JsonSerializable()
class RevisionRestore {
  const RevisionRestore({required this.revision, required this.dropped});

  final SettingsRevision revision;
  final List<String> dropped;

  factory RevisionRestore.fromJson(Map<String, dynamic> json) =>
      _$RevisionRestoreFromJson(json);

  Map<String, dynamic> toJson() => _$RevisionRestoreToJson(this);
}
