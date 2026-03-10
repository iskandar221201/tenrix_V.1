# Tenrix — `--columns` Flag Feature

**Versi:** 1.0.0  
**Depends on:** `core/session.py`, `core/loader.py`, `cli/cli_args.py`

---

## Gambaran Umum

Flag `--columns` memungkinkan user memilih kolom spesifik yang ingin dianalisis,
tanpa harus analisis semua kolom di file. Berguna untuk data dengan banyak kolom
tapi user hanya peduli subset tertentu.

```bash
# Analisis semua kolom (default, seperti sekarang)
tenrix run data.csv

# Analisis hanya kolom tertentu
tenrix run data.csv --columns revenue,region,product_category

# Kombinasi dengan fitur lain
tenrix run data.csv --columns revenue,date --news-auto
```

---

## File yang Perlu Diupdate

```
cli/cli_args.py       ← tambah parsing --columns
core/loader.py        ← filter kolom setelah load data
core/session.py       ← tambah selected_columns ke Session
core/profiler.py      ← profiling hanya kolom yang dipilih
main.py               ← teruskan selected_columns ke loader
```

---

## 1. `cli/cli_args.py` — Tambahan

```python
# Tambahkan ke HELP_TEXT
"""
  --columns col1,col2,col3   Analyze specific columns only
                              Example: --columns revenue,region,date
"""

# Tambahkan ke parse_args()
def parse_args(argv: list[str] | None = None) -> dict:
    # ... existing parsing ...

    # --columns
    selected_columns = None
    if "--columns" in argv:
        idx = argv.index("--columns")
        if idx + 1 < len(argv) and not argv[idx + 1].startswith("--"):
            raw = argv[idx + 1]
            selected_columns = [c.strip() for c in raw.split(",") if c.strip()]

    return {
        # ... existing keys ...
        "selected_columns": selected_columns,  # None = semua kolom
    }
```

---

## 2. `core/loader.py` — Tambahan

Tambahkan parameter `selected_columns` ke fungsi load utama:

```python
def load_data(
    source_path: str,
    selected_columns: list[str] | None = None,
) -> tuple[pd.DataFrame, list[str]]:
    """
    Load data dari file dan filter kolom jika diperlukan.

    Returns:
        df                  : DataFrame hasil load (sudah difilter)
        available_columns   : semua kolom yang ada di file asli
    """
    # Load seperti biasa dulu
    df = _load_raw(source_path)

    # Simpan semua kolom yang tersedia sebelum filter
    available_columns = df.columns.tolist()

    if selected_columns:
        # Validasi — cek kolom yang diminta ada di data
        missing = [c for c in selected_columns if c not in df.columns]
        valid   = [c for c in selected_columns if c in df.columns]

        if missing:
            # Tampilkan warning tapi tidak crash
            _warn_missing_columns(missing, available_columns)

        if not valid:
            # Semua kolom tidak ditemukan — fallback ke semua kolom
            _warn_fallback_all_columns(selected_columns)
            return df, available_columns

        df = df[valid]

    return df, available_columns


def _warn_missing_columns(missing: list[str], available: list[str]) -> None:
    """Tampilkan warning kolom tidak ditemukan + saran kolom yang ada."""
    from rich.console import Console
    from rich.panel import Panel

    console = Console()
    missing_str   = ", ".join(missing)
    available_str = ", ".join(available[:15])
    suffix = "..." if len(available) > 15 else ""

    console.print(Panel(
        f"[yellow]Kolom tidak ditemukan: [bold]{missing_str}[/bold][/yellow]\n"
        f"[dim]Kolom yang tersedia: {available_str}{suffix}[/dim]",
        border_style="yellow",
        title="⚠ Column Warning",
        padding=(0, 2),
    ))


def _warn_fallback_all_columns(requested: list[str]) -> None:
    from rich.console import Console
    console = Console()
    console.print(
        f"[yellow]⚠ Semua kolom yang diminta tidak ditemukan. "
        f"Menggunakan semua kolom.[/yellow]"
    )
```

---

## 3. `core/session.py` — Tambahan

```python
@dataclass
class Session:
    # ... field yang sudah ada ...
    selected_columns: list[str] | None = None    # None = semua kolom
    available_columns: list[str] = field(default_factory=list)  # semua kolom di file asli
```

---

## 4. `core/profiler.py` — Tambahan

Profiler perlu tahu kolom mana yang aktif agar insight tidak merujuk kolom
yang tidak dipilih user:

```python
def profile_data(
    df: pd.DataFrame,
    selected_columns: list[str] | None = None,
) -> DataProfile:
    """
    Profile data. Jika selected_columns diisi, hanya profile kolom tersebut.
    Kolom yang tidak dipilih tidak masuk ke numeric_columns / categorical_columns.
    """
    # existing profiling logic tidak berubah —
    # df yang masuk sudah difilter di loader.py,
    # jadi profiler otomatis hanya melihat kolom yang dipilih.
    # 
    # Hanya perlu tambah metadata:
    profile = _build_profile(df)
    profile.is_filtered   = selected_columns is not None
    profile.column_filter = selected_columns or []
    return profile


@dataclass
class DataProfile:
    # ... field yang sudah ada ...
    is_filtered:   bool       = False
    column_filter: list[str]  = field(default_factory=list)
```

---

## 5. `main.py` — Integrasi

```python
# Parse args
args = parse_args()
selected_columns = args.get("selected_columns")  # None atau list

# Load data dengan filter kolom
df, available_columns = load_data(
    source_path=args["file"],
    selected_columns=selected_columns,
)

# Simpan ke session
session.selected_columns  = selected_columns
session.available_columns = available_columns

# Tampilkan info ke user kalau pakai filter
if selected_columns:
    console.print(
        f"[cyan]→ Menganalisis {len(df.columns)} kolom: "
        f"{', '.join(df.columns.tolist())}[/cyan]"
    )

# Lanjut seperti biasa — profiling, analisis, export
```

---

## Contoh Output Terminal

```
$ tenrix run samsung_sales.csv --columns revenue,product_category,region

→ Menganalisis 3 kolom: revenue, product_category, region

✓ Data loaded: 15.500 rows × 3 columns
  Filtered from 24 columns (original file)

[analisis berjalan hanya untuk 3 kolom...]
```

---

## Edge Cases yang Ditangani

| Kondisi | Behaviour |
|---|---|
| `--columns` tidak dipakai | Semua kolom dianalisis (default) |
| Semua kolom valid | Filter dan analisis kolom tersebut |
| Sebagian kolom tidak ada | Warning + analisis kolom yang valid saja |
| Semua kolom tidak ada | Warning + fallback ke semua kolom |
| Nama kolom pakai spasi | Gunakan underscore: `--columns product_name` |
| Case sensitive | Kolom harus persis sama dengan nama di file |

---

## Urutan Implementasi

1. Update `cli/cli_args.py` — tambah parsing `--columns`
2. Update `core/session.py` — tambah `selected_columns` dan `available_columns`
3. Update `core/loader.py` — tambah filter + warning logic
4. Update `core/profiler.py` — tambah metadata `is_filtered`
5. Update `main.py` — teruskan `selected_columns` ke loader dan session
