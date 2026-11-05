from pathlib import Path
import secrets
p = Path('.env')
if p.exists():
    raise SystemExit('.env already exists; refusing to overwrite')
p.write_text('API_TOKEN=' + secrets.token_urlsafe(32) + '\nPOSTGRES_PASSWORD=' + secrets.token_hex(24) + '\nLLM_MODE=demo\nOLLAMA_MODEL=qwen2.5:3b\n')
p.chmod(0o600)
print('Created .env (private permissions); no credentials printed.')
