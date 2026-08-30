import math

from google.genai import errors


def _fake_client(embed_hook=None, generate_hook=None):
    class FakeModels:
        def embed_content(self, *, model, contents, config):
            if embed_hook:
                embed_hook(model, contents, config)
            return type("R", (), {"embeddings": [
                type("E", (), {"values": [3.0, 4.0]})() for _ in contents
            ]})()

        def generate_content(self, *, model, contents, config):
            if generate_hook:
                generate_hook(model, contents, config)
            return type("R", (), {"parsed": "PARSED", "usage_metadata": type(
                "U", (), {"prompt_token_count": 11, "candidates_token_count": 7})()})()

    return type("C", (), {"models": FakeModels()})()


def _quota_exhausted_client():
    """A client whose calls fail the way Gemini's free tier does once the
    daily quota for the model is used up."""
    error = errors.APIError(429, {"error": {
        "status": "RESOURCE_EXHAUSTED", "message": "quota exceeded"}}, None)

    class FailingModels:
        def embed_content(self, *, model, contents, config):
            raise error

        def generate_content(self, *, model, contents, config):
            raise error

    return type("C", (), {"models": FailingModels()})()


def test_normalize_returns_a_unit_vector():
    from chat.gemini import normalize

    out = normalize([3.0, 4.0])
    assert math.isclose(math.sqrt(sum(x * x for x in out)), 1.0, rel_tol=1e-9)
    assert math.isclose(out[0], 0.6, rel_tol=1e-9)


def test_normalize_leaves_a_zero_vector_alone():
    from chat.gemini import normalize

    assert normalize([0.0, 0.0]) == [0.0, 0.0]


def test_embed_documents_asks_for_the_document_task_type(monkeypatch):
    from chat import gemini

    seen = {}
    monkeypatch.setattr(gemini, "_client", _fake_client(
        embed_hook=lambda m, c, cfg: seen.update(
            task_type=cfg.task_type, dims=cfg.output_dimensionality, model=m)))

    out = gemini.embed_documents(["a", "b"])
    assert seen["task_type"] == "RETRIEVAL_DOCUMENT"
    assert seen["dims"] == 1536
    assert len(out) == 2
    assert math.isclose(math.sqrt(sum(x * x for x in out[0])), 1.0, rel_tol=1e-9)


def test_embed_query_asks_for_the_query_task_type(monkeypatch):
    from chat import gemini

    seen = {}
    monkeypatch.setattr(gemini, "_client", _fake_client(
        embed_hook=lambda m, c, cfg: seen.update(task_type=cfg.task_type)))

    gemini.embed_query("who is he")
    assert seen["task_type"] == "RETRIEVAL_QUERY"


def test_structured_uses_the_strong_model_by_default(monkeypatch, settings):
    from chat import gemini

    settings.GEMINI_MODEL = "strong-model"
    settings.GEMINI_FAST_MODEL = "fast-model"
    seen = {}
    monkeypatch.setattr(gemini, "_client", _fake_client(
        generate_hook=lambda m, c, cfg: seen.update(model=m)))

    parsed, usage = gemini.structured("prompt", dict)
    assert seen["model"] == "strong-model"
    assert parsed == "PARSED"
    assert usage == {"prompt_tokens": 11, "completion_tokens": 7}


def test_structured_uses_the_fast_model_when_asked(monkeypatch, settings):
    from chat import gemini

    settings.GEMINI_MODEL = "strong-model"
    settings.GEMINI_FAST_MODEL = "fast-model"
    seen = {}
    monkeypatch.setattr(gemini, "_client", _fake_client(
        generate_hook=lambda m, c, cfg: seen.update(model=m)))

    gemini.structured("prompt", dict, fast=True)
    assert seen["model"] == "fast-model"


def test_structured_never_sends_a_thinking_budget(monkeypatch, settings):
    """gemini-3.5-flash-lite and gemini-3.6-flash reject thinking_budget with a
    400, so the spec's thinking_budget=0 optimization cannot be sent at all."""
    from chat import gemini

    seen = {}
    monkeypatch.setattr(gemini, "_client", _fake_client(
        generate_hook=lambda m, c, cfg: seen.update(
            thinking=getattr(cfg, "thinking_config", None))))

    gemini.structured("prompt", dict, fast=True)
    assert seen["thinking"] is None


def test_structured_fails_closed_on_a_quota_error(monkeypatch):
    """A 429 from the API must not crash the request -- it should look like
    an unparseable response to callers, who already fail closed on that."""
    from chat import gemini

    monkeypatch.setattr(gemini, "_client", _quota_exhausted_client())

    parsed, usage = gemini.structured("prompt", dict)
    assert parsed is None
    assert usage == {"prompt_tokens": None, "completion_tokens": None, "api_error": True}


def test_embed_query_fails_closed_on_a_quota_error(monkeypatch):
    from chat import gemini

    monkeypatch.setattr(gemini, "_client", _quota_exhausted_client())

    assert gemini.embed_query("who is he") is None
