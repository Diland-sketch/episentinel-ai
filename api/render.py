"""Fail-closed public transport adapter. Never changes B03/B04/B05/B06/B07/B10."""
from collections import deque
import json
import os
from pathlib import Path
import secrets
import threading
import time
from urllib.parse import urlsplit
from uuid import uuid4

from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

from .main import create_app, ROOT
from .store import SessionStore

PUBLIC_BODY_LIMIT = 128 * 1024


def memory_current():
    try:
        return int(Path("/sys/fs/cgroup/memory.current").read_text())
    except (OSError, ValueError):
        return None


class PublicGuard:
    def __init__(self, app, key, methods, ingestion, clock=time.monotonic):
        self.app, self.key, self.methods, self.ingestion = app, key, methods, ingestion
        self.clock = clock
        self.lock = threading.Lock()
        self.active = threading.BoundedSemaphore(2)
        self.reads, self.writes = deque(), deque()

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path, method = scope["path"], scope["method"]

        async def reject(status, code):
            rid = uuid4().hex
            response = JSONResponse({"error": {"code": code, "message": code, "details": None}, "request_id": rid},
                                    status_code=status, headers={"Cache-Control": "no-store", "X-Request-ID": rid})
            await response(scope, receive, send)

        if method == "OPTIONS" or path in ("/api/v1/health", "/api/v1/ready"):
            return await self.app(scope, receive, send)
        protected = method not in ("GET", "HEAD") or path.startswith("/api/v1/datasets")
        headers = dict(scope["headers"])
        if protected and not secrets.compare_digest(headers.get(b"x-operator-key", b""), self.key.encode()):
            return await reject(401, "OPERATOR_KEY_REQUIRED")
        if (path.startswith("/api/v1/datasets") or path.startswith("/api/v1/sessions")) and not self.ingestion:
            return await reject(403, "INGESTION_DISABLED")
        if path == "/api/v1/forecasts/retrospective" and not self.methods:
            return await reject(403, "FORECAST_DISABLED")
        # Global budgets, unaffected by forged X-Forwarded-For headers.
        now = self.clock()
        with self.lock:
            queue, maximum = (self.writes, 5) if protected else (self.reads, 120)
            while queue and queue[0] <= now - 60:
                queue.popleft()
            limited = len(queue) >= maximum
            if not limited:
                queue.append(now)
        if limited:
            return await reject(429, "RATE_LIMITED")
        if not self.active.acquire(blocking=False):
            return await reject(429, "SERVER_BUSY")
        try:
            if method in {"POST", "PUT", "PATCH"}:
                chunks, total = [], 0
                while True:
                    event = await receive()
                    if event["type"] == "http.disconnect":
                        return
                    total += len(event.get("body", b""))
                    if total > PUBLIC_BODY_LIMIT:
                        return await reject(413, "BODY_TOO_LARGE")
                    chunks.append(event.get("body", b""))
                    if not event.get("more_body", False):
                        break
                payload = b"".join(chunks)
                if path == "/api/v1/forecasts/retrospective":
                    try:
                        body = json.loads(payload)
                        if not isinstance(body, dict):
                            raise ValueError()
                    except (ValueError, UnicodeError, RecursionError):
                        return await reject(422, "INVALID_REQUEST")
                    if not isinstance(body.get("method"), str):
                        return await reject(422, "INVALID_REQUEST")
                    if body.get("method") not in self.methods:
                        return await reject(403, "METHOD_DISABLED")
                    current = memory_current()
                    if body.get("method") == "sarima_sin_estacional" and (current is None or current > 256 * 1024**2):
                        return await reject(503, "INSUFFICIENT_MEMORY_HEADROOM")
                delivered = False
                original_receive = receive

                async def replay():
                    nonlocal delivered
                    if not delivered:
                        delivered = True
                        return {"type": "http.request", "body": payload, "more_body": False}
                    return await original_receive()

                receive = replay
            await self.app(scope, receive, send)
        finally:
            self.active.release()


def application():
    key = os.getenv("EPISENTINEL_OPERATOR_KEY", "")
    origins = [s.strip() for s in os.getenv("EPISENTINEL_CORS_ORIGINS", "").split(",") if s.strip()]
    if len(key) < 32 or not key.isascii() or not origins:
        raise ValueError("Public operator key and exact HTTPS origins required")
    for origin in origins:
        url = urlsplit(origin)
        local = (os.getenv("EPISENTINEL_ALLOW_LOOPBACK_ORIGIN") == "1" and url.scheme == "http" and url.hostname in {"127.0.0.1", "localhost"})
        if (url.scheme != "https" and not local) or not url.hostname or url.path or url.query or url.fragment or url.username is not None or url.password is not None or "*" in origin:
            raise ValueError("Exact HTTPS origin required")
    methods = frozenset(s.strip() for s in os.getenv("EPISENTINEL_FORECAST_METHODS", "ultimo_valor").split(",") if s.strip())
    if not methods <= {"ultimo_valor", "sarima_sin_estacional"}:
        raise ValueError("Method not approved for Render Free")
    if "sarima_sin_estacional" in methods and os.getenv("EPISENTINEL_SARIMA_ACCEPTED") != "1":
        raise ValueError("Explicit memory/CPU acceptance is required before SARIMA exposure")
    ingestion = os.getenv("EPISENTINEL_ENABLE_INGESTION") == "1"
    root = Path(os.getenv("EPISENTINEL_RUNTIME_ROOT", "/tmp/episentinel"))
    app = create_app(ROOT, store=SessionStore(ttl=1800, capacity=4, datasets_per_session=1), panel_root=root)

    @app.get("/api/v1/capabilities")
    def capabilities():
        return {"forecast_methods": sorted(methods), "ingestion_enabled": ingestion,
                "session_ttl_s": 1800, "max_sessions": 4, "datasets_per_session": 1,
                "body_limit_bytes": PUBLIC_BODY_LIMIT, "forecast_timeout_s": 45,
                "max_concurrent_forecasts": 1, "ephemeral_sessions": True,
                "source_attribution": "INS; datos.gov.co/4hyg-wa9d; CC BY-SA 4.0",
                "limitations": ["Technical historical 7D calendar; not official epidemiological weeks", "No distributed sessions or hard per-request RSS limit"]}

    @app.get("/api/v1/ready", include_in_schema=False)
    def ready():
        # Provisioning already verifies identity and structure before server startup.
        available = (root / "data/processed/panel_casos.parquet").is_file()
        return JSONResponse({"ready": available}, status_code=200 if available else 503)

    app.add_middleware(PublicGuard, key=key, methods=methods, ingestion=ingestion)
    app.add_middleware(CORSMiddleware, allow_origins=origins, allow_methods=["GET", "POST", "DELETE"],
                       allow_headers=["Authorization", "Content-Type", "X-Filename", "X-Operator-Key"],
                       expose_headers=["X-Request-ID"], allow_credentials=False)
    original_openapi = app.openapi

    def public_openapi():
        schema = original_openapi()
        schema["components"]["securitySchemes"]["OperatorKey"] = {
            "type": "apiKey", "in": "header", "name": "X-Operator-Key",
            "description": "Operator secret entered at runtime; never embed in a frontend build"}
        for path, operations in schema["paths"].items():
            for verb, operation in operations.items():
                if verb in {"post", "delete"} or path.startswith("/api/v1/datasets"):
                    operation["security"] = [{**item, "OperatorKey": []} for item in operation.get("security", [{}])]
        return schema

    app.openapi = public_openapi
    return app
