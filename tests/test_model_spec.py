import pytest

from gesso.model_spec import DEFAULT_KIMI_MODEL, DEFAULT_PERPLEXITY_MODEL, resolve_model


def test_resolve_defaults():
    r = resolve_model("perplexity")
    assert r.provider == "perplexity"
    assert r.api_model == DEFAULT_PERPLEXITY_MODEL
    r2 = resolve_model("kimi")
    assert r2.provider == "kimi"
    assert r2.api_model == DEFAULT_KIMI_MODEL


def test_resolve_provider_colon_model():
    r = resolve_model("kimi:kimi-k2-turbo")
    assert r.provider == "kimi"
    assert r.api_model == "kimi-k2-turbo"
    r2 = resolve_model("perplexity:sonar")
    assert r2.provider == "perplexity"
    assert r2.api_model == "sonar"


def test_resolve_bare_model_ids():
    r = resolve_model("kimi-k2.6")
    assert r.provider == "kimi"
    assert r.api_model == "kimi-k2.6"
    r2 = resolve_model("sonar-pro")
    assert r2.provider == "perplexity"
    assert r2.api_model == "sonar-pro"


def test_resolve_unknown_raises():
    with pytest.raises(SystemExit):
        resolve_model("wat")
