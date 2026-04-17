-- Add image_url column to product_reviews table
ALTER TABLE product_reviews ADD COLUMN IF NOT EXISTS image_url VARCHAR(1000);
