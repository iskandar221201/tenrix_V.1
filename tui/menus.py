"""Helper functions for single-keypress input and menu display."""
import msvcrt
import sys


def get_keypress() -> str:
    """Get a single keypress without requiring Enter. Returns lowercase."""
    try:
        if sys.platform == "win32":
            ch = msvcrt.getch()
            return ch.decode("utf-8", errors="replace").lower()
        else:
            import tty
            import termios
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                ch = sys.stdin.read(1)
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)
            return ch.lower()
    except Exception:
        # Fallback to input
        return input("> ").strip().lower()[:1]


def prompt_choice(prompt: str = "> ", valid: set = None) -> str:
    """Prompt for a single keypress, optionally validating against valid set."""
    from tui.components import console
    console.print(f"  {prompt}", end="")
    while True:
        key = get_keypress()
        if valid is None or key in valid:
            console.print(key)
            return key
