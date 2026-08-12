# QuantivaIQ Power BI Report Template

This document defines a complete Power BI report built on the QuantivaIQ PostgreSQL warehouse. Use it to construct the report manually in Power BI Desktop, then connect it to the same database used by the Python backend.

---

## Data Sources

Use these views and tables as your report sources:

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

> Recommended: import only the materialized views and the customer/product master tables first. Use `orders`/`order_items` only when you need detailed drill-down.

---

## Model Relationships

Create the following model relationships in Power BI Model view:

- `orders[customer_id]` → `customers[customer_id]`
- `orders[order_id]` → `order_items[order_id]`
- `order_items[product_id]` → `products[product_id]`
- `customer_segments[customer_id]` → `customers[customer_id]`
- `fraud_logs[customer_id]` → `customers[customer_id]`
- `fraud_logs[order_id]` → `orders[order_id]`
- `mv_customer_kpis[customer_id]` → `customers[customer_id]` (optional)
- `mv_product_performance[product_id]` → `products[product_id]` (optional)

For a clean model, treat `customers` and `products` as dimension tables and the materialized views as analytical fact tables.

---

## Report Settings

- Connection mode: **DirectQuery**
- Auto page refresh: **enabled** (recommended interval: 5 seconds in development)
- Date table: create a `Date` table from `orders[order_date]` or use the report-level date table in Power BI
- Use the `refresh_powerbi_views.py` helper when new data is written directly to PostgreSQL and you need fresh aggregates

---

## Page 1 — Executive Overview

### Page Layout

1. Top KPI cards
2. Line chart trend
3. Regional revenue map/bar
4. Product profitability visual
5. Customer summary table

### KPI cards

- `Total Revenue`
  - `SUM(orders[total_amount])`
- `MoM Growth %`
  - `DIVIDE([Total Revenue] - [PM Revenue], [PM Revenue], 0)`
- `AOV`
  - `DIVIDE([Total Revenue], DISTINCTCOUNT(orders[order_id]))`
- `YTD Revenue`
  - `TOTALYTD([Total Revenue], 'Date'[Date])`
- `Gross Profit`
  - `SUMX(order_items, order_items[quantity] * (order_items[unit_price] - RELATED(products[cost_price])))`
- `Profit Margin %`
  - `DIVIDE([Gross Profit], [Total Revenue], 0)`

### Visuals

- Line chart: `mv_daily_revenue[order_date]` vs `Total Revenue`
- Bar chart: `orders[region]` vs `Total Revenue`
- Treemap: `products[product_name]` vs `Gross Profit`
- Matrix / table: `mv_customer_kpis` with `customer_id`, `name`, `total_orders`, `total_spend`, `avg_order_value`

### Filters and slicers

- Date range slicer on `mv_daily_revenue[order_date]`
- Region slicer on `orders[region]`
- Product category or product name slicer (from `products`)

---

## Page 2 — Customer Intelligence

### Page Layout

1. Customer engagement KPI cards
2. Segment distribution visual
3. Customer segment table
4. Churn and retention trend

### KPI cards

- `Total Customers`
  - `DISTINCTCOUNT(customers[customer_id])`
- `Active Customers 30D`
  - `CALCULATE(DISTINCTCOUNT(orders[customer_id]), orders[order_date] >= TODAY() - 30)`
- `New Customers`
  - `CALCULATE(DISTINCTCOUNT(customers[customer_id]), customers[registration_date] >= DATEADD(LASTDATE('Date'[Date]), -1, MONTH))`
- `Retention Rate %`
  - `DIVIDE([Active Customers 30D], [Total Customers], 0)`
- `Churn Rate %`
  - `1 - [Retention Rate %]`
- `Avg CLTV`
  - `DIVIDE([Total Revenue], [Total Customers])`

### Visuals

- Donut chart: `customer_segments[segment_name]`
- Bar chart: customer counts by `segment_name`
- Table: `customer_segments` with `customer_id`, `segment_name`, `rfm_score`, `recency`, `frequency`, `monetary`
- Line chart: New customers over time by `orders[order_date]`

---

## Page 3 — Fraud & Risk

### Page Layout

1. Fraud KPI cards
2. Fraud type breakdown
3. Risk trend chart
4. Fraud log table

### KPI cards

- `Total Fraud Txns`
  - `COUNTROWS(fraud_logs)`
