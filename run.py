"""Entry point for running from source (`python run.py`) or bundling with
PyInstaller (`pyinstaller run.py`).

Kept as a thin top-level script, separate from the package, because a
script executed directly can't use the package's relative imports -- see
clipboard_google_translate/main.py.
"""

from clipboard_google_translate.main import main

if __name__ == "__main__":
    main()
