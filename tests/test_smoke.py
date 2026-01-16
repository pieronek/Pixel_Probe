
import importlib

def test_app_imports():
    mod = importlib.import_module("rgb_cursor.app")
    assert hasattr(mod, "main")
