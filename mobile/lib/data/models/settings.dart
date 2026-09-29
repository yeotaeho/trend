// 설정 모델 — 04 관심사(InterestsSettings)와 05 알림 설정(NotificationSettings) (계약 4.3·4.4).
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
  });

  final NotifyChannels channels;
  final int dailyPushCap;
  final QuietHours quietHours;

  /// `같은 이슈 하루 1건` (`cluster_daily_cap > 0`).
  final bool dedupeSameIssueDaily;
  final DeliveryByImportance deliveryByImportance;
  final ExplorationSlot explorationSlot;
  final DateTime? updatedAt;

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
