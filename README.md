# 🛒 Sales Analytics Dashboard (Streamlit)

Interactive analysis of 1,000 retail transactions (2023-2025, 4 branches / cities, 8 categories, amounts in PKR).

## Run it
```bash
pip install -r requirements.txt
streamlit run app.py
```
or double-click `run.bat` (Windows) / run `./run.sh` (macOS/Linux). Needs Python 3.9+.

## Tabs
| Tab | Content |
|---|---|
| Overview | KPIs, auto-generated key findings, category share, branch sales, monthly trend, category→subcategory treemap |
| Trends | Seasonality by year, yearly/quarterly totals, year × month heatmap, weekday pattern |
| Products | Category sales & basket size, Pareto, top-N products, category × branch heatmap |
| Branches | Sales / transactions / basket by branch, monthly lines, branch × category mix |
| Discounts | Discount share & depth, bands, by category / branch, effect on units |
| Transactions | Basket-size distribution, ticket bands, quantity, largest transactions |
| Data & quality | Cleaning & validation log, filtered table, CSV downloads |

Sidebar filters (date range, branch, category, subcategory, discount status) drive every chart, KPI and insight.
You can upload another file with the same columns.

## Data cleaning (`src/data_cleaning.py`)
The source was already structurally clean: no duplicates, no missing values, and gross/discount/net arithmetic,
dates, city↔branch and product hierarchy all reconcile. The pipeline still enforces this (and would repair
arithmetic or drop bad rows on other files), renames columns, derives calendar and discount fields, and logs it all.
**Flag:** unit prices of the same product vary >5x for 81 of 138 products, which suggests synthetic or mis-keyed
prices. Values are kept as recorded; the dashboard focuses on revenue rather than per-SKU price.

`python -m src.data_cleaning` regenerates `data/processed/`. `python tests/test_pipeline.py` runs sanity tests.
"# sales-analytics" 
