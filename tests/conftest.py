import os
import pytest
from fastapi.testclient import TestClient
from app.core import Settings
from app.main import create_app, metadata

TOKEN = 'test-only-token-with-at-least-24-characters'
@pytest.fixture
def client(tmp_path):
    settings = Settings(database_url=os.getenv('TEST_DATABASE_URL', 'sqlite:///' + str(tmp_path / 'test.db')), api_token=TOKEN)
    app = create_app(settings)
    metadata.drop_all(app.state.engine)
    with TestClient(app, headers={'Authorization': 'Bearer ' + TOKEN}) as c:
        yield c
    metadata.drop_all(app.state.engine)

@pytest.fixture
def settings(tmp_path):
    return Settings(database_url='sqlite:///' + str(tmp_path / 'provider.db'), api_token=TOKEN, llm_mode='ollama')
