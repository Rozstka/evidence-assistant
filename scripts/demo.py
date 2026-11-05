import json
import os
from pathlib import Path
import httpx
base = os.getenv('API_URL', 'http://127.0.0.1:8001')
with httpx.Client(base_url=base, headers={'Authorization': 'Bearer ' + os.environ['API_TOKEN']}, timeout=300) as c:
    for doc in json.loads(Path('examples/handbook.json').read_text()):
        c.post('/documents', json=doc).raise_for_status()
    for question in ('How long do refunds take?', 'How long does express shipping take?', 'What is the orbital period of Neptune?'):
        r = c.post('/chat', json={'question': question})
        r.raise_for_status()
        print(json.dumps(r.json(), indent=2))
