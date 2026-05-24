from __future__ import annotations

import argparse

from app.services.jobs_service import execute_job


def main() -> None:
    parser = argparse.ArgumentParser(description="Run a queued AI-OuYi web job")
    parser.add_argument("job_id", type=int)
    args = parser.parse_args()
    job = execute_job(args.job_id)
    print(f"job {job['id']} {job['status']}")


if __name__ == "__main__":
    main()
