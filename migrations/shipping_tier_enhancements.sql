-- Shipping tier enhancements: add calculation_type, cutoff_time, and order-value bracket columns
-- Run once: psql -d <db_name> -f shipping_tier_enhancements.sql

-- 1. Add calculation_type to shipping_tiers
ALTER TABLE shipping_tiers
    ADD COLUMN IF NOT EXISTS calculation_type VARCHAR(20) NOT NULL DEFAULT 'units',
    ADD COLUMN IF NOT EXISTS cutoff_time VARCHAR(20);

-- 2. Add order-value bracket columns to shipping_brackets
ALTER TABLE shipping_brackets
    ADD COLUMN IF NOT EXISTS min_order_value NUMERIC(10,2),
    ADD COLUMN IF NOT EXISTS max_order_value NUMERIC(10,2);

-- 3. Make min_units default to 0 (was non-nullable with no default)
ALTER TABLE shipping_brackets ALTER COLUMN min_units SET DEFAULT 0;
