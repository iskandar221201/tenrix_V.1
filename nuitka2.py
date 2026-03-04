import os
import sys
import shutil
import subprocess
import platform
from pathlib import Path


# ── Platform detection ────────────────────────────────────────────────────────

IS_WINDOWS = sys.platform == "win32"
IS_MAC     = sys.platform == "darwin"
IS_LINUX   = sys.platform.startswith("linux")


def get_venv_python(project_root: Path) -> Path:
    """Return path ke Python executable di dalam .venv (cross-platform)."""
    if IS_WINDOWS:
        return project_root / ".venv" / "Scripts" / "python.exe"
    else:
        return project_root / ".venv" / "bin" / "python"


def get_output_binary(dist_dir: Path) -> Path:
    """Return path ke binary hasil build (cross-platform)."""
    if IS_WINDOWS:
        return dist_dir / "main.dist" / "main.exe"
    else:
        return dist_dir / "main.dist" / "main"


def main():
    # ── STEP 0: Bootstrap — pastikan jalan dari .venv ─────────────────────────
    python_exe   = Path(sys.executable)
    project_root = Path(__file__).parent.resolve()
    venv_python  = get_venv_python(project_root)

    if venv_python.exists() and python_exe.resolve() != venv_python.resolve():
        print(f"\n[BOOTSTRAP] Not in .venv. Re-executing with: {venv_python}")
        result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        sys.exit(result.returncode)

    main_script = project_root / "main.py"
    dist_dir    = project_root / "dist_nuitka"

    if not main_script.exists():
        print(f"[ERROR] main.py tidak ditemukan di: {project_root}")
        sys.exit(1)

    # ── STEP 1: Info build ────────────────────────────────────────────────────
    print("=" * 60)
    print("  TENRIX NUITKA BUILDER")
    print(f"  Platform  : {platform.system()} {platform.machine()}")
    print(f"  Python    : {sys.version.split()[0]}")
    print(f"  Root      : {project_root}")
    print("=" * 60)

    # ── STEP 2: Clean previous build ──────────────────────────────────────────
    if dist_dir.exists():
        print(f"\n  Cleaning old build: {dist_dir}")
        shutil.rmtree(dist_dir)

    # ── STEP 3: Validasi data dirs yang wajib ada ─────────────────────────────
    required_dirs = {
        "export/templates": project_root / "export" / "templates",
    }
    optional_dirs = {
        "GTK3-Runtime": project_root / "GTK3-Runtime",   # hanya Windows + WeasyPrint
    }

    for name, path in required_dirs.items():
        if not path.exists():
            print(f"\n[WARN] Data dir tidak ditemukan: {path}")
            print(f"       Pastikan folder '{name}' ada sebelum build.")

    # ── STEP 4: Build Nuitka command ──────────────────────────────────────────
    cmd = [
        sys.executable, "-m", "nuitka",

        # ── Mode & output ──────────────────────────────────────────────────────
        "--standalone",                    # bundle semua dependencies
        "--output-dir=dist_nuitka",
        "--remove-output",                 # hapus build artifacts setelah selesai

        # ── Stability (cegah OOM / linker crash) ──────────────────────────────
        "--jobs=1",                        # 1 CPU core = RAM usage lebih rendah

        # ── Compiler backend ──────────────────────────────────────────────────
        # --zig diperlukan untuk Python 3.13 di Windows (MinGW belum support)
        # Di Mac/Linux, zig opsional tapi lebih stabil
        "--zig",

        # ── Plugins ───────────────────────────────────────────────────────────
        "--enable-plugin=anti-bloat",      # kurangi ukuran output

        # tk-inter DINONAKTIFKAN: Tenrix adalah CLI, tidak butuh GUI backend
        # "--enable-plugin=tk-inter",

        # ── Numba / UMAP exclusion ────────────────────────────────────────────
        # Tenrix tidak pakai Numba — exclude untuk hemat waktu dan ukuran
        "--noinclude-numba-mode=nofollow",
        "--module-parameter=numba-disable-jit=yes",

        # ── Follow imports ────────────────────────────────────────────────────
        "--follow-imports",

        # ── Package data: Prophet ─────────────────────────────────────────────
        # Stan binary model dan data bawaan Prophet wajib ikut
        "--include-package-data=prophet",

        # ── Package data: Plotly ──────────────────────────────────────────────
        # JavaScript bundle plotly (untuk chart export)
        "--include-package-data=plotly",

        # ── Package data: DuckDB ──────────────────────────────────────────────
        # DuckDB punya native .so/.dll binary sendiri
        "--include-package-data=duckdb",

        # ── Package data: Excel ───────────────────────────────────────────────
        "--include-package-data=openpyxl",   # template dan data openpyxl

        # ── Package data: PDF export ──────────────────────────────────────────
        "--include-package-data=reportlab",  # fonts dan data ReportLab
        "--include-package-data=weasyprint", # CSS & internal templates WeasyPrint

        # ── Package data: Kaleido (chart image export) ────────────────────────
        "--include-package-data=kaleido",    # Chromium binaries internal kaleido

        # ── Scientific packages dengan C extensions ───────────────────────────
        # Perlu di-include eksplisit karena punya binary extensions
        "--include-package=scipy",
        "--include-package=statsmodels",
        "--include-package=sklearn",
        "--include-package=pandas",
        "--include-package=numpy",

        # ── Data directories ──────────────────────────────────────────────────
        f"--include-data-dir={project_root / 'export' / 'templates'}=export/templates",
    ]

    # GTK3-Runtime hanya untuk Windows + WeasyPrint
    gtk_dir = project_root / "GTK3-Runtime"
    if IS_WINDOWS and gtk_dir.exists():
        cmd.append(f"--include-data-dir={gtk_dir}=GTK3-Runtime")
        print("  GTK3-Runtime: ditemukan, akan diinclude (WeasyPrint Windows)")
    elif IS_WINDOWS and not gtk_dir.exists():
        print("  [WARN] GTK3-Runtime tidak ditemukan.")
        print("         WeasyPrint PDF export mungkin tidak berfungsi di Windows.")
        print("         Download: https://github.com/tschoonj/GTK-for-Windows-Runtime")

    # macOS: tambah icon kalau ada
    if IS_MAC:
        icon_path = project_root / "assets" / "tenrix.icns"
        if icon_path.exists():
            cmd.append(f"--macos-app-icon={icon_path}")

    # Windows: tambah icon dan version info kalau ada
    if IS_WINDOWS:
        icon_path = project_root / "assets" / "tenrix.ico"
        if icon_path.exists():
            cmd.append(f"--windows-icon-from-ico={icon_path}")

    # Entry point — selalu di akhir
    cmd.append(str(main_script))

    # ── STEP 5: Tampilkan command dan jalankan ────────────────────────────────
    print("\n  Nuitka build command:")
    print("  " + " \\\n    ".join(cmd[3:]))   # skip python -m nuitka untuk keterbacaan
    print(f"\n  NOTE: Build bisa memakan waktu 5–15 menit.")
    print(f"        Nuitka akan compile Python ke C lalu ke native binary.\n")

    if not IS_WINDOWS:
        # Mac/Linux: cek cc / clang tersedia
        if not shutil.which("cc") and not shutil.which("clang") and not shutil.which("gcc"):
            print("  [WARN] C compiler tidak ditemukan.")
            if IS_MAC:
                print("         Jalankan: xcode-select --install")
            elif IS_LINUX:
                print("         Jalankan: sudo apt install build-essential  (Debian/Ubuntu)")
                print("                   sudo yum install gcc               (RHEL/CentOS)")
            print()
    else:
        if not shutil.which("cl") and not shutil.which("gcc"):
            print("  TIP: Nuitka akan menawarkan download MinGW-64 otomatis.")
            print("       Atau gunakan --zig (sudah aktif) sebagai alternatif.\n")

    # ── STEP 6: Jalankan build ─────────────────────────────────────────────────
    try:
        result = subprocess.run(cmd, check=True)

        output_bin = get_output_binary(dist_dir)
        print(f"\n{'=' * 60}")
        print("  BUILD SUCCESSFUL ✅")
        print(f"  Output : {output_bin}")
        if output_bin.exists():
            size_mb = output_bin.stat().st_size / 1024 / 1024
            print(f"  Size   : {size_mb:.1f} MB")
        print(f"  Dist   : {dist_dir / 'main.dist'}")
        print(f"{'=' * 60}")

        # Post-build: rename binary ke "tenrix" / "tenrix.exe"
        if output_bin.exists():
            if IS_WINDOWS:
                final_bin = output_bin.parent / "tenrix.exe"
            else:
                final_bin = output_bin.parent / "tenrix"

            output_bin.rename(final_bin)
            print(f"\n  Renamed to: {final_bin}")
            print(f"\n  Cara menjalankan:")
            if IS_WINDOWS:
                print(f"    .\\dist_nuitka\\main.dist\\tenrix.exe data.csv")
            else:
                print(f"    ./dist_nuitka/main.dist/tenrix data.csv")

    except subprocess.CalledProcessError as e:
        print(f"\n{'=' * 60}")
        print("  BUILD FAILED ❌")
        print(f"  Exit code: {e.returncode}")
        print(f"{'=' * 60}")
        _print_error_hint(e.returncode)
        sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n  [CANCELLED] Build dibatalkan oleh user.")
        sys.exit(1)


def _print_error_hint(returncode: int) -> None:
    """Tampilkan hint berdasarkan exit code umum."""
    hints = {
        -1073741510: (
            "Memory exhaustion atau linker crash.\n"
            "  → Pastikan RAM cukup (min. 4GB free)\n"
            "  → Tutup aplikasi lain saat build\n"
            "  → --jobs=1 sudah aktif, coba tambah: --low-memory"
        ),
        1: (
            "Build error umum.\n"
            "  → Cek output Nuitka di atas untuk detail error\n"
            "  → Pastikan semua package terinstall di .venv\n"
            "  → Coba: python -m pip install --upgrade nuitka"
        ),
        2: (
            "Nuitka tidak ditemukan.\n"
            "  → Jalankan: pip install nuitka"
        ),
    }
    hint = hints.get(returncode, f"Unknown error (code {returncode}).")
    print(f"\n  HINT: {hint}\n")


def dist_nuitka_bin_path() -> Path:
    """Path ke binary hasil build (untuk backward compatibility)."""
    return get_output_binary(Path("dist_nuitka"))


if __name__ == "__main__":
    main()