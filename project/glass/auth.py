"""Bearer token authentication middleware for Glass API endpoints.

Every production deployment needs access control. Without it, Glass is a
compliance tool with no security boundary — a contradiction.

Design:
- If GLASS_API_TOKEN is not set, auth is disabled (open access for local dev).
- If set, all /api/* endpoints require Authorization: Bearer <token>.
- Health probes (/healthz, /readyz) and static assets (/, /static/*) are
  always unauthenticated — required for k8s probes and browser loading.
- Returns 401 with a clear error message, never leaks the expected token.
"""

import logging
import os
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse

logger = logging.getLogger("glass.auth")

# Paths that never require authentication
PUBLIC_PATHS = frozenset({"/healthz", "/readyz", "/", "/docs", "/openapi.json"})
PUBLIC_PREFIXES = ("/static/",)


def _is_public(path: str) -> bool:
    """Check if a request path is public (no auth required)."""
    if path in PUBLIC_PATHS:
        return True
    for prefix in PUBLIC_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


class BearerAuthMiddleware(BaseHTTPMiddleware):
    """Middleware that enforces Bearer token auth on /api/* endpoints.

    Activated only when GLASS_API_TOKEN environment variable is set.
    Uses constant-time comparison to prevent timing attacks.
    """

    def __init__(self, app, token: str | None = None):
        super().__init__(app)
        self.token = token or os.environ.get("GLASS_API_TOKEN")
        if self.token:
            logger.info("Bearer token auth enabled for /api/* endpoints")
        else:
            logger.info("Bearer token auth disabled (GLASS_API_TOKEN not set)")

    async def dispatch(self, request: Request, call_next):
        # Skip auth if no token configured (local dev mode)
        if not self.token:
            return await call_next(request)

        path = request.url.path

        # Public paths bypass auth
        if _is_public(path):
            return await call_next(request)

        # All other paths (including /api/*) require auth
        auth_header = request.headers.get("Authorization", "")
        if not auth_header.startswith("Bearer "):
            return JSONResponse(
                status_code=401,
                content={
                    "detail": "Authentication required. Set Authorization: Bearer <token> header.",
                },
                headers={"WWW-Authenticate": "Bearer"},
            )

        provided_token = auth_header[7:]  # Strip "Bearer "

        # Constant-time comparison to prevent timing attacks
        if not secrets.compare_digest(provided_token, self.token):
            logger.warning("Invalid bearer token from %s", request.client.host if request.client else "unknown")
            return JSONResponse(
                status_code=401,
                content={"detail": "Invalid token."},
                headers={"WWW-Authenticate": "Bearer"},
            )

        return await call_next(request)
