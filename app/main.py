from contextlib import asynccontextmanager
from datetime import datetime, timezone
import hashlib
import threading
import uuid
from typing import Literal
from fastapi import Depends, FastAPI, HTTPException
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import Column, JSON, MetaData, String, Table, Text, insert, select, text as sqltext, func
from .core import Settings, auth, database, Ollama, ProviderError, BodyLimitMiddleware
from .retrieval import chunks, search
from .agent import answer_question

metadata = MetaData()
documents = Table('assistant_documents', metadata, Column('id', String, primary_key=True),
    Column('title', String, nullable=False), Column('text', Text, nullable=False))
passages = Table('assistant_chunks', metadata, Column('id', String, primary_key=True),
    Column('document_id', String, nullable=False), Column('title', String, nullable=False), Column('text', Text, nullable=False))
runs = Table('assistant_runs', metadata, Column('id', String, primary_key=True),
    Column('question', Text, nullable=False), Column('result', JSON, nullable=False), Column('at', String, nullable=False))

class Document(BaseModel):
    model_config = ConfigDict(extra='forbid')
    title: str = Field(min_length=1, max_length=120)
    text: str = Field(min_length=1, max_length=20000)
    synthetic: Literal[True]

class Question(BaseModel):
    model_config = ConfigDict(extra='forbid')
    question: str = Field(min_length=1, max_length=500)

def create_app(settings=None, provider=None):
    settings = settings or Settings.env()
    engine = database(settings.database_url)
    require = auth(settings)
    ingestion_lock = threading.Lock()
    llm = provider or (Ollama(settings) if settings.llm_mode == 'ollama' else None)

    @asynccontextmanager
    async def lifespan(app):
        settings.validate()
        metadata.create_all(engine)
        try:
            yield
        finally:
            engine.dispose()

    app = FastAPI(title='Evidence Assistant — RAG and bounded tools', lifespan=lifespan)
    app.add_middleware(BodyLimitMiddleware)
    app.state.engine = engine

    @app.get('/health')
    def health():
        with engine.connect() as conn:
            conn.execute(sqltext('SELECT 1'))
        return {'status': 'ok', 'mode': settings.llm_mode, 'retrieval': 'BM25'}

    @app.post('/documents', status_code=201, dependencies=[Depends(require)])
    def ingest(payload: Document):
        if not payload.text.strip():
            raise HTTPException(422, 'Empty document')
        document_id = hashlib.sha256((payload.title + '\0' + payload.text).encode()).hexdigest()[:24]
        with ingestion_lock, engine.begin() as conn:
            # Serialize ingestion in PostgreSQL so the cap and deduplication remain atomic.
            if engine.dialect.name == 'postgresql':
                conn.execute(sqltext('SELECT pg_advisory_xact_lock(4162301)'))
            if conn.execute(select(documents.c.id).where(documents.c.id == document_id)).first():
                return {'id': document_id, 'duplicate': True}
            if conn.execute(select(func.count()).select_from(documents)).scalar_one() >= 100:
                raise HTTPException(409, 'Demo corpus limit reached: 100 documents')
            conn.execute(insert(documents).values(id=document_id, title=payload.title, text=payload.text))
            parts = chunks(payload.text)
            conn.execute(insert(passages), [dict(id=f'{document_id}:{i}', document_id=document_id, title=payload.title, text=part) for i, part in enumerate(parts)])
        return {'id': document_id, 'chunks': len(parts), 'duplicate': False}

    def retrieve(question):
        with engine.connect() as conn:
            rows = [dict(row) for row in conn.execute(select(passages)).mappings()]
        return search(rows, question)

    @app.post('/search', dependencies=[Depends(require)])
    def search_endpoint(payload: Question):
        return {'sources': retrieve(payload.question)}

    @app.post('/chat', dependencies=[Depends(require)])
    def chat(payload: Question):
        try:
            answer, sources, trace = answer_question(payload.question, retrieve, llm)
        except ProviderError as exc:
            raise HTTPException(502, str(exc)) from exc
        run_id = str(uuid.uuid4())
        result = {**answer.model_dump(), 'sources': sources, 'trace': trace,
                  'mode': settings.llm_mode, 'run_id': run_id}
        with engine.begin() as conn:
            conn.execute(insert(runs).values(id=run_id, question=payload.question, result=result,
                at=datetime.now(timezone.utc).isoformat()))
        return result

    @app.get('/runs/{run_id}', dependencies=[Depends(require)])
    def get_run(run_id: str):
        with engine.connect() as conn:
            row = conn.execute(select(runs).where(runs.c.id == run_id)).mappings().first()
        if row is None:
            raise HTTPException(404, 'Run not found')
        return dict(row)

    return app

app = create_app()
