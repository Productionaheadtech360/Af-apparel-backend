"""Admin — QuickBooks sync dashboard endpoints.

T195: GET /admin/quickbooks/status, POST /admin/quickbooks/retry/{log_id}
"""
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.middleware.auth_middleware import require_admin
from app.models.system import QBSyncLog

router = APIRouter(prefix="/admin", tags=["Admin — QuickBooks"])


@router.get("/quickbooks/status")
async def quickbooks_status(
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Return QB sync dashboard data: last sync, today's count, failed entries."""
    from datetime import date, datetime, timezone

    today_start = datetime.combine(date.today(), datetime.min.time()).replace(tzinfo=timezone.utc)

    # Last successful sync
    last_success_q = (
        select(QBSyncLog)
        .where(QBSyncLog.status == "success")
        .order_by(QBSyncLog.updated_at.desc())
        .limit(1)
    )
    last_log = (await db.execute(last_success_q)).scalar_one_or_none()
    last_sync_at = last_log.updated_at.isoformat() if last_log else None

    # Synced today
    synced_today_q = (
        select(func.count(QBSyncLog.id))
        .where(QBSyncLog.status == "success")
        .where(QBSyncLog.updated_at >= today_start)
    )
    synced_today = (await db.execute(synced_today_q)).scalar_one() or 0

    # Failed syncs (most recent 50)
    failed_q = (
        select(QBSyncLog)
        .where(QBSyncLog.status == "failed")
        .order_by(QBSyncLog.updated_at.desc())
        .limit(50)
    )
    failed_logs = (await db.execute(failed_q)).scalars().all()

    return {
        "last_sync_at": last_sync_at,
        "synced_today": synced_today,
        "failed_syncs": [
            {
                "id": str(log.id),
                "entity_type": log.entity_type,
                "entity_id": str(log.entity_id),
                "attempt_count": log.attempt_count,
                "error_message": log.error_message,
                "updated_at": log.updated_at.isoformat() if log.updated_at else None,
            }
            for log in failed_logs
        ],
    }


@router.post("/quickbooks/retry/{log_id}")
async def retry_qb_sync(
    log_id: UUID,
    _: None = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Manually trigger a QB sync retry for a failed log entry."""
    result = await db.execute(select(QBSyncLog).where(QBSyncLog.id == log_id))
    log = result.scalar_one_or_none()
    if not log:
        raise HTTPException(status_code=404, detail="Sync log entry not found")

    entity_id = str(log.entity_id)

    if log.entity_type == "company":
        from app.tasks.quickbooks_tasks import sync_customer_to_qb
        task = sync_customer_to_qb.delay(entity_id)
    elif log.entity_type == "order":
        from app.tasks.quickbooks_tasks import sync_order_invoice_to_qb
        task = sync_order_invoice_to_qb.delay(entity_id)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown entity type: {log.entity_type}")

    # Reset status to retry
    log.status = "retry"
    log.error_message = None
    await db.commit()

    return {"status": "queued", "task_id": task.id, "entity_type": log.entity_type, "entity_id": entity_id}
