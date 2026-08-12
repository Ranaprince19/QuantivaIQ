import pandas as pd
import numpy as np
from faker import Faker
from datetime import datetime, timedelta
import random
from config import NUM_CUSTOMERS, NUM_PRODUCTS, NUM_ORDERS, setup_logging, test_db_connection, is_sqlite
from utils import get_engine, fetch_data, bulk_insert, execute_query, refresh_materialized_views

logger = setup_logging("ETL_Pipeline")
fake = Faker('en_IN')

def generate_customers(num_customers):
    logger.info(f"Generating {num_customers} customers...")
    data = []
    for _ in range(num_customers):
        data.append({
            "name": fake.name(),
            "email": fake.unique.email(),
            "phone": fake.phone_number()[:20],
            "city": fake.city(),
            "state": fake.state(),
            "country": "India", # Simplified
            "registration_date": fake.date_time_between(start_date='-2y', end_date='now'),
            "is_active": random.choices([True, False], weights=[0.9, 0.1])[0]
        })
    df = pd.DataFrame(data)
    bulk_insert(df, "customers", if_exists="append")
    logger.info("Customers inserted.")

def generate_categories_and_suppliers():
    logger.info("Generating Categories and Suppliers...")
    categories = [
        {"category_name": "Electronics", "parent_category_id": None},
        {"category_name": "Clothing & Ethnic Wear", "parent_category_id": None},
        {"category_name": "Home & Kitchen", "parent_category_id": None},
        {"category_name": "Sports & Fitness", "parent_category_id": None},
        {"category_name": "Books & Stationery", "parent_category_id": None},
        {"category_name": "Grocery & Essentials", "parent_category_id": None}
    ]
    df_cat = pd.DataFrame(categories)
    bulk_insert(df_cat, "categories", if_exists="append")

    # Suppliers are mostly India-based (domestic sourcing), with a
    # realistic minority of overseas import partners.
    overseas_sourcing_countries = ["China", "Vietnam", "Bangladesh", "USA", "Germany", "Japan"]
    suppliers = []
    for _ in range(30):
        is_domestic = random.random() < 0.75
        suppliers.append({
            "supplier_name": fake.company(),
            "contact_email": fake.company_email(),
            "country": "India" if is_domestic else random.choice(overseas_sourcing_countries),
            "reliability_score": round(random.uniform(80.0, 100.0), 2)
        })
    df_sup = pd.DataFrame(suppliers)
    bulk_insert(df_sup, "suppliers", if_exists="append")
    logger.info("Categories and Suppliers inserted.")

INDIAN_PRODUCT_CATALOG = {
    "Electronics": [
        "Wireless Bluetooth Earbuds", "Smart LED TV 43-inch", "Fast Charging Power Bank 20000mAh",
        "Noise Cancelling Headphones", "Smartwatch with Heart Rate Monitor", "4G Android Smartphone",
        "Bluetooth Party Speaker", "Laptop Cooling Pad", "USB-C Fast Charger 65W", "Digital Kitchen Weighing Scale"
    ],
    "Clothing & Ethnic Wear": [
        "Men's Cotton Kurta", "Women's Printed Saree", "Men's Formal Shirt", "Women's Anarkali Suit Set",
        "Kids' Ethnic Dhoti Set", "Men's Nehru Jacket", "Women's Palazzo Set", "Unisex Cotton Track Pants",
        "Men's Denim Jeans", "Women's Silk Dupatta"
    ],
    "Home & Kitchen": [
        "Stainless Steel Pressure Cooker 5L", "Non-Stick Tawa 28cm", "Copper Water Bottle 1L",
        "Ceramic Dinner Set 24-Piece", "Wooden Masala Dabba", "Electric Induction Cooktop",
        "Steel Tiffin Box 3-Tier", "Cotton Bedsheet Set Queen Size", "Air-Tight Storage Containers Set",
        "Mixer Grinder 750W"
    ],
    "Sports & Fitness": [
        "Yoga Mat Anti-Skid", "Cricket Bat Kashmir Willow", "Badminton Racket Set", "Adjustable Dumbbells Pair",
        "Football Size 5", "Resistance Bands Set", "Skipping Rope", "Running Shoes Unisex",
        "Cycling Helmet", "Table Tennis Paddle Set"
    ],
    "Books & Stationery": [
        "Hindi Fiction Bestseller Novel", "UPSC General Studies Guide", "Spiral Notebook Pack of 5",
        "NCERT Mathematics Textbook", "Gel Pen Set of 10", "Children's Panchatantra Story Book",
        "Competitive Exam Practice Set", "Desk Organizer with Calendar", "English Grammar Workbook",
        "Motivational Self-Help Book"
    ],
    "Grocery & Essentials": [
        "Basmati Rice 5kg", "Toor Dal 1kg", "Cold Pressed Groundnut Oil 1L", "Assorted Masala Combo Pack",
        "Green Tea 100 Bags", "Whole Wheat Atta 5kg", "Ghee 1L Pouch", "Mixed Dry Fruits 500g",
        "Instant Noodles Family Pack", "Herbal Soap Combo Pack of 4"
    ]
}


