"""Idempotent product seed — inserts sample apparel products with variants.

Safe to run on every deploy: skips products whose slug already exists.
"""
import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.product import Category, Product, ProductCategory, ProductVariant

logger = logging.getLogger(__name__)

# ── Category definitions ───────────────────────────────────────────────────────

CATEGORIES = [
    {"name": "T-Shirts",      "slug": "t-shirts"},
    {"name": "Polo Shirts",   "slug": "polo-shirts"},
    {"name": "Jackets",       "slug": "jackets"},
    {"name": "Hoodies",       "slug": "hoodies"},
    {"name": "Dress Shirts",  "slug": "dress-shirts"},
]

# ── Product definitions ────────────────────────────────────────────────────────
# retail_price = wholesale price shown to B2B buyers

PRODUCTS = [
    {
        "name": "Classic White T-Shirt",
        "slug": "classic-white-t-shirt",
        "description": (
            "A timeless wardrobe staple crafted from 100% combed ring-spun cotton. "
            "Pre-shrunk, side-seamed, and available in all standard sizes."
        ),
        "short_description": "100% combed ring-spun cotton, pre-shrunk.",
        "moq": 12,
        "status": "active",
        "category_slug": "t-shirts",
        "variants": [
            {"sku": "CWT-S",   "color": "White", "size": "S",   "retail_price": 15.00},
            {"sku": "CWT-M",   "color": "White", "size": "M",   "retail_price": 15.00},
            {"sku": "CWT-L",   "color": "White", "size": "L",   "retail_price": 15.00},
            {"sku": "CWT-XL",  "color": "White", "size": "XL",  "retail_price": 15.00},
        ],
    },
    {
        "name": "Business Polo Shirt",
        "slug": "business-polo-shirt",
        "description": (
            "A sharp, moisture-wicking polo perfect for corporate settings. "
            "60% cotton / 40% polyester blend. Available in Navy and Black."
        ),
        "short_description": "Moisture-wicking 60/40 blend, corporate ready.",
        "moq": 6,
        "status": "active",
        "category_slug": "polo-shirts",
        "variants": [
            {"sku": "BPS-NVY-S",  "color": "Navy",  "size": "S",  "retail_price": 28.00},
            {"sku": "BPS-NVY-M",  "color": "Navy",  "size": "M",  "retail_price": 28.00},
            {"sku": "BPS-NVY-L",  "color": "Navy",  "size": "L",  "retail_price": 28.00},
            {"sku": "BPS-NVY-XL", "color": "Navy",  "size": "XL", "retail_price": 28.00},
            {"sku": "BPS-BLK-S",  "color": "Black", "size": "S",  "retail_price": 28.00},
            {"sku": "BPS-BLK-M",  "color": "Black", "size": "M",  "retail_price": 28.00},
            {"sku": "BPS-BLK-L",  "color": "Black", "size": "L",  "retail_price": 28.00},
            {"sku": "BPS-BLK-XL", "color": "Black", "size": "XL", "retail_price": 28.00},
        ],
    },
    {
        "name": "Casual Denim Jacket",
        "slug": "casual-denim-jacket",
        "description": (
            "Classic stonewashed denim jacket with button-front closure and two chest pockets. "
            "12 oz. 100% cotton denim. Great for promotional outerwear programs."
        ),
        "short_description": "12 oz. stonewashed 100% cotton denim.",
        "moq": 6,
        "status": "active",
        "category_slug": "jackets",
        "variants": [
            {"sku": "CDJ-S",  "color": "Stonewash Blue", "size": "S",  "retail_price": 62.00},
            {"sku": "CDJ-M",  "color": "Stonewash Blue", "size": "M",  "retail_price": 62.00},
            {"sku": "CDJ-L",  "color": "Stonewash Blue", "size": "L",  "retail_price": 62.00},
            {"sku": "CDJ-XL", "color": "Stonewash Blue", "size": "XL", "retail_price": 62.00},
        ],
    },
    {
        "name": "Sport Hoodie",
        "slug": "sport-hoodie",
        "description": (
            "An 80/20 cotton-polyester pullover hoodie with a kangaroo pocket and "
            "matching drawcord. Double-lined hood and ribbed cuffs and waistband."
        ),
        "short_description": "80/20 fleece pullover with kangaroo pocket.",
        "moq": 12,
        "status": "active",
        "category_slug": "hoodies",
        "variants": [
            {"sku": "SPH-GRY-S",   "color": "Sport Grey", "size": "S",   "retail_price": 34.00},
            {"sku": "SPH-GRY-M",   "color": "Sport Grey", "size": "M",   "retail_price": 34.00},
            {"sku": "SPH-GRY-L",   "color": "Sport Grey", "size": "L",   "retail_price": 34.00},
            {"sku": "SPH-GRY-XL",  "color": "Sport Grey", "size": "XL",  "retail_price": 34.00},
            {"sku": "SPH-GRY-2XL", "color": "Sport Grey", "size": "2XL", "retail_price": 36.00},
            {"sku": "SPH-BLK-S",   "color": "Black",      "size": "S",   "retail_price": 34.00},
            {"sku": "SPH-BLK-M",   "color": "Black",      "size": "M",   "retail_price": 34.00},
            {"sku": "SPH-BLK-L",   "color": "Black",      "size": "L",   "retail_price": 34.00},
            {"sku": "SPH-BLK-XL",  "color": "Black",      "size": "XL",  "retail_price": 34.00},
            {"sku": "SPH-BLK-2XL", "color": "Black",      "size": "2XL", "retail_price": 36.00},
        ],
    },
    {
        "name": "Formal Dress Shirt",
        "slug": "formal-dress-shirt",
        "description": (
            "A slim-fit formal dress shirt in easy-care 60% cotton / 40% polyester. "
            "French placket, spread collar, and adjustable barrel cuffs. "
            "Ideal for uniform and corporate identity programs."
        ),
        "short_description": "Slim-fit, easy-care for uniform programs.",
        "moq": 6,
        "status": "active",
        "category_slug": "dress-shirts",
        "variants": [
            {"sku": "FDS-WHT-S",  "color": "White", "size": "S",  "retail_price": 42.00},
            {"sku": "FDS-WHT-M",  "color": "White", "size": "M",  "retail_price": 42.00},
            {"sku": "FDS-WHT-L",  "color": "White", "size": "L",  "retail_price": 42.00},
            {"sku": "FDS-WHT-XL", "color": "White", "size": "XL", "retail_price": 42.00},
            {"sku": "FDS-LBL-S",  "color": "Light Blue", "size": "S",  "retail_price": 42.00},
            {"sku": "FDS-LBL-M",  "color": "Light Blue", "size": "M",  "retail_price": 42.00},
            {"sku": "FDS-LBL-L",  "color": "Light Blue", "size": "L",  "retail_price": 42.00},
            {"sku": "FDS-LBL-XL", "color": "Light Blue", "size": "XL", "retail_price": 42.00},
        ],
    },
    {
        "name": "Performance Quarter-Zip",
        "slug": "performance-quarter-zip",
        "description": (
            "A lightweight 100% polyester performance quarter-zip with moisture-wicking "
            "finish and cadet collar. Perfect for outdoor and sport programs."
        ),
        "short_description": "Moisture-wicking 100% polyester, cadet collar.",
        "moq": 12,
        "status": "active",
        "category_slug": "hoodies",
        "variants": [
            {"sku": "PQZ-RED-S",  "color": "Red",  "size": "S",  "retail_price": 38.00},
            {"sku": "PQZ-RED-M",  "color": "Red",  "size": "M",  "retail_price": 38.00},
            {"sku": "PQZ-RED-L",  "color": "Red",  "size": "L",  "retail_price": 38.00},
            {"sku": "PQZ-RED-XL", "color": "Red",  "size": "XL", "retail_price": 38.00},
            {"sku": "PQZ-NVY-S",  "color": "Navy", "size": "S",  "retail_price": 38.00},
            {"sku": "PQZ-NVY-M",  "color": "Navy", "size": "M",  "retail_price": 38.00},
            {"sku": "PQZ-NVY-L",  "color": "Navy", "size": "L",  "retail_price": 38.00},
            {"sku": "PQZ-NVY-XL", "color": "Navy", "size": "XL", "retail_price": 38.00},
        ],
    },
]


