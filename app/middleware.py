from __future__ import annotations

import os
import re
import secrets
import time

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars

# req-<8-char-hex>, ví dụ req-1a2b3c4d
REQUEST_ID_RE = re.compile(r"^req-[0-9a-f]{8}$")


def make_correlation_id() -> str:
    return f"req-{secrets.token_hex(4)}"


def is_valid_correlation_id(value: str) -> bool:
    return bool(REQUEST_ID_RE.match(value))


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # Xóa context của request trước đó để tránh rò rỉ contextvars giữa các request
        clear_contextvars()

        # Nhận x-request-id từ client hoặc sinh mới theo format req-<8-hex>
        incoming = request.headers.get("x-request-id", "")
        correlation_id = incoming if is_valid_correlation_id(incoming) else make_correlation_id()

        bind_contextvars(correlation_id=correlation_id, env=os.getenv("APP_ENV", "dev"))

        request.state.correlation_id = correlation_id

        start = time.perf_counter()
        response = await call_next(request)

        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{(time.perf_counter() - start) * 1000:.1f}"

        return response
