from __future__ import annotations

import pytest

from app.config import load_settings


def test_load_settings_requires_all_required_fields(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("APP_ID", raising=False)
    monkeypatch.delenv("BILI_ACCESS_KEY_ID", raising=False)
    monkeypatch.delenv("BILI_ACCESS_KEY_SECRET", raising=False)

    with pytest.raises(ValueError) as exc_info:
        load_settings()

    assert "APP_ID" in str(exc_info.value)
