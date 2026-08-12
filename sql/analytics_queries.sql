-- QuantivaIQ Analytical Queries

-- ==========================================
-- REVENUE ANALYTICS
-- ==========================================

-- 1. Monthly Revenue Growth with MoM%
WITH monthly_revenue AS (
    SELECT DATE_TRUNC('month', order_date) AS month, SUM(total_amount) AS revenue
    FROM orders
    WHERE status = 'Completed'
    GROUP BY 1
)
SELECT 
    month, 
    revenue,
    LAG(revenue) OVER (ORDER BY month) AS prev_month_revenue,
    ROUND(((revenue - LAG(revenue) OVER (ORDER BY month)) / NULLIF(LAG(revenue) OVER (ORDER BY month), 0)) * 100, 2) AS mom_growth_pct
FROM monthly_revenue
ORDER BY month DESC;

-- 2. Regional Revenue Trends
SELECT region, DATE_TRUNC('month', order_date) AS month, SUM(total_amount) AS revenue
FROM orders
WHERE status = 'Completed'
GROUP BY region, DATE_TRUNC('month', order_date)
ORDER BY region, month;

-- 3. Product Category Performance Ranking
SELECT 
    c.category_name, 
    SUM(oi.line_total) AS total_revenue,
    DENSE_RANK() OVER (ORDER BY SUM(oi.line_total) DESC) AS rank
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
JOIN categories c ON p.category_id = c.category_id
GROUP BY c.category_name;

-- 4. Top 10 Products by Revenue
SELECT p.product_name, SUM(oi.line_total) AS revenue
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY revenue DESC
LIMIT 10;

-- 5. Revenue by Payment Method
SELECT p.payment_method, SUM(p.amount) AS total_amount, COUNT(p.payment_id) AS num_transactions
FROM payments p
WHERE p.status = 'Completed'
GROUP BY p.payment_method;

-- 6. Profitability Analysis
SELECT 
    p.product_name, 
    SUM(oi.quantity * (oi.unit_price - p.cost_price)) AS total_profit
FROM order_items oi
JOIN products p ON oi.product_id = p.product_id
GROUP BY p.product_name
ORDER BY total_profit DESC;


-- ==========================================
-- CUSTOMER ANALYTICS
-- ==========================================

-- 7. Customer Retention Rate (Cohort Analysis base)
WITH cohort_items AS (
    SELECT customer_id, MIN(DATE_TRUNC('month', order_date)) AS cohort_month
    FROM orders
    GROUP BY customer_id
)
SELECT cohort_month, COUNT(DISTINCT customer_id) AS new_customers
FROM cohort_items
GROUP BY cohort_month
ORDER BY cohort_month;

-- 8. Customer Churn Rate (inactive > 90 days)
SELECT 
    COUNT(CASE WHEN last_order < CURRENT_DATE - INTERVAL '90 days' THEN 1 END) AS churned_customers,
    COUNT(*) AS total_customers,
    ROUND(COUNT(CASE WHEN last_order < CURRENT_DATE - INTERVAL '90 days' THEN 1 END) * 100.0 / COUNT(*), 2) AS churn_rate_pct
FROM (
    SELECT customer_id, MAX(order_date) AS last_order
    FROM orders
    GROUP BY customer_id
) t;

-- 9. Repeat Purchase Rate
WITH customer_orders AS (
    SELECT customer_id, COUNT(order_id) as order_count
    FROM orders
    GROUP BY customer_id
)
SELECT 
    COUNT(CASE WHEN order_count > 1 THEN 1 END) * 100.0 / COUNT(*) AS repeat_purchase_rate
FROM customer_orders;

-- 10. Customer Lifetime Value (CLTV) ranking
SELECT customer_id, SUM(total_amount) AS cltv
FROM orders
WHERE status = 'Completed'
GROUP BY customer_id
ORDER BY cltv DESC;

-- 11. New vs Returning Customer Revenue Split
WITH customer_first_order AS (
    SELECT customer_id, MIN(order_date) AS first_order_date
    FROM orders
    GROUP BY customer_id
)
SELECT 
    CASE 
        WHEN DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', c.first_order_date) THEN 'New'
        ELSE 'Returning'
    END AS customer_type,
    SUM(o.total_amount) AS revenue
FROM orders o
JOIN customer_first_order c ON o.customer_id = c.customer_id
WHERE DATE_TRUNC('month', o.order_date) = DATE_TRUNC('month', CURRENT_DATE)
GROUP BY 1;

-- 12. Customer Activity Heatmap (Session count by day of week)
SELECT 
    EXTRACT(DOW FROM login_time) AS day_of_week,
    COUNT(session_id) AS session_count
FROM customer_sessions
GROUP BY 1
ORDER BY 1;


-- ==========================================
-- INVENTORY ANALYTICS
-- ==========================================

