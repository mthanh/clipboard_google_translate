import csv

from clipboard_google_translate.logger import TranslationLogger


def _read_rows(logger: TranslationLogger):
    with open(logger.log_path, encoding="utf-8-sig", newline="") as f:
        return list(csv.reader(f))


def test_save_creates_file_with_header_and_row(tmp_path):
    logger = TranslationLogger(log_dir=tmp_path)

    assert logger.save("hello", "xin chao") is True
    assert _read_rows(logger) == [["source", "translated"], ["hello", "xin chao"]]


def test_save_skips_duplicate_consecutive_source(tmp_path):
    logger = TranslationLogger(log_dir=tmp_path)
    logger.save("hello", "xin chao")

    assert logger.save("hello", "xin chao again") is False
    assert len(_read_rows(logger)) == 2


def test_save_allows_new_source_after_a_different_one(tmp_path):
    logger = TranslationLogger(log_dir=tmp_path)
    logger.save("hello", "xin chao")

    assert logger.save("world", "the gioi") is True
    assert len(_read_rows(logger)) == 3


def test_save_handles_commas_and_quotes_in_text(tmp_path):
    logger = TranslationLogger(log_dir=tmp_path)
    logger.save('a, "quoted" text', "result, with comma")

    assert _read_rows(logger)[1] == ['a, "quoted" text', "result, with comma"]


def test_save_empty_source_is_a_noop(tmp_path):
    logger = TranslationLogger(log_dir=tmp_path)

    assert logger.save("", "") is False
    assert not logger.log_path.exists()
