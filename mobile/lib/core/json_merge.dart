// JSON 중첩 병합 — PATCH 본문을 기존 객체 JSON 위에 키 단위로 겹친다 (계약 4.4).

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
