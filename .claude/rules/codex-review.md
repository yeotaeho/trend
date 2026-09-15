# Codex 최종 리뷰 (항상 적용)

계획·구현·수정 작업을 논리적 단위로 마치고 **커밋한 뒤**, 완료를 선언하기 전에 Codex 리뷰를 최종 게이트로 실행한다.

- **언제** — 작업 단위(기능·수정·리팩터) 커밋 직후. 커밋이 여럿 쌓였으면 마지막에 한 번 범위 리뷰.
- **어떻게** — `/codex:review`. 미커밋 변경은 working-tree 기본, 이미 커밋한 분은 `--base <직전 ref> --scope branch`.
  - 1~2파일 소규모 → foreground(`--wait`). 그 이상·불확실 → background.
  - 적대적 관점이 필요하면 `/codex:adversarial-review`.
- **원칙** — 리뷰는 read-only. 지적을 무비판 수용하지 않고 실제 결함인지 판단한 뒤 반영한다. **Critical/Important** 는 조치 후 **재리뷰**, **Minor** 는 트리아지(즉시 vs 후속).
- **자동화(선택)** — `/codex:setup --enable-review-gate` 로 stop-time 리뷰 게이트를 켤 수 있다.
