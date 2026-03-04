import os
import csv
from dataclasses import dataclass, field
from typing import Any

import pandas as pd
import chardet

from core.engine import select_engine, read_file
from utils.logger import get_logger

logger = get_logger(__name__)


@dataclass
class DataProfile:
    columns: list[str]
    row_count: int
    numeric_columns: list[str]
    categorical_columns: list[str]
    date_columns: list[str]
    missing_count: int = 0
    duplicate_count: int = 0
    source_info: dict = field(default_factory=dict)


@dataclass
class LoadSuccess:
    df: Any
    file_path: str
    file_name: str
    file_size_bytes: int
    row_count: int
    col_count: int
    engine: str
    sheet_name: str | None


@dataclass
class SheetSelectionRequired:
    file_path: str
    sheets: list[str]


@dataclass
class LoadError:
    file_path: str
    error_type: str      # "not_found"|"unsupported_format"|"encoding_error"|"empty_file"|"corrupt"
    user_message: str


LoadResult = LoadSuccess | SheetSelectionRequired | LoadError


def sanitize_path(raw: str) -> str:
    """Strip whitespace and surrounding quotes. Call on ALL user-provided paths."""
    return raw.strip().strip('"').strip("'").strip()


def load(file_path: str, sheet_name: str | None = None) -> LoadResult:
    """
    Load CSV or Excel. Never raises - returns LoadError on failure.

    CSV encoding chain: utf-8 -> utf-8-sig -> chardet auto -> latin-1
    CSV delimiter: try comma, semicolon, tab, pipe (csv.Sniffer on first 8KB)
    Excel single sheet: auto-load
    Excel multiple sheets: return SheetSelectionRequired
    """
    try:
        file_path = sanitize_path(file_path)

        if not os.path.exists(file_path):
            return LoadError(file_path, "not_found", f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in (".csv", ".xlsx", ".xls", ".tsv"):
            return LoadError(file_path, "unsupported_format",
                             f"Unsupported format: {ext}. Use CSV or Excel.")

        file_size = os.path.getsize(file_path)
        file_name = os.path.basename(file_path)

        if ext in (".xlsx", ".xls"):
            return _load_excel(file_path, file_name, file_size, sheet_name)
        else:
            return _load_csv(file_path, file_name, file_size)

    except Exception as e:
        logger.error(f"Unexpected error loading {file_path}: {e}")
        return LoadError(file_path, "corrupt", f"Failed to load file: {e}")


def _load_excel(file_path: str, file_name: str, file_size: int,
                sheet_name: str | None) -> LoadResult:
    try:
        xl = pd.ExcelFile(file_path)
        sheets = xl.sheet_names

        if len(sheets) > 1 and sheet_name is None:
            return SheetSelectionRequired(file_path, sheets)

        target_sheet = sheet_name or sheets[0]
        engine_name = select_engine(file_path)
        df, engine_name = read_file(file_path, target_sheet)

        if df.empty:
            return LoadError(file_path, "empty_file", "File is empty (no data rows).")

        return LoadSuccess(
            df=df, file_path=file_path, file_name=file_name,
            file_size_bytes=file_size, row_count=len(df), col_count=len(df.columns),
            engine=engine_name, sheet_name=target_sheet,
        )
    except Exception as e:
        logger.error(f"Excel load error: {e}")
        return LoadError(file_path, "corrupt", f"Failed to read Excel: {e}")


def _load_csv(file_path: str, file_name: str, file_size: int) -> LoadResult:
    # Try encoding chain
    encodings = ["utf-8", "utf-8-sig"]

    # Detect encoding with chardet
    try:
        with open(file_path, "rb") as f:
            raw = f.read(min(file_size, 100_000))
        detected = chardet.detect(raw)
        if detected and detected.get("encoding"):
            enc = detected["encoding"].lower()
            if enc not in ("utf-8", "utf-8-sig", "ascii"):
                encodings.append(enc)
    except Exception:
        pass

    encodings.append("latin-1")  # fallback that never fails

    # Detect delimiter
    delimiter = _detect_delimiter(file_path)

    for enc in encodings:
        try:
            df = pd.read_csv(file_path, encoding=enc, sep=delimiter, on_bad_lines="warn")
            if df.empty:
                return LoadError(file_path, "empty_file", "File is empty (no data rows).")

            engine_name = select_engine(file_path)
            return LoadSuccess(
                df=df, file_path=file_path, file_name=file_name,
                file_size_bytes=file_size, row_count=len(df),
                col_count=len(df.columns), engine=engine_name, sheet_name=None,
            )
        except UnicodeDecodeError:
            continue
        except Exception as e:
            logger.error(f"CSV load with encoding {enc} failed: {e}")
            continue

    return LoadError(file_path, "encoding_error",
                     "Could not read file with any known encoding.")


def _detect_delimiter(file_path: str) -> str:
    """Detect CSV delimiter using csv.Sniffer on first 8KB."""
    try:
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            sample = f.read(8192)
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        return dialect.delimiter
    except Exception:
        return ","
