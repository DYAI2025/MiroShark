"""Test Wonderwall LLM fallback mechanism. Does not hit the network."""

from __future__ import annotations

import os

from wonderwall.social_agent.agent import _get_fallback_model, _fallback_model_backend


def test_fallback_returns_none_when_unconfigured():
    """When no WONDERWALL_FALLBACK env vars are set, returns None."""
    # Ensure env is clean
    os.environ.pop('WONDERWALL_FALLBACK_MODEL_NAME', None)
    os.environ.pop('WONDERWALL_FALLBACK_BASE_URL', None)
    os.environ.pop('WONDERWALL_FALLBACK_API_KEY', None)
    # Reset the module-level singleton
    import wonderwall.social_agent.agent as _agent_mod
    _agent_mod._fallback_model_backend = None

    fb = _get_fallback_model()
    assert fb is None


def test_fallback_module_level_attributes_exist():
    """Module-level fallback attributes should be accessible."""
    import wonderwall.social_agent.agent as _agent_mod
    assert hasattr(_agent_mod, '_get_fallback_model')
    assert hasattr(_agent_mod, '_fallback_model_backend')
    assert callable(_agent_mod._get_fallback_model)
