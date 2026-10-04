// JSON 중첩 병합 — PATCH 본문을 기존 객체 JSON 위에 키 단위로 겹치고, 되돌리기 본문을 고른다 (계약 4.4).

/// [patch] 를 [base] 위에 키 단위로 겹친다. 양쪽 다 맵인 키는 재귀로 합친다.
Map<String, dynamic> deepMerge(
  Map<String, dynamic> base,
  Map<String, Object?> patch,
) => {
  ...base,
  for (final MapEntry(:key, :value) in patch.entries)
    key: value is Map && base[key] is Map
        ? deepMerge(
            base[key] as Map<String, dynamic>,
            value.cast<String, Object?>(),
          )
        : value,
};


/// [shape] 와 같은 키 모양으로 [source] 의 값을 고른다. 저장 전 JSON 으로 그 PATCH 의 되돌리기 본문을 만든다.
Map<String, Object?> pickLike(
  Map<String, dynamic> source,
  Map<String, Object?> shape,
) => {
  for (final MapEntry(:key, :value) in shape.entries)
    key: value is Map && source[key] is Map
        ? pickLike(
            source[key] as Map<String, dynamic>,
            value.cast<String, Object?>(),
          )
        : source[key],
};
