import os
import sys
import shutil
import subprocess
from pathlib import Path

def main():
    # ── STEP 0: Bootstrap — Ensure we are running in .venv ──────────────────
    python_exe = Path(sys.executable)
    project_root = Path(__file__).parent.resolve()
    venv_python = project_root / ".venv" / "Scripts" / "python.exe"

    if venv_python.exists() and python_exe.resolve() != venv_python.resolve():
        print(f"\n[BOOTSTRAP] Not running in .venv. Re-executing with: {venv_python}")
        result = subprocess.run([str(venv_python), __file__] + sys.argv[1:])
        sys.exit(result.returncode)

    main_script = project_root / "main.py"
    dist_dir = project_root / "dist_nuitka"
    
    print("=" * 60)
    print("  TENRIX NUITKA BUILDER (Environment: .venv)")
    print("=" * 60)

    # 1. Clean previous build
    if dist_dir.exists():
        print(f"  Removing old dist directory: {dist_dir}")
        shutil.rmtree(dist_dir)

    # 2. Build Nuitka command
    cmd = [
        sys.executable, "-m", "nuitka",
        "--standalone",
        "--output-dir=dist_nuitka",
        "--remove-output",
        
        # Stability & Memory Optimization 
        # Exit code -1073741510 usually means memory exhaustion or linker crash
        "--jobs=1",                # Use only 1 CPU core to keep memory usage low
        
        # Plugins
        "--enable-plugin=tk-inter", # Often needed for scientific backend logic
        "--enable-plugin=anti-bloat",    # Helps reduce output size
        "--zig",                         # Required for Python 3.13 on Windows (MinGW not yet supported)
        
        # Optimization & Compatibility (Fix for Numba/UMAP)
        "--noinclude-numba-mode=nofollow",
        "--module-parameter=numba-disable-jit=yes",

        # Performance/Size
        "--follow-imports",

        # Explicit Package Data (diperlukan untuk fitur-fitur baru dan rendering)
        "--include-package-data=prophet",      # Binary model stan dan data bawaan Prophet
        "--include-package-data=kaleido",      # Chromium binaries internal kaleido u/ export image
        "--include-package-data=weasyprint",   # CSS & internal template WEasyPrint
        "--include-package-data=plotly",       # Javascript bundle plotly
        
        # Data files
        f"--include-data-dir={project_root}/export/templates=export/templates",
        f"--include-data-dir={project_root}/GTK3-Runtime=GTK3-Runtime",
        
        # Entry point
        str(main_script)
    ]

    print("\n  Executing Nuitka build command:")
    print("  " + " ".join(cmd))
    print("\n  NOTE: This will take several minutes. Nuitka will compile Python to C.")
    if not shutil.which("cl") and not shutil.which("gcc"):
        print("  TIP: No C compiler found. Nuitka will ask to download MinGW-64. Please allow it.")

    try:
        # Run Nuitka. We use subprocess.run so we can see the output.
        result = subprocess.run(cmd, check=True)
        
        if result.returncode == 0:
            print(f"\n{'=' * 60}")
            print("  BUILD SUCCESSFUL")
            print(f"  Output: {dist_nuitka_bin_path()}")
            print(f"{'=' * 60}")
        else:
            print("\n  [FAIL] Nuitka build failed.")
            sys.exit(1)
            
    except subprocess.CalledProcessError as e:
        print(f"\n  [ERROR] Build process crashed: {e}")
        sys.exit(1)

def dist_nuitka_bin_path():
    # Nuitka 4.x creates dist_nuitka/main.dist/main.exe by default
    return Path("dist_nuitka/main.dist/main.exe").absolute()

if __name__ == "__main__":
    main()
