"""Keep automated checks separate from the learner's local attempt database."""

import pytest


@pytest.fixture(autouse=True)
def isolated_history(tmp_path, monkeypatch):
    """Give every test a separate database, including existing submission tests."""
    monkeypatch.setenv("TECHSPEECH_DB", str(tmp_path / "attempts.sqlite3"))
