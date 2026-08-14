from .app import TranslatorApp


def main() -> None:
    try:
        TranslatorApp().run()
    except KeyboardInterrupt:
        pass  # Ctrl+C in the launching terminal; the window is already gone


if __name__ == "__main__":
    main()
