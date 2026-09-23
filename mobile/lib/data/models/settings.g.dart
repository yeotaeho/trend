// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'settings.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

InterestsSettings _$InterestsSettingsFromJson(Map<String, dynamic> json) =>
    InterestsSettings(
      profile: InterestsProfile.fromJson(
        json['profile'] as Map<String, dynamic>,
      ),
      selectedCategories: (json['selected_categories'] as List<dynamic>)
          .map((e) => e as String)
          .toList(),
      watchKeywords:
          (json['watch_keywords'] as List<dynamic>?)
              ?.map((e) => e as String)
              .toList() ??
          [],
      kindWeights: (json['kind_weights'] as Map<String, dynamic>).map(
        (k, e) => MapEntry(k, (e as num).toDouble()),
      ),
      updatedAt: json['updated_at'] == null
          ? null
          : DateTime.parse(json['updated_at'] as String),
    );

Map<String, dynamic> _$InterestsSettingsToJson(InterestsSettings instance) =>
    <String, dynamic>{
      'profile': instance.profile.toJson(),
      'selected_categories': instance.selectedCategories,
      'watch_keywords': instance.watchKeywords,
      'kind_weights': instance.kindWeights,
    };

InterestsProfile _$InterestsProfileFromJson(Map<String, dynamic> json) =>
    InterestsProfile(
      selfDescription: json['self_description'] as String,
      notInterested: json['not_interested'] as String,
    );

Map<String, dynamic> _$InterestsProfileToJson(InterestsProfile instance) =>
    <String, dynamic>{
      'self_description': instance.selfDescription,
      'not_interested': instance.notInterested,
    };

NotificationSettings _$NotificationSettingsFromJson(
  Map<String, dynamic> json,
) => NotificationSettings(
  channels: NotifyChannels.fromJson(json['channels'] as Map<String, dynamic>),
  dailyPushCap: (json['daily_push_cap'] as num).toInt(),
  quietHours: QuietHours.fromJson(json['quiet_hours'] as Map<String, dynamic>),
  dedupeSameIssueDaily: json['dedupe_same_issue_daily'] as bool,
  deliveryByImportance: DeliveryByImportance.fromJson(
    json['delivery_by_importance'] as Map<String, dynamic>,
  ),
  explorationSlot: ExplorationSlot.fromJson(
    json['exploration_slot'] as Map<String, dynamic>,
  ),
  updatedAt: json['updated_at'] == null
      ? null
      : DateTime.parse(json['updated_at'] as String),
);

Map<String, dynamic> _$NotificationSettingsToJson(
  NotificationSettings instance,
) => <String, dynamic>{
  'channels': instance.channels.toJson(),
  'daily_push_cap': instance.dailyPushCap,
  'quiet_hours': instance.quietHours.toJson(),
  'dedupe_same_issue_daily': instance.dedupeSameIssueDaily,
  'delivery_by_importance': instance.deliveryByImportance.toJson(),
  'exploration_slot': instance.explorationSlot.toJson(),
  'updated_at': instance.updatedAt?.toIso8601String(),
};

NotifyChannels _$NotifyChannelsFromJson(Map<String, dynamic> json) =>
    NotifyChannels(
      fcm: FcmChannel.fromJson(json['fcm'] as Map<String, dynamic>),
      discord: DiscordChannel.fromJson(json['discord'] as Map<String, dynamic>),
      telegram: TelegramChannel.fromJson(
        json['telegram'] as Map<String, dynamic>,
      ),
    );

Map<String, dynamic> _$NotifyChannelsToJson(NotifyChannels instance) =>
    <String, dynamic>{
      'fcm': instance.fcm.toJson(),
      'discord': instance.discord.toJson(),
      'telegram': instance.telegram.toJson(),
    };

FcmChannel _$FcmChannelFromJson(Map<String, dynamic> json) => FcmChannel(
  enabled: json['enabled'] as bool,
  connected: json['connected'] as bool,
  deviceCount: (json['device_count'] as num).toInt(),
);

Map<String, dynamic> _$FcmChannelToJson(FcmChannel instance) =>
    <String, dynamic>{
      'enabled': instance.enabled,
      'connected': instance.connected,
      'device_count': instance.deviceCount,
    };

DiscordChannel _$DiscordChannelFromJson(Map<String, dynamic> json) =>
    DiscordChannel(
      enabled: json['enabled'] as bool,
      connected: json['connected'] as bool,
      channelName: json['channel_name'] as String?,
      reactionSync: json['reaction_sync'] as bool,
    );

Map<String, dynamic> _$DiscordChannelToJson(DiscordChannel instance) =>
    <String, dynamic>{
      'enabled': instance.enabled,
      'connected': instance.connected,
      'channel_name': instance.channelName,
      'reaction_sync': instance.reactionSync,
    };

TelegramChannel _$TelegramChannelFromJson(Map<String, dynamic> json) =>
    TelegramChannel(
      enabled: json['enabled'] as bool,
      connected: json['connected'] as bool,
    );

Map<String, dynamic> _$TelegramChannelToJson(TelegramChannel instance) =>
    <String, dynamic>{
      'enabled': instance.enabled,
      'connected': instance.connected,
    };

QuietHours _$QuietHoursFromJson(Map<String, dynamic> json) => QuietHours(
  start: json['start'] as String,
  end: json['end'] as String,
  timezone: json['timezone'] as String,
);

Map<String, dynamic> _$QuietHoursToJson(QuietHours instance) =>
    <String, dynamic>{
      'start': instance.start,
      'end': instance.end,
      'timezone': instance.timezone,
    };

DeliveryByImportance _$DeliveryByImportanceFromJson(
  Map<String, dynamic> json,
) => DeliveryByImportance(
  high: $enumDecode(
    _$DeliveryChoiceEnumMap,
    json['high'],
    unknownValue: DeliveryChoice.unknown,
  ),
  mid: $enumDecode(
    _$DeliveryChoiceEnumMap,
    json['mid'],
    unknownValue: DeliveryChoice.unknown,
  ),
  low: $enumDecode(
    _$DeliveryChoiceEnumMap,
    json['low'],
    unknownValue: DeliveryChoice.unknown,
  ),
);

Map<String, dynamic> _$DeliveryByImportanceToJson(
  DeliveryByImportance instance,
) => <String, dynamic>{
  'high': _$DeliveryChoiceEnumMap[instance.high]!,
  'mid': _$DeliveryChoiceEnumMap[instance.mid]!,
  'low': _$DeliveryChoiceEnumMap[instance.low]!,
};

const _$DeliveryChoiceEnumMap = {
  DeliveryChoice.instant: 'instant',
  DeliveryChoice.quiet: 'quiet',
  DeliveryChoice.feedOnly: 'feed_only',
  DeliveryChoice.unknown: 'unknown',
};

ExplorationSlot _$ExplorationSlotFromJson(Map<String, dynamic> json) =>
    ExplorationSlot(
      enabled: json['enabled'] as bool,
      dailyLimit: (json['daily_limit'] as num).toInt(),
    );

Map<String, dynamic> _$ExplorationSlotToJson(ExplorationSlot instance) =>
    <String, dynamic>{
      'enabled': instance.enabled,
      'daily_limit': instance.dailyLimit,
    };
