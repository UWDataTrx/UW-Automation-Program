from config import config_loader


def test_import():
    assert config_loader is not None
