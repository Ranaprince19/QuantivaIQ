-- QuantivaIQ Stored Procedures, Triggers, and Materialized Views

-- ==========================================
-- STORED PROCEDURES
-- ==========================================

-- 1. Calculate Monthly Revenue
CREATE OR REPLACE FUNCTION sp_calculate_monthly_revenue()
RETURNS TABLE(month_year TEXT, total_revenue NUMERIC, mom_growth_pct NUMERIC) AS $$
BEGIN
    RETURN QUERY
    WITH monthly AS (
        SELECT 
            TO_CHAR(DATE_TRUNC('month', order_date), 'YYYY-MM') AS month_year,
            SUM(total_amount) AS total_revenue
        FROM orders
        WHERE status = 'Completed'
        GROUP BY DATE_TRUNC('month', order_date)
    )
    SELECT 
        m1.month_year,
        m1.total_revenue,
        ROUND(((m1.total_revenue - LAG(m1.total_revenue) OVER (ORDER BY m1.month_year)) / NULLIF(LAG(m1.total_revenue) OVER (ORDER BY m1.month_year), 0)) * 100, 2) AS mom_growth_pct
    FROM monthly m1;
END;
$$ LANGUAGE plpgsql;

-- 2. Detect Suspicious Refunds
CREATE OR REPLACE FUNCTION sp_detect_suspicious_refunds(threshold INT DEFAULT 3)
RETURNS VOID AS $$
BEGIN
    INSERT INTO suspicious_transactions (customer_id, transaction_type, amount, reason, flagged_at)
    SELECT 
        o.customer_id,
        'Refund Abuse' AS transaction_type,
        SUM(r.refund_amount) AS amount,
        'Customer has ' || COUNT(r.refund_id) || ' refunds in the last 30 days.' AS reason,
        CURRENT_TIMESTAMP
    FROM refunds r
    JOIN orders o ON r.order_id = o.order_id
    WHERE r.refund_date >= CURRENT_DATE - INTERVAL '30 days'
    GROUP BY o.customer_id
    HAVING COUNT(r.refund_id) > threshold;
END;
$$ LANGUAGE plpgsql;

-- 3. Update Customer Segments (RFM)
CREATE OR REPLACE FUNCTION sp_update_customer_segments()
RETURNS VOID AS $$
BEGIN
    -- We would calculate the quantiles and update in real life.
    -- Here is a simplified version just updating recency/frequency/monetary.
    UPDATE customer_segments cs
    SET 
        recency = r.recency,
        frequency = r.frequency,
        monetary = r.monetary,
        last_updated = CURRENT_TIMESTAMP
    FROM (
        SELECT 
            customer_id,
            CURRENT_DATE - MAX(DATE(order_date)) AS recency,
            COUNT(order_id) AS frequency,
            SUM(total_amount) AS monetary
        FROM orders
        GROUP BY customer_id
    ) r
    WHERE cs.customer_id = r.customer_id;
END;
$$ LANGUAGE plpgsql;

-- 4. Check Low Stock
CREATE OR REPLACE FUNCTION sp_check_low_stock()
RETURNS TABLE(product_id INT, product_name VARCHAR, stock_quantity INT, reorder_level INT) AS $$
BEGIN
    RETURN QUERY
    SELECT p.product_id, p.product_name, p.stock_quantity, p.reorder_level
    FROM products p
    WHERE p.stock_quantity <= p.reorder_level;
END;
$$ LANGUAGE plpgsql;

-- 5. Calculate CLTV (Simplified Historical CLTV)
CREATE OR REPLACE FUNCTION sp_calculate_cltv()
RETURNS TABLE(customer_id INT, cltv NUMERIC) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        o.customer_id,
        SUM(o.total_amount) AS cltv
    FROM orders o
    WHERE o.status = 'Completed'
    GROUP BY o.customer_id;
END;
$$ LANGUAGE plpgsql;

-- 6. Fraud Risk Scoring (Dummy base function)
CREATE OR REPLACE FUNCTION sp_fraud_risk_scoring()
RETURNS VOID AS $$
BEGIN
    -- To be implemented fully via ML, but we can do a baseline rule-based here.
    NULL;
END;
$$ LANGUAGE plpgsql;

-- ==========================================
-- TRIGGERS
-- ==========================================

