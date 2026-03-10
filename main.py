import os
import sys
from pathlib import Path
from utils.logger import get_logger

# Ensure console supports UTF-8 characters on Windows
if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Determine base directory (handles both dev and Nuitka/Pyinstaller standalone)
if getattr(sys, 'frozen', False) or hasattr(sys, '_MEIPASS') or '__compiled__' in globals():
    base_dir = Path(sys.executable).parent
else:
    base_dir = Path(__file__).resolve().parent

# Add local GTK3 runtime to PATH for WeasyPrint
gtk_path = base_dir / "GTK3-Runtime" / "bin"
if gtk_path.exists():
    os.environ["PATH"] = f"{gtk_path};{os.environ.get('PATH', '')}"
    if hasattr(os, "add_dll_directory"):
        try:
            os.add_dll_directory(str(gtk_path))
        except Exception:
            pass

logger = get_logger(__name__)


def main():
    try:
        from cli.cli_args import parse_args, handle_meta_commands
        args = parse_args()
        handle_meta_commands(args)
        
        file_path = args.get("file")
        template_name = args.get("template_name")
        
        from tui.app import run
        run(initial_file=file_path, template_name=template_name)
    except KeyboardInterrupt:
        print("\nGoodbye.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"Unhandled exception: {e}", exc_info=True)
        print(f"\nUnexpected error: {e}")
        print("Details logged to ~/.tenrix/tenrix.log")
        sys.exit(1)


if __name__ == "__main__":
    main()
