// 커서 페이지 봉투 — 목록 API 공통 `{"items": [...], "next_cursor": ...}` (계약 1.3).
import 'package:json_annotation/json_annotation.dart';

part 'cursor_page.g.dart';

@JsonSerializable(genericArgumentFactories: true)
class CursorPage<T> {
  const CursorPage({required this.items, this.nextCursor});

  final List<T> items;

  /// `null` 이면 마지막 페이지다. 불투명 문자열이라 해석하지 않는다.
  final String? nextCursor;

  bool get hasMore => nextCursor != null;

  factory CursorPage.fromJson(
    Map<String, dynamic> json,
    T Function(Object? json) fromJsonT,
  ) => _$CursorPageFromJson(json, fromJsonT);

  Map<String, dynamic> toJson(Object? Function(T value) toJsonT) =>
      _$CursorPageToJson(this, toJsonT);
}
