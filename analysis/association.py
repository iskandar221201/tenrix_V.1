import pandas as pd
import numpy as np
import plotly.graph_objects as go
from analysis.statistics import AnalysisResult
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


def run_market_basket(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        from mlxtend.frequent_patterns import apriori, association_rules

        # Detect transaction ID and item columns
        tid_col = None
        item_col = None
        cols_lower = {c.lower().replace("_", "").replace(" ", ""): c for c in df.columns}

        for lc, orig in cols_lower.items():
            if any(kw in lc for kw in ["transactionid", "orderid", "basketid", "invoiceno", "invoiceid", "tid"]):
                tid_col = orig
            if any(kw in lc for kw in ["item", "product", "productname", "itemname", "description", "stockcode"]):
                item_col = orig

        if not tid_col or not item_col:
            return AnalysisResult(
                analysis_name="Market Basket Analysis", analysis_id="market_basket",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["market_basket"],
                interpretation=None, warning=None, error="Need transaction_id and item columns",
            )

        # Build transaction-item matrix
        basket = df.groupby([tid_col, item_col]).size().unstack(fill_value=0)
        basket = basket.map(lambda x: 1 if x > 0 else 0).astype(bool)

        freq_items = apriori(basket, min_support=0.01, use_colnames=True)
        if freq_items.empty:
            return AnalysisResult(
                analysis_name="Market Basket Analysis", analysis_id="market_basket",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["market_basket"],
                interpretation=None, warning=None, error="No frequent itemsets found. Try lowering min_support.",
            )

        rules = association_rules(freq_items, metric="confidence", min_threshold=0.3)
        rules = rules[rules["lift"] >= 1.0].sort_values("lift", ascending=False)

        summary = {
            "Transactions": int(basket.shape[0]),
            "Unique Items": int(basket.shape[1]),
            "Frequent Itemsets": len(freq_items),
            "Rules Found": len(rules),
        }

        for i, (_, row) in enumerate(rules.head(3).iterrows()):
            ant = ", ".join(list(row["antecedents"]))
            con = ", ".join(list(row["consequents"]))
            summary[f"#{i+1} Rule"] = f"{ant} -> {con} (lift={row['lift']:.2f})"

        charts = []
        if len(rules) > 0:
            top = rules.head(15)
            labels = [f"{', '.join(list(r['antecedents']))} -> {', '.join(list(r['consequents']))}"
                      for _, r in top.iterrows()]
            fig = go.Figure(go.Bar(x=top["lift"].values, y=labels, orientation="h"))
            fig.update_layout(title="Top Association Rules by Lift", xaxis_title="Lift", height=400)
            charts.append(fig)
        else:
            fig = go.Figure(go.Bar(x=["No rules"], y=[0]))
            fig.update_layout(title="No Association Rules Found")
            charts.append(fig)

        data = {"n_rules": len(rules), "n_itemsets": len(freq_items)}

        return AnalysisResult(
            analysis_name="Market Basket Analysis", analysis_id="market_basket",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["market_basket"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"market_basket failed: {e}")
        return AnalysisResult(
            analysis_name="Market Basket Analysis", analysis_id="market_basket",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["market_basket"],
            interpretation=None, warning=None, error=str(e),
        )
