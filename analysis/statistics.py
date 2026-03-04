import pandas as pd
import numpy as np
from dataclasses import dataclass, field
import plotly.graph_objects as go
import plotly.express as px
from scipy import stats
from analysis.methodology import METHODOLOGY_REGISTRY
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class AnalysisResult:
    analysis_name: str
    analysis_id: str
    success: bool
    data: dict
    summary: dict
    charts: list
    methodology: object
    interpretation: str | None
    warning: str | None
    error: str | None
    confidence_score: float | None = None
    confidence_reasons: list = field(default_factory=list)


def run_descriptive_stats(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        # Apply filter if specified (for counting/filtering questions)
        filter_col = params.get("filter_column")
        filter_val = params.get("filter_value")
        
        filter_text = ""
        if filter_col and filter_col in df.columns and filter_val is not None:
            # We use string matching to be robust against types
            matched = df[filter_col].astype(str).str.contains(str(filter_val), case=False, na=False)
            df = df[matched]
            filter_text = f" (Filtered: {filter_col} ~ '{filter_val}')"

            if df.empty:
                return AnalysisResult(
                    analysis_name="Descriptive Statistics", analysis_id="descriptive_stats",
                    success=False, data={}, summary={}, charts=[],
                    methodology=METHODOLOGY_REGISTRY["descriptive_stats"],
                    interpretation=None, warning=None, error=f"No data matched filter {filter_col}='{filter_val}'",
                )

        target = params.get("target_column")
        group = params.get("group_column")

        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        categorical_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        # Validate target and group
        target = target if target in df.columns else None
        group = group if group in df.columns else None

        summary = {
            "Rows": len(df),
            "Columns": len(df.columns),
            "Numeric Columns": len(numeric_cols),
            "Categorical Columns": len(categorical_cols),
            "Missing Values": int(df.isnull().sum().sum()),
            "Duplicate Rows": int(df.duplicated().sum()),
        }
        
        if target:
            summary["Focus Column"] = target

        data = {"describe": {}}
        # Focus on target if provided, otherwise top 5
        num_to_show = [target] if target in numeric_cols else (numeric_cols[:5] if numeric_cols else [])
        if numeric_cols:
            desc = df[numeric_cols].describe()
            data["describe"] = desc.to_dict()
            for col in num_to_show:
                if col in df.columns:
                    vals = df[col].dropna()
                    if len(vals) > 0:
                        summary[f"{col} (mean)"] = f"{vals.mean():.4f}"
                        summary[f"{col} (std)"] = f"{vals.std():.4f}"

        # Include categorical column frequency data
        cat_to_show = [target] if target in categorical_cols else ([group] if group in categorical_cols else categorical_cols[:10])
        if categorical_cols:
            cat_data = {}
            for col in cat_to_show:
                if col in df.columns:
                    counts = df[col].value_counts().head(10)
                    cat_data[col] = {
                        "top_values": {str(k): int(v) for k, v in counts.items()},
                        "unique_count": int(df[col].nunique()),
                        "total_non_null": int(df[col].notna().sum()),
                    }
            data["categorical"] = cat_data

        charts = []
        
        # 1. Comparison logic if group/target both provided
        if target and group and target != group:
            if target in numeric_cols and group in categorical_cols:
                # Numeric vs Categorical -> Box Plot
                fig = px.box(df, x=group, y=target, title=f"{target} by {group}")
                charts.append(fig)
            elif target in categorical_cols and group in categorical_cols:
                # Categorical vs Categorical -> Grouped Bar
                pivot = df.groupby([group, target], observed=True).size().reset_index(name="count")
                fig = px.bar(pivot, x=group, y="count", color=target, barmode="group",
                             title=f"Distribution of {target} across {group}")
                charts.append(fig)
        
        # 2. Singular logic if only target/nothing provided or above failed
        if not charts:
            if target:
                if target in numeric_cols:
                    fig = go.Figure(go.Histogram(x=df[target].dropna(), name=target, nbinsx=30))
                    fig.update_layout(title=f"Distribution of {target}", xaxis_title=target, yaxis_title="Count")
                    charts.append(fig)
                elif target in categorical_cols:
                    counts = df[target].value_counts().head(15)
                    fig = go.Figure(go.Bar(x=counts.index.astype(str), y=counts.values, name=target))
                    fig.update_layout(title=f"Frequency of {target}", xaxis_title=target, yaxis_title="Count")
                    charts.append(fig)

        # Fallback to first available if still no charts
        if not charts:
            if numeric_cols:
                col = numeric_cols[0]
                fig = go.Figure(go.Histogram(x=df[col].dropna(), name=col, nbinsx=30))
                fig.update_layout(title=f"Distribution of {col}", xaxis_title=col, yaxis_title="Count")
                charts.append(fig)
            elif categorical_cols:
                col = categorical_cols[0]
                counts = df[col].value_counts().head(15)
                fig = go.Figure(go.Bar(x=counts.index.astype(str), y=counts.values, name=col))
                fig.update_layout(title=f"Frequency of {col}", xaxis_title=col, yaxis_title="Count")
                charts.append(fig)

        if not charts:
            fig = go.Figure(go.Bar(x=["Total Rows"], y=[len(df)]))
            fig.update_layout(title=f"Dataset Overview{filter_text}")
            charts.append(fig)

        return AnalysisResult(
            analysis_name=f"Descriptive Statistics{filter_text}", analysis_id="descriptive_stats",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["descriptive_stats"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"descriptive_stats failed: {e}")
        return AnalysisResult(
            analysis_name="Descriptive Statistics", analysis_id="descriptive_stats",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["descriptive_stats"],
            interpretation=None, warning=None, error=str(e),
        )


def run_correlation(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_df = df.select_dtypes(include=[np.number])
        if numeric_df.shape[1] < 2:
            return AnalysisResult(
                analysis_name="Correlation Analysis", analysis_id="correlation",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["correlation"],
                interpretation=None, warning=None, error="Need at least 2 numeric columns",
            )

        pearson = numeric_df.corr(method="pearson")
        spearman = numeric_df.corr(method="spearman")

        # Top correlated pairs
        pairs = []
        for i in range(len(pearson.columns)):
            for j in range(i+1, len(pearson.columns)):
                pairs.append((pearson.columns[i], pearson.columns[j], pearson.iloc[i, j]))
        pairs.sort(key=lambda x: abs(x[2]), reverse=True)

        summary = {"Numeric Columns": len(numeric_df.columns)}
        for i, (c1, c2, r) in enumerate(pairs[:5]):
            summary[f"#{i+1} {c1} vs {c2}"] = f"{r:.4f}"

        # Heatmap
        fig = go.Figure(go.Heatmap(
            z=pearson.values, x=pearson.columns.tolist(), y=pearson.columns.tolist(),
            colorscale="RdBu_r", zmid=0, text=np.round(pearson.values, 2), texttemplate="%{text}",
        ))
        fig.update_layout(title="Pearson Correlation Matrix")

        charts = [fig]

        top_pairs = []
        for c1, c2, r in pairs[:10]:
            top_pairs.append({
                "col1": str(c1),
                "col2": str(c2),
                "pearson": float(r),
                "spearman": float(spearman.loc[c1, c2])
            })

        data = {
            "pearson": pearson.to_dict(),
            "spearman": spearman.to_dict(),
            "top_pairs": top_pairs,
        }

        return AnalysisResult(
            analysis_name="Correlation Analysis", analysis_id="correlation",
            success=True, data=data, summary=summary, charts=charts,
            methodology=METHODOLOGY_REGISTRY["correlation"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"correlation failed: {e}")
        return AnalysisResult(
            analysis_name="Correlation Analysis", analysis_id="correlation",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["correlation"],
            interpretation=None, warning=None, error=str(e),
        )


def run_ttest(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        group_col = params.get("group_column")
        target_col = params.get("target_column")

        if not target_col and numeric_cols:
            target_col = numeric_cols[0]
        if not group_col and cat_cols:
            for c in cat_cols:
                if df[c].dropna().nunique() == 2:
                    group_col = c
                    break
            if not group_col and cat_cols:
                group_col = cat_cols[0]

        if not target_col or not group_col:
            return AnalysisResult(
                analysis_name="T-Test", analysis_id="ttest",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["ttest"],
                interpretation=None, warning=None, error="Need numeric target and group column",
            )

        groups = df[group_col].dropna().unique()[:2]
        g1 = df[df[group_col] == groups[0]][target_col].dropna()
        g2 = df[df[group_col] == groups[1]][target_col].dropna()

        t_stat, p_value = stats.ttest_ind(g1, g2)

        # Cohen's d
        pooled_std = np.sqrt((g1.std()**2 + g2.std()**2) / 2)
        cohens_d = (g1.mean() - g2.mean()) / pooled_std if pooled_std > 0 else 0

        summary = {
            "Test": "Independent T-Test",
            f"Group 1 ({groups[0]}) Mean": f"{g1.mean():.4f}",
            f"Group 2 ({groups[1]}) Mean": f"{g2.mean():.4f}",
            "T-Statistic": f"{t_stat:.4f}",
            "P-Value": f"{p_value:.6f}",
            "Significant (p<0.05)": "Yes" if p_value < 0.05 else "No",
            "Cohen's d": f"{cohens_d:.4f}",
        }

        fig = go.Figure()
        fig.add_trace(go.Box(y=g1, name=str(groups[0])))
        fig.add_trace(go.Box(y=g2, name=str(groups[1])))
        fig.update_layout(title=f"T-Test: {target_col} by {group_col}", yaxis_title=target_col)

        data = {"t_stat": float(t_stat), "p_value": float(p_value), "cohens_d": float(cohens_d)}

        return AnalysisResult(
            analysis_name="T-Test", analysis_id="ttest",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["ttest"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"ttest failed: {e}")
        return AnalysisResult(
            analysis_name="T-Test", analysis_id="ttest",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["ttest"],
            interpretation=None, warning=None, error=str(e),
        )


def run_anova(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        group_col = params.get("group_column")
        target_col = params.get("target_column")

        if not target_col and numeric_cols:
            target_col = numeric_cols[0]
        if not group_col:
            for c in cat_cols:
                if df[c].dropna().nunique() >= 3:
                    group_col = c
                    break

        if not target_col or not group_col:
            return AnalysisResult(
                analysis_name="ANOVA", analysis_id="anova",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["anova"],
                interpretation=None, warning=None, error="Need numeric target and group column with 3+ groups",
            )

        groups = [g[target_col].dropna().values for _, g in df.groupby(group_col)]
        f_stat, p_value = stats.f_oneway(*groups)

        # Eta-squared
        grand_mean = df[target_col].mean()
        ss_between = sum(len(g) * (np.mean(g) - grand_mean)**2 for g in groups)
        ss_total = sum((x - grand_mean)**2 for g in groups for x in g)
        eta_sq = ss_between / ss_total if ss_total > 0 else 0

        summary = {
            "Test": "One-Way ANOVA",
            "Groups": df[group_col].nunique(),
            "F-Statistic": f"{f_stat:.4f}",
            "P-Value": f"{p_value:.6f}",
            "Significant (p<0.05)": "Yes" if p_value < 0.05 else "No",
            "Eta-Squared": f"{eta_sq:.4f}",
        }

        fig = go.Figure()
        for name, group in df.groupby(group_col):
            fig.add_trace(go.Box(y=group[target_col], name=str(name)))
        fig.update_layout(title=f"ANOVA: {target_col} by {group_col}", yaxis_title=target_col)

        data = {"f_stat": float(f_stat), "p_value": float(p_value), "eta_squared": float(eta_sq)}

        return AnalysisResult(
            analysis_name="ANOVA", analysis_id="anova",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["anova"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"anova failed: {e}")
        return AnalysisResult(
            analysis_name="ANOVA", analysis_id="anova",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["anova"],
            interpretation=None, warning=None, error=str(e),
        )


def run_chi_square(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()
        if len(cat_cols) < 2:
            return AnalysisResult(
                analysis_name="Chi-Square Test", analysis_id="chi_square",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["chi_square"],
                interpretation=None, warning=None, error="Need at least 2 categorical columns",
            )

        col1 = params.get("group_column", cat_cols[0])
        col2 = params.get("target_column", cat_cols[1])

        contingency = pd.crosstab(df[col1], df[col2])
        chi2, p_value, dof, expected = stats.chi2_contingency(contingency)

        # Cramer's V
        n = contingency.sum().sum()
        min_dim = min(contingency.shape) - 1
        cramers_v = np.sqrt(chi2 / (n * min_dim)) if n * min_dim > 0 else 0

        summary = {
            "Test": "Chi-Square Test of Independence",
            "Variables": f"{col1} x {col2}",
            "Chi-Square": f"{chi2:.4f}",
            "P-Value": f"{p_value:.6f}",
            "Degrees of Freedom": dof,
            "Significant (p<0.05)": "Yes" if p_value < 0.05 else "No",
            "Cramer's V": f"{cramers_v:.4f}",
        }

        fig = go.Figure(go.Heatmap(
            z=contingency.values, x=contingency.columns.astype(str).tolist(),
            y=contingency.index.astype(str).tolist(), colorscale="Blues",
            text=contingency.values, texttemplate="%{text}",
        ))
        fig.update_layout(title=f"Contingency Table: {col1} x {col2}")

        data = {"chi2": float(chi2), "p_value": float(p_value), "cramers_v": float(cramers_v)}

        return AnalysisResult(
            analysis_name="Chi-Square Test", analysis_id="chi_square",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["chi_square"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"chi_square failed: {e}")
        return AnalysisResult(
            analysis_name="Chi-Square Test", analysis_id="chi_square",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["chi_square"],
            interpretation=None, warning=None, error=str(e),
        )


def run_mann_whitney(df: pd.DataFrame, params: dict) -> AnalysisResult:
    try:
        numeric_cols = df.select_dtypes(include=[np.number]).columns.tolist()
        cat_cols = df.select_dtypes(include=["object", "category", "string"]).columns.tolist()

        group_col = params.get("group_column")
        target_col = params.get("target_column")

        if not target_col and numeric_cols:
            target_col = numeric_cols[0]
        if not group_col:
            for c in cat_cols:
                if df[c].dropna().nunique() == 2:
                    group_col = c
                    break
            if not group_col and cat_cols:
                group_col = cat_cols[0]

        if not target_col or not group_col:
            return AnalysisResult(
                analysis_name="Mann-Whitney U Test", analysis_id="mann_whitney",
                success=False, data={}, summary={}, charts=[],
                methodology=METHODOLOGY_REGISTRY["mann_whitney"],
                interpretation=None, warning=None, error="Need numeric target and group column",
            )

        groups = df[group_col].dropna().unique()[:2]
        g1 = df[df[group_col] == groups[0]][target_col].dropna()
        g2 = df[df[group_col] == groups[1]][target_col].dropna()

        u_stat, p_value = stats.mannwhitneyu(g1, g2, alternative="two-sided")

        # Rank-biserial correlation
        n1, n2 = len(g1), len(g2)
        rbc = 1 - (2 * u_stat) / (n1 * n2) if n1 * n2 > 0 else 0

        summary = {
            "Test": "Mann-Whitney U Test",
            f"Group 1 ({groups[0]}) Median": f"{g1.median():.4f}",
            f"Group 2 ({groups[1]}) Median": f"{g2.median():.4f}",
            "U-Statistic": f"{u_stat:.4f}",
            "P-Value": f"{p_value:.6f}",
            "Significant (p<0.05)": "Yes" if p_value < 0.05 else "No",
            "Rank-Biserial Correlation": f"{rbc:.4f}",
        }

        fig = go.Figure()
        fig.add_trace(go.Box(y=g1, name=str(groups[0])))
        fig.add_trace(go.Box(y=g2, name=str(groups[1])))
        fig.update_layout(title=f"Mann-Whitney: {target_col} by {group_col}", yaxis_title=target_col)

        data = {"u_stat": float(u_stat), "p_value": float(p_value), "rbc": float(rbc)}

        return AnalysisResult(
            analysis_name="Mann-Whitney U Test", analysis_id="mann_whitney",
            success=True, data=data, summary=summary, charts=[fig],
            methodology=METHODOLOGY_REGISTRY["mann_whitney"],
            interpretation=None, warning=None, error=None,
        )
    except Exception as e:
        logger.error(f"mann_whitney failed: {e}")
        return AnalysisResult(
            analysis_name="Mann-Whitney U Test", analysis_id="mann_whitney",
            success=False, data={}, summary={}, charts=[],
            methodology=METHODOLOGY_REGISTRY["mann_whitney"],
            interpretation=None, warning=None, error=str(e),
        )
