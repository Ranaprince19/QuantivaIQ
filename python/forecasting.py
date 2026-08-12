import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from statsmodels.tsa.arima.model import ARIMA
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_absolute_error, mean_squared_error
from config import setup_logging
from utils import fetch_data
import os

logger = setup_logging("ForecastingEngine")

class ForecastingEngine:
    def __init__(self):
        logger.info("Initializing Demand Forecasting Engine...")
        self.reports_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'reports')
        os.makedirs(self.reports_dir, exist_ok=True)

    def load_time_series_data(self):
        logger.info("Loading daily sales data for forecasting...")
        query = """
            SELECT 
                DATE(order_date) as ds,
                SUM(total_amount) as y
            FROM orders
            WHERE status = 'Completed'
            GROUP BY DATE(order_date)
            ORDER BY DATE(order_date)
        """
        df = fetch_data(query)
        if df.empty:
            logger.warning("No sales data available for forecasting.")
            return None
            
        df['ds'] = pd.to_datetime(df['ds'])
        df.set_index('ds', inplace=True)
        # Resample to daily frequency to fill missing dates with 0
        df = df.resample('D').sum().fillna(0)
        return df

    def forecast_linear_regression(self, df, forecast_days=30):
        logger.info("Training Linear Regression with Lag Features...")
        data = df.copy()
        
        # Create lag features
        data['lag_1'] = data['y'].shift(1)
        data['lag_7'] = data['y'].shift(7)
        data['day_of_week'] = data.index.dayofweek
        
        data.dropna(inplace=True)
        
        if len(data) < 30:
            logger.warning("Insufficient data for Linear Regression forecasting.")
            return
            
        X = data[['lag_1', 'lag_7', 'day_of_week']]
        y = data['y']
        
        # Train-test split (last 30 days as test)
        train_size = len(data) - forecast_days
        X_train, X_test = X.iloc[:train_size], X.iloc[train_size:]
        y_train, y_test = y.iloc[:train_size], y.iloc[train_size:]
        
        model = LinearRegression()
        model.fit(X_train, y_train)
        
        # If we want to forecast future recursively, we can.
        # For simplicity, let's just evaluate on test set
        preds = model.predict(X_test)
        mae = mean_absolute_error(y_test, preds)
        logger.info(f"Linear Regression MAE on test set: {mae:.2f}")

    def forecast_arima(self, df, forecast_days=30):
        logger.info("Training ARIMA Model...")
        if len(df) < 50:
            logger.warning("Insufficient data for ARIMA forecasting.")
            return
            
        train = df['y'][:-forecast_days]
        test = df['y'][-forecast_days:]
        
        # Auto-regressive Integrated Moving Average (p, d, q)
        # We use a simple (5,1,0) configuration for demonstration
        try:
            model = ARIMA(train, order=(5,1,0))
            model_fit = model.fit()
            
            # Forecast
            forecast = model_fit.forecast(steps=forecast_days)
            
            mae = mean_absolute_error(test, forecast)
            logger.info(f"ARIMA MAE on test set: {mae:.2f}")
            
            # Plot
            plt.figure(figsize=(12, 6))
            plt.plot(train.index[-90:], train[-90:], label='Historical Training Data')
            plt.plot(test.index, test, label='Actual Test Data')
            plt.plot(test.index, forecast, color='red', label='ARIMA Forecast')
            plt.title('ARIMA 30-Day Sales Forecast')
            plt.xlabel('Date')
            plt.ylabel('Revenue')
            plt.legend()
            
            plot_path = os.path.join(self.reports_dir, 'arima_forecast.png')
            plt.savefig(plot_path)
            plt.close()
            logger.info(f"Forecast plot saved to {plot_path}")
            
        except Exception as e:
            logger.error(f"ARIMA training failed: {e}")

    def run(self):
        df = self.load_time_series_data()
        if df is not None:
            self.forecast_linear_regression(df)
            self.forecast_arima(df)

if __name__ == "__main__":
    engine = ForecastingEngine()
    engine.run()
