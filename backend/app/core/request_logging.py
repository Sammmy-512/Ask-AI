import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from app.core.request_context import request_id_var

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):

    async def dispatch(self, request: Request, call_next):
        request_id = str(uuid.uuid4())
        request_id_var.set(request_id)
        start_time = time.perf_counter()

        request.state.request_id = request_id

        try:
            response = await call_next(request)

            logger.info(
                "HTTP request completed | request_id=%s | method=%s | path=%s | status=%d | duration=%.2fs",
                request_id,
                request.method,
                request.url.path,
                response.status_code,
                time.perf_counter() - start_time
            )

            response.headers["X-Request-ID"] = request_id

            return response

        except Exception:
            logger.exception(
                "HTTP request failed | request_id=%s | method=%s | path=%s",
                request_id,
                request.method,
                request.url.path
            )
            raise
