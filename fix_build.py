"""
fix_build.py — Auto-fix _ctypes DLL error and rebuild tenrix.exe
Supports: standard Python, Miniconda, Anaconda, virtualenv

Run from tenrix project root:
    python fix_build.py

What it does:
1. Finds _ctypes.pyd and libffi DLLs across ALL common install locations
2. Copies missing DLLs directly into dist/tenrix/ (instant fix — no rebuild needed)
3. If instant fix works: done. If not: regenerates tenrix.spec and rebuilds.
"""

import sys
import os
import shutil
import subprocess
from pathlib import Path


def get_search_dirs() -> list[Path]:
    """
    Return all directories to search for DLLs.
    Covers: standard Python, Miniconda, Anaconda, virtualenv, common paths.
    """
    python_exe = Path(sys.executable)
    python_dir = python_exe.parent
    home = Path.home()

    candidates = [
        # Standard Python
        python_dir / "DLLs",
        python_dir,
        python_dir / "lib",
        python_dir / "Library" / "bin",
        Path(sys.base_prefix) / "DLLs",
        Path(sys.base_prefix) / "Library" / "bin",

        # Miniconda / Anaconda — system-wide installs
        Path("C:/ProgramData/miniconda3/DLLs"),
        Path("C:/ProgramData/miniconda3/Library/bin"),
        Path("C:/ProgramData/miniconda3"),
        Path("C:/ProgramData/Anaconda3/DLLs"),
        Path("C:/ProgramData/Anaconda3/Library/bin"),
        Path("C:/ProgramData/Anaconda3"),

        # Miniconda / Anaconda — user installs
        home / "miniconda3" / "DLLs",
        home / "miniconda3",
        home / "Miniconda3" / "DLLs",
        home / "Miniconda3",
        home / "anaconda3" / "DLLs",
        home / "anaconda3",
        home / "Anaconda3" / "DLLs",
        home / "Anaconda3",

        # Common Windows Python installs
        Path("C:/Python312/DLLs"),
        Path("C:/Python311/DLLs"),
        Path("C:/Python310/DLLs"),
        Path("C:/Python39/DLLs"),

        # Walk up from python.exe — catches virtualenvs pointing to base env
        python_dir.parent / "DLLs",
        python_dir.parent.parent / "DLLs",
    ]

    # Also walk up to 6 levels from sys.executable searching for DLLs folder
    p = python_exe
    for _ in range(6):
        p = p.parent
        dll_candidate = p / "DLLs"
        if dll_candidate.exists():
            candidates.append(dll_candidate)

    # Deduplicate, keep order, only include dirs that exist
    seen = set()
    result = []
    for d in candidates:
        if d not in seen:
            seen.add(d)
            if d.exists():
                result.append(d)

    return result


def find_dll(name: str, search_dirs: list[Path]) -> Path | None:
    """Search all dirs for a DLL/PYD. Return first match or None."""
    for d in search_dirs:
        p = d / name
        if p.exists():
            return p
    return None


