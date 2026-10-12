"""Small windowed entry point; the core keeps working stdin/stdout for workers."""
import ctypes
from pathlib import Path
import subprocess
import sys


def main():
    root = Path(sys.executable).resolve().parent
    executable = root / 'core' / 'policycompass.exe'
    try:
        if not executable.is_file():
            raise OSError('The application files are incomplete. Reinstall PolicyCompass or extract the whole portable folder.')
        process = subprocess.Popen([str(executable), 'browser'], cwd=root,
            stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW)
        try:
            code = process.wait(timeout=12)
            if code:
                raise OSError('PolicyCompass could not start. Check available space and access to your local application folder. If it is already closing, wait a moment and try again.')
        except subprocess.TimeoutExpired:
            pass
    except OSError as error:
        ctypes.windll.user32.MessageBoxW(None, str(error), 'PolicyCompass', 0x10)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
