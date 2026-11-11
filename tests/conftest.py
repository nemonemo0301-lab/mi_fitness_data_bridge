"""Shared test isolation. Tests must never read the developer's real keyring."""

import pytest

from mi_fitness_mcp.adapters import mi_fitness_cloud


@pytest.fixture(autouse=True)
def _no_real_keyring_in_adapter(monkeypatch):
    monkeypatch.setattr(mi_fitness_cloud, "load_mi_fitness_token", lambda: (None, None))
