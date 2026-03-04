from analysis.statistics import (
    run_descriptive_stats, run_correlation, run_ttest,
    run_anova, run_chi_square, run_mann_whitney,
    AnalysisResult,
)
from analysis.regression import (
    run_linear_regression, run_logistic_regression, run_polynomial_regression,
)
from analysis.clustering import run_kmeans, run_dbscan, run_hierarchical
from analysis.time_series import run_arima, run_prophet, run_granger_causality
from analysis.dimensionality import run_pca, run_tsne, run_umap
from analysis.anomaly import run_isolation_forest, run_zscore
from analysis.survival import run_kaplan_meier
from analysis.association import run_market_basket
from analysis.business import run_pareto, run_cohort
from analysis.ai_reasoning import run_ai_custom_reasoning

ANALYSIS_REGISTRY: dict[str, callable] = {
    "descriptive_stats":        run_descriptive_stats,
    "correlation":              run_correlation,
    "ttest":                    run_ttest,
    "anova":                    run_anova,
    "chi_square":               run_chi_square,
    "mann_whitney":             run_mann_whitney,
    "regression_linear":        run_linear_regression,
    "regression_logistic":      run_logistic_regression,
    "regression_polynomial":    run_polynomial_regression,
    "clustering_kmeans":        run_kmeans,
    "clustering_dbscan":        run_dbscan,
    "clustering_hierarchical":  run_hierarchical,
    "time_series_arima":        run_arima,
    "time_series_prophet":      run_prophet,
    "granger_causality":        run_granger_causality,
    "pca":                      run_pca,
    "tsne":                     run_tsne,
    "umap":                     run_umap,
    "anomaly_isolation_forest": run_isolation_forest,
    "anomaly_zscore":           run_zscore,
    "survival_kaplan_meier":    run_kaplan_meier,
    "market_basket":            run_market_basket,
    "pareto":                   run_pareto,
    "cohort":                   run_cohort,
    "ai_custom_reasoning":      run_ai_custom_reasoning,
}
