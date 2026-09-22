from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.security import decode_token


class AuthMiddleware(BaseHTTPMiddleware):
    """Reject missing or expired credentials before protected routes execute."""

    protected_prefixes = ("/analysis", "/repositories", "/patches")
    protected_paths = {"/auth/me"}

    async def dispatch(self, request: Request, call_next) -> Response:
        is_options = request.method == "OPTIONS"
        is_protected = request.url.path in self.protected_paths or request.url.path.startswith(self.protected_prefixes)

        if is_protected and not is_options:
            authorization = request.headers.get("Authorization", "")
            scheme, _, token = authorization.partition(" ")
            if scheme.lower() != "bearer" or not token or not decode_token(token):
                return JSONResponse(
                    status_code=401,
                    content={"detail": "Authentication required or token expired"},
                    headers={"WWW-Authenticate": "Bearer"},
                )

        return await call_next(request)