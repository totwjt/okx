from __future__ import annotations

import asyncio
from typing import Any

from fastapi import APIRouter, Query, WebSocket, WebSocketDisconnect
from fastapi.encoders import jsonable_encoder

from app.services.jobs_service import list_jobs
from app.services.registry_service import list_runtime_artifacts


router = APIRouter(tags=["ws"])

TOPIC_JOBS = "jobs"
TOPIC_RUNTIME_ARTIFACTS = "runtime.artifacts"
SUPPORTED_TOPICS = {TOPIC_JOBS, TOPIC_RUNTIME_ARTIFACTS}


def _topics_from_query(raw_topics: str) -> set[str]:
    requested = {topic.strip() for topic in raw_topics.split(",") if topic.strip()}
    return requested & SUPPORTED_TOPICS or set(SUPPORTED_TOPICS)


def _signature(rows: list[dict[str, Any]], time_key: str) -> str:
    if not rows:
        return "0:none"
    latest = rows[0]
    return f"{len(rows)}:{latest.get('id')}:{latest.get(time_key)}"


async def _topic_payload(topic: str) -> tuple[str, dict[str, Any]]:
    if topic == TOPIC_JOBS:
        rows = list_jobs(limit=25)
        return _signature(rows, "updated_at"), {"items": rows}
    if topic == TOPIC_RUNTIME_ARTIFACTS:
        rows = list_runtime_artifacts(limit=50)
        return _signature(rows, "created_at"), {"items": rows}
    raise RuntimeError(f"unsupported websocket topic: {topic}")


@router.websocket("/ws")
async def websocket_updates(
    websocket: WebSocket,
    topics: str = Query(default="jobs,runtime.artifacts"),
) -> None:
    await websocket.accept()
    selected_topics = _topics_from_query(topics)
    versions: dict[str, str] = {}

    try:
        await websocket.send_json(
            {
                "topic": "connection",
                "event": "ready",
                "payload": {"topics": sorted(selected_topics)},
            },
        )
        while True:
            for topic in selected_topics:
                try:
                    version, payload = await _topic_payload(topic)
                except Exception as exc:
                    await websocket.send_json(
                        {
                            "topic": topic,
                            "event": "error",
                            "payload": {"message": str(exc)},
                        },
                    )
                    continue

                if versions.get(topic) != version:
                    versions[topic] = version
                    await websocket.send_json(
                        jsonable_encoder(
                            {
                                "topic": topic,
                                "event": "changed",
                                "version": version,
                                "payload": payload,
                            },
                        ),
                    )
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return