async def seed_products(db: AsyncSession) -> None:
    """Insert categories and products. Skips any slug that already exists."""

    # ── 1. Upsert categories ───────────────────────────────────────────────────
    cat_map: dict[str, Category] = {}
    for cat_data in CATEGORIES:
        existing = (
            await db.execute(select(Category).where(Category.slug == cat_data["slug"]))
        ).scalar_one_or_none()

        if existing:
            cat_map[cat_data["slug"]] = existing
        else:
            cat = Category(
                name=cat_data["name"],
                slug=cat_data["slug"],
                is_active=True,
                sort_order=0,
            )
            db.add(cat)
            await db.flush()  # populate cat.id
            cat_map[cat_data["slug"]] = cat
            logger.info("Created category: %s", cat_data["slug"])

    # ── 2. Upsert products + variants ─────────────────────────────────────────
    products_created = 0
    variants_created = 0

    for prod_data in PRODUCTS:
        existing_product = (
            await db.execute(select(Product).where(Product.slug == prod_data["slug"]))
        ).scalar_one_or_none()

        if existing_product:
            logger.info("Skipping existing product: %s", prod_data["slug"])
            product = existing_product
        else:
            product = Product(
                name=prod_data["name"],
                slug=prod_data["slug"],
                description=prod_data.get("description"),
                short_description=prod_data.get("short_description"),
                moq=prod_data["moq"],
                status=prod_data["status"],
            )
            db.add(product)
            await db.flush()  # populate product.id
            products_created += 1

            # Link to category
            cat = cat_map.get(prod_data["category_slug"])
            if cat:
                db.add(ProductCategory(product_id=product.id, category_id=cat.id))

        # Insert variants that don't exist yet (idempotent by SKU)
        for v in prod_data["variants"]:
            existing_variant = (
                await db.execute(
                    select(ProductVariant).where(ProductVariant.sku == v["sku"])
                )
            ).scalar_one_or_none()

            if not existing_variant:
                db.add(ProductVariant(
                    product_id=product.id,
                    sku=v["sku"],
                    color=v.get("color"),
                    size=v.get("size"),
                    retail_price=v["retail_price"],
                    status="active",
                    sort_order=0,
                ))
                variants_created += 1

    await db.commit()
    logger.info(
        "Seed complete — %d products, %d variants created.",
        products_created,
        variants_created,
    )
    print(f"✓ Seeded {products_created} products and {variants_created} variants.")
