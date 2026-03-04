"""
core/connectors.py
==================
Tenrix multi-source data connector.

Sources:
  CSV      — .csv, .tsv
  Excel    — .xlsx, .xls, .xlsm        (multi-sheet, pilih atau merge semua)
  SQLite   — .db, .sqlite, .sqlite3    (read-only, multi-table, JOIN via DuckDB)
  SQL Dump — .sql                      (export dari MySQL / PostgreSQL / MariaDB)

SourceResult fields:
  .dataframes   dict[name, DataFrame]   satu per sheet/tabel
  .merged       DataFrame               semua sheet digabung + kolom __source__
  .source_type  "csv" | "excel" | "sqlite" | "sql_dump"
  .sheet_names  list[str]               sheet/tabel yang dimuat
  .file_path    str
  .meta         dict

JOIN query (sqlite + sql_dump):
  result.run_query(sql)  — DuckDB, semua DataFrame sebagai virtual table
  result.table_schemas() — string schema semua tabel, untuk AI prompt
"""

from __future__ import annotations

import os
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

import duckdb
import pandas as pd
from rich import box
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

console = Console()

EXCEL_EXTS   = {".xlsx", ".xls", ".xlsm", ".xlsb"}
SQLITE_EXTS  = {".db", ".sqlite", ".sqlite3"}
CSV_EXTS     = {".csv", ".tsv"}
SQLDUMP_EXTS = {".sql"}


# ─────────────────────────────────────────────────────────────────────────────
# SourceResult
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class SourceResult:
    dataframes:  dict[str, pd.DataFrame]
    merged:      pd.DataFrame
    source_type: str
    sheet_names: list[str]
    file_path:   str
    meta:        dict = field(default_factory=dict)

    def run_query(self, sql: str) -> pd.DataFrame:
        """
        Jalankan SQL query (termasuk JOIN) terhadap semua DataFrame.
        Menggunakan DuckDB in-memory — tidak menyentuh file asli.

        Tersedia untuk: sqlite, sql_dump
        Tidak tersedia untuk: csv, excel

        Contoh:
            df = result.run_query('''
                SELECT o.*, c.name, p.category
                FROM orders o
                JOIN customers c ON o.customer_id = c.id
                JOIN products  p ON o.product_id  = p.id
            ''')
        """
        if self.source_type in ("csv", "excel"):
            raise ValueError(
                "run_query() hanya tersedia untuk SQLite dan SQL dump.\n"
                "Untuk CSV/Excel, gunakan groupby='__source__' di analysis."
            )

        con = duckdb.connect()
        try:
            for name, df in self.dataframes.items():
                safe = re.sub(r"[^a-zA-Z0-9_]", "_", name)
                con.register(safe, df)
            return con.execute(sql).df()
        except Exception as e:
            raise ValueError(f"Query error: {e}\n\nSQL:\n{sql}")
        finally:
            con.close()

    def table_schemas(self) -> str:
        """
        Schema summary semua tabel sebagai string.
        Dimasukkan ke AI prompt sebagai konteks untuk JOIN query.
        """
        lines = []
        for name, df in self.dataframes.items():
            col_info = ", ".join(
                f"{c} ({str(df[c].dtype).replace('object', 'str')})"
                for c in df.columns[:8]
            )
            suffix = f"... (+{len(df.columns) - 8} more)" if len(df.columns) > 8 else ""
            lines.append(f"  {name} ({len(df):,} rows): {col_info}{suffix}")
        return "\n".join(lines)


# ─────────────────────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────────────────────

def load_source(path: str) -> SourceResult:
    """
    Auto-detect format dari extension, load data.
    path bisa relatif, absolut, atau path file yang diupload user.
    """
    p   = Path(path).resolve()
    ext = p.suffix.lower()

    if not p.exists():
        raise FileNotFoundError(
            f"File tidak ditemukan: {path}\n"
            f"Pastikan path benar atau file sudah diupload."
        )

    if ext in CSV_EXTS:       return _load_csv(str(p))
    if ext in EXCEL_EXTS:     return _load_excel(str(p))
    if ext in SQLITE_EXTS:    return _load_sqlite(str(p))
    if ext in SQLDUMP_EXTS:   return _load_sql_dump(str(p))

    raise ValueError(
        f"Format tidak didukung: '{ext}'\n"
        f"Didukung: CSV {CSV_EXTS}, Excel {EXCEL_EXTS}, "
        f"SQLite {SQLITE_EXTS}, SQL Dump {SQLDUMP_EXTS}"
    )


