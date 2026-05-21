#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys

from app.services.system_check import run_system_check


def main() -> int:
    parser = argparse.ArgumentParser(description="Check AI-OuYi Web foundation dependencies.")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when any check fails.")
    args = parser.parse_args()

    result = run_system_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.strict and not result["ok"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())

