from uuid import UUID

from fastapi import APIRouter, Body, Depends, File, Query, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.inventory import (
    AdjustmentResult,
    BulkImportResult,
    InventoryAdjustRequest,
    WarehouseCreate,
    WarehouseOut,
)
from app.services.inventory_service import InventoryService

router = APIRouter(prefix="/admin", tags=["admin", "inventory"])


@router.get("/warehouses", response_model=list[WarehouseOut])
async def list_warehouses(db: AsyncSession = Depends(get_db)):
    svc = InventoryService(db)
    return await svc.list_warehouses()


@router.post("/warehouses", response_model=WarehouseOut, status_code=status.HTTP_201_CREATED)
async def create_warehouse(payload: WarehouseCreate, db: AsyncSession = Depends(get_db)):
    svc = InventoryService(db)
    wh = await svc.create_warehouse(
        payload.name,
        payload.code,
        address_line1=payload.address_line1,
        city=payload.city,
        state=payload.state,
        postal_code=payload.postal_code,
        country=payload.country,
    )
    await db.commit()
    return wh


@router.patch("/warehouses/{warehouse_id}", response_model=WarehouseOut)
async def update_warehouse(
    warehouse_id: UUID,
    payload: dict = Body(...),
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db)
    wh = await svc.update_warehouse(warehouse_id, payload)
    await db.commit()
    return wh


@router.get("/inventory")
async def list_inventory(
    variant_id: UUID | None = None,
    warehouse_id: UUID | None = None,
    low_stock_only: bool = False,
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db)
    if variant_id:
        return await svc.get_inventory_by_variant(variant_id)
    if low_stock_only:
        return await svc.get_low_stock_variants()
    # Return all — paginated by variant
    from sqlalchemy import select
    from app.models.inventory import InventoryRecord, Warehouse
    from app.models.product import ProductVariant

    result = await db.execute(
        select(InventoryRecord, ProductVariant, Warehouse)
        .join(ProductVariant, InventoryRecord.variant_id == ProductVariant.id)
        .join(Warehouse, InventoryRecord.warehouse_id == Warehouse.id)
        .limit(500)
    )
    return [
        {
            "variant_id": str(v.id),
            "sku": v.sku,
            "color": v.color,
            "size": v.size,
            "warehouse_id": str(wh.id),
            "warehouse_name": wh.name,
            "quantity": rec.quantity,
            "low_stock_threshold": rec.low_stock_threshold,
        }
        for rec, v, wh in result.all()
    ]


@router.post("/inventory/adjust", response_model=AdjustmentResult)
async def adjust_inventory(
    payload: InventoryAdjustRequest,
    db: AsyncSession = Depends(get_db),
):
    svc = InventoryService(db)
    record = await svc.adjust_stock_with_log(
        variant_id=payload.variant_id,
        warehouse_id=payload.warehouse_id,
        quantity_delta=payload.quantity_delta,
        reason=payload.reason,
        notes=payload.notes,
    )
    await db.commit()
    return AdjustmentResult(
        variant_id=record.variant_id,
        warehouse_id=record.warehouse_id,
        quantity_after=record.quantity,
    )


@router.post("/inventory/import-csv", response_model=BulkImportResult)
async def import_inventory_csv(
    file: UploadFile = File(...), db: AsyncSession = Depends(get_db)
):
    content = await file.read()
    svc = InventoryService(db)
    result = await svc.bulk_import_csv(content.decode("utf-8"))
    await db.commit()
    return BulkImportResult(**result)