def generate_products(num_products):
    logger.info(f"Generating {num_products} products...")
    cat_df = fetch_data("SELECT category_id, category_name FROM categories")
    cat_ids = cat_df['category_id'].tolist()
    sup_ids = fetch_data("SELECT supplier_id FROM suppliers")['supplier_id'].tolist()

    if not cat_ids or not sup_ids:
        logger.error("No categories or suppliers found. Cannot generate products.")
        return

    cat_name_by_id = dict(zip(cat_df['category_id'], cat_df['category_name']))

    data = []
    for _ in range(num_products):
        cost_price = round(random.uniform(200.0, 25000.0), 2)  # INR cost price
        price = round(cost_price * random.uniform(1.2, 2.5), 2) # 20% to 150% markup
        chosen_cat_id = random.choice(cat_ids)
        cat_name = cat_name_by_id.get(chosen_cat_id, "Electronics")
        catalog = INDIAN_PRODUCT_CATALOG.get(cat_name, INDIAN_PRODUCT_CATALOG["Electronics"])
        base_name = random.choice(catalog)
        product_name = f"{base_name} - {fake.word().capitalize()} Edition" if random.random() < 0.3 else base_name
        data.append({
            "product_name": product_name,
            "category_id": chosen_cat_id,
            "supplier_id": random.choice(sup_ids),
            "price": price,
            "cost_price": cost_price,
            "stock_quantity": random.randint(50, 1000),
            "reorder_level": random.randint(10, 50)
        })
    df = pd.DataFrame(data)
    bulk_insert(df, "products", if_exists="append")
    
    # Generate Inventory
    prod_ids = fetch_data("SELECT product_id FROM products")['product_id'].tolist()
    inv_data = []
    for pid in prod_ids:
        inv_data.append({
            "product_id": pid,
            "warehouse_location": fake.city() + " Warehouse",
            "quantity_on_hand": random.randint(50, 1000),
            "quantity_reserved": 0,
            "last_restock_date": datetime.now()
        })
    bulk_insert(pd.DataFrame(inv_data), "inventory", if_exists="append")
    logger.info("Products and Inventory inserted.")

def generate_orders(num_orders):
    logger.info(f"Generating {num_orders} orders...")
    cust_ids = fetch_data("SELECT customer_id FROM customers")['customer_id'].tolist()
    prod_df = fetch_data("SELECT product_id, price FROM products")
    
    if not cust_ids or prod_df.empty:
        logger.error("Missing customers or products.")
        return

    # To optimize memory, we'll batch this
    batch_size = 5000
    for i in range(0, num_orders, batch_size):
        batch_orders = min(batch_size, num_orders - i)
        orders = []
        for _ in range(batch_orders):
            orders.append({
                "customer_id": random.choice(cust_ids),
                "order_date": fake.date_time_between(start_date='-1y', end_date='now'),
                "status": random.choices(['Completed', 'Pending', 'Cancelled'], weights=[0.85, 0.1, 0.05])[0],
                "total_amount": 0.0, # Will be updated by trigger, but we'll insert 0 for now
                "shipping_address": fake.address().replace('\n', ', '),
                "region": random.choice(["North", "South", "East", "West", "Central", "North-East"])
            })
        df_orders = pd.DataFrame(orders)
        
        # Need to insert and then fetch generated order_ids to create items
        engine = get_engine()
        with engine.begin() as conn:
            df_orders.to_sql('orders', conn, if_exists='append', index=False, method='multi')
        
        # Fetch the newly inserted order_ids. We'll use a rough heuristic: get max N order_ids
        recent_order_ids = fetch_data(f"SELECT order_id FROM orders ORDER BY order_id DESC LIMIT {batch_orders}")['order_id'].tolist()
        
        items = []
        payments = []
        refunds = []
        for oid in recent_order_ids:
            num_items = random.randint(1, 5)
            order_total = 0
            for _ in range(num_items):
                p = prod_df.sample(1).iloc[0]
                qty = random.randint(1, 3)
                items.append({
                    "order_id": oid,
                    "product_id": int(p['product_id']),
                    "quantity": qty,
                    "unit_price": float(p['price']),
                    "discount": 0.0
                })
                order_total += qty * float(p['price'])
            
            # Payment
            payment_status = 'Completed'
            payments.append({
                "order_id": oid,
                "payment_method": random.choices(
                    ["UPI", "Debit Card", "Credit Card", "Net Banking", "Paytm Wallet", "Cash on Delivery"],
                    weights=[0.45, 0.18, 0.12, 0.10, 0.10, 0.05]
                )[0],
                "amount": float(order_total),
                "payment_date": datetime.now(),
                "status": payment_status,
                "transaction_ref": fake.uuid4()
            })
            
            # Refund (5% chance)
            if random.random() < 0.05:
                refunds.append({
                    "order_id": oid,
                    "payment_id": None, # Will map later or leave null for simplicity
                    "refund_amount": float(order_total),
                    "reason": random.choice(["Defective", "Not Needed", "Wrong Item"]),
                    "refund_date": datetime.now(),
                    "status": "Processed"
                })

        items_df = pd.DataFrame(items)
        if is_sqlite() and not items_df.empty:
            items_df['line_total'] = items_df['quantity'] * items_df['unit_price'] - items_df['discount']

        bulk_insert(items_df, "order_items", if_exists="append")
        bulk_insert(pd.DataFrame(payments), "payments", if_exists="append")
        if refunds:
            bulk_insert(pd.DataFrame(refunds), "refunds", if_exists="append")

        update_order_totals()
        logger.info(f"Inserted order batch {i} to {i + batch_orders}")

