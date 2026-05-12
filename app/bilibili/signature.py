from __future__ import annotations

from hashlib import md5, sha256
import hmac


def build_content_md5(body: str) -> str:
    return md5(body.encode("utf-8")).hexdigest()


def build_canonical_headers(
    *,
    access_key_id: str,
    content_md5: str,
    nonce: str,
    timestamp: int,
) -> str:
    return "\n".join(
        [
            f"x-bili-accesskeyid:{access_key_id}",
            f"x-bili-content-md5:{content_md5}",
            "x-bili-signature-method:HMAC-SHA256",
            f"x-bili-signature-nonce:{nonce}",
            "x-bili-signature-version:1.0",
            f"x-bili-timestamp:{timestamp}",
        ]
    )


def build_signature(secret: str, canonical_headers: str) -> str:
    return hmac.new(
        secret.encode("utf-8"),
        canonical_headers.encode("utf-8"),
        digestmod=sha256,
    ).hexdigest()
