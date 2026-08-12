import os
from pathlib import Path
from dotenv import load_dotenv
from sqlalchemy import text
from config import get_engine, setup_logging, is_sqlite, test_db_connection

load_dotenv()
logger = setup_logging("DBSetup")

ROOT_DIR = Path(__file__).resolve().parent.parent
SQL_DIR = ROOT_DIR / "sql"


def run_sql_file(engine, path: Path):
    logger.info(f"Running SQL script: {path}")
    sql_text = path.read_text(encoding="utf-8")
    with engine.begin() as conn:
        conn.exec_driver_sql(sql_text)
    logger.info(f"Completed: {path.name}")


def create_sqlite_schema(engine):
    logger.info("Creating SQLite schema...")
    sqlite_sql = """
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS customers (
    customer_id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT UNIQUE NOT NULL,
    phone TEXT,
    city TEXT,
    state TEXT,
    country TEXT,
    registration_date TEXT DEFAULT CURRENT_TIMESTAMP,
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS customer_sessions (
    session_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    login_time TEXT NOT NULL,
    logout_time TEXT,
    device_type TEXT,
    ip_address TEXT,
    pages_viewed INTEGER DEFAULT 0,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS customer_segments (
    segment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    segment_name TEXT NOT NULL,
    rfm_score TEXT,
    recency INTEGER,
    frequency INTEGER,
    monetary NUMERIC,
    last_updated TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS categories (
    category_id INTEGER PRIMARY KEY AUTOINCREMENT,
    category_name TEXT NOT NULL,
    parent_category_id INTEGER,
    FOREIGN KEY(parent_category_id) REFERENCES categories(category_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS suppliers (
    supplier_id INTEGER PRIMARY KEY AUTOINCREMENT,
    supplier_name TEXT NOT NULL,
    contact_email TEXT,
    country TEXT,
    reliability_score NUMERIC DEFAULT 100.00
);

CREATE TABLE IF NOT EXISTS products (
    product_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name TEXT NOT NULL,
    category_id INTEGER,
    supplier_id INTEGER,
    price NUMERIC NOT NULL,
    cost_price NUMERIC NOT NULL,
    stock_quantity INTEGER DEFAULT 0,
    reorder_level INTEGER DEFAULT 10,
    FOREIGN KEY(category_id) REFERENCES categories(category_id) ON DELETE SET NULL,
    FOREIGN KEY(supplier_id) REFERENCES suppliers(supplier_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS inventory (
    inventory_id INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id INTEGER,
    warehouse_location TEXT,
    quantity_on_hand INTEGER DEFAULT 0,
    quantity_reserved INTEGER DEFAULT 0,
    last_restock_date TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS orders (
    order_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    order_date TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Pending',
    total_amount NUMERIC DEFAULT 0.00,
    shipping_address TEXT,
    region TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS order_items (
    item_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    product_id INTEGER,
    quantity INTEGER NOT NULL,
    unit_price NUMERIC NOT NULL,
    discount NUMERIC DEFAULT 0.00,
    line_total NUMERIC,
    FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE RESTRICT
);

CREATE TABLE IF NOT EXISTS payments (
    payment_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    payment_method TEXT NOT NULL,
    amount NUMERIC NOT NULL,
    payment_date TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Completed',
    transaction_ref TEXT UNIQUE,
    FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS refunds (
    refund_id INTEGER PRIMARY KEY AUTOINCREMENT,
    order_id INTEGER,
    payment_id INTEGER,
    refund_amount NUMERIC NOT NULL,
    reason TEXT,
    refund_date TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'Processed',
    FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY(payment_id) REFERENCES payments(payment_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS fraud_logs (
    fraud_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    order_id INTEGER,
    fraud_type TEXT,
    risk_score NUMERIC,
    detection_method TEXT,
    detected_at TEXT DEFAULT CURRENT_TIMESTAMP,
    is_confirmed INTEGER DEFAULT 0,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS suspicious_transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    transaction_type TEXT,
    amount NUMERIC,
    reason TEXT,
    flagged_at TEXT DEFAULT CURRENT_TIMESTAMP,
    reviewed INTEGER DEFAULT 0,
    reviewer_notes TEXT,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS reviews (
    review_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_id INTEGER,
    order_id INTEGER,
    rating INTEGER,
    review_text TEXT,
    review_date TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE CASCADE,
    FOREIGN KEY(order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS ratings (
    rating_id INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_id INTEGER,
    product_id INTEGER,
    rating_value INTEGER,
    rated_at TEXT DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(customer_id) REFERENCES customers(customer_id) ON DELETE CASCADE,
    FOREIGN KEY(product_id) REFERENCES products(product_id) ON DELETE CASCADE
);
    """
    statements = [stmt.strip() for stmt in sqlite_sql.split(';') if stmt.strip()]
    with engine.begin() as conn:
        for stmt in statements:
            conn.exec_driver_sql(stmt)
    logger.info("SQLite schema created successfully.")


def main():
    engine = get_engine()

    if is_sqlite():
        create_sqlite_schema(engine)
        return

    if not test_db_connection():
        logger.error("Database connectivity check failed. Start PostgreSQL and verify .env settings before running db_setup.py.")
        return

    schema_file = SQL_DIR / "schema.sql"
    procedures_file = SQL_DIR / "procedures.sql"

    if not schema_file.exists() or not procedures_file.exists():
        logger.error("SQL schema or procedures file not found. Please check the sql/ directory.")
        return

    run_sql_file(engine, schema_file)
    run_sql_file(engine, procedures_file)
    logger.info("Database schema and stored procedures loaded successfully.")


if __name__ == "__main__":
    main()
