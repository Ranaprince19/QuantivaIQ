# QuantivaIQ Power BI Dashboard Template

This document defines a full Power BI report template for QuantivaIQ, including pages, cards, charts, data sources, the model, and DAX measures. Use it to build a Power BI report manually or as a blueprint for a future `.pbix` template.

---

## Report Overview

QuantivaIQ Power BI report should be built in **DirectQuery** mode against the PostgreSQL warehouse.

### Primary datasets

- `mv_daily_revenue`
- `mv_customer_kpis`
- `mv_product_performance`
- `mv_fraud_summary`
- `mv_inventory_status`
- `customer_segments`
- `fraud_logs`
- `orders`
- `order_items`
- `products`
- `customers`

### Report goals

- Provide executive revenue and growth visibility
- Measure customer acquisition, retention, and lifetime value
- Detect fraud and monitor risk in near real time
- Track inventory health and product performance
- Enable drill-through analysis from summary to transaction detail
- Support live refresh during simulation runs

---

## Data Model

### Relationship recommendations

- `orders[customer_id]` → `customers[customer_id]`
- `order_items[order_id]` → `orders[order_id]`
- `order_items[product_id]` → `products[product_id]`
- `customer_segments[customer_id]` → `customers[customer_id]`
- `fraud_logs[customer_id]` → `customers[customer_id]`
- `fraud_logs[order_id]` → `orders[order_id]`
- `mv_customer_kpis[customer_id]` → `customers[customer_id]` (optional)
- `mv_product_performance[product_id]` → `products[product_id]` (optional)

> Use chained relationships through lookup tables where possible, and avoid many-to-many relationships between facts.

### Recommended table roles

- Fact / aggregate tables: `mv_*` views, `fraud_logs`, `orders`, `order_items`
- Dimension tables: `customers`, `products`, `customer_segments`

---

## Page 1: Executive Overview

### Page purpose

Show the company-wide business health metrics for revenue, order volume, customer activity, and high-level performance trends.

### Page layout

1. **Header**
   - Report title: `QuantivaIQ Executive Overview`
   - Subtitle: `Live dashboard for revenue, orders, and customer performance`
   - Last refreshed timestamp card (optional)

2. **KPI cards** (top row)
   - `Total Revenue`
   - `Monthly Revenue Growth %`
   - `Average Order Value (AOV)`
   - `Total Orders`
   - `Total Customers`

3. **Trend charts**
   - Line chart: `mv_daily_revenue[order_date]` vs `revenue`
   - Area chart: `mv_daily_revenue[order_date]` vs `order_count`

4. **Regional analysis**
   - Stacked bar chart: `orders[region]` vs `total_amount`
   - Map visual: `orders[region]` revenue distribution (if region coordinates are available)

5. **Top products**
   - Table or bar chart: `mv_product_performance[product_name]` vs `total_revenue`

### Visual definitions

#### Total Revenue
- Visual: KPI card
- Value: `SUM(orders[total_amount])`
- Target/reference: optional previous period or monthly plan

#### Monthly Revenue Growth %
- Visual: KPI card
- Value: `DIVIDE([Total Revenue] - [PM Revenue], [PM Revenue], 0)`

#### Average Order Value
- Visual: KPI card
- Value: `DIVIDE([Total Revenue], DISTINCTCOUNT(orders[order_id]))`

#### Total Orders
- Visual: KPI card
- Value: `DISTINCTCOUNT(orders[order_id])`

#### Total Customers
- Visual: KPI card
- Value: `DISTINCTCOUNT(customers[customer_id])`

#### Revenue trend
- Visual: Line chart
- Axis: `mv_daily_revenue[order_date]`
- Values: `revenue`
- Optional line: `order_count`

#### Order volume trend
- Visual: Area chart or line chart
- Axis: `mv_daily_revenue[order_date]`
- Values: `order_count`

#### Revenue by region
- Visual: Stacked bar chart
- Axis: `orders[region]`
- Values: `orders[total_amount]`

#### Top products by revenue
- Visual: Bar chart
- Axis: `mv_product_performance[product_name]`
- Values: `total_revenue`
- Tooltip: `total_units_sold`, `category_name`

---

## Page 2: Customer Intelligence

### Page purpose

Measure customer acquisition, loyalty, RFM segmentation, churn risk, and customer lifetime value.

### Page layout

1. **KPI cards**
   - `Total Customers`
   - `Active Customers 30D`
   - `Retention Rate %`
   - `Churn Rate %`
   - `Avg CLTV`

2. **Customer segments**
   - Donut or pie chart: `customer_segments[segment_name]`
   - Table: `customer_segments` with `rfm_score`, `recency`, `frequency`, `monetary`

