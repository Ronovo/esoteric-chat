import pytest


@pytest.fixture(autouse=True)
def data_dir(tmp_path, monkeypatch):
    """Every app the tests create keeps its database and generated key in a fresh folder."""
    monkeypatch.setenv("ESOTERIC_CHAT_DATA_DIR", str(tmp_path / "data"))
    return tmp_path / "data"
