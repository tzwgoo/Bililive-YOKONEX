from __future__ import annotations

import os

import uvicorn

from management_server.config import load_management_settings
from management_server.main import create_management_app


def main() -> None:
    settings = load_management_settings()
    app = create_management_app(settings)
    uvicorn.run(
        app,
        host=str(os.getenv("MANAGEMENT_HOST", "127.0.0.1") or "127.0.0.1"),
        port=int(str(os.getenv("MANAGEMENT_PORT", "9000") or "9000")),
        log_level="info",
    )


if __name__ == "__main__":
    main()