3. **Customer revenue distribution**
   - Clustered bar chart: `mv_customer_kpis[name]` vs `total_spend`
   - Top customers table: `mv_customer_kpis` sorted by `total_spend`

4. **Acquisition & retention trend**
   - Line chart: new customers over time
   - Line chart: active customers over time

### Visual definitions

#### Active Customers 30D
- Visual: KPI card
- Measure:
```dax
Active Customers 30D = CALCULATE(
    DISTINCTCOUNT(orders[customer_id]),
    orders[order_date] >= TODAY() - 30
)
```

#### Retention Rate %
- Visual: KPI card
- Measure:
```dax
Retention Rate % = DIVIDE([Active Customers 30D], [Total Customers], 0)
```

#### Churn Rate %
- Visual: KPI card
- Measure: `1 - [Retention Rate %]`

#### Avg CLTV
- Visual: KPI card
- Measure:
```dax
Avg CLTV = DIVIDE([Total Revenue], [Total Customers])
```

#### Customer segment distribution
- Visual: Donut chart
- Category: `customer_segments[segment_name]`
- Values: `COUNTROWS(customer_segments)`

#### Segment details table
- Fields:
  - `customer_id`
  - `segment_name`
  - `rfm_score`
  - `recency`
  - `frequency`
  - `monetary`

---

## Page 3: Fraud & Risk

### Page purpose

Surface fraud incidence, risk score distribution, fraud type breakdown, and impact to revenue.

### Page layout

1. **KPI cards**
   - `Total Fraud Txns`
   - `Fraud Rate %`
   - `Avg Risk Score`
   - `Value at Risk`
   - `High Risk Customers`

2. **Fraud type breakdown**
   - Column chart: `fraud_logs[fraud_type]` vs `COUNTROWS(fraud_logs)`

3. **Fraud timeline**
   - Line chart: `fraud_logs[detected_at]` vs `COUNTROWS(fraud_logs)`

4. **High-risk customer table**
   - Table: `fraud_logs` filtered on `risk_score >= 80`
   - Columns: `order_id`, `customer_id`, `fraud_type`, `risk_score`, `detection_method`, `detected_at`

5. **Refund analytics**
   - Card: `Total Refunds`
   - Card: `Refund Rate %`

### Visual definitions

#### Total Fraud Txns
```dax
Total Fraud Txns = COUNTROWS(fraud_logs)
```

#### Fraud Rate %
```dax
Fraud Rate % = DIVIDE([Total Fraud Txns], COUNTROWS(orders), 0)
```

#### Avg Risk Score
```dax
Avg Risk Score = AVERAGE(fraud_logs[risk_score])
```

#### High Risk Customers
```dax
High Risk Customers = CALCULATE(
    DISTINCTCOUNT(fraud_logs[customer_id]),
    fraud_logs[risk_score] >= 80
)
```

#### Value at Risk
```dax
Value at Risk = CALCULATE(
    SUM(orders[total_amount]),
    USERELATIONSHIP(orders[order_id], fraud_logs[order_id])
)
```

#### Total Refunds
```dax
Total Refunds = SUM(refunds[refund_amount])
```

#### Refund Rate %
```dax
Refund Rate % = DIVIDE([Total Refunds], [Total Revenue], 0)
```

---

## Page 4: Inventory & Product Health

### Page purpose

Track stock levels, low-stock risk, inventory value, and product revenue performance.

### Page layout

1. **KPI cards**
   - `Total Units Sold`
   - `Total Inventory Value`
   - `Out of Stock Items`
   - `Low Stock Items`
   - `Inventory Turnover`

2. **Inventory status**
   - Table or matrix: `mv_inventory_status` showing `warehouse_location`, `product_name`, `quantity_on_hand`, `quantity_reserved`, `reorder_level`

3. **Top product revenue**
   - Bar chart: `mv_product_performance[product_name]` vs `total_revenue`
   - Column chart: `mv_product_performance[product_name]` vs `total_units_sold`

4. **Low stock alert list**
   - Table: products where `stock_quantity <= reorder_level`

### Visual definitions

#### Total Units Sold
```dax
Total Units Sold = SUM(order_items[quantity])
```

#### Total Inventory Value
```dax
Total Inventory Value = SUMX(products, products[stock_quantity] * products[cost_price])
```

#### Out of Stock Items
```dax
Out of Stock Items = CALCULATE(
    COUNTROWS(products),
    products[stock_quantity] <= 0
)
```

#### Low Stock Items
```dax
Low Stock Items = CALCULATE(
    COUNTROWS(products),
    products[stock_quantity] <= products[reorder_level]
)
```

