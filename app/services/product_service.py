"""ProductService — product catalog with filters, full-text search, and tier pricing."""
import json
import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select, text
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import NotFoundError
from app.core.redis import redis_delete, redis_get, redis_set
from app.models.product import Category, Product, ProductCategory, ProductVariant, ProductImage
from app.models.inventory import InventoryRecord
from app.schemas.product import FilterParams

logger = logging.getLogger(__name__)

_LISTING_TTL = 300    # 5 min
_DETAIL_TTL = 600     # 10 min
_CATEGORY_TTL = 3600  # 1 hr


class ProductService:
    def __init__(self, db: AsyncSession):
        self.db = db

    # ------------------------------------------------------------------
    # Category tree
    # ------------------------------------------------------------------

    async def get_category_tree(self) -> list[Category]:
        cached = await redis_get("categories:tree")
        if cached:
            return json.loads(cached)  # returned as plain dicts for response

        result = await self.db.execute(
            select(Category).options(selectinload(Category.children)).order_by(Category.name)
        )
        all_cats = result.scalars().all()

        # Only top-level categories; children are already eagerly loaded via selectinload
        root = [c for c in all_cats if c.parent_id is None]

        await redis_set("categories:tree", json.dumps([_cat_to_dict(c) for c in root]), expire=_CATEGORY_TTL)
        return root

    # ------------------------------------------------------------------
    # Product listing
    # ------------------------------------------------------------------

    async def list_with_filters_and_search(
        self,
        params: FilterParams,
        discount_percent: Decimal = Decimal("0"),
    ) -> tuple[list[Product], int]:
        cache_key = (
            f"products:list:{params.category}:{params.size}:{params.color}:"
            f"{params.price_min}:{params.price_max}:{params.q}:{params.page}:"
            f"{params.page_size}:{discount_percent}"
        )
        cached = await redis_get(cache_key)
        if cached:
            data = json.loads(cached)
            return data["items"], data["total"]

        query = (
            select(Product)
            .options(
                selectinload(Product.variants),
                selectinload(Product.images),
                selectinload(Product.category_links).selectinload(
                    ProductCategory.category
                ).selectinload(Category.children),
            )
            .where(Product.status == "active")
        )

        if params.category:
            query = query.join(ProductCategory).join(Category).where(
                or_(Category.slug == params.category, Category.name == params.category)
            )

        if params.q:
            query = query.where(
                or_(
                    Product.search_vector.op("@@")(
                        func.plainto_tsquery("english", params.q)
                    ),
                    Product.name.ilike(f"%{params.q}%"),
                )
            )

        if params.size:
            query = query.join(ProductVariant).where(
                ProductVariant.size == params.size,
                ProductVariant.status == "active",
            )

        if params.color:
            query = query.join(ProductVariant, isouter=True).where(
                ProductVariant.color == params.color,
                ProductVariant.status == "active",
            )

        # Count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar_one()

        # Paginate
        offset = (params.page - 1) * params.page_size
        query = query.offset(offset).limit(params.page_size).distinct()

        result = await self.db.execute(query)
        products = result.scalars().unique().all()

        # Apply pricing
        products = await self._attach_pricing_and_stock(list(products), discount_percent)

        await redis_set(
            cache_key,
            json.dumps({"items": [_product_to_dict(p) for p in products], "total": total}),
            expire=_LISTING_TTL,
        )
        return list(products), total

    # ------------------------------------------------------------------
    # Product detail
    # ------------------------------------------------------------------

    async def get_by_slug_with_variants(
        self, slug: str, discount_percent: Decimal = Decimal("0")
    ) -> Product:
        cache_key = f"products:detail:{slug}:{discount_percent}"
        cached = await redis_get(cache_key)
        if cached:
            return json.loads(cached)

        result = await self.db.execute(
            select(Product)
            .options(
                selectinload(Product.variants),
                selectinload(Product.images),
                selectinload(Product.category_links).selectinload(
                    ProductCategory.category
                ).selectinload(Category.children),
            )
            .where(Product.slug == slug, Product.status == "active")
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(f"Product '{slug}' not found")

        products = await self._attach_pricing_and_stock([product], discount_percent)
        product = products[0]

        await redis_set(cache_key, json.dumps(_product_to_dict(product)), expire=_DETAIL_TTL)
        return product

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    async def _attach_pricing_and_stock(
        self, products: list[Product], discount_percent: Decimal
    ) -> list[Product]:
        from app.services.pricing_service import PricingService

        pricing_svc = PricingService(self.db)

        for product in products:
            for variant in product.variants:
                variant.effective_price = pricing_svc.calculate_effective_price(
                    variant.retail_price, discount_percent
                )
                # Sum stock across all warehouses
                stock_result = await self.db.execute(
                    select(func.coalesce(func.sum(InventoryRecord.quantity), 0)).where(
                        InventoryRecord.variant_id == variant.id
                    )
                )
                variant.stock_quantity = stock_result.scalar_one()

        return products

    async def invalidate_product_cache(self, slug: str | None = None) -> None:
        if slug:
            await redis_delete(f"products:detail:{slug}:*")
        # Listing cache invalidation is approximate (TTL-based)

    # ------------------------------------------------------------------
    # Admin methods (T104 — Phase 10)
    # ------------------------------------------------------------------

    async def create_product(self, data) -> Product:
        from app.schemas.product import ProductCreate
        product = Product(
            name=data.name,
            slug=data.slug,
            description=data.description,
            moq=data.moq,
            status=data.status,
            meta_title=data.meta_title,
            meta_description=data.meta_description,
        )
        self.db.add(product)
        await self.db.flush()

        for cat_id in data.category_ids:
            self.db.add(ProductCategory(product_id=product.id, category_id=cat_id))

        await self.db.flush()
        await self.db.refresh(product)
        return product

    async def update_product(self, product_id: UUID, data) -> Product:
        result = await self.db.execute(
            select(Product).where(Product.id == product_id)
        )
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(f"Product {product_id} not found")

        update_data = data.model_dump(exclude_unset=True, exclude={"category_ids"})
        for field, value in update_data.items():
            setattr(product, field, value)

        if data.category_ids is not None:
            await self.db.execute(
                ProductCategory.__table__.delete().where(
                    ProductCategory.product_id == product_id
                )
            )
            for cat_id in data.category_ids:
                self.db.add(ProductCategory(product_id=product_id, category_id=cat_id))

        await self.db.flush()
        await self.db.refresh(product)
        await self.invalidate_product_cache(product.slug)
        return product

    async def bulk_generate_variants(
        self, product_id: UUID, colors: list[str], sizes: list[str], base_price: Decimal
    ) -> list[ProductVariant]:
        import itertools

        result = await self.db.execute(select(Product).where(Product.id == product_id))
        product = result.scalar_one_or_none()
        if not product:
            raise NotFoundError(f"Product {product_id} not found")

        variants = []
        for color, size in itertools.product(colors, sizes):
            sku = f"{product.slug[:20].upper()}-{color[:3].upper()}-{size.upper()}"
            variant = ProductVariant(
                product_id=product_id,
                sku=sku,
                color=color,
                size=size,
                retail_price=base_price,
                status="active",
            )
            self.db.add(variant)
            variants.append(variant)

        await self.db.flush()
        return variants

    async def delete_variant(self, variant_id: UUID) -> None:
        result = await self.db.execute(
            select(ProductVariant).where(ProductVariant.id == variant_id)
        )
        variant = result.scalar_one_or_none()
        if not variant:
            raise NotFoundError(f"Variant {variant_id} not found")
        variant.status = "discontinued"
        await self.db.flush()

    async def apply_bulk_action(self, ids: list[UUID], action: str) -> int:
        """publish | unpublish | delete (soft) products."""
        from sqlalchemy import update

        status_map = {"publish": "active", "unpublish": "draft", "delete": "archived"}
        new_status = status_map.get(action)
        if not new_status:
            raise ValidationError(f"Unknown bulk action: {action}")

        await self.db.execute(
            update(Product).where(Product.id.in_(ids)).values(status=new_status)
        )
        await self.db.flush()
        return len(ids)

    async def import_from_csv(self, csv_content: str) -> dict:
        """Parse CSV rows; insert or update products + variants."""
        import csv
        import io

        reader = csv.DictReader(io.StringIO(csv_content))
        imported = skipped = 0
        errors: list[str] = []

        for i, row in enumerate(reader, start=2):  # row 1 = header
            try:
                name = row.get("name", "").strip()
                slug = row.get("slug", "").strip()
                sku = row.get("sku", "").strip()
                if not name or not sku:
                    skipped += 1
                    continue

                # Upsert product by slug
                product_result = await self.db.execute(
                    select(Product).where(Product.slug == slug)
                )
                product = product_result.scalar_one_or_none()
                if not product:
                    product = Product(
                        name=name,
                        slug=slug or name.lower().replace(" ", "-"),
                        moq=int(row.get("moq", 1)),
                        status=row.get("status", "draft"),
                    )
                    self.db.add(product)
                    await self.db.flush()

                # Upsert variant by SKU
                from decimal import Decimal

                variant_result = await self.db.execute(
                    select(ProductVariant).where(ProductVariant.sku == sku)
                )
                variant = variant_result.scalar_one_or_none()
                if not variant:
                    variant = ProductVariant(
                        product_id=product.id,
                        sku=sku,
                        color=row.get("color"),
                        size=row.get("size"),
                        retail_price=Decimal(row.get("retail_price", "0")),
                        status="active",
                    )
                    self.db.add(variant)
                else:
                    variant.retail_price = Decimal(row.get("retail_price", str(variant.retail_price)))

                imported += 1
            except Exception as exc:
                errors.append(f"Row {i}: {exc}")
                skipped += 1

        await self.db.flush()
        return {"imported": imported, "skipped": skipped, "errors": errors}

    async def export_to_csv(self) -> str:
        """Export all products + variants as CSV string."""
        import csv
        import io

        result = await self.db.execute(select(Product))
        products = result.scalars().all()

        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["name", "slug", "moq", "status", "sku", "color", "size", "retail_price"])

        for product in products:
            variant_result = await self.db.execute(
                select(ProductVariant).where(ProductVariant.product_id == product.id)
            )
            variants = variant_result.scalars().all()
            if not variants:
                writer.writerow([product.name, product.slug, product.moq, product.status, "", "", "", ""])
            for variant in variants:
                writer.writerow([
                    product.name, product.slug, product.moq, product.status,
                    variant.sku, variant.color, variant.size, variant.retail_price,
                ])

        return buf.getvalue()


