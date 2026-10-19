"""
Real-Time Server-Sent Events (SSE) Event Bus for Research Intelligence Assistant V2.
Streams authentic backend execution events without simulated timers or fake progress.
Enforces data sanitization so secrets, environment variables, and credentials are never emitted.
"""

import asyncio
import json
import time
from collections import defaultdict
from typing import Any, AsyncGenerator, Dict, List, Optional

from app.core.logging import SECRET_PATTERNS, logger


def sanitize_event_payload(payload: Any) -> Any:
    """Recursively scrubs strings for secret patterns and sensitive infrastructure keys."""
    if isinstance(payload, str):
        sanitized = payload
        for pattern in SECRET_PATTERNS:
            if pattern.groups >= 3:
                sanitized = pattern.sub(r"\1***REDACTED***\3", sanitized)
            elif pattern.groups == 1:
                sanitized = pattern.sub(r"\1***REDACTED***", sanitized)
            else:
                sanitized = pattern.sub("***REDACTED***", sanitized)
        return sanitized
    elif isinstance(payload, dict):
        scrubbed = {}
        for k, v in payload.items():
            # Block sensitive internal metadata keys
            if k.lower() in {"gemini_api_key", "password", "hashed_password", "jwt_secret_key", "secret"}:
                continue
            scrubbed[k] = sanitize_event_payload(v)
        return scrubbed
    elif isinstance(payload, list):
        return [sanitize_event_payload(item) for item in payload]
    return payload


class JobEventBus:
    """
    Per-job event bus broadcasting real execution transitions to SSE subscribers.
    Maintains bounded event history per job to support reconnecting clients.
    """

    def __init__(self):
        self._subscribers: Dict[str, List[asyncio.Queue]] = defaultdict(list)
        self._event_history: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
        self._lock = asyncio.Lock()

    async def publish(self, job_id: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Publishes an event to all active SSE subscribers for a given job."""
        event_record = {
            "id": f"{job_id}_{int(time.time() * 1000)}",
            "job_id": job_id,
            "event": event_type,
            "data": sanitize_event_payload(data or {}),
            "timestamp": time.time()
        }

        # Save to bounded event history (last 50 events per job)
        history = self._event_history[job_id]
        history.append(event_record)
        if len(history) > 50:
            history.pop(0)

        # Distribute to queues
        async with self._lock:
            queues = list(self._subscribers.get(job_id, []))

        for q in queues:
            await q.put(event_record)

    def publish_sync(self, job_id: str, event_type: str, data: Optional[Dict[str, Any]] = None) -> None:
        """Thread-safe synchronous bridge for worker threads calling publish."""
        event_record = {
            "id": f"{job_id}_{int(time.time() * 1000)}",
            "job_id": job_id,
            "event": event_type,
            "data": sanitize_event_payload(data or {}),
            "timestamp": time.time()
        }
        history = self._event_history[job_id]
        history.append(event_record)
        if len(history) > 50:
            history.pop(0)

        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.run_coroutine_threadsafe(self.publish(job_id, event_type, data), loop)
        except RuntimeError:
            pass

    def get_history(self, job_id: str) -> List[Dict[str, Any]]:
        """Returns recorded event history for a job."""
        return list(self._event_history.get(job_id, []))

    async def subscribe(self, job_id: str, last_event_id: Optional[str] = None) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Subscribes to an SSE event stream for a specific research job.
        Replays prior events for reconnecting clients.
        """
        queue: asyncio.Queue = asyncio.Queue()

        async with self._lock:
            self._subscribers[job_id].append(queue)
            prior_events = list(self._event_history.get(job_id, []))

        try:
            # Replay prior events to restore state on reconnect
            for ev in prior_events:
                yield {
                    "id": ev["id"],
                    "event": ev["event"],
                    "data": json.dumps(ev["data"])
                }

            while True:
                # Wait for next live event with a heartbeat timeout
                try:
                    event = await asyncio.wait_for(queue.get(), timeout=15.0)
                    yield {
                        "id": event["id"],
                        "event": event["event"],
                        "data": json.dumps(event["data"])
                    }
                    if event["event"] in {"research_completed", "research_failed", "research_cancelled"}:
                        break
                except asyncio.TimeoutError:
                    # Send periodic SSE keep-alive ping
                    yield {
                        "event": "ping",
                        "data": json.dumps({"timestamp": time.time()})
                    }
        finally:
            async with self._lock:
                if queue in self._subscribers[job_id]:
                    self._subscribers[job_id].remove(queue)


# Global event bus singleton
job_event_bus = JobEventBus()
