from __future__ import annotations

import threading
import webbrowser

import uvicorn

from app.main import create_app


def main() -> None:
    url = "http://127.0.0.1:8000"
    threading.Timer(1.2, lambda: webbrowser.open(url)).start()
    uvicorn.run(
        create_app(),
        host="127.0.0.1",
        port=8000,
        reload=False,
        log_level="info",
    )


if __name__ == "__main__":
    main()