- `Fraud Rate %`
  - `DIVIDE([Total Fraud Txns], COUNTROWS(orders), 0)`
- `Value at Risk`
  - `CALCULATE(SUM(orders[total_amount]), USERELATIONSHIP(orders[order_id], fraud_logs[order_id]))`
- `High Risk Customers`
  - `CALCULATE(DISTINCTCOUNT(fraud_logs[customer_id]), fraud_logs[risk_score] >= 80)`
- `Avg Risk Score`
  - `AVERAGE(fraud_logs[risk_score])`
- `Total Refunds`
  - `SUM(refunds[refund_amount])`
- `Refund Rate %`
  - `DIVIDE([Total Refunds], [Total Revenue], 0)`

### Visuals

- Bar chart: `fraud_logs[fraud_type]` vs count of fraud incidents
- Line chart: `fraud_logs[detection_date]` vs `fraud_incidents` or average risk
- Table: `fraud_logs` filtered for `risk_score >= 80`
- Region chart: `orders[region]` vs `Fraud Rate %`

---

## Page 4 — Inventory & Product Performance

### Page Layout

1. Inventory KPI cards
2. Product revenue table
3. Stock status chart
4. Low-stock alert list

### KPI cards

- `Total Units Sold`
  - `SUM(order_items[quantity])`
- `Total Inventory Value`
  - `SUMX(products, products[stock_quantity] * products[cost_price])`
- `Out of Stock Items`
  - `CALCULATE(COUNTROWS(products), products[stock_quantity] <= 0)`
- `Low Stock Items`
  - `CALCULATE(COUNTROWS(products), products[stock_quantity] <= products[reorder_level])`
- `Inventory Turnover`
  - `DIVIDE(SUM(order_items[quantity]), AVERAGE(products[stock_quantity]), 0)`

### Visuals

- Bar chart: `mv_inventory_status[product_name]` vs `quantity_on_hand`
- Gauge card: `Inventory Turnover`
- Table: `mv_product_performance` with `product_name`, `category_name`, `total_units_sold`, `total_revenue`
- Table: `products` with `stock_quantity`, `reorder_level`, and low stock warning

---

## Optional Page 5 — Executive Forecasts

Use this page if you want a forecast view using the Python forecasting models from the repo.

### Visuals

- Forecast line charts for future demand
- Forecast revenue trend using `orders[order_date]` and historical totals
- Key metrics for forecast accuracy and horizon

---

## DAX Measure Library

### Standard KPI measures

```dax
Total Revenue = SUM(orders[total_amount])

PM Revenue = CALCULATE([Total Revenue], PREVIOUSMONTH('Date'[Date]))

MoM Growth % = DIVIDE([Total Revenue] - [PM Revenue], [PM Revenue], 0)

AOV = DIVIDE([Total Revenue], DISTINCTCOUNT(orders[order_id]))

Gross Profit = SUMX(order_items,
    order_items[quantity] * (order_items[unit_price] - RELATED(products[cost_price])))

Profit Margin % = DIVIDE([Gross Profit], [Total Revenue], 0)

YTD Revenue = TOTALYTD([Total Revenue], 'Date'[Date])

Total Discount = SUM(order_items[discount])
```

### Customer measures

```dax
Total Customers = DISTINCTCOUNT(customers[customer_id])

Active Customers 30D = CALCULATE(
    DISTINCTCOUNT(orders[customer_id]),
    orders[order_date] >= TODAY() - 30)

New Customers = CALCULATE(
    DISTINCTCOUNT(customers[customer_id]),
    customers[registration_date] >= DATEADD(LASTDATE('Date'[Date]), -1, MONTH))

Retention Rate % = DIVIDE([Active Customers 30D], [Total Customers], 0)

Churn Rate % = 1 - [Retention Rate %]

Repeat Purchase Rate =
VAR CustomersWithMultipleOrders =
    FILTER(VALUES(orders[customer_id]),
        CALCULATE(COUNT(orders[order_id])) > 1)
RETURN DIVIDE(COUNTROWS(CustomersWithMultipleOrders), [Total Customers])

Avg CLTV = DIVIDE([Total Revenue], [Total Customers])
```

### Fraud measures

