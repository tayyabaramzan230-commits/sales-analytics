"""Run with:  python -m pytest -q   (or)   python tests/test_pipeline.py"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from src import analysis as an  # noqa: E402
from src.data_cleaning import load_and_clean  # noqa: E402

RAW, DF, LOG = load_and_clean(ROOT / "data" / "raw" / "Sales.xlsx")


def test_shape_and_ids():
    assert len(DF) == 1000 and DF["TransactionID"].is_unique and DF.isna().sum().sum() == 0


def test_totals_reconcile():
    assert abs(DF["NetSales"].sum() - (DF["GrossSales"].sum() - DF["DiscountAmt"].sum())) < 1
    assert abs(DF["NetSales"].sum() - RAW["Net Sales (PKR)"].sum()) < 1


def test_summaries_add_up():
    for by in ["Category", "Branch", "Year", "YearMonth"]:
        assert abs(an.summarize(DF, by)["NetSales"].sum() - DF["NetSales"].sum()) < 1


def test_pareto_ends_at_100pct():
    assert abs(an.pareto(DF, "Subcategory")["CumShare"].iloc[-1] - 1) < 1e-9


if __name__ == "__main__":
    for n, f in list(globals().items()):
        if n.startswith("test_"):
            f(); print("PASS", n)
