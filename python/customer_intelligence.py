import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import accuracy_score, mean_absolute_error
from config import setup_logging
from utils import get_engine, fetch_data, bulk_insert, execute_query

logger = setup_logging("CustomerIntelligence")

class CustomerIntelligence:
    def __init__(self):
        logger.info("Initializing Customer Intelligence System...")

    def update_rfm_segments(self):
        logger.info("Calculating RFM Segments...")
        query = """
            SELECT 
                customer_id,
                EXTRACT(DAY FROM CURRENT_DATE - MAX(DATE(order_date))) AS recency,
                COUNT(order_id) AS frequency,
                SUM(total_amount) AS monetary
            FROM orders
            WHERE status = 'Completed'
            GROUP BY customer_id
        """
        rfm_df = fetch_data(query)
        if rfm_df.empty:
            logger.warning("No order data available for RFM.")
            return

        # Calculate quantiles
        rfm_df['R_Quartile'] = pd.qcut(rfm_df['recency'], 5, labels=[5, 4, 3, 2, 1], duplicates='drop').astype(int)
        rfm_df['F_Quartile'] = pd.qcut(rfm_df['frequency'].rank(method='first'), 5, labels=[1, 2, 3, 4, 5]).astype(int)
        rfm_df['M_Quartile'] = pd.qcut(rfm_df['monetary'], 5, labels=[1, 2, 3, 4, 5], duplicates='drop').astype(int)

        rfm_df['rfm_score'] = rfm_df['R_Quartile'].astype(str) + rfm_df['F_Quartile'].astype(str) + rfm_df['M_Quartile'].astype(str)

        def map_segment(row):
            score = int(row['rfm_score'])
            if score >= 444: return 'VIP Customers'
            elif score >= 333: return 'Loyal Customers'
            elif row['R_Quartile'] <= 2: return 'At-Risk Customers'
            elif score <= 222: return 'Inactive Customers'
            else: return 'Regular Customers'

        rfm_df['segment_name'] = rfm_df.apply(map_segment, axis=1)

        # Truncate and Insert
        execute_query("TRUNCATE TABLE customer_segments")
        segments_to_insert = rfm_df[['customer_id', 'segment_name', 'rfm_score', 'recency', 'frequency', 'monetary']]
        bulk_insert(segments_to_insert, "customer_segments")
        logger.info("RFM Segmentation complete.")

    def predict_churn(self):
        logger.info("Training Churn Prediction Model...")
        query = """
            SELECT 
                c.customer_id,
                EXTRACT(DAY FROM CURRENT_DATE - MAX(DATE(o.order_date))) AS days_since_last_order,
                COUNT(o.order_id) AS total_orders,
                SUM(o.total_amount) AS total_spend,
                AVG(o.total_amount) AS avg_order_value
            FROM customers c
            JOIN orders o ON c.customer_id = o.customer_id
            WHERE o.status = 'Completed'
            GROUP BY c.customer_id
        """
        df = fetch_data(query)
        if len(df) < 100:
            logger.warning("Not enough data to train churn model.")
            return
            
        # Define churn: No orders in last 90 days
        df['is_churned'] = (df['days_since_last_order'] > 90).astype(int)
        
        features = ['total_orders', 'total_spend', 'avg_order_value']
        X = df[features]
        y = df['is_churned']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = RandomForestClassifier(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        acc = accuracy_score(y_test, preds)
        logger.info(f"Churn Model Accuracy: {acc:.2f}")

    def predict_cltv(self):
        logger.info("Training CLTV Prediction Model...")
        query = """
            WITH monthly_spend AS (
                SELECT 
                    customer_id,
                    EXTRACT(MONTH FROM order_date) as month,
                    SUM(total_amount) as amount
                FROM orders
                WHERE status = 'Completed' AND order_date >= CURRENT_DATE - INTERVAL '1 year'
                GROUP BY customer_id, EXTRACT(MONTH FROM order_date)
            )
            SELECT 
                customer_id,
                COUNT(month) as active_months,
                AVG(amount) as avg_monthly_spend,
                SUM(amount) as total_12m_spend
            FROM monthly_spend
            GROUP BY customer_id
        """
        df = fetch_data(query)
        if len(df) < 100:
            logger.warning("Not enough data to train CLTV model.")
            return
            
        # Simplified regression to predict future value based on past activity
        X = df[['active_months', 'avg_monthly_spend']]
        y = df['total_12m_spend']
        
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        
        model = RandomForestRegressor(n_estimators=100, random_state=42)
        model.fit(X_train, y_train)
        
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        logger.info(f"CLTV Model MAE: ${mae:.2f}")

if __name__ == "__main__":
    ci = CustomerIntelligence()
    ci.update_rfm_segments()
    ci.predict_churn()
    ci.predict_cltv()
