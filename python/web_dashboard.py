import os
from flask import Flask, render_template, jsonify
from .config import setup_logging, test_db_connection
from .utils import fetch_data, format_inr_currency, format_inr_number

logger = setup_logging("WebDashboard")

TEMPLATE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'templates'))
app = Flask(__name__, template_folder=TEMPLATE_DIR)
app.jinja_env.filters['inr'] = format_inr_currency
app.jinja_env.filters['inr_num'] = format_inr_number


def fetch_dashboard_metrics():
    logger.info("Loading dashboard metrics from database...")
    total_customers = fetch_data("SELECT COUNT(*) AS count FROM customers").iloc[0]['count']
    total_orders = fetch_data("SELECT COUNT(*) AS count FROM orders").iloc[0]['count']
    total_revenue = fetch_data("SELECT COALESCE(SUM(total_amount), 0) AS revenue FROM orders WHERE status = 'Completed'").iloc[0]['revenue']
    fraud_cases = fetch_data("SELECT COUNT(*) AS count FROM fraud_logs").iloc[0]['count']
    top_products = fetch_data(
        "SELECT p.product_name, SUM(oi.line_total) AS revenue "
        "FROM order_items oi "
        "JOIN products p ON oi.product_id = p.product_id "
        "GROUP BY p.product_name "
        "ORDER BY revenue DESC LIMIT 10"
    )
    revenue_by_region = fetch_data(
        "SELECT region, COALESCE(SUM(total_amount), 0) AS revenue "
        "FROM orders WHERE status = 'Completed' GROUP BY region ORDER BY revenue DESC"
    )
    segments = fetch_data(
        "SELECT segment_name, COUNT(*) AS customers "
        "FROM customer_segments GROUP BY segment_name ORDER BY customers DESC"
    )
    return {
        'total_customers': int(total_customers),
        'total_orders': int(total_orders),
        'total_revenue': float(total_revenue),
        'fraud_cases': int(fraud_cases),
        'top_products': top_products.to_dict(orient='records'),
        'revenue_by_region': revenue_by_region.to_dict(orient='records'),
        'segments': segments.to_dict(orient='records'),
    }


@app.route('/')
def index():
    db_available, db_error = test_db_connection()
    if not db_available:
        return render_template('index.html', db_ok=False, db_error=db_error)

    metrics = fetch_dashboard_metrics()
    # Determine whether Power BI integration is configured
    try:
        pbi_info = get_report_embed_info()
        pbi_available = pbi_info is not None
    except Exception:
        pbi_available = False

    return render_template('index.html', db_ok=True, pbi_available=pbi_available, **metrics)


@app.route('/powerbi/embed')
def powerbi_embed():
    """Return Power BI embed configuration for client-side embedding."""
    try:
        pbi_info = get_report_embed_info()
        if not pbi_info:
            return jsonify({"error": "Power BI not configured"}), 404
        return jsonify(pbi_info)
    except Exception as exc:
        logger.error(f"Power BI embed error: {exc}")
        return jsonify({"error": str(exc)}), 500


@app.route('/health')
def health():
    db_available, _ = test_db_connection()
    return {'status': 'ok', 'db_available': db_available}


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=False)
