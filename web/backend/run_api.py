#!/usr/bin/env python3
from __future__ import annotations

import uvicorn


def main() -> None:
    uvicorn.run(
        "app.main:app",
        app_dir="web/backend",
        host="127.0.0.1",
        port=8123,
    )


if __name__ == "__main__":
    main()

