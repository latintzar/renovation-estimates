"""Offline contract for recipient-owned translation and unchanged-text fallback."""
import importlib.util
from pathlib import Path
from types import SimpleNamespace
import sys
import pytest
import httpx

MODULE_PATH = Path(__file__).parents[2] / "backend/services/translation_service.py"
spec = importlib.util.spec_from_file_location("owned_translation_under_test", MODULE_PATH)
service = importlib.util.module_from_spec(spec);spec.loader.exec_module(service)

def test_unconfigured_translation_preserves_text_without_network(monkeypatch):
    monkeypatch.delenv("TRANSLATION_PROVIDER", raising=False)
    monkeypatch.setattr(httpx.Client, "post", lambda *a, **k: pytest.fail("Unconfigured translation called a provider"))
    assert service.TranslationService().translate_text("Cocina", "en") == "Cocina"

@pytest.mark.parametrize("project", ["", "../../other", "recipient.example/path", "project?token=fixture"])
def test_project_validation_precedes_credentials(monkeypatch, project):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "google-cloud");monkeypatch.setenv("GOOGLE_TRANSLATION_PROJECT", project)
    with pytest.raises(RuntimeError):service.GoogleTranslator(source="es", target="en")

def test_official_provider_receives_plaintext_and_owned_project(monkeypatch):
    import google.auth
    monkeypatch.setenv("TRANSLATION_PROVIDER", "google-cloud");monkeypatch.setenv("GOOGLE_TRANSLATION_PROJECT", "fixture-project")
    credential_requests=[];requests=[]
    def credentials(**kwargs):
        credential_requests.append(kwargs)
        return SimpleNamespace(valid=True, token="fixture-access-token"), "fixture-project"
    monkeypatch.setattr(google.auth, "default", credentials)
    original_client = httpx.Client
    def respond(request):
        requests.append(request)
        return httpx.Response(200, json={"translations": [{"translatedText": "Kitchen"}]})
    monkeypatch.setattr(service.httpx, "Client", lambda **kwargs: original_client(transport=httpx.MockTransport(respond), **kwargs))
    translator=service.TranslationService()
    assert translator.translate_text("Cocina", "en") == "Kitchen"
    assert translator.translate_text("Cocina", "en") == "Kitchen"
    assert len(requests)==1
    assert str(requests[0].url)=="https://translate.googleapis.com/v3/projects/fixture-project/locations/global:translateText"
    assert b'"mimeType":"text/plain"' in requests[0].content
    assert credential_requests[0]["quota_project_id"]=="fixture-project"

def test_size_bound_precedes_credentials(monkeypatch):
    monkeypatch.setenv("TRANSLATION_PROVIDER", "google-cloud");monkeypatch.setenv("GOOGLE_TRANSLATION_PROJECT", "fixture-project")
    translator=service.GoogleTranslator(source="es", target="en")
    with pytest.raises(ValueError):translator.translate("x"*20001)
