import json, time, os, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pathlib import Path
from fastapi.testclient import TestClient
from app.core import Settings
from app.main import create_app
project='evidence-assistant'
settings=Settings(database_url='sqlite:///:memory:', api_token='live-smoke-test-temporary-token', llm_mode='ollama',ollama_model=os.getenv('OLLAMA_MODEL', 'qwen2.5:3b'), ollama_url=os.getenv('OLLAMA_URL', 'http://localhost:11434'))
start=time.time()
with TestClient(create_app(settings), headers={'Authorization':'Bearer '+settings.api_token}) as c:
 if project=='lab-review-ai':
  r=c.post('/documents/text',json={'patient_id':'SYN-001','synthetic':True,'text':Path('examples/synthetic-lab.txt').read_text()})
 else:
  for d in json.loads(Path('examples/handbook.json').read_text()): c.post('/documents',json=d).raise_for_status()
  r=c.post('/chat',json={'question':'How long do refunds take?'})
 result={'project':project,'model':settings.ollama_model,'status_code':r.status_code,'result':r.json(),'seconds':round(time.time()-start,2)}
 Path('reports').mkdir(exist_ok=True)
 Path('reports/live-llm.json').write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result,indent=2))

if result['status_code'] >= 400:
 raise SystemExit('Live model smoke failed; inspect reports/live-llm.json')
if project == 'lab-review-ai':
 assert len(result['result']['measurements']) == 3 and not result['result']['issues']
else:
 assert result['result']['status'] == 'answered' and '5' in result['result']['answer']