# ─────────────────────────────────────────────────────────────────────────────
# CSV
# ─────────────────────────────────────────────────────────────────────────────

def _load_csv(path: str) -> SourceResult:
    sep = "\t" if path.endswith(".tsv") else ","
    try:
        df = pd.read_csv(path, sep=sep, low_memory=False)
    except Exception as e:
        raise ValueError(f"Gagal membaca CSV: {e}")

    name = Path(path).stem
    console.print(
        f"[green]✅ CSV loaded:[/green] {os.path.basename(path)}  "
        f"[dim]{len(df):,} rows × {len(df.columns)} cols[/dim]"
    )
    return SourceResult(
        dataframes  = {name: df},
        merged      = df,
        source_type = "csv",
        sheet_names = [name],
        file_path   = path,
        meta        = {"rows": len(df), "columns": list(df.columns)},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Excel (multi-sheet)
# ─────────────────────────────────────────────────────────────────────────────

def _load_excel(path: str) -> SourceResult:
    console.print(f"\n[blue]📊 Reading Excel:[/blue] {os.path.basename(path)}")

    try:
        xl         = pd.ExcelFile(path)
        all_sheets = xl.sheet_names
    except Exception as e:
        raise ValueError(f"Gagal membuka Excel: {e}")

    if not all_sheets:
        raise ValueError("File Excel tidak memiliki sheet.")

    # Load semua sheet dulu untuk preview row counts
    sheet_data: dict[str, pd.DataFrame] = {}
    for name in all_sheets:
        try:
            df = pd.read_excel(path, sheet_name=name)
            df.columns = [str(c).strip() for c in df.columns]
            sheet_data[name] = df
        except Exception:
            sheet_data[name] = pd.DataFrame()

    _print_source_table(
        title = "Sheet tersedia / Available Sheets",
        items = [(n, len(df), list(df.columns)) for n, df in sheet_data.items()],
    )

    n   = len(all_sheets)
    raw = _ask_selection(n, label="Sheet")
    indices        = _parse_selection(raw, n)
    selected_names = [all_sheets[i] for i in indices]

    dataframes: dict[str, pd.DataFrame] = {}
    for name in selected_names:
        df = sheet_data.get(name, pd.DataFrame())
        if not df.empty:
            dataframes[name] = df
            console.print(
                f"  [green]✓[/green] [bold]{name}[/bold]  "
                f"[dim]{len(df):,} rows × {len(df.columns)} cols[/dim]"
            )
        else:
            console.print(f"  [red]✗[/red] {name}: kosong atau gagal dimuat")

    if not dataframes:
        raise ValueError("Tidak ada sheet yang berhasil dimuat.")

    merged = _merge_frames(dataframes)
    return SourceResult(
        dataframes  = dataframes,
        merged      = merged,
        source_type = "excel",
        sheet_names = selected_names,
        file_path   = path,
        meta        = {
            "total_sheets_in_file": len(all_sheets),
            "selected_sheets":      selected_names,
            "merged_rows":          len(merged),
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# SQLite (read-only, multi-table, JOIN)
# ─────────────────────────────────────────────────────────────────────────────

def _load_sqlite(path: str) -> SourceResult:
    console.print(f"\n[blue]🗄️  Reading SQLite:[/blue] {os.path.basename(path)}")
    console.print(f"[dim]   Mode: READ-ONLY[/dim]")

    try:
        uri  = f"file:{path}?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
    except Exception as e:
        raise ValueError(f"Gagal membuka SQLite (read-only): {e}")

    try:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='table' AND name NOT LIKE 'sqlite_%' "
            "ORDER BY name"
        )
        all_tables = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        conn.close()
        raise ValueError(f"Tidak bisa membaca tabel: {e}")

    if not all_tables:
        conn.close()
        raise ValueError("Database tidak memiliki tabel.")

    table_info = []
    for name in all_tables:
        try:
            cursor.execute(f'SELECT COUNT(*) FROM "{name}"')
            count = cursor.fetchone()[0]
            cursor.execute(f'PRAGMA table_info("{name}")')
            cols  = [row[1] for row in cursor.fetchall()]
            table_info.append((name, count, cols))
        except Exception:
            table_info.append((name, 0, []))

    _print_source_table("Tabel tersedia / Available Tables", table_info)

    n = len(all_tables)
    console.print(
        f"\n[bold]Opsi:[/bold]\n"
        f"  [green]all[/green]     → Load semua tabel (merge + analisis gabungan)\n"
        f"  [green]1,2[/green]     → Pilih tabel tertentu (pisah koma)\n"
        f"  [green]1-3[/green]     → Range tabel\n"
        f"  [green]1[/green]       → Satu tabel saja\n"
        f"  [green]query[/green]   → Tulis JOIN SQL query sendiri\n"
    )
    raw = Prompt.ask(
        f"[bold blue]Pilihan[/bold blue] [dim](1–{n} / all / query)[/dim]",
        default="all"
    )

    if raw.strip().lower() == "query":
        return _custom_query_sqlite(path, conn, table_info)

    indices        = _parse_selection(raw.strip(), n)
    selected_names = [all_tables[i] for i in indices]

    console.print(f"\n[dim]Loading {len(selected_names)} tabel...[/dim]")
    dataframes: dict[str, pd.DataFrame] = {}
    for name in selected_names:
        try:
            df = pd.read_sql_query(f'SELECT * FROM "{name}"', conn)
            dataframes[name] = df
            console.print(
                f"  [green]✓[/green] [bold]{name}[/bold]  "
                f"[dim]{len(df):,} rows × {len(df.columns)} cols[/dim]"
            )
        except Exception as e:
            console.print(f"  [red]✗[/red] {name}: {e}")

    conn.close()
    if not dataframes:
        raise ValueError("Tidak ada tabel yang berhasil dimuat.")

    merged = _merge_frames(dataframes)
    return SourceResult(
        dataframes  = dataframes,
        merged      = merged,
        source_type = "sqlite",
        sheet_names = selected_names,
        file_path   = path,
        meta        = {
            "total_tables":    len(all_tables),
            "selected_tables": selected_names,
            "merged_rows":     len(merged),
            "readonly":        True,
            "join_available":  True,
        },
    )


# ─────────────────────────────────────────────────────────────────────────────
# SQL Dump (.sql) — export dari MySQL / PostgreSQL / MariaDB
# ─────────────────────────────────────────────────────────────────────────────

def _load_sql_dump(path: str) -> SourceResult:
    """
    Parse SQL dump file → load semua tabel ke DuckDB in-memory → DataFrame.

    Mendukung output dari:
      mysqldump, pg_dump --inserts, phpMyAdmin, DBeaver, TablePlus, Sequel Pro

    Flow:
      1. Baca file .sql sebagai teks
      2. Bersihkan MySQL/PostgreSQL-specific syntax
      3. Parse & execute di DuckDB in-memory
      4. Export tiap tabel ke DataFrame
      5. Tampilkan tabel, tanya user pilih atau JOIN query
    """
    console.print(f"\n[blue]📄 Reading SQL Dump:[/blue] {os.path.basename(path)}")

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            sql_text = f.read()
    except Exception as e:
        raise ValueError(f"Gagal membaca file SQL: {e}")

    file_size_mb = os.path.getsize(path) / 1024 / 1024
    console.print(f"[dim]   File size: {file_size_mb:.1f} MB[/dim]")

    # Parse ke DuckDB in-memory
    con = duckdb.connect()

    try:
        cleaned    = _clean_sql_dump(sql_text)
        statements = _split_sql_statements(cleaned)

        console.print(f"[dim]   Parsing {len(statements):,} SQL statements...[/dim]")

        loaded  = 0
        skipped = 0
        errors  = 0

        first_error = None
        for stmt in statements:
            stmt  = stmt.strip()
            upper = stmt.upper().lstrip()
            if not stmt:
                continue
            if not (upper.startswith("CREATE TABLE") or
                    upper.startswith("INSERT INTO")):
                skipped += 1
                continue
            try:
                con.execute(stmt)
                loaded += 1
            except Exception as e:
                errors += 1
                if not first_error:
                    first_error = str(e)
        
        if first_error and errors > 0:
            console.print(f"[yellow]⚠ {errors} statements gagal dimuat. Error pertama:[/yellow] {first_error}")

        # List tabel hasil parsing
        rows       = con.execute(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = 'main' ORDER BY table_name"
        ).fetchall()
        all_tables = [r[0] for r in rows]

    except Exception as e:
        con.close()
        raise ValueError(f"Gagal memproses SQL dump: {e}")

    if not all_tables:
        con.close()
        raise ValueError(
            "Tidak ada tabel yang berhasil dimuat dari SQL dump.\n"
            "Pastikan file berisi CREATE TABLE dan INSERT INTO statements.\n"
            "Untuk PostgreSQL, gunakan: pg_dump --inserts mydb > dump.sql"
        )

    # Info per tabel
    table_info = []
    for name in all_tables:
        try:
            count = con.execute(f'SELECT COUNT(*) FROM "{name}"').fetchone()[0]
            cols  = [r[0] for r in con.execute(f'DESCRIBE "{name}"').fetchall()]
            table_info.append((name, count, cols))
        except Exception:
            table_info.append((name, 0, []))

    console.print(
        f"[green]✅ SQL dump parsed:[/green]  "
        f"[dim]{len(all_tables)} tabel, {loaded:,} statements berhasil"
        f"{f', {errors} gagal' if errors else ''}[/dim]"
    )

    _print_source_table("Tabel dalam SQL dump", table_info)

    n = len(all_tables)
    console.print(
        f"\n[bold]Opsi:[/bold]\n"
        f"  [green]all[/green]     → Load semua tabel\n"
        f"  [green]1,2[/green]     → Pilih tabel tertentu\n"
        f"  [green]1-3[/green]     → Range\n"
        f"  [green]query[/green]   → Tulis JOIN SQL query\n"
    )
    raw = Prompt.ask(
        f"[bold blue]Pilihan[/bold blue] [dim](1–{n} / all / query)[/dim]",
        default="all"
    )

    if raw.strip().lower() == "query":
        return _custom_query_duckdb(con, table_info, path, source_type="sql_dump")

    indices        = _parse_selection(raw.strip(), n)
    selected_names = [all_tables[i] for i in indices]

    dataframes: dict[str, pd.DataFrame] = {}
    for name in selected_names:
        try:
            df = con.execute(f'SELECT * FROM "{name}"').df()
            dataframes[name] = df
            console.print(
                f"  [green]✓[/green] [bold]{name}[/bold]  "
                f"[dim]{len(df):,} rows × {len(df.columns)} cols[/dim]"
            )
        except Exception as e:
            console.print(f"  [red]✗[/red] {name}: {e}")

    con.close()
    if not dataframes:
        raise ValueError("Tidak ada tabel yang berhasil dimuat.")

    merged = _merge_frames(dataframes)
    return SourceResult(
        dataframes  = dataframes,
        merged      = merged,
        source_type = "sql_dump",
        sheet_names = selected_names,
        file_path   = path,
        meta        = {
            "total_tables":      len(all_tables),
            "selected_tables":   selected_names,
            "merged_rows":       len(merged),
            "statements_parsed": loaded,
            "join_available":    True,
            "dump_size_mb":      round(file_size_mb, 2),
        },
    )


def _clean_sql_dump(sql: str) -> str:
    """
    Bersihkan MySQL/PostgreSQL-specific syntax agar kompatibel dengan DuckDB.
    """
    # MySQL conditional comments: /*!40101 ... */
    sql = re.sub(r'/\*!.*?\*/', '', sql, flags=re.DOTALL)

    # Block comments
    sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

    # Line comments
    sql = re.sub(r'--[^\n]*', '', sql)

    # SET statements
    sql = re.sub(r'^\s*SET\s+[^;]+;', '', sql, flags=re.MULTILINE | re.IGNORECASE)

    # LOCK/UNLOCK TABLES
    sql = re.sub(r'^\s*(LOCK|UNLOCK)\s+TABLES[^;]*;', '', sql,
                 flags=re.MULTILINE | re.IGNORECASE)

    # MySQL table options di akhir CREATE TABLE
    sql = re.sub(
        r'\b(ENGINE|DEFAULT CHARSET|CHARSET|COLLATE|AUTO_INCREMENT|'
        r'ROW_FORMAT|KEY_BLOCK_SIZE|COMMENT)\s*=\s*\S+',
        '', sql, flags=re.IGNORECASE
    )

    # MySQL backtick → double quote
    sql = re.sub(r'`([^`]+)`', r'"\1"', sql)

    # PostgreSQL COPY ... \. blocks (tidak ada --inserts)
    sql = re.sub(r'COPY\s+.*?\\\.', '', sql,
                 flags=re.DOTALL | re.IGNORECASE)

    # DROP TABLE (tidak perlu di in-memory)
    sql = re.sub(r'^\s*DROP TABLE[^;]*;', '', sql,
                 flags=re.MULTILINE | re.IGNORECASE)

    # MySQL-specific types → DuckDB compatible
    replacements = [
        (r'\bTINYINT\b',    'SMALLINT'),
        (r'\bMEDIUMINT\b',  'INTEGER'),
        (r'\bINT\b',        'BIGINT'),
        (r'\bDATETIME\b',   'TIMESTAMP'),
        (r'\bLONGTEXT\b',   'TEXT'),
        (r'\bMEDIUMTEXT\b', 'TEXT'),
        (r'\bTINYTEXT\b',   'TEXT'),
        (r'\bBLOB\b',       'TEXT'),
        (r'\bLONGBLOB\b',   'TEXT'),
        (r'\bENUM\([^)]+\)','VARCHAR'),
        (r'\bSET\([^)]+\)', 'VARCHAR'),
        (r'\bUNSIGNED\b',   ''),
        (r'\bZEROFILL\b',   ''),
    ]
    for pattern, replacement in replacements:
        sql = re.sub(pattern, replacement, sql, flags=re.IGNORECASE)

    return sql


def _split_sql_statements(sql: str) -> list[str]:
    """Split SQL teks menjadi statements by semicolon, respects string literals."""
    statements  = []
    current     = []
    in_string   = False
    string_char = None

    for char in sql:
        if in_string:
            current.append(char)
            if char == string_char:
                in_string = False
        else:
            if char in ("'", '"'):
                in_string   = True
                string_char = char
                current.append(char)
            elif char == ";":
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
            else:
                current.append(char)

    stmt = "".join(current).strip()
    if stmt:
        statements.append(stmt)

    return statements


# ─────────────────────────────────────────────────────────────────────────────
# Custom query helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_query_hint(table_info: list[tuple]) -> None:
    console.print("\n[bold blue]📝 Custom SQL Query Mode[/bold blue]")
    console.print("[dim]Schema tabel yang tersedia:[/dim]\n")
    for name, count, cols in table_info:
        col_str = ", ".join(cols[:6]) + ("..." if len(cols) > 6 else "")
        console.print(f"  [bold]{name}[/bold] ({count:,} rows)\n  [dim]  → {col_str}[/dim]\n")
    console.print(
        "[dim]Contoh JOIN query:[/dim]\n"
        "  [green]SELECT o.*, c.name FROM orders o "
        "JOIN customers c ON o.customer_id = c.id[/green]\n"
    )


def _custom_query_sqlite(
    path: str,
    conn: sqlite3.Connection,
    table_info: list[tuple],
) -> SourceResult:
    _print_query_hint(table_info)
    sql = Prompt.ask("[bold blue]SQL Query[/bold blue]")
    if not sql.strip():
        raise ValueError("Query kosong.")

    console.print(f"\n[dim]Menjalankan query...[/dim]")
    try:
        df = pd.read_sql_query(sql, conn)
    except Exception as e:
        raise ValueError(f"Query gagal: {e}")
    finally:
        conn.close()

    console.print(
        f"[green]✅ Query berhasil:[/green]  "
        f"[dim]{len(df):,} rows × {len(df.columns)} cols[/dim]"
    )
    return SourceResult(
        dataframes  = {"query_result": df},
        merged      = df,
        source_type = "sqlite",
        sheet_names = ["query_result"],
        file_path   = path,
        meta        = {"mode": "custom_query", "sql": sql,
                       "rows": len(df), "join_available": True},
    )


def _custom_query_duckdb(
    con:         duckdb.DuckDBPyConnection,
    table_info:  list[tuple],
    path:        str,
    source_type: str,
) -> SourceResult:
    _print_query_hint(table_info)
    sql = Prompt.ask("[bold blue]SQL Query[/bold blue]")
    if not sql.strip():
        raise ValueError("Query kosong.")

    console.print(f"\n[dim]Menjalankan query...[/dim]")
    try:
        df = con.execute(sql).df()
    except Exception as e:
        raise ValueError(f"Query gagal: {e}")
    finally:
        con.close()

    console.print(
        f"[green]✅ Query berhasil:[/green]  "
        f"[dim]{len(df):,} rows × {len(df.columns)} cols[/dim]"
    )
    return SourceResult(
        dataframes  = {"query_result": df},
        merged      = df,
        source_type = source_type,
        sheet_names = ["query_result"],
        file_path   = path,
        meta        = {"mode": "custom_query", "sql": sql,
                       "rows": len(df), "join_available": True},
    )


# ─────────────────────────────────────────────────────────────────────────────
# Shared helpers
# ─────────────────────────────────────────────────────────────────────────────

def _print_source_table(title: str, items: list[tuple]) -> None:
    tbl = Table(
        title=title, box=box.ROUNDED,
        border_style="blue", show_header=True, header_style="bold blue"
    )
    tbl.add_column("#",      width=4,  justify="right")
    tbl.add_column("Name",   width=26)
    tbl.add_column("Rows",   width=10, justify="right")
    tbl.add_column("Cols",   width=6,  justify="right")
    tbl.add_column("Preview columns", min_width=30)

    for i, (name, rows, cols) in enumerate(items, 1):
        preview = ", ".join(cols[:3]) + ("..." if len(cols) > 3 else "")
        tbl.add_row(
            str(i), name,
            f"{rows:,}" if rows else "?",
            str(len(cols)),
            preview or "[dim]—[/dim]",
        )
    console.print(tbl)


def _ask_selection(n: int, label: str = "Sheet") -> str:
    console.print(
        f"\n[bold]Pilih {label.lower()} untuk dianalisis:[/bold]\n"
        f"  [green]all[/green]    → Semua (merge jadi 1 DataFrame)\n"
        f"  [green]1,3[/green]    → Tertentu (pisah koma)\n"
        f"  [green]1-3[/green]    → Range\n"
        f"  [green]1[/green]      → Satu saja\n"
    )
    return Prompt.ask(
        f"[bold blue]{label}[/bold blue] [dim](1–{n} / all)[/dim]",
        default="all"
    )


def _parse_selection(raw: str, n: int) -> list[int]:
    """
    "all"   → [0..n-1]
    "1"     → [0]
    "1,3"   → [0, 2]
    "1-3"   → [0, 1, 2]
    "1,3-5" → [0, 2, 3, 4]
    """
    raw = raw.strip().lower()
    if raw in ("all", "a", ""):
        return list(range(n))

    indices = set()
    for part in raw.split(","):
        part = part.strip()
        if "-" in part:
            try:
                lo, hi = part.split("-", 1)
                for i in range(int(lo.strip()) - 1, int(hi.strip())):
                    if 0 <= i < n:
                        indices.add(i)
            except ValueError:
                pass
        else:
            try:
                i = int(part) - 1
                if 0 <= i < n:
                    indices.add(i)
            except ValueError:
                pass

    if not indices:
        console.print("[yellow]⚠ Input tidak dikenali, memuat semua.[/yellow]")
        return list(range(n))

    return sorted(indices)


def _merge_frames(dataframes: dict[str, pd.DataFrame]) -> pd.DataFrame:
    """
    Merge semua DataFrame dengan kolom __source__.
    Single frame: dikembalikan as-is (tanpa __source__).
    """
    if len(dataframes) == 1:
        return next(iter(dataframes.values())).copy()

    frames = []
    for name, df in dataframes.items():
        df_copy = df.copy()
        df_copy.insert(0, "__source__", name)
        frames.append(df_copy)

    merged = pd.concat(frames, ignore_index=True, sort=False)
    console.print(
        f"\n[green]✅ Merged {len(dataframes)} sheets/tables:[/green]  "
        f"[dim]{len(merged):,} total rows  (kolom '__source__' ditambahkan)[/dim]"
    )
    return merged


def iter_analysis_targets(result: SourceResult, mode: str = "merged"):
    """
    Yield (name, dataframe) untuk analysis engine.
    mode="merged"   → merged saja (default, dipakai sebagian besar analisis)
    mode="separate" → tiap sheet/tabel satu-satu
    mode="auto"     → merged dulu, lalu masing-masing
    """
    if len(result.dataframes) == 1:
        yield result.sheet_names[0], result.dataframes[result.sheet_names[0]]
        return

    if mode in ("merged", "auto"):
        yield "__merged__", result.merged

    if mode in ("separate", "auto"):
        for name in result.sheet_names:
            yield name, result.dataframes[name]
