from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.main import create_app
from app.server_settings import load_server_settings

def main() -> None:
    settings = load_server_settings()

    url = f"http://127.0.0.1:{settings.port}"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=settings.port,
        reload=False,
        log_level=settings.log_level,
    )


if __name__ == "__main__":
    main()
