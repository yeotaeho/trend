// GENERATED CODE - DO NOT MODIFY BY HAND

part of 'cursor_page.dart';

// **************************************************************************
// JsonSerializableGenerator
// **************************************************************************

CursorPage<T> _$CursorPageFromJson<T>(
  Map<String, dynamic> json,
  T Function(Object? json) fromJsonT,
) => CursorPage<T>(
  items: (json['items'] as List<dynamic>).map(fromJsonT).toList(),
  nextCursor: json['next_cursor'] as String?,
);

Map<String, dynamic> _$CursorPageToJson<T>(
  CursorPage<T> instance,
  Object? Function(T value) toJsonT,
) => <String, dynamic>{
  'items': instance.items.map(toJsonT).toList(),
  'next_cursor': instance.nextCursor,
};
