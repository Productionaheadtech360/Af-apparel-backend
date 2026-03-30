"""Add tsvector trigger for products.search_vector.

Revision ID: 002
Revises: 001
Create Date: 2026-03-08
"""
from alembic import op

revision = "002"
down_revision = "001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Function to rebuild search_vector from name + description
    op.execute("""
        CREATE OR REPLACE FUNCTION products_search_vector_update()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector :=
                setweight(to_tsvector('english', coalesce(NEW.name, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'B');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)

    # Trigger fires on INSERT and UPDATE
    op.execute("""
        DROP TRIGGER IF EXISTS products_search_vector_trigger ON products;
        CREATE TRIGGER products_search_vector_trigger
        BEFORE INSERT OR UPDATE OF name, description
        ON products
        FOR EACH ROW
        EXECUTE FUNCTION products_search_vector_update();
    """)

    # Populate existing rows
    op.execute("""
        UPDATE products
        SET search_vector =
            setweight(to_tsvector('english', coalesce(name, '')), 'A') ||
            setweight(to_tsvector('english', coalesce(description, '')), 'B');
    """)

    # GIN index for fast full-text search
    op.execute("""
        CREATE INDEX IF NOT EXISTS ix_products_search_vector
        ON products USING GIN (search_vector);
    """)


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS products_search_vector_trigger ON products;")
    op.execute("DROP FUNCTION IF EXISTS products_search_vector_update();")
    op.execute("DROP INDEX IF EXISTS ix_products_search_vector;")
