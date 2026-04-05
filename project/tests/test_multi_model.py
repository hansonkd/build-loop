"""Tests for multi-model verification configuration.

The Feb 2026 HN 'Harness Problem' story (755 pts) showed that the harness
matters more than the model. The Jan 2026 'Distinct AI Models Converge'
story showed different models have different failure modes. The Jan 2026
'LLM-as-a-Courtroom' story showed adversarial agents produce more reliable
decisions than single-model scoring.

Glass uses the same model for generation and verification -- this is its
stated architectural weakness. Multi-model verification decouples generation
from verification: the first step toward actual independence.
"""

import copy
import os
import pytest

from glass.config import Settings


def test_verifier_backend_default_none():
    """By default, no separate verifier backend is configured."""
    s = Settings.from_env()
    assert s.verifier_backend is None
    assert s.verifier_model is None


def test_verifier_settings_returns_self_when_no_override():
    """verifier_settings() returns the same Settings when no verifier is configured."""
    s = Settings.from_env()
    vs = s.verifier_settings()
    assert vs is s


def test_verifier_settings_overrides_model(monkeypatch):
    """verifier_settings() produces a copy with the verifier model overridden."""
    monkeypatch.setenv("GLASS_VERIFIER_BACKEND", "ollama")
    monkeypatch.setenv("GLASS_VERIFIER_MODEL", "mistral")
    s = Settings.from_env()

    assert s.verifier_backend == "ollama"
    assert s.verifier_model == "mistral"

    vs = s.verifier_settings()
    assert vs is not s
    assert vs.ollama_model == "mistral"
    # Original settings unchanged
    assert s.ollama_model == "llama3.2"


def test_verifier_settings_openrouter(monkeypatch):
    """verifier_settings() overrides the correct model for openrouter backend."""
    monkeypatch.setenv("GLASS_VERIFIER_BACKEND", "openrouter")
    monkeypatch.setenv("GLASS_VERIFIER_MODEL", "meta-llama/llama-3-70b")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    s = Settings.from_env()

    vs = s.verifier_settings()
    assert vs.openrouter_model == "meta-llama/llama-3-70b"
    # Generator model unchanged
    assert s.openrouter_model == "anthropic/claude-sonnet-4"


def test_verifier_settings_claude(monkeypatch):
    """verifier_settings() overrides the correct model for claude backend."""
    monkeypatch.setenv("GLASS_VERIFIER_BACKEND", "claude")
    monkeypatch.setenv("GLASS_VERIFIER_MODEL", "claude-haiku-4-20250514")
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")
    s = Settings.from_env()

    vs = s.verifier_settings()
    assert vs.claude_model == "claude-haiku-4-20250514"
    assert s.claude_model == "claude-sonnet-4-20250514"


def test_verifier_backend_without_model(monkeypatch):
    """When verifier backend is set but model is not, use the default model for that backend."""
    monkeypatch.setenv("GLASS_VERIFIER_BACKEND", "ollama")
    s = Settings.from_env()

    assert s.verifier_backend == "ollama"
    assert s.verifier_model is None

    vs = s.verifier_settings()
    # Should still return a copy (different backend configured) but model unchanged
    assert vs is not s
    assert vs.ollama_model == "llama3.2"  # default


def test_glass_response_includes_verifier_backend():
    """GlassResponse model includes verifier_backend field."""
    from glass.models import GlassResponse

    resp = GlassResponse(
        id="test",
        query="test",
        raw_response="test",
        reasoning_trace="test",
        claims=[],
        premise_flags=[],
        audit_trail=[],
        backend="openrouter",
        verifier_backend="ollama",
        timestamp="2026-01-01T00:00:00Z",
    )
    assert resp.verifier_backend == "ollama"
    d = resp.model_dump()
    assert d["verifier_backend"] == "ollama"


def test_glass_response_verifier_backend_optional():
    """verifier_backend is None by default (same model mode)."""
    from glass.models import GlassResponse

    resp = GlassResponse(
        id="test",
        query="test",
        raw_response="test",
        reasoning_trace="test",
        claims=[],
        premise_flags=[],
        audit_trail=[],
        backend="ollama",
        timestamp="2026-01-01T00:00:00Z",
    )
    assert resp.verifier_backend is None
