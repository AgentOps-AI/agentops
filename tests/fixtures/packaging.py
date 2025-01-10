import builtins
import pytest


@pytest.fixture
def hide_available_pkg(monkeypatch):
    """
    Hide the availability of a package by mocking the __import__ function.

    Usage:
        @pytest.mark.usefixtures('hide_available_pkg')
        def test_message():
            with pytest.raises(ImportError, match='Install "pkg" to use test_function'):
                foo('test_function')

    Source:
        https://stackoverflow.com/questions/60227582/making-a-python-test-think-an-installed-package-is-not-available
    """
    import_orig = builtins.__import__

    def mocked_import(name, *args, **kwargs):
        if name == "pkg":
            raise ImportError()
        return import_orig(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", mocked_import)
