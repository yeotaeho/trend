// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'saved.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

SavedItem _$SavedItemFromJson(Map<String, dynamic> json) => SavedItem(
  alertId: json['alert_id'] as String,
  sourceName: json['source_name'] as String,
  title: json['title'] as String,
  url: json['url'] as String,
  deliveredAt: json['delivered_at'] == null
      ? null
      : DateTime.parse(json['delivered_at'] as String),
  savedAt: DateTime.parse(json['saved_at'] as String),
  folder: json['folder'] == null
      ? null
      : FolderRef.fromJson(json['folder'] as Map<String, dynamic>),
  memo: json['memo'] as String?,
  isRead: json['is_read'] as bool,
  readAt: json['read_at'] == null
      ? null
      : DateTime.parse(json['read_at'] as String),
);

Map<String, dynamic> _$SavedItemToJson(SavedItem instance) => <String, dynamic>{
  'alert_id': instance.alertId,
  'source_name': instance.sourceName,
  'title': instance.title,
  'url': instance.url,
  'delivered_at': instance.deliveredAt?.toIso8601String(),
  'saved_at': instance.savedAt.toIso8601String(),
  'folder': instance.folder?.toJson(),
  'memo': instance.memo,
  'is_read': instance.isRead,
  'read_at': instance.readAt?.toIso8601String(),
};

FolderRef _$FolderRefFromJson(Map<String, dynamic> json) =>
    FolderRef(id: json['id'] as String, name: json['name'] as String);

Map<String, dynamic> _$FolderRefToJson(FolderRef instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
};

Folder _$FolderFromJson(Map<String, dynamic> json) => Folder(
  id: json['id'] as String,
  name: json['name'] as String,
  count: (json['count'] as num).toInt(),
  unreadCount: (json['unread_count'] as num).toInt(),
  position: (json['position'] as num).toInt(),
);

Map<String, dynamic> _$FolderToJson(Folder instance) => <String, dynamic>{
  'id': instance.id,
  'name': instance.name,
  'count': instance.count,
  'unread_count': instance.unreadCount,
  'position': instance.position,
};

FolderList _$FolderListFromJson(Map<String, dynamic> json) => FolderList(
  totalCount: (json['total_count'] as num).toInt(),
  unreadCount: (json['unread_count'] as num).toInt(),
  unfiledCount: (json['unfiled_count'] as num).toInt(),
  folders:
      (json['folders'] as List<dynamic>?)
          ?.map((e) => Folder.fromJson(e as Map<String, dynamic>))
          .toList() ??
      [],
);

Map<String, dynamic> _$FolderListToJson(FolderList instance) =>
    <String, dynamic>{
      'total_count': instance.totalCount,
      'unread_count': instance.unreadCount,
      'unfiled_count': instance.unfiledCount,
      'folders': instance.folders.map((e) => e.toJson()).toList(),
    };
