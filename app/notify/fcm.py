# 앱 푸시 발송 — FCM HTTP v1, 서비스 계정 OAuth 토큰, 활성 기기 팬아웃·무효 토큰 비활성화

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import httpx
from google.auth import crypt, jwt
from sqlalchemy import func, select, update
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.config import get_settings
from app.db.models import Device, Item, Summary
from app.db.session import session_scope
from app.db.users import DEFAULT_USER_ID
from app.log import get_logger
from app.schemas import Level

log = get_logger(__name__)

SEND_URL = "https://fcm.googleapis.com/v1/projects/{project}/messages:send"
TOKEN_URI = "https://oauth2.googleapis.com/token"
SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
GRANT_TYPE = "urn:ietf:params:oauth:grant-type:jwt-bearer"
TIMEOUT = httpx.Timeout(15.0)
TOKEN_MARGIN = 300.0  # 만료까지 이만큼 남으면 새로 받는다
# FCM 메시지 전체 상한은 4KB 다. 넘치면 INVALID_ARGUMENT 가 오고 기기가 비활성화되므로 자른다.
MAX_TITLE = 200
MAX_BODY = 500
MAX_MESSAGE_ID = 100  # notifications.message_id 길이
# 이 오류 코드를 받은 토큰은 다시 보내도 소용없다. 기기를 비활성화한다.
INVALID_TOKEN_CODES = frozenset({"UNREGISTERED", "INVALID_ARGUMENT"})
FCM_ERROR_TYPE = "type.googleapis.com/google.firebase.fcm.v1.FcmError"

DELIVERY_MODES = {Level.PUSH: "instant", Level.SILENT: "quiet", Level.EXPLORE: "experiment"}
EXPERIMENT_PREFIX = "🧪 "
RESURFACE_PREFIX = "📌 "
RESURFACE_BODY = "찜해 두고 아직 읽지 않았어요."

# 프로세스 전역 OAuth 토큰 캐시 — (access_token, 만료 시각 monotonic).
_cached_token: tuple[str, float] | None = None


class InvalidToken(RuntimeError):
    """FCM 이 이 기기 토큰을 거부했다. 기기를 비활성화한다."""


class _Transient(RuntimeError):
    """429·5xx. 잠시 뒤 같은 요청을 다시 보낸다."""


def _assertion(info: dict[str, Any], token_uri: str) -> str:
    # google-auth 는 타입 힌트가 일부 없다.
    signer = crypt.RSASigner.from_service_account_info(info)  # type: ignore[no-untyped-call]
    now = int(time.time())
    payload = {
        "iss": info["client_email"],
        "scope": SCOPE,
        "aud": token_uri,
        "iat": now,
        "exp": now + 3600,
    }
    assertion: bytes = jwt.encode(signer, payload)  # type: ignore[no-untyped-call]
    return assertion.decode()


async def access_token() -> str:
    """서비스 계정 JWT 로 받은 OAuth 토큰. 만료 전에는 캐시를 재사용한다."""
    global _cached_token
    if _cached_token and _cached_token[1] - time.monotonic() > TOKEN_MARGIN:
        return _cached_token[0]
    info = json.loads(Path(get_settings().fcm_service_account_file).read_text())
    token_uri = info.get("token_uri", TOKEN_URI)
    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        response = await client.post(
            token_uri, data={"grant_type": GRANT_TYPE, "assertion": _assertion(info, token_uri)}
        )
    if response.status_code >= 400:
        raise RuntimeError(f"fcm oauth HTTP {response.status_code}: {response.text[:200]}")
    body = response.json()
    _cached_token = (str(body["access_token"]), time.monotonic() + float(body["expires_in"]))
    return _cached_token[0]


def build_message(
    token: str, *, title: str, body: str, data: dict[str, str], loud: bool
) -> dict[str, Any]:
    """계약 4.9 페이로드. loud=False 면 Android `quiet` 채널·APNs 우선순위 5·소리 없음."""
    aps: dict[str, Any] = {"sound": "default"} if loud else {}
    return {
        "message": {
            "token": token,
            "notification": {"title": title[:MAX_TITLE], "body": body[:MAX_BODY]},
            "data": data,
            "android": {
                "priority": "HIGH" if loud else "NORMAL",
                "notification": {"channel_id": "instant" if loud else "quiet"},
            },
            "apns": {
                "headers": {"apns-priority": "10" if loud else "5"},
                "payload": {"aps": aps},
            },
        }
    }


