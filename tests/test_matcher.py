from types import SimpleNamespace
from app.models import Category
from app.services.matcher import classify_event, host_from_destination

def test_host_parsing():
    assert host_from_destination("api.openai.com") == "api.openai.com"
    assert host_from_destination("x", "https://huggingface.co/a/b") == "huggingface.co"

def test_model_download_category():
    asset = SimpleNamespace(category=Category.model_registry)
    model, api = classify_event(asset, "huggingface.co", "/foo")
    assert model is True
    assert api is False

def test_api_path_detection():
    model, api = classify_event(None, "example.invalid", "https://example.invalid/v1/responses")
    assert api is True