def _product_to_dict(product: Product) -> dict:
    """Serialize a Product ORM object to a plain dict (JSON-safe)."""
    return {
        "id": str(product.id),
        "name": product.name,
        "slug": product.slug,
        "status": product.status,
        "moq": product.moq,
        "description": product.description,
        "meta_title": getattr(product, "meta_title", None),
        "meta_description": getattr(product, "meta_description", None),
        "images": [_image_to_dict(i) for i in getattr(product, "images", [])],
        "variants": [_variant_to_dict(v) for v in getattr(product, "variants", [])],
        "categories": [_cat_to_dict(link.category) for link in getattr(product, "category_links", []) if getattr(link, "category", None)],
        "created_at": str(product.created_at),
        "updated_at": str(product.updated_at),
    }


def _variant_to_dict(variant: ProductVariant) -> dict:
    return {
        "id": str(variant.id),
        "sku": variant.sku,
        "color": variant.color,
        "size": variant.size,
        "retail_price": str(variant.retail_price),
        "effective_price": str(getattr(variant, "effective_price", variant.retail_price)),
        "stock_quantity": getattr(variant, "stock_quantity", 0),
        "status": variant.status,
    }


def _image_to_dict(image: ProductImage) -> dict:
    return {
        "id": str(image.id),
        "url_thumbnail": image.url_thumbnail,
        "url_medium": image.url_medium,
        "url_large": image.url_large,
        "url_thumbnail_webp": getattr(image, "url_thumbnail_webp", None),
        "url_medium_webp": getattr(image, "url_medium_webp", None),
        "url_large_webp": getattr(image, "url_large_webp", None),
        "alt_text": image.alt_text,
        "is_primary": image.is_primary,
        "position": image.position,
    }


def _cat_to_dict(cat: Category) -> dict:
    return {
        "id": str(cat.id),
        "name": cat.name,
        "slug": cat.slug,
        "parent_id": str(cat.parent_id) if cat.parent_id else None,
        "children": [_cat_to_dict(c) for c in getattr(cat, "children", [])],
    }