-- 1. Update Inventory on Order
CREATE OR REPLACE FUNCTION fn_update_inventory_on_order()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE products
    SET stock_quantity = stock_quantity - NEW.quantity
    WHERE product_id = NEW.product_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_inventory_on_order ON order_items;
CREATE TRIGGER trg_update_inventory_on_order
AFTER INSERT ON order_items
FOR EACH ROW
EXECUTE FUNCTION fn_update_inventory_on_order();

-- 2. Flag High Refund
CREATE OR REPLACE FUNCTION fn_flag_high_refund()
RETURNS TRIGGER AS $$
DECLARE
    refund_count INT;
    cust_id INT;
BEGIN
    SELECT customer_id INTO cust_id FROM orders WHERE order_id = NEW.order_id;
    
    SELECT COUNT(*) INTO refund_count 
    FROM refunds r 
    JOIN orders o ON r.order_id = o.order_id
    WHERE o.customer_id = cust_id AND r.refund_date >= CURRENT_DATE - INTERVAL '30 days';

    IF refund_count > 3 THEN
        INSERT INTO suspicious_transactions (customer_id, transaction_type, amount, reason)
        VALUES (cust_id, 'Refund Anomaly', NEW.refund_amount, 'Auto-flagged: High refund frequency');
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_flag_high_refund ON refunds;
CREATE TRIGGER trg_flag_high_refund
AFTER INSERT ON refunds
FOR EACH ROW
EXECUTE FUNCTION fn_flag_high_refund();

-- 3. Update Order Total
CREATE OR REPLACE FUNCTION fn_update_order_total()
RETURNS TRIGGER AS $$
BEGIN
    UPDATE orders
    SET total_amount = (
        SELECT COALESCE(SUM(line_total), 0) FROM order_items WHERE order_id = NEW.order_id
    )
    WHERE order_id = NEW.order_id;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_order_total ON order_items;
CREATE TRIGGER trg_update_order_total
AFTER INSERT OR UPDATE ON order_items
FOR EACH ROW
EXECUTE FUNCTION fn_update_order_total();

-- ==========================================
-- MATERIALIZED VIEWS
-- ==========================================

DROP MATERIALIZED VIEW IF EXISTS mv_daily_revenue CASCADE;
CREATE MATERIALIZED VIEW mv_daily_revenue AS
SELECT 
    DATE(order_date) AS order_date,
    SUM(total_amount) AS revenue,
    COUNT(order_id) AS order_count
FROM orders
WHERE status = 'Completed'
GROUP BY DATE(order_date);

DROP MATERIALIZED VIEW IF EXISTS mv_customer_kpis CASCADE;
CREATE MATERIALIZED VIEW mv_customer_kpis AS
SELECT 
    c.customer_id,
    c.name,
    COUNT(o.order_id) AS total_orders,
    SUM(o.total_amount) AS total_spend,
    AVG(o.total_amount) AS avg_order_value,
    MAX(o.order_date) AS last_order_date
FROM customers c
LEFT JOIN orders o ON c.customer_id = o.customer_id AND o.status = 'Completed'
GROUP BY c.customer_id, c.name;

DROP MATERIALIZED VIEW IF EXISTS mv_product_performance CASCADE;
CREATE MATERIALIZED VIEW mv_product_performance AS
SELECT 
    p.product_id,
    p.product_name,
    c.category_name,
    SUM(oi.quantity) AS total_units_sold,
    SUM(oi.line_total) AS total_revenue
FROM products p
JOIN categories c ON p.category_id = c.category_id
LEFT JOIN order_items oi ON p.product_id = oi.product_id
GROUP BY p.product_id, p.product_name, c.category_name;

DROP MATERIALIZED VIEW IF EXISTS mv_fraud_summary CASCADE;
CREATE MATERIALIZED VIEW mv_fraud_summary AS
SELECT 
    fraud_type,
    DATE(detected_at) AS detection_date,
    COUNT(fraud_id) AS fraud_incidents,
    AVG(risk_score) AS avg_risk_score
FROM fraud_logs
GROUP BY fraud_type, DATE(detected_at);

DROP MATERIALIZED VIEW IF EXISTS mv_inventory_status CASCADE;
CREATE MATERIALIZED VIEW mv_inventory_status AS
SELECT 
    i.warehouse_location,
    p.product_name,
    i.quantity_on_hand,
    i.quantity_reserved,
    p.reorder_level
FROM inventory i
JOIN products p ON i.product_id = p.product_id;