def _error_code(response: httpx.Response) -> str:
    """FcmError 상세의 errorCode, 없으면 error.status."""
    try:
        error = response.json()["error"]
        for detail in error.get("details", []):
            if detail.get("@type") == FCM_ERROR_TYPE and detail.get("errorCode"):
                return str(detail["errorCode"])
        return str(error.get("status", ""))
    except (ValueError, KeyError, TypeError, AttributeError):
        return ""


@retry(
    retry=retry_if_exception_type((httpx.TransportError, _Transient)),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=4),
    reraise=True,
)
async def _send_one(client: httpx.AsyncClient, url: str, message: dict[str, Any]) -> str:
    global _cached_token
    headers = {"Authorization": f"Bearer {await access_token()}"}
    response = await client.post(url, json=message, headers=headers)
    status = response.status_code
    if status < 400:
        # name = projects/<id>/messages/<message_id>
        return str(response.json()["name"]).rsplit("/", 1)[-1][:MAX_MESSAGE_ID]
    code = _error_code(response)
    detail = f"fcm HTTP {status} {code}".rstrip()
    if code in INVALID_TOKEN_CODES:
        raise InvalidToken(detail)
    if status == 401:
        # 캐시한 토큰이 먼저 죽었다. 다음 요청은 새로 받는다.
        _cached_token = None
    if status == 429 or status >= 500:
        raise _Transient(detail)
    raise RuntimeError(f"{detail}: {response.text[:200]}")


async def active_devices(user_id: int) -> list[tuple[int, str]]:
    """(기기 id, 토큰). 발송 잡의 항목 트랜잭션과 따로 읽는다."""
    async with session_scope() as session:
        rows = await session.execute(
            select(Device.id, Device.token)
            .where(Device.user_id == user_id, Device.disabled_at.is_(None))
            .order_by(Device.id)
        )
        return [(row.id, row.token) for row in rows]


async def disable_device(device_id: int, error: str) -> None:
    """항목 발송이 롤백돼도 남도록 따로 커밋한다. 앱이 다시 등록하면 활성으로 돌아온다."""
    async with session_scope() as session:
        await session.execute(
            update(Device)
            .where(Device.id == device_id)
            .values(disabled_at=func.now(), last_error=error)
        )


class FcmNotifier:
    channel = "fcm"

    async def send(
        self, item: Item, summary: Summary, level: Level, source_name: str, *, title: str
    ) -> str:
        mode = DELIVERY_MODES[level]
        if level is Level.EXPLORE:
            title = f"{EXPERIMENT_PREFIX}{title}"
        data = {"alert_id": str(item.id), "delivery_mode": mode, "type": "alert"}
        return await self._fan_out(
            title=title, body=summary.summary_ko, data=data, loud=level is Level.PUSH
        )

    async def send_resurface(self, item: Item, title: str) -> str:
        """읽지 않은 찜 재알림. 조용히 보낸다. 무음 시간·채널 꺼짐 판단은 호출자가 한다."""
        data = {"alert_id": str(item.id), "delivery_mode": "quiet", "type": "resurface"}
        return await self._fan_out(
            title=f"{RESURFACE_PREFIX}{title}", body=RESURFACE_BODY, data=data, loud=False
        )

    async def _fan_out(self, *, title: str, body: str, data: dict[str, str], loud: bool) -> str:
        """활성 기기마다 보낸다. 한 대라도 성공하면 첫 message_id, 기기가 없거나 다 실패면 예외."""
        devices = await active_devices(DEFAULT_USER_ID)
        if not devices:
            raise RuntimeError("fcm 등록된 기기 없음")
        url = SEND_URL.format(project=get_settings().fcm_project_id)
        message_ids: list[str] = []
        errors: list[str] = []
        async with httpx.AsyncClient(timeout=TIMEOUT) as client:
            for device_id, token in devices:
                message = build_message(token, title=title, body=body, data=data, loud=loud)
                try:
                    message_ids.append(await _send_one(client, url, message))
                except InvalidToken as exc:
                    await disable_device(device_id, str(exc))
                    errors.append(str(exc))
                    log.info("fcm.device_disabled", device_id=device_id, error=str(exc))
                except Exception as exc:
                    errors.append(f"{type(exc).__name__}: {exc}")
                    log.warning("fcm.send_failed", device_id=device_id, error=str(exc))
        if not message_ids:
            raise RuntimeError(f"fcm 기기 {len(devices)}대 전부 실패: {errors[0]}")
        return message_ids[0]
