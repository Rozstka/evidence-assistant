from pathlib import Path
import sys
import json
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.main import create_app
Path('docs').mkdir(exist_ok=True)
Path('docs/openapi.json').write_text(json.dumps(create_app().openapi(), indent=2) + '\n')
print('Exported docs/openapi.json')
