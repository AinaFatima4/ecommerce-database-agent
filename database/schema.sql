-- ============================================================
-- Ecommerce Database Agent — schema
-- Pure SQL. Run this file to (re)create all 8 tables.
-- Safe to run repeatedly: each table is dropped first if it exists.
-- ============================================================

-- Drop in reverse dependency order (children before parents),
-- so we never try to drop a table another table still points to.
DROP TABLE IF EXISTS shipments;
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS payments;
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS categories;
DROP TABLE IF EXISTS customers;

-- ------------------------------------------------------------
-- 1. customers
-- ------------------------------------------------------------
CREATE TABLE customers (
    customer_id  INTEGER PRIMARY KEY,          -- auto-assigned by SQLite
    first_name   TEXT    NOT NULL,
    last_name    TEXT    NOT NULL,
    email        TEXT    UNIQUE NOT NULL,
    phone        TEXT,                          -- optional
    city         TEXT,
    country      TEXT,
    signup_date  DATE
);

-- ------------------------------------------------------------
-- 2. categories
-- ------------------------------------------------------------
CREATE TABLE categories (
    category_id  INTEGER PRIMARY KEY,
    name         TEXT    UNIQUE NOT NULL,
    description  TEXT
);

-- ------------------------------------------------------------
-- 3. products
-- ------------------------------------------------------------
CREATE TABLE products (
    product_id      INTEGER PRIMARY KEY,
    category_id     INTEGER,
    name            TEXT    NOT NULL,
    description     TEXT,
    price           REAL    CHECK (price >= 0),
    stock_quantity  INTEGER CHECK (stock_quantity >= 0),
    rating          REAL    CHECK (rating >= 0 AND rating <= 5),
    created_at      DATE,
    FOREIGN KEY (category_id) REFERENCES categories (category_id)
);

-- ------------------------------------------------------------
-- 4. orders
-- ------------------------------------------------------------
CREATE TABLE orders (
    order_id        INTEGER PRIMARY KEY,
    customer_id     INTEGER,
    order_date      DATETIME,
    status          TEXT,          -- pending, shipped, delivered, cancelled
    payment_method  TEXT,          -- card, COD, bank_transfer
    shipping_city   TEXT,
    total_amount    REAL,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id)
);

-- ------------------------------------------------------------
-- 5. order_items
-- discount convention: absolute amount subtracted from the line,
--   line revenue = (quantity * unit_price) - discount
-- ------------------------------------------------------------
CREATE TABLE order_items (
    order_item_id  INTEGER PRIMARY KEY,
    order_id       INTEGER,
    product_id     INTEGER,
    quantity       INTEGER NOT NULL CHECK (quantity > 0),
    unit_price     REAL    CHECK (unit_price >= 0),
    discount       REAL    DEFAULT 0 CHECK (discount >= 0),
    FOREIGN KEY (order_id)   REFERENCES orders (order_id),
    FOREIGN KEY (product_id) REFERENCES products (product_id)
);

-- ------------------------------------------------------------
-- 6. payments
-- ------------------------------------------------------------
CREATE TABLE payments (
    payment_id       INTEGER PRIMARY KEY,
    order_id         INTEGER,
    payment_date     DATETIME,
    amount           REAL    CHECK (amount >= 0),
    status           TEXT,          -- paid, failed, refunded, pending
    transaction_ref  TEXT    UNIQUE,
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- ------------------------------------------------------------
-- 7. reviews
-- ------------------------------------------------------------
CREATE TABLE reviews (
    review_id    INTEGER PRIMARY KEY,
    customer_id  INTEGER,
    product_id   INTEGER,
    rating       INTEGER CHECK (rating >= 1 AND rating <= 5),
    review_text  TEXT,
    review_date  DATE,
    FOREIGN KEY (customer_id) REFERENCES customers (customer_id),
    FOREIGN KEY (product_id)  REFERENCES products (product_id)
);

-- ------------------------------------------------------------
-- 8. shipments
-- ------------------------------------------------------------
CREATE TABLE shipments (
    shipment_id      INTEGER PRIMARY KEY,
    order_id         INTEGER,
    carrier          TEXT,
    tracking_number  TEXT    UNIQUE,
    shipped_date     DATE,
    delivered_date   DATE,          -- nullable: empty until delivered
    status           TEXT,          -- processing, shipped, delivered, returned
    FOREIGN KEY (order_id) REFERENCES orders (order_id)
);

-- ============================================================
-- Indexes: speed up the joins and filters the agent will run most.
-- Foreign keys aren't indexed automatically in SQLite, so we do it.
-- ============================================================
CREATE INDEX index_products_category    ON products    (category_id);
CREATE INDEX index_orders_customer      ON orders      (customer_id);
CREATE INDEX index_orders_date          ON orders      (order_date);
CREATE INDEX index_orders_status        ON orders      (status);
CREATE INDEX index_order_items_order    ON order_items (order_id);
CREATE INDEX index_order_items_product  ON order_items (product_id);
CREATE INDEX index_payments_order       ON payments    (order_id);
CREATE INDEX index_reviews_customer     ON reviews     (customer_id);
CREATE INDEX index_reviews_product      ON reviews     (product_id);
CREATE INDEX index_shipments_order      ON shipments   (order_id);