```dax
Total Fraud Txns = COUNTROWS(fraud_logs)

Fraud Rate % = DIVIDE([Total Fraud Txns], COUNTROWS(orders), 0)

Value at Risk = CALCULATE(
    SUM(orders[total_amount]),
    USERELATIONSHIP(orders[order_id], fraud_logs[order_id]))

High Risk Customers = CALCULATE(
    DISTINCTCOUNT(fraud_logs[customer_id]),
    fraud_logs[risk_score] >= 80)

Avg Risk Score = AVERAGE(fraud_logs[risk_score])

Total Refunds = SUM(refunds[refund_amount])

Refund Rate % = DIVIDE([Total Refunds], [Total Revenue], 0)
```

### Inventory measures

```dax
Total Units Sold = SUM(order_items[quantity])

Total Inventory Value = SUMX(products,
    products[stock_quantity] * products[cost_price])

Out of Stock Items = CALCULATE(
    COUNTROWS(products),
    products[stock_quantity] <= 0)

Low Stock Items = CALCULATE(
    COUNTROWS(products),
    products[stock_quantity] <= products[reorder_level])

Inventory Turnover = DIVIDE(
    SUM(order_items[quantity]),
    AVERAGE(products[stock_quantity]), 0)

Top Product Revenue = MAXX(VALUES(products[product_name]), [Total Revenue])
```

### UI helpers

```dax
MoM Color = IF([MoM Growth %] > 0, "Green", "Red")

Risk Color = SWITCH(TRUE(),
    [Avg Risk Score] >= 80, "#FF0000",
    [Avg Risk Score] >= 50, "#FFA500",
    "#00FF00")

Dashboard Title = "QuantivaIQ Analytics - " & FORMAT(TODAY(), "MMMM YYYY")
```

---

## How to integrate with QuantivaIQ code

### Step 1: Connect Power BI to the same database backend

Update `.env` in the repo to point to your PostgreSQL environment.

Example for local PostgreSQL:

```text
DB_DRIVER=postgres
DB_HOST=localhost
DB_PORT=5432
DB_NAME=quantivaiq
DB_USER=postgres
DB_PASSWORD=postgres
```

If your database is hosted in Google Cloud SQL or on a Google domain, set:

```text
DB_DRIVER=postgres
DB_HOST=<google-cloud-sql-ip-or-hostname>
DB_PORT=5432
DB_NAME=quantivaiq
DB_USER=<your_user>
DB_PASSWORD=<your_password>
```

Then run:

```bash
python python/db_setup.py
python python/etl_pipeline.py
```

### Step 2: If using Google Cloud SQL

- Use a **public IP** or **private IP** for your Cloud SQL instance.
- Authorize your Power BI Desktop IP in Cloud SQL authorized networks.
- Optionally use **Cloud SQL Proxy** if you cannot expose a public IP.
- If using private IP, ensure Power BI has network access via VPN or gateway.

### Step 3: Build the Power BI report

1. Open Power BI Desktop.
2. Select **Get Data > PostgreSQL database**.
3. Enter server/DB credentials.
4. Set **Data Connectivity Mode** to **DirectQuery**.
5. Load the views and tables listed above.
6. Build pages using the template in this file.

### Step 4: Keep the report live

- Enable page refresh in Power BI (recommended 5s for development).
- If the Python simulator is running, use the `live_data_generator.py` process to insert live transactions.
- Refresh materialized views after bulk updates with:

```bash
python python/refresh_powerbi_views.py
```

### Step 5: Use the report with Google domain / on-prem gateway

If your PostgreSQL database is not directly reachable by Power BI Desktop or Service, use one of these:

- **On-premises data gateway**: install on a machine that can reach the DB host and configure Power BI Service to use it.
- **Cloud SQL Proxy**: run locally and connect Power BI Desktop to `localhost:5432` while proxy is active.
- **Private network/VPN**: ensure the machine running Power BI can access the database host.

---

## File references

- `python/config.py` — database connection settings
- `python/db_setup.py` — schema creation and DB init
- `python/etl_pipeline.py` — loads data and refreshes views
- `python/live_data_generator.py` — live transactions for DirectQuery
- `python/refresh_powerbi_views.py` — refreshes PostgreSQL materialized views
- `docker-compose.yml` — local PostgreSQL + app services
- `deploy.bat` / `deploy.ps1` — helpful local deployment scripts

---

## Notes

- This repo does not include a `.pbix` file.
- Use this template to manually build the report in Power BI Desktop.
- Once built, save the report locally and use the same database connection for live Power BI integration.
