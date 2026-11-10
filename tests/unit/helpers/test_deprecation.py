import agentops.helpers.deprecation as dep
from agentops.helpers.deprecation import deprecated, warn_deprecated_param


def test_deprecated_passes_through_and_warns(monkeypatch):
    recorded = []
    monkeypatch.setattr(dep.logger, "warning", lambda msg: recorded.append(msg))
    dep._shown_warnings.clear()

    @deprecated("use new_func instead")
    def old_func(x):
        return x * 2

    assert old_func(21) == 42
    assert len(recorded) == 1
    assert "old_func" in recorded[0]
    assert "use new_func instead" in recorded[0]


def test_deprecated_warns_only_once(monkeypatch):
    recorded = []
    monkeypatch.setattr(dep.logger, "warning", lambda msg: recorded.append(msg))
    dep._shown_warnings.clear()

    @deprecated("msg")
    def another_func(x):
        return x + 1

    assert another_func(1) == 2
    assert another_func(1) == 2
    assert len(recorded) == 1


def test_warn_deprecated_param_with_replacement(monkeypatch):
    recorded = []
    monkeypatch.setattr(dep.logger, "warning", lambda msg: recorded.append(msg))
    dep._shown_warnings.clear()

    warn_deprecated_param("old_param", "new_param")
    assert len(recorded) == 1
    assert "old_param" in recorded[0]
    assert "new_param" in recorded[0]


def test_warn_deprecated_param_without_replacement(monkeypatch):
    recorded = []
    monkeypatch.setattr(dep.logger, "warning", lambda msg: recorded.append(msg))
    dep._shown_warnings.clear()

    warn_deprecated_param("another_param")
    assert len(recorded) == 1
    assert "another_param" in recorded[0]
    assert "instead" not in recorded[0]
