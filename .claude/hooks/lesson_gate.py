# Stop 훅 — 커밋이 있던 턴 끝에 마무리 순서(Codex 리뷰 → 교훈 → 옵시디언)를 확인시킨다
import json
import re
import sys

sys.stdin.reconfigure(encoding="utf-8")
sys.stdout.reconfigure(encoding="utf-8")
try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)

if data.get("stop_hook_active"):
    sys.exit(0)

msg = data.get("last_assistant_message") or ""
if not re.search(r"커밋|commit|푸시|push|cherry-pick", msg, re.I):
    sys.exit(0)
if not re.search(r"\b[0-9a-f]{7,40}\b", msg):
    sys.exit(0)
if re.search(r"기록할 교훈 없음|BANK\.md", msg):
    sys.exit(0)

reason = (
    "작업 단위가 끝났다. 마무리 순서는 Codex 리뷰(지적 반영·재커밋) → 교훈 판단 → "
    "옵시디언 기록 1회다. Codex 리뷰가 남았으면 먼저 끝낸다. "
    "교훈은 스킬 lesson-capture 기준으로 판단한다. "
    "세 조건(명백하지 않음·오래 감·중요함)을 모두 넘고, "
    "'이것이 사라지면 다음 사람이 같은 실수나 조사를 반복할까?' 에 예일 때만 남긴다. "
    "테스트·주석·커밋·옵시디언으로 충분하면 그쪽에 둔다. "
    "BANK 에 쓸 때는 기존 행과 다섯 기준으로 겹침을 먼저 본다. "
    "기준에 못 미치면 '기록할 교훈 없음' 한 줄로 끝낸다."
)
print(json.dumps({"decision": "block", "reason": reason}, ensure_ascii=False))
