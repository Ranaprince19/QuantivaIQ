"""
Real Data Ingestor — pulls REAL payments from your Razorpay account and
inserts them into the same database tables the dashboard already reads
from (orders, payments, customers). This REPLACES live_data_generator.py
once you have a real store connected.

Setup:
  1. pip install requests
  2. Set these environment variables (in .env or your shell):
       RAZORPAY_KEY_ID=your_key_id
       RAZORPAY_KEY_SECRET=your_key_secret
       INGEST_INTERVAL_SECONDS=30   (optional, default 30)
  3. Run: python python/real_data_ingestor.py

What it does every cycle:
  - Calls Razorpay's /payments API for payments captured since the last run
  - For each NEW payment not already in your database, it:
      - Creates (or reuses) a customer record
      - Creates an order + payment record with the REAL amount and REAL
        payment method (upi, card, netbanking, wallet, etc.)
  - Leaves everything else (fraud_detection.py, forecasting.py,
    web_dashboard.py) untouched — they just read the same tables.

NOTE: Razorpay amounts are in paise (1/100 rupee) — this script converts
to rupees automatically.
"""

import os
import time
import base64
import requests
from datetime import datetime
from dotenv import load_dotenv

from config import setup_logging, test_db_connection
from utils import get_engine, fetch_data, execute_query
import pandas as pd

load_dotenv()
logger = setup_logging("RealDataIngestor")

RAZORPAY_KEY_ID = os.getenv("RAZORPAY_KEY_ID")
RAZORPAY_KEY_SECRET = os.getenv("RAZORPAY_KEY_SECRET")
INGEST_INTERVAL = int(os.getenv("INGEST_INTERVAL_SECONDS", 30))

RAZORPAY_API_BASE = "https://api.razorpay.com/v1"

# Razorpay payment method -> a label matching your dashboard's style
METHOD_LABELS = {
    "upi": "UPI",
    "card": "Credit Card",
    "netbanking": "Net Banking",
    "wallet": "Paytm Wallet",
    "emi": "Credit Card",
}


def _auth_header():
    if not RAZORPAY_KEY_ID or not RAZORPAY_KEY_SECRET:
        raise ValueError(
            "Missing RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET. "
            "Add them to your .env file before running this script."
        )
    token = base64.b64encode(f"{RAZORPAY_KEY_ID}:{RAZORPAY_KEY_SECRET}".encode()).decode()
    return {"Authorization": f"Basic {token}"}


def fetch_recent_payments(count=50):
    """Fetch the most recent captured payments from Razorpay."""
    resp = requests.get(
        f"{RAZORPAY_API_BASE}/payments",
        headers=_auth_header(),
        params={"count": count},
        timeout=15,
    )
    resp.raise_for_status()
    return resp.json().get("items", [])


def already_ingested(transaction_ref):
    result = fetch_data(
        "SELECT COUNT(*) AS c FROM payments WHERE transaction_ref = :ref",
        {"ref": transaction_ref},
    )
    return result.iloc[0]["c"] > 0


def get_or_create_generic_customer():
    """
    Razorpay's basic payment object doesn't always include full customer
    details unless you're using Orders API with customer records. For a
    simple Payment Pages / Payment Links setup, we attach real payments to
    a single 'Online Store Customers' bucket customer, or you can extend
    this to call Razorpay's /customers API if you collect customer_id.
    """
    existing = fetch_data(
        "SELECT customer_id FROM customers WHERE email = 'real-store@online.customers' LIMIT 1"
    )
    if not existing.empty:
        return int(existing.iloc[0]["customer_id"])

    df = pd.DataFrame([{
        "name": "Real Store Customer",
        "email": "real-store@online.customers",
        "phone": None,
        "city": None,
        "state": None,
        "country": "India",
        "registration_date": datetime.now(),
        "is_active": 1,
    }])
    engine = get_engine()
    with engine.begin() as conn:
        df.to_sql("customers", conn, if_exists="append", index=False)
    new_row = fetch_data(
        "SELECT customer_id FROM customers WHERE email = 'real-store@online.customers' LIMIT 1"
    )
    return int(new_row.iloc[0]["customer_id"])


def ingest_payment(payment, customer_id):
    amount_inr = payment["amount"] / 100.0  # paise -> rupees
    method = METHOD_LABELS.get(payment.get("method"), payment.get("method", "Other"))
    created_at = datetime.fromtimestamp(payment["created_at"])

    order_df = pd.DataFrame([{
        "customer_id": customer_id,
        "order_date": created_at,
        "status": "Completed" if payment["status"] == "captured" else payment["status"].capitalize(),
        "total_amount": amount_inr,
        "shipping_address": None,
        "region": "Online",
    }])
    engine = get_engine()
    with engine.begin() as conn:
        order_df.to_sql("orders", conn, if_exists="append", index=False)

    new_order_id = fetch_data("SELECT MAX(order_id) AS id FROM orders").iloc[0]["id"]

    payment_df = pd.DataFrame([{
        "order_id": int(new_order_id),
        "payment_method": method,
        "amount": amount_inr,
        "payment_date": created_at,
        "status": "Completed" if payment["status"] == "captured" else payment["status"].capitalize(),
        "transaction_ref": payment["id"],
    }])
    with engine.begin() as conn:
        payment_df.to_sql("payments", conn, if_exists="append", index=False)

    logger.info(f"Ingested REAL payment {payment['id']}: ₹{amount_inr:,.2f} via {method}")


def run_ingestor():
    if not test_db_connection():
        logger.error("Database not reachable. Run db_setup.py first.")
        return

    logger.info("Starting REAL data ingestor. Polling Razorpay every "
                f"{INGEST_INTERVAL} seconds. Press CTRL+C to stop.")

    customer_id = get_or_create_generic_customer()

    while True:
        try:
            payments = fetch_recent_payments()
            new_count = 0
            for payment in payments:
                if payment["status"] != "captured":
                    continue
                if already_ingested(payment["id"]):
                    continue
                ingest_payment(payment, customer_id)
                new_count += 1
            if new_count == 0:
                logger.info("No new real payments this cycle.")
        except requests.exceptions.RequestException as e:
            logger.error(f"Razorpay API error: {e}")
        except Exception as e:
            logger.error(f"Ingestion error: {e}")

        time.sleep(INGEST_INTERVAL)


if __name__ == "__main__":
    run_ingestor()
