import pandas as pd
import numpy as np
from faker import Faker
import random
from datetime import datetime, timedelta
import os
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from statsmodels.tsa.arima.model import ARIMA
import warnings

warnings.filterwarnings('ignore')
fake = Faker()

def generate_demo_data():
    print("[1/4] Generating simulated retail data in memory...")
    # Customers
    customers = []
    for i in range(1, 501):
        customers.append({"customer_id": i, "name": fake.name()})
    
    # Orders
    orders = []
    end_date = datetime.now()
    start_date = end_date - timedelta(days=180)
    
    for _ in range(5000):
        # Generate some fraud behaviors (abnormally high amounts)
        is_fraud = random.random() < 0.02
        amount = random.uniform(500, 5000) if is_fraud else random.uniform(10, 200)
        
        # Some customers order way more often (velocity fraud)
        cid = random.randint(1, 10) if is_fraud else random.randint(1, 500)
        
        order_date = fake.date_time_between(start_date=start_date, end_date=end_date)
        orders.append({
            "order_id": fake.uuid4(),
            "customer_id": cid,
            "order_date": order_date,
            "total_amount": amount,
            "is_fraud_injected": is_fraud
        })
        
    df_orders = pd.DataFrame(orders)
    print(f"Generated {len(customers)} customers and {len(df_orders)} orders.")
    return pd.DataFrame(customers), df_orders

def run_fraud_detection(df_orders):
    print("\n[2/4] Running Fraud Detection Engine (Isolation Forest)...")
    
    # Feature Engineering in Pandas (mimicking our SQL aggregations)
    df_orders['order_date_only'] = df_orders['order_date'].dt.date
    
    customer_stats = df_orders.groupby('customer_id').agg(
        total_orders=('order_id', 'count'),
        avg_order_amount=('total_amount', 'mean'),
        max_order_amount=('total_amount', 'max'),
        amount_stddev=('total_amount', 'std'),
        active_days=('order_date_only', 'nunique')
    ).reset_index()
    
    customer_stats.fillna(0, inplace=True)
    customer_stats['order_frequency'] = customer_stats['total_orders'] / customer_stats['active_days']
    
    features = ['avg_order_amount', 'max_order_amount', 'amount_stddev', 'order_frequency']
    X = customer_stats[features]
    
    # Run Isolation Forest
    iso_forest = IsolationForest(contamination=0.03, random_state=42)
    customer_stats['is_anomaly'] = iso_forest.fit_predict(X)
    
    fraud_cases = customer_stats[customer_stats['is_anomaly'] == -1]
    print(f"--> Machine Learning Engine flagged {len(fraud_cases)} customers for suspicious activity.")
    print("Top 5 Suspicious Profiles:")
    print(fraud_cases[['customer_id', 'total_orders', 'avg_order_amount', 'max_order_amount']].head(5).to_string(index=False))

def run_demand_forecasting(df_orders):
    print("\n[3/4] Running Demand Forecasting Engine (ARIMA)...")
    
    # Aggregate daily sales
    daily_sales = df_orders.groupby('order_date_only')['total_amount'].sum().reset_index()
    daily_sales['order_date_only'] = pd.to_datetime(daily_sales['order_date_only'])
    daily_sales.set_index('order_date_only', inplace=True)
    daily_sales = daily_sales.resample('D').sum().fillna(0)
    
    if len(daily_sales) > 50:
        train = daily_sales['total_amount']
        
        # Fit ARIMA
        model = ARIMA(train, order=(5,1,0))
        model_fit = model.fit()
        
        # Forecast next 30 days
        forecast = model_fit.forecast(steps=30)
        
        # Plot
        os.makedirs("reports", exist_ok=True)
        plt.figure(figsize=(10, 5))
        plt.plot(train.index[-60:], train[-60:], label='Historical Sales')
        forecast_index = pd.date_range(start=train.index[-1] + pd.Timedelta(days=1), periods=30)
        plt.plot(forecast_index, forecast, color='red', label='ARIMA 30-Day Forecast')
        plt.title('Retail Demand Forecasting')
        plt.xlabel('Date')
        plt.ylabel('Total Revenue ($)')
        plt.legend()
        
        plot_path = os.path.join("reports", "demo_forecast.png")
        plt.savefig(plot_path)
        print(f"--> Forecasting complete! Projected next 30 days of sales.")
        print(f"--> Beautiful forecast chart saved to: {plot_path}")

def run_customer_intelligence(df_orders):
    print("\n[4/4] Running Customer Intelligence (RFM)...")
    
    latest_date = df_orders['order_date'].max()
    rfm = df_orders.groupby('customer_id').agg(
        recency=('order_date', lambda x: (latest_date - x.max()).days),
        frequency=('order_id', 'count'),
        monetary=('total_amount', 'sum')
    ).reset_index()
    
    print("Sample Customer Segments (RFM Metrics):")
    print(rfm.head(5).to_string(index=False))

if __name__ == "__main__":
    print("==================================================")
    print("   QuantivaIQ - Standalone In-Memory Execution    ")
    print("==================================================\n")
    
    _, orders = generate_demo_data()
    run_fraud_detection(orders)
    run_demand_forecasting(orders)
    run_customer_intelligence(orders)
    
    print("\n==================================================")
    print(" Pipeline Execution Completed Successfully!")
    print("==================================================")
