import os
import sys
from pathlib import Path
import pandas as pd
from dotenv import load_dotenv

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from config import get_engine, setup_logging, is_sqlite

logger = setup_logging("PowerBIExporter")

DATA_DIR = ROOT_DIR / "dashboards" / "powerbi_data"
DATA_DIR.mkdir(parents=True, exist_ok=True)

EXPORT_TABLES = [
    "customers",
    "customer_segments",
    "categories",
    "suppliers",
    "products",
    "inventory",
    "orders",
    "order_items",
    "payments",
    "refunds",
    "fraud_logs",
]

EXPORT_QUERIES = {
    "mv_daily_revenue": "SELECT DATE(order_date) AS order_date, SUM(total_amount) AS revenue, COUNT(order_id) AS order_count FROM orders WHERE status = 'Completed' GROUP BY DATE(order_date)",
    "mv_customer_kpis": "SELECT c.customer_id, c.name, COUNT(o.order_id) AS total_orders, COALESCE(SUM(o.total_amount), 0) AS total_spend, AVG(o.total_amount) AS avg_order_value, MAX(o.order_date) AS last_order_date FROM customers c LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'Completed' GROUP BY c.customer_id, c.name",
    "mv_product_performance": "SELECT p.product_id, p.product_name, c.category_name, COALESCE(SUM(oi.quantity), 0) AS total_units_sold, COALESCE(SUM(oi.line_total), 0) AS total_revenue FROM products p JOIN categories c ON p.category_id = c.category_id LEFT JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.product_id, p.product_name, c.category_name",
    "mv_fraud_summary": "SELECT fraud_type, DATE(detected_at) AS detection_date, COUNT(fraud_id) AS fraud_incidents, AVG(risk_score) AS avg_risk_score FROM fraud_logs GROUP BY fraud_type, DATE(detected_at)",
    "mv_inventory_status": "SELECT i.warehouse_location, p.product_name, i.quantity_on_hand, i.quantity_reserved, p.reorder_level FROM inventory i JOIN products p ON i.product_id = p.product_id",
}


def fetch_df(query):
    engine = get_engine()
    with engine.connect() as conn:
        return pd.read_sql(query, conn)


def export_table(table_name):
    logger.info(f"Exporting {table_name}...")
    df = fetch_df(f"SELECT * FROM {table_name}")
    out_path = DATA_DIR / f"{table_name}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    logger.info(f"Written {len(df)} rows to {out_path}")


def export_query(name, query):
    logger.info(f"Exporting analytic dataset {name}...")
    df = fetch_df(query)
    out_path = DATA_DIR / f"{name}.csv"
    df.to_csv(out_path, index=False, encoding="utf-8")
    logger.info(f"Written {len(df)} rows to {out_path}")


def main():
    if not is_sqlite():
        logger.warning("DB_DRIVER is not sqlite. This export script is intended for the local SQLite demo dataset.")

    for table in EXPORT_TABLES:
        try:
            export_table(table)
        except Exception as exc:
            logger.error(f"Failed to export {table}: {exc}")

    for name, query in EXPORT_QUERIES.items():
        try:
            export_query(name, query)
        except Exception as exc:
            logger.error(f"Failed to export analytic dataset {name}: {exc}")

    logger.info(f"All exports completed. CSV files are in: {DATA_DIR}")


if __name__ == "__main__":
    load_dotenv(ROOT_DIR / ".env")
    main()
