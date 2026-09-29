// 찜 모델 — SavedItem, 폴더·폴더 목록 (계약 3.3·4.7).
import 'package:json_annotation/json_annotation.dart';

part 'saved.g.dart';

@JsonSerializable()
class SavedItem {
  const SavedItem({
    required this.alertId,
    required this.sourceName,
    required this.title,
    required this.url,
    this.deliveredAt,
    required this.savedAt,
    this.folder,
    this.memo,
    required this.isRead,
    this.readAt,
  });

  final String alertId;
  final String sourceName;
  final String title;
  final String url;
  final DateTime? deliveredAt;

  /// 메타 행 날짜 (`9월 14일`).
  final DateTime savedAt;

  /// `null` 이면 미분류이고 배지를 숨긴다.
  final FolderRef? folder;
  final String? memo;
  final bool isRead;
  final DateTime? readAt;

  SavedItem copyWith({
    FolderRef? Function()? folder,
    String? Function()? memo,
    bool? isRead,
    DateTime? Function()? readAt,
  }) => SavedItem(
    alertId: alertId,
    sourceName: sourceName,
    title: title,
    url: url,
    deliveredAt: deliveredAt,
    savedAt: savedAt,
    folder: folder == null ? this.folder : folder(),
    memo: memo == null ? this.memo : memo(),
    isRead: isRead ?? this.isRead,
    readAt: readAt == null ? this.readAt : readAt(),
  );

  factory SavedItem.fromJson(Map<String, dynamic> json) =>
      _$SavedItemFromJson(json);

  Map<String, dynamic> toJson() => _$SavedItemToJson(this);
}

@JsonSerializable()
class FolderRef {
  const FolderRef({required this.id, required this.name});

  final String id;
  final String name;

  factory FolderRef.fromJson(Map<String, dynamic> json) =>
      _$FolderRefFromJson(json);

  Map<String, dynamic> toJson() => _$FolderRefToJson(this);
}

@JsonSerializable()
class Folder {
  const Folder({
    required this.id,
    required this.name,
    required this.count,
    required this.unreadCount,
    required this.position,
  });

  final String id;
  final String name;
  final int count;
  final int unreadCount;
  final int position;

  FolderRef get ref => FolderRef(id: id, name: name);

  Folder copyWith({
    String? name,
    int? count,
    int? unreadCount,
    int? position,
  }) => Folder(
    id: id,
    name: name ?? this.name,
    count: count ?? this.count,
    unreadCount: unreadCount ?? this.unreadCount,
    position: position ?? this.position,
  );

  factory Folder.fromJson(Map<String, dynamic> json) => _$FolderFromJson(json);

  Map<String, dynamic> toJson() => _$FolderToJson(this);
}

/// `GET /folders` — `전체` 칩·`안 읽음 N`·폴더 칩.
@JsonSerializable()
class FolderList {
  const FolderList({
    required this.totalCount,
    required this.unreadCount,
    required this.unfiledCount,
    required this.folders,
  });

  final int totalCount;
  final int unreadCount;
  final int unfiledCount;
  @JsonKey(defaultValue: <Folder>[])
  final List<Folder> folders;

  factory FolderList.fromJson(Map<String, dynamic> json) =>
      _$FolderListFromJson(json);

  Map<String, dynamic> toJson() => _$FolderListToJson(this);
}
