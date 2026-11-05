import hashlib
import hmac
import os
from dataclasses import dataclass
from fastapi import HTTPException, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
import httpx

@dataclass
class Settings:
    database_url: str = 'sqlite:///./demo.db'
    api_token: str = ''
    llm_mode: str = 'demo'
    ollama_url: str = 'http://localhost:11434'
    ollama_model: str = 'qwen2.5:3b'

    @classmethod
    def env(cls):
        return cls(**{k: os.environ[k.upper()] for k in cls.__dataclass_fields__ if k.upper() in os.environ})

    def validate(self):
        if len(self.api_token) < 24:
            raise ValueError('API_TOKEN must contain at least 24 characters')
        if self.llm_mode not in ('demo', 'ollama'):
            raise ValueError('LLM_MODE must be demo or ollama')

def database(url):
    options = {}
    if url.startswith('sqlite'):
        options['connect_args'] = {'check_same_thread': False}
        if ':memory:' in url:
            options['poolclass'] = StaticPool
    return create_engine(url, **options)

def auth(settings):
    bearer = HTTPBearer(auto_error=False)
    def require(credentials: HTTPAuthorizationCredentials | None = Security(bearer)):
        if credentials is None or not hmac.compare_digest(credentials.credentials, settings.api_token):
            raise HTTPException(401, 'Invalid API token')
        return 'token:' + hashlib.sha256(settings.api_token.encode()).hexdigest()[:12]
    return require

class ProviderError(Exception):
    pass

class Ollama:
    def __init__(self, settings):
        self.settings = settings

    def chat(self, messages, *, schema=None, tools=None):
        body = {'model': self.settings.ollama_model, 'messages': messages,
                'stream': False, 'options': {'temperature': 0, 'num_predict': 1500}}
        if schema is not None:
            body['format'] = schema
        if tools is not None:
            body['tools'] = tools
        try:
            with httpx.Client(timeout=60, trust_env=False) as client:
                with client.stream('POST', self.settings.ollama_url.rstrip('/') + '/api/chat', json=body) as response:
                    response.raise_for_status()
                    raw = bytearray()
                    for block in response.iter_bytes():
                        raw.extend(block)
                        if len(raw) > 1_000_000:
                            raise ProviderError('Provider response too large')
            import json
            payload = json.loads(raw)
            message = payload['message']
            if not isinstance(message, dict):
                raise ValueError('message must be an object')
            return message
        except (httpx.HTTPError, ValueError, KeyError) as exc:
            raise ProviderError('LLM unavailable or invalid response') from exc


class BodyLimitMiddleware:
    """Bound the body before multipart parsing can spool a large upload to disk."""
    def __init__(self, app, max_bytes=2_100_000):
        self.app, self.max_bytes = app, max_bytes

    async def __call__(self, scope, receive, send):
        if scope['type'] != 'http' or scope['method'] not in ('POST', 'PUT', 'PATCH'):
            return await self.app(scope, receive, send)
        from starlette.responses import JSONResponse
        body = bytearray()
        while True:
            message = await receive()
            if message['type'] == 'http.disconnect':
                return
            body.extend(message.get('body', b''))
            if len(body) > self.max_bytes:
                return await JSONResponse({'detail': 'Request body too large'}, status_code=413)(scope, receive, send)
            if not message.get('more_body', False):
                break
        sent = False
        async def replay():
            nonlocal sent
            if not sent:
                sent = True
                return {'type': 'http.request', 'body': bytes(body), 'more_body': False}
            return await receive()
        await self.app(scope, replay, send)
