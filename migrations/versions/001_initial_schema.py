"""Initial schema — all tables.

Revision ID: 001
Revises:
Create Date: 2026-03-08
"""
from alembic import op
import sqlalchemy as sa

revision = "001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    conn.execute(sa.text("""
        DO $$ BEGIN
            CREATE TYPE company_status AS ENUM ('pending','active','suspended','rejected');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE company_user_role AS ENUM ('owner','buyer','viewer','finance');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE product_status AS ENUM ('draft','active','archived');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE variant_status AS ENUM ('active','discontinued','out_of_stock');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE asset_type AS ENUM ('flyer','spec_sheet','size_chart','other');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE adjustment_reason AS ENUM ('received','damaged','returned','correction','sold','migration');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE order_status AS ENUM ('pending','confirmed','processing','shipped','delivered','cancelled','refunded');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE payment_status AS ENUM ('unpaid','pending','paid','refunded','failed');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE qb_order_sync_status AS ENUM ('pending','synced','failed','skipped');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE rma_status AS ENUM ('pending','approved','rejected','completed');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE application_status AS ENUM ('pending','approved','rejected');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE email_trigger_event AS ENUM (
                'order_confirmation','order_shipped','wholesale_approved','wholesale_rejected',
                'password_reset','email_verification','welcome','user_invitation',
                'rma_approved','rma_rejected','payment_failed'
            );
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE audit_action AS ENUM ('CREATE','UPDATE','DELETE');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE qb_entity_type AS ENUM ('company','order');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE qb_sync_status AS ENUM ('pending','success','failed','retry');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE webhook_status AS ENUM ('received','processed','failed');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE pricelist_format AS ENUM ('pdf','excel');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;

        DO $$ BEGIN
            CREATE TYPE pricelist_status AS ENUM ('pending','processing','completed','failed');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
    """))

    conn.execute(sa.text("""
        CREATE TABLE pricing_tiers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            discount_percent NUMERIC(5,2) NOT NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE shipping_tiers (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE shipping_brackets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            tier_id UUID NOT NULL REFERENCES shipping_tiers(id) ON DELETE CASCADE,
            min_units INTEGER NOT NULL,
            max_units INTEGER,
            cost NUMERIC(10,2) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_shipping_brackets_tier_id ON shipping_brackets(tier_id);

        CREATE TABLE users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email VARCHAR(255) NOT NULL UNIQUE,
            hashed_password VARCHAR(255) NOT NULL,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            phone VARCHAR(50),
            is_admin BOOLEAN NOT NULL DEFAULT FALSE,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            email_verified BOOLEAN NOT NULL DEFAULT FALSE,
            email_verification_token VARCHAR(255),
            password_reset_token VARCHAR(255),
            password_reset_expires TIMESTAMPTZ,
            last_login TIMESTAMPTZ,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_users_email ON users(email);

        CREATE TABLE companies (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            trading_name VARCHAR(255),
            tax_id VARCHAR(100),
            business_type VARCHAR(100),
            website VARCHAR(500),
            phone VARCHAR(50),
            status company_status NOT NULL DEFAULT 'pending',
            pricing_tier_id UUID REFERENCES pricing_tiers(id) ON DELETE SET NULL,
            shipping_tier_id UUID REFERENCES shipping_tiers(id) ON DELETE SET NULL,
            shipping_override_amount NUMERIC(10,2),
            qb_customer_id VARCHAR(255),
            admin_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_companies_status ON companies(status);
        CREATE INDEX ix_companies_pricing_tier_id ON companies(pricing_tier_id);
        CREATE INDEX ix_companies_shipping_tier_id ON companies(shipping_tier_id);

        CREATE TABLE company_users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            role company_user_role NOT NULL DEFAULT 'buyer',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            invited_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE contacts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            title VARCHAR(100),
            is_primary BOOLEAN NOT NULL DEFAULT FALSE,
            notify_order_confirmation BOOLEAN DEFAULT TRUE,
            notify_order_shipped BOOLEAN DEFAULT TRUE,
            notify_invoices BOOLEAN DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_contacts_company_id ON contacts(company_id);

        CREATE TABLE user_addresses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            label VARCHAR(100) NOT NULL,
            address_line1 VARCHAR(255) NOT NULL,
            address_line2 VARCHAR(255),
            city VARCHAR(100) NOT NULL,
            state VARCHAR(100) NOT NULL,
            postal_code VARCHAR(20) NOT NULL,
            country VARCHAR(2) NOT NULL DEFAULT 'US',
            is_default BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_user_addresses_company_id ON user_addresses(company_id);

        CREATE TABLE categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            slug VARCHAR(100) NOT NULL UNIQUE,
            description TEXT,
            parent_id UUID REFERENCES categories(id) ON DELETE SET NULL,
            sort_order INTEGER NOT NULL DEFAULT 0,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_categories_slug ON categories(slug);
        CREATE INDEX ix_categories_parent_id ON categories(parent_id);

        CREATE TABLE products (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(255) NOT NULL,
            slug VARCHAR(255) NOT NULL UNIQUE,
            description TEXT,
            short_description VARCHAR(500),
            moq INTEGER NOT NULL DEFAULT 1,
            status product_status NOT NULL DEFAULT 'draft',
            meta_title VARCHAR(255),
            meta_description VARCHAR(500),
            search_vector TSVECTOR,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_products_slug ON products(slug);
        CREATE INDEX ix_products_status ON products(status);

        CREATE TABLE product_variants (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            sku VARCHAR(100) NOT NULL UNIQUE,
            color VARCHAR(100),
            size VARCHAR(50),
            retail_price NUMERIC(10,2) NOT NULL,
            status variant_status NOT NULL DEFAULT 'active',
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_product_variants_product_id ON product_variants(product_id);
        CREATE INDEX ix_product_variants_sku ON product_variants(sku);

        CREATE TABLE product_images (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            url_thumbnail VARCHAR(1000) NOT NULL,
            url_medium VARCHAR(1000) NOT NULL,
            url_large VARCHAR(1000) NOT NULL,
            url_webp_thumbnail VARCHAR(1000),
            url_webp_medium VARCHAR(1000),
            url_webp_large VARCHAR(1000),
            alt_text VARCHAR(255),
            is_primary BOOLEAN NOT NULL DEFAULT FALSE,
            sort_order INTEGER NOT NULL DEFAULT 0,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_product_images_product_id ON product_images(product_id);

        CREATE TABLE product_assets (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            asset_type asset_type NOT NULL,
            url VARCHAR(1000) NOT NULL,
            file_name VARCHAR(255) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_product_assets_product_id ON product_assets(product_id);

        CREATE TABLE product_categories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
            category_id UUID NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );

        CREATE TABLE warehouses (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name VARCHAR(100) NOT NULL,
            code VARCHAR(20) NOT NULL UNIQUE,
            address_line1 VARCHAR(255),
            city VARCHAR(100),
            state VARCHAR(100),
            postal_code VARCHAR(20),
            country VARCHAR(2) NOT NULL DEFAULT 'US',
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_warehouses_code ON warehouses(code);

        CREATE TABLE inventory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
            warehouse_id UUID NOT NULL REFERENCES warehouses(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL DEFAULT 0,
            low_stock_threshold INTEGER NOT NULL DEFAULT 10,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_inventory_variant_id ON inventory(variant_id);
        CREATE INDEX ix_inventory_warehouse_id ON inventory(warehouse_id);

        CREATE TABLE inventory_adjustments (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            inventory_record_id UUID NOT NULL REFERENCES inventory(id) ON DELETE CASCADE,
            adjusted_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            quantity_before INTEGER NOT NULL,
            quantity_after INTEGER NOT NULL,
            reason adjustment_reason NOT NULL,
            notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_inventory_adjustments_inventory_record_id ON inventory_adjustments(inventory_record_id);

        CREATE TABLE orders (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_number VARCHAR(50) NOT NULL UNIQUE,
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE RESTRICT,
            placed_by_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            status order_status NOT NULL DEFAULT 'pending',
            po_number VARCHAR(100),
            notes TEXT,
            shipping_address_id UUID REFERENCES user_addresses(id) ON DELETE SET NULL,
            shipping_address_snapshot TEXT,
            subtotal NUMERIC(10,2) NOT NULL,
            shipping_cost NUMERIC(10,2) NOT NULL,
            tax_amount NUMERIC(10,2) NOT NULL DEFAULT 0,
            total NUMERIC(10,2) NOT NULL,
            payment_status payment_status NOT NULL DEFAULT 'unpaid',
            stripe_payment_intent_id VARCHAR(255),
            stripe_customer_id VARCHAR(255),
            tracking_number VARCHAR(255),
            carrier VARCHAR(100),
            qb_sync_status qb_order_sync_status NOT NULL DEFAULT 'pending',
            qb_invoice_id VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_orders_order_number ON orders(order_number);
        CREATE INDEX ix_orders_company_id ON orders(company_id);
        CREATE INDEX ix_orders_status ON orders(status);
        CREATE INDEX ix_orders_po_number ON orders(po_number);
        CREATE INDEX ix_orders_stripe_payment_intent_id ON orders(stripe_payment_intent_id);

        CREATE TABLE order_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
            variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE RESTRICT,
            quantity INTEGER NOT NULL,
            unit_price NUMERIC(10,2) NOT NULL,
            line_total NUMERIC(10,2) NOT NULL,
            product_name VARCHAR(255) NOT NULL,
            sku VARCHAR(100) NOT NULL,
            color VARCHAR(100),
            size VARCHAR(50),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_order_items_order_id ON order_items(order_id);

        CREATE TABLE cart_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            variant_id UUID NOT NULL REFERENCES product_variants(id) ON DELETE CASCADE,
            quantity INTEGER NOT NULL,
            price_at_add NUMERIC(10,2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_cart_items_user_id ON cart_items(user_id);

        CREATE TABLE abandoned_carts (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
            items_snapshot TEXT NOT NULL,
            total_value NUMERIC(10,2),
            email_sent BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_abandoned_carts_user_id ON abandoned_carts(user_id);

        CREATE TABLE order_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            created_by_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            name VARCHAR(100) NOT NULL,
            items TEXT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_order_templates_company_id ON order_templates(company_id);

        CREATE TABLE rma_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            order_id UUID NOT NULL REFERENCES orders(id) ON DELETE RESTRICT,
            submitted_by_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            rma_number VARCHAR(50) NOT NULL UNIQUE,
            status rma_status NOT NULL DEFAULT 'pending',
            reason VARCHAR(500) NOT NULL,
            notes TEXT,
            admin_notes TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_rma_requests_order_id ON rma_requests(order_id);
        CREATE INDEX ix_rma_requests_rma_number ON rma_requests(rma_number);
        CREATE INDEX ix_rma_requests_status ON rma_requests(status);

        CREATE TABLE rma_items (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            rma_id UUID NOT NULL REFERENCES rma_requests(id) ON DELETE CASCADE,
            order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE RESTRICT,
            quantity INTEGER NOT NULL,
            reason VARCHAR(500),
            refund_amount NUMERIC(10,2),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_rma_items_rma_id ON rma_items(rma_id);

        CREATE TABLE wholesale_applications (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_name VARCHAR(255) NOT NULL,
            tax_id VARCHAR(100),
            business_type VARCHAR(100) NOT NULL,
            website VARCHAR(500),
            expected_monthly_volume VARCHAR(100),
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            email VARCHAR(255) NOT NULL,
            phone VARCHAR(50),
            status application_status NOT NULL DEFAULT 'pending',
            rejection_reason TEXT,
            admin_notes TEXT,
            company_id UUID REFERENCES companies(id) ON DELETE SET NULL,
            reviewed_by_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_wholesale_applications_email ON wholesale_applications(email);
        CREATE INDEX ix_wholesale_applications_status ON wholesale_applications(status);
        CREATE INDEX ix_wholesale_applications_company_id ON wholesale_applications(company_id);

        CREATE TABLE messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            sender_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            subject VARCHAR(255) NOT NULL,
            body TEXT NOT NULL,
            parent_id UUID REFERENCES messages(id) ON DELETE SET NULL,
            is_read_by_admin BOOLEAN NOT NULL DEFAULT FALSE,
            is_read_by_company BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_messages_company_id ON messages(company_id);

        CREATE TABLE email_templates (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            trigger_event email_trigger_event NOT NULL UNIQUE,
            name VARCHAR(100) NOT NULL,
            subject VARCHAR(255) NOT NULL,
            body_html TEXT NOT NULL,
            body_text TEXT,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            available_variables TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_email_templates_trigger_event ON email_templates(trigger_event);

        CREATE TABLE settings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            key VARCHAR(100) NOT NULL UNIQUE,
            value TEXT NOT NULL,
            description VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_settings_key ON settings(key);

        CREATE TABLE audit_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            admin_user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action audit_action NOT NULL,
            entity_type VARCHAR(100) NOT NULL,
            entity_id VARCHAR(100),
            old_values TEXT,
            new_values TEXT,
            ip_address VARCHAR(45),
            user_agent VARCHAR(500),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_audit_log_admin_user_id ON audit_log(admin_user_id);
        CREATE INDEX ix_audit_log_entity_type ON audit_log(entity_type);
        CREATE INDEX ix_audit_log_entity_id ON audit_log(entity_id);

        CREATE TABLE qb_sync_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            entity_type qb_entity_type NOT NULL,
            entity_id UUID NOT NULL,
            status qb_sync_status NOT NULL DEFAULT 'pending',
            attempt_count INTEGER NOT NULL DEFAULT 0,
            error_message TEXT,
            qb_entity_id VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_qb_sync_log_entity_id ON qb_sync_log(entity_id);
        CREATE INDEX ix_qb_sync_log_status ON qb_sync_log(status);

        CREATE TABLE webhook_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            event_id VARCHAR(255) NOT NULL UNIQUE,
            provider VARCHAR(50) NOT NULL,
            event_type VARCHAR(100) NOT NULL,
            payload TEXT NOT NULL,
            status webhook_status NOT NULL DEFAULT 'received',
            error_message TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_webhook_log_event_id ON webhook_log(event_id);

        CREATE TABLE price_list_requests (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            company_id UUID NOT NULL REFERENCES companies(id) ON DELETE CASCADE,
            requested_by_id UUID NOT NULL REFERENCES users(id) ON DELETE RESTRICT,
            format pricelist_format NOT NULL,
            status pricelist_status NOT NULL DEFAULT 'pending',
            file_url VARCHAR(1000),
            celery_task_id VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        CREATE INDEX ix_price_list_requests_company_id ON price_list_requests(company_id);
    """))


def downgrade() -> None:
    conn = op.get_bind()
    conn.execute(sa.text("""
        DROP TABLE IF EXISTS price_list_requests CASCADE;
        DROP TABLE IF EXISTS webhook_log CASCADE;
        DROP TABLE IF EXISTS qb_sync_log CASCADE;
        DROP TABLE IF EXISTS audit_log CASCADE;
        DROP TABLE IF EXISTS settings CASCADE;
        DROP TABLE IF EXISTS email_templates CASCADE;
        DROP TABLE IF EXISTS messages CASCADE;
        DROP TABLE IF EXISTS wholesale_applications CASCADE;
        DROP TABLE IF EXISTS rma_items CASCADE;
        DROP TABLE IF EXISTS rma_requests CASCADE;
        DROP TABLE IF EXISTS order_templates CASCADE;
        DROP TABLE IF EXISTS abandoned_carts CASCADE;
        DROP TABLE IF EXISTS cart_items CASCADE;
        DROP TABLE IF EXISTS order_items CASCADE;
        DROP TABLE IF EXISTS orders CASCADE;
        DROP TABLE IF EXISTS inventory_adjustments CASCADE;
        DROP TABLE IF EXISTS inventory CASCADE;
        DROP TABLE IF EXISTS warehouses CASCADE;
        DROP TABLE IF EXISTS product_categories CASCADE;
        DROP TABLE IF EXISTS product_assets CASCADE;
        DROP TABLE IF EXISTS product_images CASCADE;
        DROP TABLE IF EXISTS product_variants CASCADE;
        DROP TABLE IF EXISTS products CASCADE;
        DROP TABLE IF EXISTS categories CASCADE;
        DROP TABLE IF EXISTS user_addresses CASCADE;
        DROP TABLE IF EXISTS contacts CASCADE;
        DROP TABLE IF EXISTS company_users CASCADE;
        DROP TABLE IF EXISTS companies CASCADE;
        DROP TABLE IF EXISTS users CASCADE;
        DROP TABLE IF EXISTS shipping_brackets CASCADE;
        DROP TABLE IF EXISTS shipping_tiers CASCADE;
        DROP TABLE IF EXISTS pricing_tiers CASCADE;

        DROP TYPE IF EXISTS pricelist_status;
        DROP TYPE IF EXISTS pricelist_format;
        DROP TYPE IF EXISTS webhook_status;
        DROP TYPE IF EXISTS qb_sync_status;
        DROP TYPE IF EXISTS qb_entity_type;
        DROP TYPE IF EXISTS audit_action;
        DROP TYPE IF EXISTS email_trigger_event;
        DROP TYPE IF EXISTS application_status;
        DROP TYPE IF EXISTS rma_status;
        DROP TYPE IF EXISTS qb_order_sync_status;
        DROP TYPE IF EXISTS payment_status;
        DROP TYPE IF EXISTS order_status;
        DROP TYPE IF EXISTS adjustment_reason;
        DROP TYPE IF EXISTS asset_type;
        DROP TYPE IF EXISTS variant_status;
        DROP TYPE IF EXISTS product_status;
        DROP TYPE IF EXISTS company_user_role;
        DROP TYPE IF EXISTS company_status;
    """))