def main():
    # ── STEP 0: Bootstrap — Ensure we are running in .venv ──────────────────
    python_exe = Path(sys.executable)
    project_root = Path(__file__).parent.resolve()
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"

    if venv_python.exists() and python_exe.resolve() != venv_python.resolve():
        print(f"\n[BOOTSTRAP] Not running in .venv. Re-executing with: {venv_python}")
        # Pass all arguments to the new process
        result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        sys.exit(result.returncode)

    print("=" * 60)
    print("  TENRIX BUILD FIX (Environment: .venv)")
    print("=" * 60)
    print(f"\n  Python:  {sys.executable}")
    print(f"  Version: {sys.version.split()[0]}")

    search_dirs = get_search_dirs()
    print(f"\n  Searching {len(search_dirs)} locations for DLLs...")

    REQUIRED_DLLS = ["_ctypes.pyd", "pyexpat.pyd"]
    OPTIONAL_DLLS = ["libffi-8.dll", "libffi-7.dll", "libffi.dll", "ffi-8.dll", "ffi-7.dll", "ffi.dll", "libexpat.dll", "expat.dll", "sqlite3.dll", "libmpdec-4.dll", "liblzma.dll", "libbz2.dll", "libcrypto-3-x64.dll", "libssl-3-x64.dll"]

    found = []
    missing_required = []

    for name in REQUIRED_DLLS:
        path = find_dll(name, search_dirs)
        if path:
            found.append(path)
            print(f"  [OK] {name}")
            print(f"     {path}")
        else:
            missing_required.append(name)
            print(f"  [FAIL] {name} — NOT FOUND")

    for name in OPTIONAL_DLLS:
        path = find_dll(name, search_dirs)
        if path:
            found.append(path)
            print(f"  [OK] {name}")
            print(f"     {path}")

    if missing_required:
        print(f"\n  [FAIL] Could not find: {missing_required}")
        print("\n  Searched:")
        for d in search_dirs:
            print(f"    {d}")
        print("\n  Possible fixes:")
        print("  1. Ensure Miniconda/Python is installed and in PATH")
        print("  2. If using virtualenv, ensure the base Python has DLLs folder")
        sys.exit(1)

    # ── STEP 1: Instant fix — copy DLLs into dist/tenrix/ ───────────────────

    dist_dir = Path("dist") / "tenrix"
    if dist_dir.exists():
        print(f"\n{'=' * 60}")
        print("  INSTANT FIX — copying DLLs to dist/tenrix/")
        print(f"{'=' * 60}")
        for dll_path in found:
            dest = dist_dir / dll_path.name
            shutil.copy2(dll_path, dest)
            print(f"  [OK] Copied: {dll_path.name}")

        print(f"\n  Try running: dist\\tenrix\\tenrix.exe")
        answer = input("\n  Did it work? (y/n, enter to skip): ").strip().lower()
        if answer == "y":
            print("\n  [OK] Fixed! No rebuild needed.")
            return
        else:
            print("\n  Proceeding to full rebuild...\n")
    else:
        print(f"\n  dist/tenrix/ not found — skipping instant fix, going straight to rebuild.")

    # ── STEP 2: Generate fixed tenrix.spec ───────────────────────────────────

    binaries_lines = "\n        ".join(
        f"(r'{p}', '.')," for p in found
    )

    spec = f"""# tenrix.spec — generated by fix_build.py
# Re-run fix_build.py if you change Python environments

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[
        {binaries_lines}
    ],
    datas=[
        ('export/templates', 'export/templates'),
    ],
    hiddenimports=[
        # Core modules often missed by PyInstaller in venv
        '_ctypes', 'ctypes', 'ctypes.util', 'ctypes.wintypes',
        'pyexpat', 'xml.parsers.expat', 'sqlite3', '_sqlite3',

        # Keychain
        'keyring', 'keyring.backends', 'keyring.backends.Windows',
        'keyring.backends.SecretService', 'keyring.backends.fail',
        'keyring.core',

        # TUI (prompt_toolkit is critical here)
        'prompt_toolkit',
        'prompt_toolkit.completion',
        'prompt_toolkit.completion.filesystem',
        'prompt_toolkit.history',
        'prompt_toolkit.shortcuts',
        'prompt_toolkit.shortcuts.progress_bar',
        'prompt_toolkit.shortcuts.progress_bar.base',
        'prompt_toolkit.shortcuts.progress_bar.formatters',
        'prompt_toolkit.formatted_text',
        'prompt_toolkit.formatted_text.html',
        'prompt_toolkit.key_binding',
        'prompt_toolkit.styles',
        'prompt_toolkit.application',
        'prompt_toolkit.input',
        'prompt_toolkit.output',
        
        # UI libraries
        'rich', 'rich.console', 'rich.theme', 'rich.live',
        'rich.spinner', 'rich.table', 'rich.panel',
        'rich.progress', 'rich.text', 'rich.markup',

        # Analysis
        'prophet', 'prophet.forecaster', 'prophet.diagnostics',
        'lifelines', 'lifelines.fitters',
        'lifelines.fitters.kaplan_meier_fitter',
        'lifelines.statistics',
        'mlxtend', 'mlxtend.frequent_patterns',
        'mlxtend.frequent_patterns.apriori',
        'mlxtend.frequent_patterns.association_rules',
        'umap', 'umap.umap_',

        # scikit-learn internals
        'sklearn.utils._cython_blas',
        'sklearn.neighbors._typedefs',
        'sklearn.neighbors._quad_tree',
        'sklearn.tree._utils',

        # scipy
        'scipy._lib.messagestream',
        'scipy.special._ufuncs_cxx',
        'scipy.special.cython_special',

        # WeasyPrint
        'weasyprint', 'weasyprint.text.ffi', 'weasyprint.css',

        # Data
        'polars', 'duckdb', 'openpyxl', 'xlrd', 'chardet',

        # Other
        'kaleido', 'psutil', 'jinja2',
    ],
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='tenrix',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
"""

    Path("tenrix.spec").write_text(spec, encoding="utf-8")
    print("  [OK] tenrix.spec updated with correct DLL paths")

    # ── STEP 3: Full rebuild ─────────────────────────────────────────────────

    print(f"\n{'=' * 60}")
    print("  REBUILDING tenrix.exe")
    print(f"{'=' * 60}\n")

    env = os.environ.copy()
    gtk_path = Path(__file__).parent / "GTK3-Runtime" / "bin"
    if gtk_path.exists():
        env["PATH"] = f"{gtk_path};{env.get('PATH', '')}"

    result = subprocess.run(
        [sys.executable, "-m", "PyInstaller", "tenrix.spec", "--clean"],
        env=env
    )

    if result.returncode != 0:
        print("\n  [FAIL] Build failed — check output above.")
        sys.exit(1)

    # ── STEP 4: Verify ───────────────────────────────────────────────────────

    print(f"\n{'=' * 60}")
    print("  DONE")
    print(f"{'=' * 60}")

    exe_path = Path("dist") / "tenrix.exe"
    if exe_path.exists():
        size_mb = exe_path.stat().st_size / (1024 * 1024)
        print(f"\n  [OK] tenrix.exe ready")
        print(f"     {exe_path.resolve()}")
        print(f"     Size: {size_mb:.1f} MB")
        print(f"\n  Run: dist\\tenrix.exe")
    else:
        print("\n  [FAIL] tenrix.exe not found after build.")
        sys.exit(1)


if __name__ == "__main__":
    main()