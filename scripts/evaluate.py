"""Tiny synthetic retrieval regression set; not a general RAG quality benchmark."""
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.retrieval import chunks,search
docs=json.loads(Path('examples/handbook.json').read_text())
rows=[{'id':f'{i}:{j}','title':d['title'],'text':c} for i,d in enumerate(docs) for j,c in enumerate(chunks(d['text']))]
cases=[('How long do refunds take?',0),('Express shipping delivery?',1),('When do password resets expire?',2),('Are returns accepted?',0),('Does support ask for authentication codes?',2)]
hits=[]
for question,expected in cases:
    results=search(rows,question)
    hits.append({'question':question,'expected_document':expected,'top_ids':[r['id'] for r in results], 'hit_at_1':bool(results and results[0]['id'].startswith(str(expected)+':')), 'hit_at_4':any(r['id'].startswith(str(expected)+':') for r in results)})
unknown=search(rows,'Orbital period Neptune?')
result={'scope':'5 questions, 3 fictional documents, 1 unrelated question', 'recall_at_4':sum(r['hit_at_4'] for r in hits)/len(hits),
        'hit_rate_at_1':sum(r['hit_at_1'] for r in hits)/len(hits),'unrelated_abstained':not unknown,'cases':hits}
Path('reports').mkdir(exist_ok=True)
Path('reports/retrieval-evaluation.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
