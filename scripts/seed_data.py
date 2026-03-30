"""Comprehensive seed script for AF Apparels B2B Wholesale Platform.

Idempotent — checks if data exists before inserting.
Uses DATABASE_URL_SYNC (psycopg2, synchronous).

Usage (inside Docker container):
    docker-compose run --rm backend python scripts/seed_data.py

Usage (outside Docker, with backend/ on path):
    DATABASE_URL_SYNC=postgresql://... python scripts/seed_data.py
"""
import os
import random
import sys
from decimal import Decimal
from pathlib import Path

# ── Path setup: works both inside Docker (/app/scripts/) and outside ──────────
_script_dir = Path(__file__).parent
_possible_backend = _script_dir.parent / "backend"
if _possible_backend.is_dir():
    # Running from project root (outside Docker): backend/ is a sibling
    sys.path.insert(0, str(_possible_backend))
else:
    # Running inside Docker container: WORKDIR is /app, app/ is directly there
    sys.path.insert(0, str(_script_dir.parent))

# ── Imports ───────────────────────────────────────────────────────────────────
from passlib.context import CryptContext
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

# Import all models to ensure SQLAlchemy registry + relationships are resolved
import app.models.user  # noqa: F401
import app.models.company  # noqa: F401
import app.models.product  # noqa: F401
import app.models.inventory  # noqa: F401
import app.models.pricing  # noqa: F401
import app.models.shipping  # noqa: F401
import app.models.order  # noqa: F401
import app.models.system  # noqa: F401

try:
    import app.models.rma  # noqa: F401
    import app.models.wholesale  # noqa: F401
    import app.models.communication  # noqa: F401
except ImportError:
    pass

from app.models.company import Company, CompanyUser, UserAddress
from app.models.inventory import InventoryRecord, Warehouse
from app.models.order import Order, OrderItem
from app.models.pricing import PricingTier
from app.models.product import Category, Product, ProductCategory, ProductVariant
from app.models.shipping import ShippingBracket, ShippingTier
from app.models.system import Settings
from app.models.user import User

# ── Password hashing (passlib directly, avoids loading full app config) ───────
_pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return _pwd_context.hash(password)


# ── DB connection ─────────────────────────────────────────────────────────────
DATABASE_URL_SYNC = os.environ.get(
    "DATABASE_URL_SYNC",
    "postgresql://afapparel:afapparel@localhost:5432/afapparel_db",
)

engine = create_engine(DATABASE_URL_SYNC, echo=False)
SessionLocal = sessionmaker(bind=engine)


# ═══════════════════════════════════════════════════════════════════════════════
# DATA DEFINITIONS
# ═══════════════════════════════════════════════════════════════════════════════

PRICING_TIERS = [
    {"name": "Tier 1 Bronze", "description": "Bronze tier — 15% off retail", "discount_percent": Decimal("15.00")},
    {"name": "Tier 2 Silver", "description": "Silver tier — 25% off retail", "discount_percent": Decimal("25.00")},
    {"name": "Tier 3 Gold",   "description": "Gold tier — 35% off retail",   "discount_percent": Decimal("35.00")},
]

SHIPPING_TIERS = [
    {
        "name": "Standard Wholesale",
        "description": "Standard wholesale shipping — quantity-based brackets",
        "brackets": [
            {"min_units": 1,   "max_units": 99,  "cost": Decimal("25.00")},
            {"min_units": 100, "max_units": 499, "cost": Decimal("15.00")},
            {"min_units": 500, "max_units": None, "cost": Decimal("0.00")},
        ],
    },
    {
        "name": "Premium Wholesale",
        "description": "Premium wholesale shipping — lower thresholds for free shipping",
        "brackets": [
            {"min_units": 1,   "max_units": 49,  "cost": Decimal("20.00")},
            {"min_units": 50,  "max_units": 199, "cost": Decimal("10.00")},
            {"min_units": 200, "max_units": None, "cost": Decimal("0.00")},
        ],
    },
]

