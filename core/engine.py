import os
import pandas as pd
from utils.logger import get_logger

logger = get_logger(__name__)

PANDAS_LIMIT = 500 * 1024 * 1024       # 500 MB
POLARS_LIMIT = 5 * 1024 * 1024 * 1024  # 5 GB


def select_engine(file_path: str) -> str:
    """Return 'pandas' | 'polars' | 'duckdb' based on file size."""
    try:
        size = os.path.getsize(file_path)
    except OSError:
        return "pandas"

    if size <= PANDAS_LIMIT:
        return "pandas"
    elif size <= POLARS_LIMIT:
        return "polars"
    else:
        return "duckdb"


def read_file(file_path: str, sheet_name: str | None = None) -> tuple:
    """
    Load file using appropriate engine.
    Returns (pandas_DataFrame, engine_name_string).
    Always returns pandas DataFrame regardless of internal engine.
    """
    engine = select_engine(file_path)
    ext = os.path.splitext(file_path)[1].lower()

    if engine == "pandas":
        df = _read_pandas(file_path, ext, sheet_name)
    elif engine == "polars":
        df = _read_polars(file_path, ext, sheet_name)
    else:
        df = _read_duckdb(file_path, ext)

    return df, engine


def _read_pandas(file_path: str, ext: str, sheet_name: str | None = None) -> pd.DataFrame:
    if ext in (".xlsx", ".xls"):
        return pd.read_excel(file_path, sheet_name=sheet_name or 0)
    else:
        return pd.read_csv(file_path)


def _read_polars(file_path: str, ext: str, sheet_name: str | None = None) -> pd.DataFrame:
    import polars as pl
    if ext in (".xlsx", ".xls"):
        df = pl.read_excel(file_path, sheet_name=sheet_name or 0)
    else:
        df = pl.read_csv(file_path)
    return df.to_pandas()


def _read_duckdb(file_path: str, ext: str) -> pd.DataFrame:
    import duckdb
    conn = duckdb.connect()
    if ext in (".xlsx", ".xls"):
        conn.install_extension("spatial")
        conn.load_extension("spatial")
        df = conn.execute(f"SELECT * FROM st_read('{file_path}')").fetchdf()
    else:
        df = conn.execute(f"SELECT * FROM read_csv_auto('{file_path}')").fetchdf()
    conn.close()
    return df
