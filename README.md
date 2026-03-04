# 🌌 Tenrix

**Tenrix** is a CLI-based data analysis tool that combines 25+ statistical methods with artificial intelligence. 

Users simply type a question in natural language — Tenrix automatically formulates an analysis plan, runs the appropriate statistics, and delivers an AI interpretation directly in the terminal.

---

## 🚀 Experience the Future of Data Analysis

Transform your raw datasets into actionable insights using simple natural language commands. Tenrix bridges the gap between complex statistical rigor and intuitive human reasoning.

### ✨ Key Features
- **Natural Language Interface**: No more complex SQL or Python scripts. Just ask: *"Why did sales dip in Q3?"*
- **Auto-Planner**: Dynamically selects the best statistical methodology for your specific data and question.
- **Deep Interpretation**: Generates human-readable summaries that explain the *why* behind the numbers.
- **Rich Visualizations**: Interactive terminal-based charts and exportable PDF reports.
- **Extensive Library**: Access to 25+ pre-configured statistical methods across 9 categories.
- **Multi-Source Support**: Seamlessly work with CSV, Excel, SQLite, and SQL Dumps.

### 📂 Supported Data Formats
- **CSV & TSV**: Standard delimited files.
- **Excel**: `.xlsx`, `.xls`, `.xlsm`, `.xlsb` (Multi-sheet support).
- **SQLite**: `.db`, `.sqlite`, `.sqlite3` (Read-only, multi-table JOIN via DuckDB).
- **SQL Dump**: `.sql` (Parsed via DuckDB for MySQL/PostgreSQL compatibility).

---

## 📊 Analytical Capabilities

Tenrix covers a wide spectrum of analytical needs, powered by industry-standard libraries like `scipy`, `statsmodels`, `scikit-learn`, `prophet`, and `polars`.

| Category | Methods Covered |
| :--- | :--- |
| **Descriptive** | Summary Stats, Correlation, T-Tests, ANOVA, Chi-Square, Mann-Whitney U |
| **Regression** | Linear, Logistic, Polynomial |
| **Clustering** | K-Means, DBSCAN, Hierarchical |
| **Time Series** | ARIMA Forecasting, Prophet, Granger Causality |
| **Dimensionality** | PCA, t-SNE, UMAP |
| **Anomaly** | Isolation Forest, Z-Score |
| **Business** | Pareto (80/20), Cohort Analysis, Market Basket Analysis |
| **Survival** | Kaplan-Meier |
| **Custom** | AI-Driven Logic & Pattern Discovery |

---

## 🛠️ Getting Started

### Prerequisites

To run Tenrix locally or build the source, you'll need:
- **Python 3.10+**
- **GTK3-Runtime** (Required for PDF export via WeasyPrint)
  - *Windows*: Download and install [GTK3-Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases) or ensure the `GTK3-Runtime/bin` folder exists in the project root.
- **API Keys** (Required for AI features):
  - `GOOGLE_API_KEY` (Gemini - Primary)
  - `OPENAI_API_KEY` (Optional)
  - `GROQ_API_KEY` (Optional)

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/iskandar221201/tenrix_V.1.git
   cd tenrix_V.1
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Configure Environment:
   You'll be prompted to enter your API keys on the first run, or you can set them in your environment variables.

### Usage

Launch the Terminal User Interface (TUI):
```bash
python main.py
```

---

## 🏗️ Architecture

Tenrix is built with a modular design for stability and ease of maintenance:
- `tui/`: Sleek, interactive terminal interface using `rich` and `prompt_toolkit`.
- `ai/`: Intelligent routing, planning, and interpretation engine (supports Gemini, OpenAI, Groq).
- `analysis/`: High-performance statistical core using `pandas`, `polars`, and `duckdb`.
- `core/`: Core logic including session management and data connectors.
- `export/`: High-quality report generation (PDF, Excel, PNG).
- `utils/`: Common utilities such as logging and configuration.

---

## 🛡️ License
Distributed under the MIT License. See `LICENSE` for more information.

---
<p align="center">
  Built with ❤️ for Data Scientists and Business Analysts.
</p>