WAREHOUSES = [
    {"name": "East Coast", "code": "WH-EAST", "city": "Newark",    "state": "NJ", "postal_code": "07102"},
    {"name": "West Coast", "code": "WH-WEST", "city": "Los Angeles", "state": "CA", "postal_code": "90021"},
    {"name": "Central",    "code": "WH-CENTRAL", "city": "Dallas",  "state": "TX", "postal_code": "75201"},
]

CATEGORIES = [
    {"name": "T-Shirts",      "slug": "t-shirts"},
    {"name": "Polo Shirts",   "slug": "polo-shirts"},
    {"name": "Hoodies",       "slug": "hoodies"},
    {"name": "Jackets",       "slug": "jackets"},
    {"name": "Pants",         "slug": "pants"},
    {"name": "Shorts",        "slug": "shorts"},
    {"name": "Caps",          "slug": "caps"},
    {"name": "Accessories",   "slug": "accessories"},
    {"name": "Activewear",    "slug": "activewear"},
    {"name": "Formal Wear",   "slug": "formal-wear"},
]

# Products: (name, slug, category, base_price, sku_prefix, moq, sizes, colors)
PRODUCTS = [
    # T-Shirts
    {
        "name": "Classic Crew Neck Tee",
        "slug": "classic-crew-neck-tee",
        "category": "T-Shirts",
        "price": Decimal("18.99"),
        "sku_prefix": "CCNT",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "White", "Navy", "Grey"],
    },
    {
        "name": "Premium V-Neck T-Shirt",
        "slug": "premium-v-neck-t-shirt",
        "category": "T-Shirts",
        "price": Decimal("22.99"),
        "sku_prefix": "PVNT",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "White", "Navy"],
    },
    {
        "name": "Essential Pocket Tee",
        "slug": "essential-pocket-tee",
        "category": "T-Shirts",
        "price": Decimal("16.99"),
        "sku_prefix": "EPKT",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "White", "Grey", "Red"],
    },
    {
        "name": "Long Sleeve Basic Tee",
        "slug": "long-sleeve-basic-tee",
        "category": "T-Shirts",
        "price": Decimal("24.99"),
        "sku_prefix": "LSBT",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
    # Polo Shirts
    {
        "name": "Performance Polo",
        "slug": "performance-polo",
        "category": "Polo Shirts",
        "price": Decimal("34.99"),
        "sku_prefix": "PPLO",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "White", "Navy", "Red"],
    },
    {
        "name": "Pique Polo Shirt",
        "slug": "pique-polo-shirt",
        "category": "Polo Shirts",
        "price": Decimal("29.99"),
        "sku_prefix": "PQPS",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["White", "Navy", "Grey"],
    },
    # Hoodies
    {
        "name": "Heavyweight Hoodie",
        "slug": "heavyweight-hoodie",
        "category": "Hoodies",
        "price": Decimal("45.99"),
        "sku_prefix": "HWHO",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
    {
        "name": "Pullover Fleece Hoodie",
        "slug": "pullover-fleece-hoodie",
        "category": "Hoodies",
        "price": Decimal("38.99"),
        "sku_prefix": "PFLH",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Grey", "Red"],
    },
    # Jackets
    {
        "name": "Zip-Up Fleece Jacket",
        "slug": "zip-up-fleece-jacket",
        "category": "Jackets",
        "price": Decimal("52.99"),
        "sku_prefix": "ZUFJ",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
    {
        "name": "Bomber Jacket",
        "slug": "bomber-jacket",
        "category": "Jackets",
        "price": Decimal("65.99"),
        "sku_prefix": "BMBJ",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Navy"],
    },
    # Pants
    {
        "name": "Slim Fit Chinos",
        "slug": "slim-fit-chinos",
        "category": "Pants",
        "price": Decimal("38.99"),
        "sku_prefix": "SLFC",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
    {
        "name": "Classic Straight Jeans",
        "slug": "classic-straight-jeans",
        "category": "Pants",
        "price": Decimal("42.99"),
        "sku_prefix": "CSTJ",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Navy"],
    },
    # Shorts
    {
        "name": "Athletic Shorts",
        "slug": "athletic-shorts",
        "category": "Shorts",
        "price": Decimal("24.99"),
        "sku_prefix": "ATLS",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
    {
        "name": "Running Shorts",
        "slug": "running-shorts",
        "category": "Shorts",
        "price": Decimal("19.99"),
        "sku_prefix": "RNGS",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Grey", "Red"],
    },
    {
        "name": "Cargo Shorts",
        "slug": "cargo-shorts",
        "category": "Shorts",
        "price": Decimal("27.99"),
        "sku_prefix": "CRGS",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "Navy"],
    },
    # Caps
    {
        "name": "Snapback Cap",
        "slug": "snapback-cap",
        "category": "Caps",
        "price": Decimal("16.99"),
        "sku_prefix": "SNPC",
        "moq": 24,
        "sizes": ["ONE"],
        "colors": ["Black", "White", "Navy", "Red", "Grey"],
    },
    {
        "name": "Dad Hat",
        "slug": "dad-hat",
        "category": "Caps",
        "price": Decimal("14.99"),
        "sku_prefix": "DADH",
        "moq": 24,
        "sizes": ["ONE"],
        "colors": ["Black", "White", "Navy", "Grey"],
    },
    # Accessories
    {
        "name": "Canvas Tote Bag",
        "slug": "canvas-tote-bag",
        "category": "Accessories",
        "price": Decimal("12.99"),
        "sku_prefix": "CVTB",
        "moq": 24,
        "sizes": ["ONE"],
        "colors": ["Black", "White", "Navy"],
    },
    {
        "name": "Gym Bag",
        "slug": "gym-bag",
        "category": "Accessories",
        "price": Decimal("29.99"),
        "sku_prefix": "GYMB",
        "moq": 12,
        "sizes": ["ONE"],
        "colors": ["Black", "Navy"],
    },
    # Activewear
    {
        "name": "Performance Tank Top",
        "slug": "performance-tank-top",
        "category": "Activewear",
        "price": Decimal("19.99"),
        "sku_prefix": "PFTT",
        "moq": 12,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["Black", "White", "Grey", "Red"],
    },
    {
        "name": "Compression Leggings",
        "slug": "compression-leggings",
        "category": "Activewear",
        "price": Decimal("34.99"),
        "sku_prefix": "CMPL",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
    # Formal Wear
    {
        "name": "Oxford Dress Shirt",
        "slug": "oxford-dress-shirt",
        "category": "Formal Wear",
        "price": Decimal("44.99"),
        "sku_prefix": "OXDS",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL", "2XL"],
        "colors": ["White", "Navy", "Grey"],
    },
    {
        "name": "Classic Blazer",
        "slug": "classic-blazer",
        "category": "Formal Wear",
        "price": Decimal("79.99"),
        "sku_prefix": "CLBZ",
        "moq": 6,
        "sizes": ["S", "M", "L", "XL"],
        "colors": ["Black", "Navy", "Grey"],
    },
]

COLOR_CODES = {
    "Black": "BLK",
    "White": "WHT",
    "Navy":  "NVY",
    "Red":   "RED",
    "Grey":  "GRY",
    "ONE":   "ONE",
}

SYSTEM_SETTINGS = [
    {"key": "minimum_order_quantity", "value": "12",          "description": "Minimum order quantity (units)"},
    {"key": "minimum_order_value",    "value": "500.00",      "description": "Minimum order value in USD"},
    {"key": "po_number_required",     "value": "false",       "description": "Whether PO number is required at checkout"},
    {"key": "guest_pricing_mode",     "value": "login_prompt", "description": "Options: show_retail | hidden | login_prompt"},
    {"key": "low_stock_threshold",    "value": "25",           "description": "Default low-stock alert threshold (units)"},
    {"key": "tax_rate",               "value": "0.00",         "description": "Flat tax rate percentage"},
    {"key": "notification_email",     "value": "orders@afapparels.com", "description": "Admin notification email"},
]

COMPANIES = [
    {
        "name": "Downtown Retail Co",
        "tax_id": "11-1111111",
        "business_type": "Retailer",
        "pricing_tier": "Tier 1 Bronze",
        "shipping_tier": "Standard Wholesale",
        "status": "active",
        "users": [
            {"email": "john@downtownretail.com", "password": "TestPass123!", "first_name": "John", "last_name": "Smith", "role": "owner"},
            {"email": "buyer@downtownretail.com", "password": "TestPass123!", "first_name": "Jane", "last_name": "Doe", "role": "buyer"},
        ],
        "address": {
            "label": "HQ",
            "address_line1": "123 Main St",
            "city": "New York",
            "state": "NY",
            "postal_code": "10001",
        },
    },
    {
        "name": "Metro Distributors LLC",
        "tax_id": "22-2222222",
        "business_type": "Distributor",
        "pricing_tier": "Tier 2 Silver",
        "shipping_tier": "Premium Wholesale",
        "status": "active",
        "users": [
            {"email": "sarah@metrodist.com", "password": "TestPass123!", "first_name": "Sarah", "last_name": "Johnson", "role": "owner"},
        ],
        "address": {
            "label": "HQ",
            "address_line1": "456 Commerce Ave",
            "city": "Chicago",
            "state": "IL",
            "postal_code": "60601",
        },
    },
    {
        "name": "Elite Fashion Group",
        "tax_id": "33-3333333",
        "business_type": "Retailer",
        "pricing_tier": "Tier 3 Gold",
        "shipping_tier": "Premium Wholesale",
        "status": "active",
        "users": [
            {"email": "mike@elitefashion.com", "password": "TestPass123!", "first_name": "Mike", "last_name": "Williams", "role": "owner"},
        ],
        "address": {
            "label": "HQ",
            "address_line1": "789 Fashion Blvd",
            "city": "Los Angeles",
            "state": "CA",
            "postal_code": "90028",
        },
    },
]


# ═══════════════════════════════════════════════════════════════════════════════
# SEED FUNCTIONS
# ═══════════════════════════════════════════════════════════════════════════════

def seed_admin_user(session: Session) -> User:
    admin_email = "admin@afapparels.com"
    admin = session.execute(select(User).where(User.email == admin_email)).scalar_one_or_none()
    if admin:
        # Ensure admin has correct password and flags
        admin.hashed_password = hash_password("Admin123!")
        admin.first_name = "Admin"
        admin.last_name = "User"
        admin.is_admin = True
        admin.is_active = True
        admin.email_verified = True
        session.flush()
        print(f"  Admin user updated: {admin_email}")
        return admin

    admin = User(
        email=admin_email,
        hashed_password=hash_password("Admin123!"),
        first_name="Admin",
        last_name="User",
        is_admin=True,
        is_active=True,
        email_verified=True,
    )
    session.add(admin)
    session.flush()
    print(f"  Created admin user: {admin_email}")
    return admin


def seed_pricing_tiers(session: Session) -> dict[str, PricingTier]:
    tier_map: dict[str, PricingTier] = {}
    for data in PRICING_TIERS:
        tier = session.execute(
            select(PricingTier).where(PricingTier.name == data["name"])
        ).scalar_one_or_none()

        if tier:
            if tier.discount_percent != data["discount_percent"]:
                tier.discount_percent = data["discount_percent"]
                tier.description = data["description"]
                print(f"  Updated pricing tier: {data['name']} → {data['discount_percent']}%")
            else:
                print(f"  Pricing tier already correct: {data['name']}")
        else:
            tier = PricingTier(**data)
            session.add(tier)
            session.flush()
            print(f"  Created pricing tier: {data['name']} ({data['discount_percent']}%)")

        tier_map[data["name"]] = tier

    return tier_map


def seed_shipping_tiers(session: Session) -> dict[str, ShippingTier]:
    tier_map: dict[str, ShippingTier] = {}
    for data in SHIPPING_TIERS:
        tier = session.execute(
            select(ShippingTier).where(ShippingTier.name == data["name"])
        ).scalar_one_or_none()

        if tier:
            print(f"  Shipping tier already exists: {data['name']}")
        else:
            tier = ShippingTier(name=data["name"], description=data["description"])
            session.add(tier)
            session.flush()
            for b in data["brackets"]:
                session.add(ShippingBracket(tier_id=tier.id, **b))
            session.flush()
            print(f"  Created shipping tier: {data['name']} ({len(data['brackets'])} brackets)")

        tier_map[data["name"]] = tier

    return tier_map


def seed_warehouses(session: Session) -> list[Warehouse]:
    warehouses = []
    for data in WAREHOUSES:
        wh = session.execute(
            select(Warehouse).where(Warehouse.code == data["code"])
        ).scalar_one_or_none()

        if wh:
            print(f"  Warehouse already exists: {data['name']}")
        else:
            wh = Warehouse(**data)
            session.add(wh)
            session.flush()
            print(f"  Created warehouse: {data['name']} ({data['code']})")

        warehouses.append(wh)

    return warehouses


def seed_categories(session: Session) -> dict[str, Category]:
    cat_map: dict[str, Category] = {}
    for i, data in enumerate(CATEGORIES):
        cat = session.execute(
            select(Category).where(Category.slug == data["slug"])
        ).scalar_one_or_none()

        if cat:
            print(f"  Category already exists: {data['name']}")
        else:
            cat = Category(name=data["name"], slug=data["slug"], sort_order=i, is_active=True)
            session.add(cat)
            session.flush()
            print(f"  Created category: {data['name']}")

        cat_map[data["name"]] = cat

    return cat_map


def seed_products(
    session: Session,
    cat_map: dict[str, Category],
) -> list[ProductVariant]:
    all_variants: list[ProductVariant] = []

    for prod_data in PRODUCTS:
        # Check if product already exists
        product = session.execute(
            select(Product).where(Product.slug == prod_data["slug"])
        ).scalar_one_or_none()

        if product:
            print(f"  Product already exists: {prod_data['name']}")
            # Still collect variants for inventory seeding
            variants = session.execute(
                select(ProductVariant).where(ProductVariant.product_id == product.id)
            ).scalars().all()
            all_variants.extend(variants)
            continue

        # Create product
        product = Product(
            name=prod_data["name"],
            slug=prod_data["slug"],
            description=f"Premium quality {prod_data['name'].lower()} for wholesale buyers.",
            short_description=f"Wholesale {prod_data['name'].lower()}, MOQ {prod_data['moq']} units.",
            moq=prod_data["moq"],
            status="active",
        )
        session.add(product)
        session.flush()

        # Link to category
        category = cat_map.get(prod_data["category"])
        if category:
            session.add(ProductCategory(product_id=product.id, category_id=category.id))

        # Create variants (all size × color combos)
        sort_order = 0
        for color in prod_data["colors"]:
            for size in prod_data["sizes"]:
                color_code = COLOR_CODES.get(color, color[:3].upper())
                sku = f"{prod_data['sku_prefix']}-{color_code}-{size}"
                variant = ProductVariant(
                    product_id=product.id,
                    sku=sku,
                    color=color if color != "ONE" else None,
                    size=size if size != "ONE" else None,
                    retail_price=prod_data["price"],
                    status="active",
                    sort_order=sort_order,
                )
                session.add(variant)
                all_variants.append(variant)
                sort_order += 1

        session.flush()
        variant_count = len(prod_data["colors"]) * len(prod_data["sizes"])
        print(f"  Created product: {prod_data['name']} ({variant_count} variants)")

    return all_variants


def seed_inventory(
    session: Session,
    variants: list[ProductVariant],
    warehouses: list[Warehouse],
) -> int:
    count = 0
    for variant in variants:
        for warehouse in warehouses:
            existing = session.execute(
                select(InventoryRecord).where(
                    InventoryRecord.variant_id == variant.id,
                    InventoryRecord.warehouse_id == warehouse.id,
                )
            ).scalar_one_or_none()

            if existing:
                continue

            record = InventoryRecord(
                variant_id=variant.id,
                warehouse_id=warehouse.id,
                quantity=random.randint(50, 500),
                low_stock_threshold=25,
            )
            session.add(record)
            count += 1

    session.flush()
    print(f"  Created {count} inventory records")
    return count


def seed_companies(
    session: Session,
    pricing_tier_map: dict[str, PricingTier],
    shipping_tier_map: dict[str, ShippingTier],
) -> list[dict]:
    """Returns list of dicts with company + owner user for order seeding."""
    company_data_list = []

    for comp_data in COMPANIES:
        company = session.execute(
            select(Company).where(Company.name == comp_data["name"])
        ).scalar_one_or_none()

        if company:
            print(f"  Company already exists: {comp_data['name']}")
            # Grab owner user for order creation
            owner_email = comp_data["users"][0]["email"]
            owner = session.execute(select(User).where(User.email == owner_email)).scalar_one_or_none()
            address = session.execute(
                select(UserAddress).where(UserAddress.company_id == company.id)
            ).scalar_one_or_none()
            company_data_list.append({"company": company, "owner": owner, "address": address})
            continue

        # Look up tiers
        pricing_tier = pricing_tier_map.get(comp_data["pricing_tier"])
        shipping_tier = shipping_tier_map.get(comp_data["shipping_tier"])

        # Create company
        company = Company(
            name=comp_data["name"],
            tax_id=comp_data["tax_id"],
            business_type=comp_data["business_type"],
            status=comp_data["status"],
            pricing_tier_id=pricing_tier.id if pricing_tier else None,
            shipping_tier_id=shipping_tier.id if shipping_tier else None,
        )
        session.add(company)
        session.flush()

        # Create address
        addr_data = comp_data["address"]
        address = UserAddress(
            company_id=company.id,
            label=addr_data["label"],
            address_line1=addr_data["address_line1"],
            city=addr_data["city"],
            state=addr_data["state"],
            postal_code=addr_data["postal_code"],
            country="US",
            is_default=True,
        )
        session.add(address)
        session.flush()

        # Create users
        owner_user = None
        for user_data in comp_data["users"]:
            user = session.execute(
                select(User).where(User.email == user_data["email"])
            ).scalar_one_or_none()

            if not user:
                user = User(
                    email=user_data["email"],
                    hashed_password=hash_password(user_data["password"]),
                    first_name=user_data["first_name"],
                    last_name=user_data["last_name"],
                    is_admin=False,
                    is_active=True,
                    email_verified=True,
                )
                session.add(user)
                session.flush()

            # Link user to company
            cu_exists = session.execute(
                select(CompanyUser).where(
                    CompanyUser.company_id == company.id,
                    CompanyUser.user_id == user.id,
                )
            ).scalar_one_or_none()

            if not cu_exists:
                cu = CompanyUser(
                    company_id=company.id,
                    user_id=user.id,
                    role=user_data["role"],
                    is_active=True,
                )
                session.add(cu)
                session.flush()

            if user_data["role"] == "owner":
                owner_user = user

        print(f"  Created company: {comp_data['name']} (tier: {comp_data['pricing_tier']})")
        company_data_list.append({"company": company, "owner": owner_user, "address": address})

    return company_data_list


def seed_orders(
    session: Session,
    company_list: list[dict],
    all_variants: list[ProductVariant],
) -> None:
    if not all_variants:
        print("  No variants available, skipping order creation")
        return

    ORDER_SPECS = [
        {"company_idx": 0, "number": "AF-2026-00001", "status": "delivered",  "payment_status": "paid",    "items": 3},
        {"company_idx": 1, "number": "AF-2026-00002", "status": "shipped",    "payment_status": "paid",    "items": 4},
        {"company_idx": 2, "number": "AF-2026-00003", "status": "processing", "payment_status": "paid",    "items": 2},
        {"company_idx": 0, "number": "AF-2026-00004", "status": "confirmed",  "payment_status": "pending", "items": 5},
        {"company_idx": 1, "number": "AF-2026-00005", "status": "pending",    "payment_status": "unpaid",  "items": 2},
    ]

    for spec in ORDER_SPECS:
        # Check if order already exists
        existing = session.execute(
            select(Order).where(Order.order_number == spec["number"])
        ).scalar_one_or_none()
        if existing:
            print(f"  Order already exists: {spec['number']}")
            continue

        comp_info = company_list[spec["company_idx"]]
        company = comp_info["company"]
        owner = comp_info["owner"]
        address = comp_info["address"]

        if not owner:
            print(f"  Skipping order {spec['number']} — no owner user found")
            continue

        # Pick random variants
        chosen_variants = random.sample(all_variants, min(spec["items"], len(all_variants)))

        # Build line items
        items = []
        subtotal = Decimal("0.00")
        for variant in chosen_variants:
            qty = random.randint(12, 50)
            # Get product name via product relationship
            product = session.execute(
                select(Product).where(Product.id == variant.product_id)
            ).scalar_one_or_none()
            product_name = product.name if product else "Unknown Product"

            unit_price = Decimal(str(variant.retail_price))
            line_total = unit_price * qty
            subtotal += line_total

            items.append(OrderItem(
                variant_id=variant.id,
                quantity=qty,
                unit_price=unit_price,
                line_total=line_total,
                product_name=product_name,
                sku=variant.sku,
                color=variant.color,
                size=variant.size,
            ))

        shipping_cost = Decimal("15.00")
        total = subtotal + shipping_cost

        import json as _json
        addr_snapshot = None
        if address:
            addr_snapshot = _json.dumps({
                "label": address.label,
                "address_line1": address.address_line1,
                "city": address.city,
                "state": address.state,
                "postal_code": address.postal_code,
                "country": address.country,
            })

        order = Order(
            order_number=spec["number"],
            company_id=company.id,
            placed_by_id=owner.id,
            status=spec["status"],
            shipping_address_id=address.id if address else None,
            shipping_address_snapshot=addr_snapshot,
            subtotal=subtotal,
            shipping_cost=shipping_cost,
            tax_amount=Decimal("0.00"),
            total=total,
            payment_status=spec["payment_status"],
            qb_sync_status="pending",
        )
        session.add(order)
        session.flush()

        for item in items:
            item.order_id = order.id
            session.add(item)

        session.flush()
        print(f"  Created order: {spec['number']} ({spec['status']}, {len(items)} items, ${total:.2f})")


def seed_settings(session: Session) -> None:
    for data in SYSTEM_SETTINGS:
        existing = session.execute(
            select(Settings).where(Settings.key == data["key"])
        ).scalar_one_or_none()

        if existing:
            if existing.value != data["value"]:
                existing.value = data["value"]
                print(f"  Updated setting: {data['key']} = {data['value']}")
            else:
                print(f"  Setting already correct: {data['key']}")
        else:
            session.add(Settings(**data))
            print(f"  Created setting: {data['key']} = {data['value']}")


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

def main() -> None:
    print("=" * 60)
    print("AF Apparels B2B Wholesale Platform — Seed Script")
    print("=" * 60)
    print(f"Database: {DATABASE_URL_SYNC.split('@')[-1]}")  # hide credentials
    print()

    with SessionLocal() as session:
        print("► Admin user")
        seed_admin_user(session)
        session.commit()

        print("\n► Pricing tiers")
        pricing_tiers = seed_pricing_tiers(session)
        session.commit()

        print("\n► Shipping tiers")
        shipping_tiers = seed_shipping_tiers(session)
        session.commit()

        print("\n► Warehouses")
        warehouses = seed_warehouses(session)
        session.commit()

        print("\n► Categories")
        cat_map = seed_categories(session)
        session.commit()

        print("\n► Products & variants")
        all_variants = seed_products(session, cat_map)
        session.commit()

        print("\n► Inventory")
        seed_inventory(session, all_variants, warehouses)
        session.commit()

        print("\n► Companies & users")
        company_list = seed_companies(session, pricing_tiers, shipping_tiers)
        session.commit()

        print("\n► Sample orders")
        seed_orders(session, company_list, all_variants)
        session.commit()

        print("\n► System settings")
        seed_settings(session)
        session.commit()

    print()
    print("=" * 60)
    print("✅  Seed complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()
