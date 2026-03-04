
<p align="center">
<pre>
████████╗███████╗███╗   ██╗██████╗ ██╗██╗  ██╗
╚══██╔══╝██╔════╝████╗  ██║██╔══██╗██║╚██╗██╔╝
   ██║   █████╗  ██╔██╗ ██║██████╔╝██║ ╚███╔╝ 
   ██║   ██╔══╝  ██║╚██╗██║██╔══██╗██║ ██╔██╗ 
   ██║   ███████╗██║ ╚████║██║  ██║██║██╔╝ ██╗
   ╚═╝   ╚══════╝╚═╝  ╚═══╝╚═╝  ╚═╝╚═╝╚═╝  ╚═╝
</pre>
</p>

<p align="center">
  <strong>Ask questions. Get insights. No code required.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python&logoColor=white" alt="Python">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/status-experimental-orange?style=flat-square" alt="Status">
  <img src="https://img.shields.io/badge/AI-Gemini%20%7C%20OpenAI%20%7C%20Groq%20%7C%20Ollama-purple?style=flat-square" alt="AI Providers">
  <img src="https://img.shields.io/badge/methods-25+-blueviolet?style=flat-square" alt="Methods">
  <img src="https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey?style=flat-square" alt="Platform">
</p>

---

**Tenrix** is a CLI-based data analysis tool that combines 25+ statistical methods with artificial intelligence.

Type a question in plain language — Tenrix automatically builds an analysis plan, runs the appropriate statistics, and delivers an AI interpretation with charts and a ready-to-share PDF report.

```
> Why did sales dip in Q3?
> Which customer segment drives the most revenue?
> Forecast the next 90 days of transactions.
```

---

## ✨ Key Features

| Feature | Description |
| :--- | :--- |
| 🗣️ **Natural Language Interface** | No SQL or Python needed. Just ask. |
| 🧠 **Auto-Planner** | Dynamically selects the best statistical method for your question. |
| 📊 **25+ Statistical Methods** | From descriptive stats to time series forecasting and clustering. |
| 📄 **PDF Report Export** | Presentation-ready reports with charts and AI interpretation. |
| 🔌 **Multi-Provider AI** | Gemini, OpenAI, Groq, OpenRouter, or fully offline via Ollama. |
| 🗄️ **Multi-Source Data** | CSV, Excel, SQLite, and SQL Dumps — all supported. |

---

## 📊 Analytical Capabilities

Powered by industry-standard libraries: `scipy`, `statsmodels`, `scikit-learn`, `prophet`, and `polars`.

| Category | Methods |
| :--- | :--- |
| **Descriptive** | Summary Stats, Correlation, T-Tests, ANOVA, Chi-Square, Mann-Whitney U |
| **Regression** | Linear, Logistic, Polynomial |
| **Clustering** | K-Means, DBSCAN, Hierarchical |
| **Time Series** | ARIMA, Prophet Forecasting, Granger Causality |
| **Dimensionality** | PCA, t-SNE, UMAP |
| **Anomaly Detection** | Isolation Forest, Z-Score |
| **Business** | Pareto (80/20), Cohort Analysis, Market Basket Analysis |
| **Survival** | Kaplan-Meier |
| **Custom** | AI-Driven Logic & Pattern Discovery |

---

## 🛠️ Getting Started

### Prerequisites

- **Python 3.10+** — [Download here](https://python.org)
- **An API key** — Tenrix will guide you through setup on first run.
  - [Gemini](https://aistudio.google.com) — Free tier available
  - [Groq](https://console.groq.com) — Free tier available
  - [OpenAI](https://platform.openai.com) — Paid
  - **No API key?** Use [Ollama](https://ollama.com) for fully offline, free AI.

#### PDF Export — System Dependencies

PDF export requires system libraries depending on your OS. **Skip this section if you don't need PDF export.**

<details>
<summary><strong>Linux (Ubuntu/Debian)</strong></summary>

```bash
sudo apt install libpango-1.0-0 libpangocairo-1.0-0 libgdk-pixbuf2.0-0
```
</details>

<details>
<summary><strong>macOS</strong></summary>

```bash
brew install pango gdk-pixbuf libffi
```
</details>

<details>
<summary><strong>Windows</strong></summary>

Download and install [GTK3-Runtime](https://github.com/tschoonj/GTK-for-Windows-Runtime-Environment-Installer/releases).
</details>

---

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/iskandar221201/tenrix_V.1.git
cd tenrix_V.1

# 2. Install dependencies
pip install -r requirements.txt

# 3. Run Tenrix — API key setup will be guided on first launch
python main.py
```

---

## 🏗️ Architecture

```
tenrix/
├── tui/         # Terminal UI — built with rich & prompt_toolkit
├── ai/          # AI routing, planning & interpretation (Gemini, OpenAI, Groq, Ollama)
├── analysis/    # Statistical core — pandas, polars, duckdb, scipy
├── core/        # Session management & data connectors
├── export/      # PDF, Excel & PNG report generation
└── utils/       # Logging & configuration
```

---

## 🛡️ License

Distributed under the MIT License. See `LICENSE` for more information.

---

<p align="center">
  Built with ❤️ for Data Scientists and Business Analysts.
</p>
