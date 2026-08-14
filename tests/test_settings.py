from clipboard_google_translate.settings import AppSettings


def test_load_missing_file_returns_defaults(tmp_path):
    settings = AppSettings.load(tmp_path / "does_not_exist.json")

    assert settings == AppSettings()


def test_save_then_load_round_trips(tmp_path):
    path = tmp_path / "settings.json"
    original = AppSettings(
        dest_lang="ja",
        ocr_enabled=False,
        overwrite_clipboard=True,
        window_width=900,
        window_height=650,
    )

    original.save(path)
    loaded = AppSettings.load(path)

    assert loaded == original


def test_load_ignores_unknown_fields(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text('{"dest_lang": "en", "some_future_field": 123}', encoding="utf-8")

    settings = AppSettings.load(path)

    assert settings.dest_lang == "en"
    assert settings.window_width == AppSettings().window_width


def test_load_corrupt_file_returns_defaults(tmp_path):
    path = tmp_path / "settings.json"
    path.write_text("not valid json{{{", encoding="utf-8")

    assert AppSettings.load(path) == AppSettings()
