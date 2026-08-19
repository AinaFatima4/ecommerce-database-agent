"""
seed.py
Recreates ecommerce.db from schema.sql and fills it with realistic
synthetic data. Run this once (or any time you want a fresh database):

    python database/seed.py

Requires the Faker library for fake names, emails, cities, etc.:

    pip install faker
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

from faker import Faker


# ------------------------------------------------------------
# Configuration
# ------------------------------------------------------------
# Build absolute paths from THIS file's location, so the script
# works no matter which folder you run it from.
CURRENT_DIRECTORY = os.path.dirname(os.path.abspath(__file__))
DATABASE_PATH = os.path.join(CURRENT_DIRECTORY, "ecommerce.db")
SCHEMA_PATH = os.path.join(CURRENT_DIRECTORY, "schema.sql")

NUMBER_OF_CUSTOMERS = 50
NUMBER_OF_ORDERS = 200
NUMBER_OF_REVIEWS = 100
MINIMUM_ITEMS_PER_ORDER = 1
MAXIMUM_ITEMS_PER_ORDER = 4

# Fixing the random seeds makes every run produce the SAME data.
# Good for reproducibility; delete these two lines if you want it
# to differ each time.
faker = Faker()
random.seed(42)
Faker.seed(42)


# ------------------------------------------------------------
# Static reference data
# ------------------------------------------------------------
CATEGORIES = [
    ("Electronics", "Phones, laptops, audio, and gadgets"),
    ("Clothing", "Men's and women's apparel"),
    ("Home & Kitchen", "Cookware, appliances, and decor"),
    ("Books", "Fiction, non-fiction, and academic"),
    ("Sports & Outdoors", "Fitness gear and outdoor equipment"),
    ("Beauty", "Skincare, makeup, and personal care"),
]

# (name, category_name, price, base_rating)
PRODUCTS = [
    ("Wireless Earbuds", "Electronics", 45.00, 4.5),
    ("Laptop Stand", "Electronics", 25.00, 4.2),
    ("Cotton T-Shirt", "Clothing", 12.00, 4.0),
    ("Running Shoes", "Sports & Outdoors", 60.00, 4.6),
    ("Stainless Steel Pan", "Home & Kitchen", 35.00, 4.3),
    ("Ceramic Coffee Mug", "Home & Kitchen", 8.00, 4.1),
    ("Yoga Mat", "Sports & Outdoors", 20.00, 4.4),
    ("Mystery Novel", "Books", 15.00, 4.7),
    ("Vitamin C Serum", "Beauty", 22.00, 4.2),
    ("Bluetooth Speaker", "Electronics", 55.00, 4.5),
]

ORDER_STATUSES = ["pending", "shipped", "delivered", "cancelled"]
ORDER_STATUS_WEIGHTS = [10, 15, 60, 15]          # delivered is most common

PAYMENT_METHODS = ["card", "COD", "bank_transfer"]

PAYMENT_STATUSES = ["paid", "failed", "refunded", "pending"]
PAYMENT_STATUS_WEIGHTS = [70, 10, 10, 10]

SHIPPING_CARRIERS = ["TCS", "Leopards", "M&P", "DHL", "FedEx"]


# ------------------------------------------------------------
# Helper: a random datetime somewhere in the last N days
# ------------------------------------------------------------
def random_datetime_within_days(number_of_days_back):
    now = datetime.now()
    seconds_in_range = number_of_days_back * 24 * 60 * 60
    seconds_back = random.randint(0, seconds_in_range)
    return now - timedelta(seconds=seconds_back)


# ------------------------------------------------------------
# Build the database
# ------------------------------------------------------------
def seed_database():
    # Start completely fresh: remove any old database file.
    if os.path.exists(DATABASE_PATH):
        os.remove(DATABASE_PATH)

    connection = sqlite3.connect(DATABASE_PATH)
    # SQLite ignores foreign keys unless we turn them on, per connection.
    connection.execute("PRAGMA foreign_keys = ON")
    cursor = connection.cursor()

    # Create all 8 tables by running the whole schema.sql file at once.
    with open(SCHEMA_PATH, "r") as schema_file:
        cursor.executescript(schema_file.read())

    # ---- categories ----
    cursor.executemany(
        "INSERT INTO categories (name, description) VALUES (?, ?)",
        CATEGORIES,
    )
    # Map category name -> its auto-assigned id, so products can reference it.
    category_name_to_id = {}
    for category_id, name in cursor.execute(
        "SELECT category_id, name FROM categories"
    ).fetchall():
        category_name_to_id[name] = category_id

    # ---- customers ----
    customer_rows = []
    for _ in range(NUMBER_OF_CUSTOMERS):
        first_name = faker.first_name()
        last_name = faker.last_name()
        email = faker.unique.email()
        phone = faker.phone_number()
        city = faker.city()
        country = faker.country()
        signup_date = random_datetime_within_days(730).strftime("%Y-%m-%d")
        customer_rows.append(
            (first_name, last_name, email, phone, city, country, signup_date)
        )
    cursor.executemany(
        """INSERT INTO customers
           (first_name, last_name, email, phone, city, country, signup_date)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        customer_rows,
    )

    # ---- products ----
    for name, category_name, price, base_rating in PRODUCTS:
        category_id = category_name_to_id[category_name]
        stock_quantity = random.randint(0, 200)
        rating = round(
            random.uniform(base_rating - 0.4, min(5.0, base_rating + 0.3)), 1
        )
        description = faker.sentence(nb_words=8)
        created_at = random_datetime_within_days(730).strftime("%Y-%m-%d")
        cursor.execute(
            """INSERT INTO products
               (category_id, name, description, price, stock_quantity, rating, created_at)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (category_id, name, description, price, stock_quantity, rating, created_at),
        )

    # Read the ids and prices back for building orders.
    customer_ids = [
        row[0] for row in cursor.execute("SELECT customer_id FROM customers").fetchall()
    ]
    product_catalog = cursor.execute(
        "SELECT product_id, price FROM products"
    ).fetchall()

    # ---- orders + order_items ----
    for _ in range(NUMBER_OF_ORDERS):
        customer_id = random.choice(customer_ids)
        order_datetime = random_datetime_within_days(240)   # last ~8 months
        status = random.choices(ORDER_STATUSES, weights=ORDER_STATUS_WEIGHTS)[0]
        payment_method = random.choice(PAYMENT_METHODS)
        shipping_city = faker.city()

        # Insert the order first with a placeholder total, then fill it in
        # once we know the line items — keeps total_amount consistent.
        cursor.execute(
            """INSERT INTO orders
               (customer_id, order_date, status, payment_method, shipping_city, total_amount)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                customer_id,
                order_datetime.strftime("%Y-%m-%d %H:%M:%S"),
                status,
                payment_method,
                shipping_city,
                0.0,
            ),
        )
        order_id = cursor.lastrowid   # the id SQLite just assigned

        number_of_items = random.randint(MINIMUM_ITEMS_PER_ORDER, MAXIMUM_ITEMS_PER_ORDER)
        # sample() picks distinct products, so one order never lists the same product twice.
        chosen_products = random.sample(product_catalog, number_of_items)

        order_total = 0.0
        for product_id, product_price in chosen_products:
            quantity = random.randint(1, 5)
            unit_price = product_price
            discount = random.choice([0, 0, 0, 5, 10])       # mostly no discount
            line_revenue = quantity * unit_price - discount
            if line_revenue < 0:
                line_revenue = 0
            order_total += line_revenue
            cursor.execute(
                """INSERT INTO order_items
                   (order_id, product_id, quantity, unit_price, discount)
                   VALUES (?, ?, ?, ?, ?)""",
                (order_id, product_id, quantity, unit_price, discount),
            )

        cursor.execute(
            "UPDATE orders SET total_amount = ? WHERE order_id = ?",
            (round(order_total, 2), order_id),
        )

    # Pull every order back once; reuse it for payments and shipments.
    orders_data = cursor.execute(
        "SELECT order_id, order_date, total_amount, status FROM orders"
    ).fetchall()

    # ---- payments (one per order) ----
    for order_id, order_date_text, total_amount, order_status in orders_data:
        order_date = datetime.strptime(order_date_text, "%Y-%m-%d %H:%M:%S")
        payment_date = order_date + timedelta(minutes=random.randint(1, 180))
        payment_status = random.choices(
            PAYMENT_STATUSES, weights=PAYMENT_STATUS_WEIGHTS
        )[0]
        transaction_ref = faker.unique.bothify("TXN-########")
        cursor.execute(
            """INSERT INTO payments
               (order_id, payment_date, amount, status, transaction_ref)
               VALUES (?, ?, ?, ?, ?)""",
            (
                order_id,
                payment_date.strftime("%Y-%m-%d %H:%M:%S"),
                total_amount,
                payment_status,
                transaction_ref,
            ),
        )

    # ---- shipments (one per order, status follows the order) ----
    for order_id, order_date_text, total_amount, order_status in orders_data:
        order_date = datetime.strptime(order_date_text, "%Y-%m-%d %H:%M:%S")
        shipped_date = order_date + timedelta(days=random.randint(1, 3))
        carrier = random.choice(SHIPPING_CARRIERS)
        tracking_number = faker.unique.bothify("??########").upper()

        if order_status == "delivered":
            shipment_status = "delivered"
            delivered_date = shipped_date + timedelta(days=random.randint(1, 7))
            delivered_date_text = delivered_date.strftime("%Y-%m-%d")
        elif order_status == "cancelled":
            shipment_status = "returned"
            delivered_date_text = None      # becomes NULL in the database
        else:
            shipment_status = random.choice(["processing", "shipped"])
            delivered_date_text = None

        cursor.execute(
            """INSERT INTO shipments
               (order_id, carrier, tracking_number, shipped_date, delivered_date, status)
               VALUES (?, ?, ?, ?, ?, ?)""",
            (
                order_id,
                carrier,
                tracking_number,
                shipped_date.strftime("%Y-%m-%d"),
                delivered_date_text,
                shipment_status,
            ),
        )

    # ---- reviews ----
    product_ids = [product_id for product_id, price in product_catalog]
    for _ in range(NUMBER_OF_REVIEWS):
        customer_id = random.choice(customer_ids)
        product_id = random.choice(product_ids)
        rating = random.randint(1, 5)
        review_text = faker.sentence(nb_words=12)
        review_date = random_datetime_within_days(240).strftime("%Y-%m-%d")
        cursor.execute(
            """INSERT INTO reviews
               (customer_id, product_id, rating, review_text, review_date)
               VALUES (?, ?, ?, ?, ?)""",
            (customer_id, product_id, rating, review_text, review_date),
        )

    # Save everything to disk, then close.
    connection.commit()

    # Quick summary so you can see it worked.
    for table_name in [
        "categories", "customers", "products", "orders",
        "order_items", "payments", "reviews", "shipments",
    ]:
        row_count = cursor.execute(
            "SELECT COUNT(*) FROM " + table_name
        ).fetchone()[0]
        print(f"{table_name:<12} {row_count} rows")

    connection.close()
    print(f"\nDatabase created at: {DATABASE_PATH}")


if __name__ == "__main__":
    seed_database()