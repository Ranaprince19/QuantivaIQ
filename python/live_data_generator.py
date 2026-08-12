import time
import schedule
import random
from faker import Faker
import pandas as pd
from datetime import datetime
from config import setup_logging, SIMULATION_INTERVAL, FRAUD_RATE, test_db_connection, is_sqlite
from utils import get_engine, fetch_data, bulk_insert, execute_query, refresh_materialized_views

logger = setup_logging("LiveSimulator")
fake = Faker('en_IN')

class LiveSimulator:
    def __init__(self):
        logger.info("Initializing Live Simulator...")
        self.cust_ids = fetch_data("SELECT customer_id FROM customers")['customer_id'].tolist()
        self.prod_df = fetch_data("SELECT product_id, price FROM products")
        
        if not self.cust_ids or self.prod_df.empty:
            logger.error("Database empty! Run ETL pipeline first.")
            raise ValueError("Empty database")

    def simulate_traffic(self):
        try:
            logger.info("Simulating live transaction cycle...")
            
            # 1. New Sessions
            sessions = []
            for _ in range(random.randint(1, 5)):
                sessions.append({
                    "customer_id": random.choice(self.cust_ids),
                    "login_time": datetime.now(),
                    "logout_time": None,
                    "device_type": random.choice(["Mobile", "Desktop", "Tablet"]),
                    "ip_address": fake.ipv4(),
                    "pages_viewed": random.randint(1, 20)
                })
            bulk_insert(pd.DataFrame(sessions), "customer_sessions")
            
            # 2. Orders & Payments
            orders = []
            num_orders = random.randint(1, 4)
            for _ in range(num_orders):
                orders.append({
                    "customer_id": random.choice(self.cust_ids),
                    "order_date": datetime.now(),
                    "status": "Completed",
                    "total_amount": 0,
                    "shipping_address": fake.address().replace('\n', ', '),
                    "region": random.choice(["North", "South", "East", "West", "Central", "North-East"])
                })
            
            if orders:
                df_orders = pd.DataFrame(orders)
                engine = get_engine()
                with engine.begin() as conn:
                    df_orders.to_sql('orders', conn, if_exists='append', index=False, method='multi')
                
                recent_order_ids = fetch_data(f"SELECT order_id FROM orders ORDER BY order_id DESC LIMIT {num_orders}")['order_id'].tolist()
                
                items = []
                payments = []
                for oid in recent_order_ids:
                    # Is Fraud?
                    is_fraud = random.random() < FRAUD_RATE
                    
                    num_items = random.randint(1, 3)
                    order_total = 0
                    for _ in range(num_items):
                        p = self.prod_df.sample(1).iloc[0]
                        # If fraud, maybe order a massive quantity
                        qty = random.randint(50, 100) if is_fraud else random.randint(1, 3)
                        item = {
                            "order_id": oid,
                            "product_id": int(p['product_id']),
                            "quantity": qty,
                            "unit_price": float(p['price']),
                            "discount": 0.0
                        }
                        if is_sqlite():
                            item["line_total"] = qty * float(p['price'])
                        items.append(item)
                        order_total += qty * float(p['price'])
                        
                    payments.append({
                        "order_id": oid,
                        "payment_method": "Credit Card" if is_fraud else random.choices(
                            ["UPI", "Debit Card", "Credit Card", "Net Banking", "Paytm Wallet", "Cash on Delivery"],
                            weights=[0.45, 0.18, 0.12, 0.10, 0.10, 0.05]
                        )[0],
                        "amount": float(order_total),
                        "payment_date": datetime.now(),
                        "status": "Completed",
                        "transaction_ref": fake.uuid4()
                    })

                items_df = pd.DataFrame(items)
                if is_sqlite() and not items_df.empty:
                    items_df['line_total'] = items_df['quantity'] * items_df['unit_price'] - items_df['discount']

                bulk_insert(items_df, "order_items")
                bulk_insert(pd.DataFrame(payments), "payments")
                execute_query(
                    """
                    UPDATE orders
                    SET total_amount = (
                        SELECT COALESCE(SUM(quantity * unit_price - discount), 0)
                        FROM order_items oi
                        WHERE oi.order_id = orders.order_id
                    )
                    """
                )
                if not is_sqlite():
                    refresh_materialized_views()
                    logger.info("Power BI materialized views refreshed after live simulation cycle.")
                logger.info(f"Inserted {num_orders} live orders.")
                
        except Exception as e:
            logger.error(f"Error during simulation cycle: {e}")

def run_simulator():
    if not test_db_connection():
        logger.error("Unable to connect to the configured database. Run db_setup.py and verify .env configuration before running live_data_generator.py.")
        return

    simulator = LiveSimulator()
    
    # Schedule job
    schedule.every(SIMULATION_INTERVAL).seconds.do(simulator.simulate_traffic)
    
    logger.info(f"Live Simulation started. Running every {SIMULATION_INTERVAL} seconds...")
    while True:
        schedule.run_pending()
        time.sleep(1)

if __name__ == "__main__":
    run_simulator()