#### Inventory Turnover
```dax
Inventory Turnover = DIVIDE(
    SUM(order_items[quantity]),
    AVERAGE(products[stock_quantity]),
    0
)
```

---

## Page 5: Operational Insights

### Page purpose

Monitor live traffic, simulator activity, and operational KPIs for time-sensitive decisions.

### Page layout

1. **Live update status**
   - Card: `Last refresh` or manual timestamp field
   - Card: `Simulator active` indicator

2. **Session activity**
   - Line chart: `customer_sessions[login_time]` over time
   - Table: recent sessions

3. **Order & payment flow**
   - KPI cards: `Live orders`, `Live payments`
   - Column chart: new orders by region or channel

4. **Customer behavior**
   - Card: `New customers today`
   - Table: top recent customer segments

### Notes

This page is optional and most valuable when the simulator is running in DirectQuery mode, and the backend is set to PostgreSQL.

---

## Report template fields for each page

### Executive Overview
- `mv_daily_revenue[order_date]`
- `mv_daily_revenue[revenue]`
- `mv_daily_revenue[order_count]`
- `orders[region]`
- `orders[total_amount]`
- `mv_product_performance[product_name]`
- `mv_product_performance[total_revenue]`
- `mv_product_performance[total_units_sold]`

### Customer Intelligence
- `customers[customer_id]`
- `customers[name]`
- `customers[registration_date]`
- `orders[order_date]`
- `orders[customer_id]`
- `customer_segments[segment_name]`
- `customer_segments[rfm_score]`
- `customer_segments[recency]`
- `customer_segments[frequency]`
- `customer_segments[monetary]`
- `mv_customer_kpis[total_spend]`
- `mv_customer_kpis[avg_order_value]`
- `mv_customer_kpis[last_order_date]`

### Fraud & Risk
- `fraud_logs[fraud_type]`
- `fraud_logs[risk_score]`
- `fraud_logs[detection_method]`
- `fraud_logs[detected_at]`
- `fraud_logs[order_id]`
- `fraud_logs[customer_id]`
- `orders[total_amount]`
- `refunds[refund_amount]`

### Inventory & Product Health
- `mv_inventory_status[warehouse_location]`
- `mv_inventory_status[product_name]`
- `mv_inventory_status[quantity_on_hand]`
- `mv_inventory_status[quantity_reserved]`
- `mv_inventory_status[reorder_level]`
- `products[stock_quantity]`
- `products[cost_price]`
- `order_items[quantity]`
- `order_items[unit_price]`

---

## Power BI page structure summary

| Page | Goal | Key visuals | Primary source |
|---|---|---|---|
| Executive Overview | Revenue, orders, customer size | KPI cards, line chart, regional bar, top products | `mv_daily_revenue`, `orders`, `mv_product_performance` |
| Customer Intelligence | RFM and retention | KPI cards, segment donut, customer table, trend lines | `customer_segments`, `mv_customer_kpis`, `orders` |
| Fraud & Risk | Fraud incident and risk | KPI cards, fraud type bar, timeline, fraud log table | `fraud_logs`, `orders`, `refunds` |
| Inventory Health | Stock and product performance | KPI cards, inventory table, product revenue bars | `mv_inventory_status`, `products`, `order_items` |
| Operational Insights | Live simulator and order flow | Live session chart, orders chart, status cards | `customer_sessions`, `orders`, `fraud_logs` |

---

## Power BI build instructions

1. Open Power BI Desktop.
2. Click **Get Data** → **PostgreSQL database**.
3. Enter server and database.
4. Choose **DirectQuery**.
5. Import the views/tables listed above.
6. Create relationships as recommended.
7. Build pages using the visual templates above.
8. Enable **Auto page refresh** on each page.
9. Save as `QuantivaIQ.pbix`.

---

## Live refresh guidance

Power BI will update when the backend data changes if:

- The report uses **DirectQuery**
- PostgreSQL is running and reachable
- The simulator is inserting new data
- Materialized views are refreshed after ETL or after new order insertions

Refresh materialized views manually:

```bash
python python/refresh_powerbi_views.py
```

For simulation-driven refresh, run the live generator in PostgreSQL mode:

```bash
python python/live_data_generator.py
```

---

## Notes for integration

- The Power BI report should read from PostgreSQL, not SQLite.
- Use the `docker-compose.yml` stack or local PostgreSQL with `.env` configured for postgres.
- Keep the Power BI file outside version control if it contains sensitive connection details.

---

## Suggested report names

- `QuantivaIQ Executive Overview`
- `QuantivaIQ Customer Intelligence`
- `QuantivaIQ Fraud & Risk`
- `QuantivaIQ Inventory Health`
- `QuantivaIQ Operational Insights`
