from __future__ import annotations

import json
import time
from typing import Any
from uuid import uuid4

import httpx

from app.bilibili.signature import (
    build_canonical_headers,
    build_content_md5,
    build_signature,
)


class BilibiliApiError(Exception):
    def __init__(self, code: int, message: str, request_id: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.request_id = request_id


class BilibiliOpenClient:
    def __init__(
        self,
        *,
        base_url: str,
        access_key_id: str,
        access_key_secret: str,
        transport: httpx.AsyncBaseTransport | None = None,
        timeout: float = 10.0,
    ) -> None:
        self._base_url = base_url.rstrip("/")
        self._access_key_id = access_key_id
        self._access_key_secret = access_key_secret
        self._transport = transport
        self._timeout = timeout

    async def start(self, *, app_id: int, code: str) -> dict[str, Any]:
        return await self._post("/v2/app/start", {"app_id": app_id, "code": code})

    async def heartbeat(self, *, game_id: str) -> dict[str, Any]:
        return await self._post("/v2/app/heartbeat", {"game_id": game_id})

    async def end(self, *, app_id: int, game_id: str) -> dict[str, Any]:
        return await self._post("/v2/app/end", {"app_id": app_id, "game_id": game_id})

    async def _post(self, path: str, payload: dict[str, Any]) -> dict[str, Any]:
        body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        timestamp = int(time.time())
        nonce = str(uuid4())
        content_md5 = build_content_md5(body)
        canonical_headers = build_canonical_headers(
            access_key_id=self._access_key_id,
            content_md5=content_md5,
            nonce=nonce,
            timestamp=timestamp,
        )
        signature = build_signature(self._access_key_secret, canonical_headers)
        headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "x-bili-content-md5": content_md5,
            "x-bili-timestamp": str(timestamp),
            "x-bili-signature-method": "HMAC-SHA256",
            "x-bili-signature-nonce": nonce,
            "x-bili-accesskeyid": self._access_key_id,
            "x-bili-signature-version": "1.0",
            "Authorization": signature,
        }
        async with httpx.AsyncClient(
            base_url=self._base_url,
            headers=headers,
            timeout=self._timeout,
            transport=self._transport,
        ) as client:
            response = await client.post(path, content=body)
            response.raise_for_status()
            data = response.json()
        if data.get("code") != 0:
            raise BilibiliApiError(
                data.get("code", -1),
                data.get("message", "unknown error"),
                data.get("request_id"),
            )
        return data
