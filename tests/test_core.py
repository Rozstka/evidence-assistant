import pytest
import httpx
from app.core import Settings, Ollama, ProviderError

def test_requires_secret():
    with pytest.raises(ValueError):
        Settings().validate()

def test_provider_contract(monkeypatch):
    def respond(request):
        import json
        body = json.loads(request.content)
        assert request.url.path == '/api/chat'
        assert body['stream'] is False
        assert body['format'] == {'type': 'object'}
        return httpx.Response(200, json={'message': {'role': 'assistant', 'content': '{}'}})
    real_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(respond)))
    assert Ollama(Settings()).chat([], schema={'type': 'object'})['content'] == '{}'

def test_provider_outage(monkeypatch):
    real_client = httpx.Client
    monkeypatch.setattr(httpx, 'Client', lambda **kwargs: real_client(transport=httpx.MockTransport(lambda r: httpx.Response(503))))
    with pytest.raises(ProviderError):
        Ollama(Settings()).chat([])

def test_auth(client):
    assert client.get('/health').status_code == 200
    path = '/documents/text' if 'Lab Review' in client.app.title else '/documents'
    assert client.post(path, json={}, headers={'Authorization': 'Bearer invalid'}).status_code == 401


def test_global_request_limit(client):
    path = '/documents/text' if 'Lab Review' in client.app.title else '/documents'
    assert client.post(path, content=b'x' * 2_100_001).status_code == 413