def update_order_totals():
    logger.info("Updating order totals from order_items...")
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


def generate_customer_segments():
    logger.info("Generating customer segments...")
    customer_metrics = fetch_data(
        """
        SELECT
            c.customer_id,
            COUNT(o.order_id) AS total_orders,
            COALESCE(SUM(o.total_amount), 0) AS monetary,
            MAX(o.order_date) AS last_order_date
        FROM customers c
        LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'Completed'
        GROUP BY c.customer_id
        """
    )

    if customer_metrics.empty:
        logger.info("No customers found for segmentation generation.")
        return

    customer_metrics["last_order_date"] = pd.to_datetime(
        customer_metrics["last_order_date"]
    ).fillna(pd.Timestamp.now() - pd.Timedelta(days=999))
    customer_metrics["recency"] = (
        pd.Timestamp.now() - customer_metrics["last_order_date"]
    ).dt.days.clip(lower=0)
    customer_metrics["frequency"] = customer_metrics["total_orders"].fillna(0).astype(int)
    customer_metrics["monetary"] = customer_metrics["monetary"].fillna(0.0)

    def choose_segment(row):
        if row["frequency"] >= 20 or row["monetary"] >= 5000:
            return "Platinum"
        if row["frequency"] >= 10 or row["monetary"] >= 2500:
            return "Gold"
        if row["frequency"] >= 4 or row["monetary"] >= 1000:
            return "Silver"
        return "Bronze"

    customer_metrics["segment_name"] = customer_metrics.apply(choose_segment, axis=1)
    customer_metrics["rfm_score"] = (
        customer_metrics["recency"].rank(method="dense", ascending=False).astype(int).astype(str)
        + "-"
        + customer_metrics["frequency"].rank(method="dense", ascending=True).astype(int).astype(str)
        + "-"
        + customer_metrics["monetary"].rank(method="dense", ascending=True).astype(int).astype(str)
    )

    execute_query("DELETE FROM customer_segments")
    bulk_insert(
        customer_metrics[
            ["customer_id", "segment_name", "rfm_score", "recency", "frequency", "monetary"]
        ],
        "customer_segments",
        if_exists="append",
    )
    logger.info("Customer segments generated.")


def generate_fraud_logs():
    logger.info("Generating fraud logs...")
    completed_orders = fetch_data(
        "SELECT order_id, customer_id FROM orders WHERE status = 'Completed'"
    )
    if completed_orders.empty:
        logger.info("No completed orders available for fraud log generation.")
        return

    sample_size = max(1, int(len(completed_orders) * 0.02))
    fraud_orders = completed_orders.sample(min(sample_size, len(completed_orders)))

    fraud_records = []
    for _, row in fraud_orders.iterrows():
        fraud_records.append({
            "customer_id": int(row["customer_id"]),
            "order_id": int(row["order_id"]),
            "fraud_type": random.choice(["Payment Fraud", "Account Takeover", "Refund Abuse", "Promo Abuse"]),
            "risk_score": round(random.uniform(65.0, 98.0), 2),
            "detection_method": random.choice(["Rule Engine", "Anomaly Detection", "Behavioral Score"]),
            "detected_at": datetime.now(),
            "is_confirmed": random.random() < 0.25,
        })

    bulk_insert(pd.DataFrame(fraud_records), "fraud_logs", if_exists="append")
    logger.info("Fraud logs generated.")


def run_pipeline():
    logger.info("Starting ETL Pipeline...")
    
    if not test_db_connection():
        logger.error("Unable to connect to the configured database. Run db_setup.py and verify your .env settings before retrying.")
        return

    # Check if data already exists
    count = fetch_data("SELECT COUNT(*) FROM customers").iloc[0,0]
    if count > 0:
        logger.info("Data already exists. Skipping ETL generation.")
        return

    generate_customers(NUM_CUSTOMERS)
    generate_categories_and_suppliers()
    generate_products(NUM_PRODUCTS)
    generate_orders(NUM_ORDERS)
    generate_customer_segments()
    generate_fraud_logs()

    if not is_sqlite():
        refresh_materialized_views()
        logger.info("Power BI materialized views refreshed.")
    
    logger.info("ETL Pipeline completed successfully.")

if __name__ == "__main__":
    run_pipeline()
