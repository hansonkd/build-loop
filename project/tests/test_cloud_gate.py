"""Tests for the cloud confirmation gate.

IBM's 'Bob' AI agent (HN Jan 2026) was tricked into auto-executing malware
because the user clicked 'always allow.' Glass applies the same lesson to
data egress: no data leaves the machine until you explicitly open the gate.
"""

import os
import pytest


def test_cloud_gate_blocks_when_required(monkeypatch):
    """Cloud backends are blocked when GLASS_CLOUD_CONFIRM=1 and not yet confirmed."""
    from glass.config import Settings

    monkeypatch.setenv("GLASS_CLOUD_CONFIRM", "1")
    s = Settings.from_env()
    assert s.cloud_confirm_required is True


def test_cloud_gate_off_by_default():
    """Cloud confirmation is not required by default."""
    from glass.config import Settings

    s = Settings.from_env()
    assert s.cloud_confirm_required is False


def test_is_cloud_backend():
    """Correctly identifies cloud vs local backends."""
    # Import from main after ensuring the module can load
    from glass.main import _is_cloud_backend

    assert _is_cloud_backend("openrouter") is True
    assert _is_cloud_backend("claude") is True
    assert _is_cloud_backend("ollama") is False
    assert _is_cloud_backend(None) is False


def test_cloud_gate_env_values(monkeypatch):
    """Various truthy values for GLASS_CLOUD_CONFIRM are accepted."""
    from glass.config import Settings

    for val in ("1", "true", "True", "TRUE", "yes", "Yes"):
        monkeypatch.setenv("GLASS_CLOUD_CONFIRM", val)
        s = Settings.from_env()
        assert s.cloud_confirm_required is True, f"Failed for value: {val}"

    for val in ("0", "false", "no", ""):
        monkeypatch.setenv("GLASS_CLOUD_CONFIRM", val)
        s = Settings.from_env()
        assert s.cloud_confirm_required is False, f"Failed for value: {val}"
