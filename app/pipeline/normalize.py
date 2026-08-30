# 정규화 — URL 정리·SHA-256 해시, 피드 HTML 본문을 평문으로

from __future__ import annotations

import hashlib
import re
from html import unescape
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PREFIXES = ("utm_", "mc_", "pk_")
TRACKING_PARAMS = {"ref", "ref_src", "fbclid", "gclid", "igshid", "source", "spm", "cmpid"}

_TAG_RE = re.compile(r"<[^>]+>")
_WS_RE = re.compile(r"\s+")


def normalize_url(url: str) -> str:
    """스킴·호스트 소문자화, 추적 파라미터·www·트레일링 슬래시 제거."""
    parts = urlsplit(url.strip())
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    # 정렬해야 ?a=1&b=2 와 ?b=2&a=1 이 같은 해시가 된다.
    params = sorted(
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if k.lower() not in TRACKING_PARAMS and not k.lower().startswith(TRACKING_PREFIXES)
    )
    path = parts.path.rstrip("/") or "/"
    return urlunsplit((parts.scheme.lower(), host, path, urlencode(params), ""))


def url_hash(normalized: str) -> str:
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def strip_html(text: str | None) -> str:
    """피드가 주는 HTML 조각을 요약 입력용 평문으로 만든다."""
    if not text:
        return ""
    return _WS_RE.sub(" ", unescape(_TAG_RE.sub(" ", text))).strip()
