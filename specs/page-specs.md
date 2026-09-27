# Page specs: how to build each page in Power BI

Canvas 1600 × 900 · theme [`theme/portfolio-theme.json`](../theme/portfolio-theme.json) (View → Themes → Browse) · page background `#F3F2F1`, cards white with a soft shadow, 4 px coloured top border on KPI cards.

Measures come from [DAX-Measures-Library](https://github.com/Shashan4321/DAX-Measures-Library) and the models in [sales-intelligence-powerbi](https://github.com/Shashan4321/sales-intelligence-powerbi) and [fabric-lakehouse-end-to-end](https://github.com/Shashan4321/fabric-lakehouse-end-to-end).

## 1 · Executive Sales Overview

| Area | Visual | Fields / measures |
|---|---|---|
| Slicers | Tile slicers | Year, Country, Channel, Category |
| KPI row | 5 cards (new card visual, reference label = vs PY) | `Total Revenue` + `Revenue YoY %`; `Orders`; `Avg Order Value`; `Gross Margin %`; `Active Customers` |
| Trend | Line and clustered column | Axis `dim_date[month_name]`; columns `Total Revenue`; line `Revenue PY` |
| Category | Bar, data labels | `dim_product[category]`, `Total Revenue`, label = `Revenue YoY %` |
| Geography | Treemap with drill-down | `Geography` hierarchy (Country → State → City → Store), `Total Revenue`, tooltip `Revenue Share of Parent` |
| Channel | Donut | `fact_sales[channel]`, `Total Revenue` |
| Insight | Smart narrative / text box | festive share of revenue |

## 2 · Product Scorecard

| Visual | Fields / measures |
|---|---|
| KPI cards | `Total Revenue`, `Units Sold`, `Gross Margin %`, `Return Rate %`, distinct count of SKUs |
| Treemap | `Product` hierarchy (Category → Subcategory), `Total Revenue` |
| Table with data bars | Top N filter on `product_name` by `Total Revenue` (N = 10); columns revenue, `Gross Margin %` |
| Scatter | X `Total Revenue` (log), Y `Gross Margin %`, size `Units Sold`, details `subcategory` |
| Column | `category`, `Return Rate %`; conditional colour on max |

## 3 · HR Analytics: Headcount & Attrition

| Visual | Fields / measures |
|---|---|
| KPI cards | `Headcount (end of period)`, `Hires`, `Exits` + `% Voluntary`, `Attrition Rate = DIVIDE([Exits], [Avg Headcount])`, `% Women` + avg tenure |
| Combo | Hires (positive) and exits (negative) columns by month, `Headcount` line on secondary axis |
| Bar | Attrition rate by department, conditional colour on max |
| Column | Exit rate by driver group (overtime, rating, grade, employment type) |
| Donut | Exit reasons |
| Security | RLS by manager hierarchy with `PATH` / `PATHCONTAINS` (see DAX library, section 07) |

Headcount pattern (semi-additive):
```dax
Headcount =
VAR _d = MAX ( dim_date[date] )
RETURN
    CALCULATE (
        COUNTROWS ( dim_employee ),
        dim_employee[hire_date] <= _d,
        OR ( ISBLANK ( dim_employee[exit_date] ), dim_employee[exit_date] > _d ),
        REMOVEFILTERS ( dim_date )
    )
```

## 4 · Supply Chain & Inventory (Direct Lake model)

| Visual | Fields / measures |
|---|---|
| KPI cards | `OTIF %` (target line 85%), `On-Time %`, `In-Full %`, median lead time, `Closing Stock Value` |
| Line | OTIF / on-time / in-full by order month, constant line at 85% |
| Table | Suppliers sorted by `Supplier OTIF Rank`, conditional formatting OTIF < 60% red |
| Histogram | `lead_time_days` binned (bin size 2 days) |
| Stacked bar | `warehouse_name` × `category`, `Closing Stock Value` |

## 5 · Customer Retention & Churn Risk

| Visual | Fields / measures |
|---|---|
| KPI cards | active customers, churn rate, month-3 retention, model ROC-AUC, at-risk lifetime value |
| Matrix heat map | cohort quarter × months since first purchase, % retained, background colour scale |
| Bar | SHAP mean \|value\| by feature (imported from the churn model output) |
| Line and column | RFM segment: customers (columns) and churn % (line) |
