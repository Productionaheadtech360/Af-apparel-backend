"""Audit middleware — auto-logs admin write operations to audit_log table.

T197: Intercepts all admin PATCH/POST/DELETE routes.
Captures: action_type, entity_type, entity_id, IP address, user_agent.
old_values/new_values are captured by route handlers via write_audit_log().
"""
import json
from typing import Any

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

AUDITED_METHODS = {"POST", "PATCH", "PUT", "DELETE"}
ADMIN_PATH_PREFIX = "/api/v1/admin/"

# Paths that should NOT be audited (read-only or export endpoints)
AUDIT_EXCLUSIONS = {"/api/v1/admin/quickbooks/status"}


class AuditMiddleware(BaseHTTPMiddleware):
    """Intercept admin write operations and write an audit_log entry after response."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        path = request.url.path
        method = request.method

        # Only audit admin write operations not in exclusion list
        should_audit = (
            path.startswith(ADMIN_PATH_PREFIX)
            and method in AUDITED_METHODS
            and path not in AUDIT_EXCLUSIONS
        )

        if not should_audit:
            return await call_next(request)

        # Capture request body for new_values (must consume before call_next)
        body_bytes = await request.body()
        new_values_raw: dict | None = None
        if body_bytes:
            try:
                new_values_raw = json.loads(body_bytes)
            except Exception:
                new_values_raw = None

        # Re-inject body so route handlers can still read it
        async def receive():
            return {"type": "http.request", "body": body_bytes, "more_body": False}

        request._receive = receive  # type: ignore[attr-defined]

        response = await call_next(request)

        # Only log successful mutations (2xx)
        if 200 <= response.status_code < 300:
            user_id = getattr(request.state, "user_id", None)
            client_ip = request.client.host if request.client else "unknown"
            user_agent = request.headers.get("user-agent", "")

            action_map = {"POST": "CREATE", "PATCH": "UPDATE", "PUT": "UPDATE", "DELETE": "DELETE"}
            action = action_map.get(method, "UPDATE")

            # /api/v1/admin/products/{id}/... → entity_type=products, entity_id={id}
            path_parts = path.replace(ADMIN_PATH_PREFIX, "").split("/")
            entity_type = path_parts[0] if path_parts else "unknown"
            entity_id = path_parts[1] if len(path_parts) > 1 and path_parts[1] else None

            # Skip UUID-like sub-action suffixes (e.g. /approve, /reject)
            if entity_id and not _looks_like_id(entity_id):
                entity_id = None

            # Persist audit log entry asynchronously
            try:
                from app.core.database import AsyncSessionLocal
                from app.models.system import AuditLog
                import uuid as _uuid

                async with AsyncSessionLocal() as session:
                    log = AuditLog(
                        admin_user_id=_uuid.UUID(str(user_id)) if user_id else None,
                        action=action,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        new_values=json.dumps(new_values_raw, default=str) if new_values_raw else None,
                        ip_address=client_ip,
                        user_agent=user_agent,
                    )
                    session.add(log)
                    await session.commit()
            except Exception:
                pass  # Never block the response due to audit failure

        return response


def _looks_like_id(value: str) -> bool:
    """Heuristic: UUID or numeric ID."""
    import re
    return bool(re.match(r"^[0-9a-f\-]{8,}$", value, re.IGNORECASE) or re.match(r"^\d+$", value))


async def write_audit_log(
    db: Any,
    admin_user_id: str | None,
    action: str,
    entity_type: str,
    entity_id: str | None,
    old_values: dict[str, Any] | None,
    new_values: dict[str, Any] | None,
    ip_address: str | None = None,
    user_agent: str | None = None,
) -> None:
    """Write a single audit log entry. Called directly from service layer for precision."""
    from app.models.system import AuditLog
    import uuid

    log = AuditLog(
        admin_user_id=uuid.UUID(admin_user_id) if admin_user_id else None,
        action=action,
        entity_type=entity_type,
        entity_id=str(entity_id) if entity_id else None,
        old_values=json.dumps(old_values, default=str) if old_values else None,
        new_values=json.dumps(new_values, default=str) if new_values else None,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(log)
    # Note: caller is responsible for committing
