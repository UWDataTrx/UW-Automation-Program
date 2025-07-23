from config import app_config


def test_import():
    assert app_config is not None