-- 13. Inventory Turnover Ratio (Simplified)
SELECT 
    p.product_id, 
    p.product_name, 
    SUM(oi.quantity) / NULLIF(AVG(i.quantity_on_hand), 0) AS turnover_ratio
FROM products p
JOIN order_items oi ON p.product_id = oi.product_id
JOIN inventory i ON p.product_id = i.product_id
GROUP BY p.product_id, p.product_name;

-- 14. Low Stock Alert Report
SELECT product_id, product_name, stock_quantity, reorder_level
FROM products
WHERE stock_quantity <= reorder_level;

-- 15. Overstock Detection (Stock > 5x average monthly sales)
WITH monthly_sales AS (
    SELECT product_id, SUM(quantity) / 3 AS avg_monthly_sales
    FROM order_items oi
    JOIN orders o ON oi.order_id = o.order_id
    WHERE o.order_date >= CURRENT_DATE - INTERVAL '90 days'
    GROUP BY product_id
)
SELECT p.product_name, p.stock_quantity, ms.avg_monthly_sales
FROM products p
JOIN monthly_sales ms ON p.product_id = ms.product_id
WHERE p.stock_quantity > ms.avg_monthly_sales * 5;

-- 16. Supplier Performance (based on reliability_score)
SELECT supplier_name, country, reliability_score
FROM suppliers
ORDER BY reliability_score DESC;


-- ==========================================
-- FRAUD ANALYTICS
-- ==========================================

-- 17. Fraud Transaction Ratio
SELECT 
    (SELECT COUNT(*) FROM fraud_logs) * 100.0 / NULLIF((SELECT COUNT(*) FROM orders), 0) AS fraud_ratio_pct;

-- 18. Suspicious Refund Patterns (Top 10 refund abusers)
SELECT customer_id, COUNT(refund_id) AS total_refunds, SUM(refund_amount) AS total_refund_amount
FROM refunds r
JOIN orders o ON r.order_id = o.order_id
GROUP BY customer_id
ORDER BY total_refunds DESC
LIMIT 10;

-- 19. High-Risk Customer Monitoring (composite score proxy)
SELECT customer_id, AVG(risk_score) AS avg_risk, COUNT(fraud_id) AS fraud_flags
FROM fraud_logs
GROUP BY customer_id
HAVING AVG(risk_score) > 80
ORDER BY avg_risk DESC;

-- 20. Fraud by Geographic Region
SELECT o.region, COUNT(f.fraud_id) AS fraud_incidents
FROM fraud_logs f
JOIN orders o ON f.order_id = o.order_id
GROUP BY o.region
ORDER BY fraud_incidents DESC;

-- 21. Payment Method Fraud Distribution
SELECT p.payment_method, COUNT(f.fraud_id) AS fraud_incidents
FROM fraud_logs f
JOIN orders o ON f.order_id = o.order_id
JOIN payments p ON o.order_id = p.order_id
GROUP BY p.payment_method
ORDER BY fraud_incidents DESC;


-- ==========================================
-- ADVANCED ANALYTICS (MARKET BASKET, ELASTICITY)
-- ==========================================

-- 22. Market Basket Analysis (Products bought together)
SELECT 
    a.product_id AS product_a, 
    b.product_id AS product_b, 
    COUNT(*) AS times_bought_together
FROM order_items a
JOIN order_items b ON a.order_id = b.order_id AND a.product_id < b.product_id
GROUP BY a.product_id, b.product_id
ORDER BY times_bought_together DESC
LIMIT 20;

-- 23. Seasonal Sales Patterns (Sales by Month across years)
SELECT 
    EXTRACT(MONTH FROM order_date) AS month, 
    SUM(total_amount) AS total_revenue
FROM orders
WHERE status = 'Completed'
GROUP BY 1
ORDER BY 1;

-- 24. Average Order Value (AOV) by Segment
SELECT 
    cs.segment_name, 
    AVG(o.total_amount) AS aov
FROM orders o
JOIN customer_segments cs ON o.customer_id = cs.customer_id
WHERE o.status = 'Completed'
GROUP BY cs.segment_name;

-- 25. Year-over-Year (YoY) Growth
WITH yearly_revenue AS (
    SELECT EXTRACT(YEAR FROM order_date) AS year, SUM(total_amount) AS revenue
    FROM orders
    WHERE status = 'Completed'
    GROUP BY 1
)
SELECT 
    year, 
    revenue,
    LAG(revenue) OVER (ORDER BY year) AS prev_year_revenue,
    ROUND(((revenue - LAG(revenue) OVER (ORDER BY year)) / NULLIF(LAG(revenue) OVER (ORDER BY year), 0)) * 100, 2) AS yoy_growth_pct
FROM yearly_revenue
ORDER BY year DESC;
