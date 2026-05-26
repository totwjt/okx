#!/usr/bin/env python3
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        app_dir="web/backend",
        host=os.getenv("AI_OUYI_WEB_HOST", "127.0.0.1"),
        port=int(os.getenv("AI_OUYI_WEB_PORT", "8123")),
    )


if __name__ == "__main__":
    main()
