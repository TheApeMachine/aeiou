# AEIOU Self-Transcoder Sidecar

Small FastAPI service that converts a natural-language prompt into a canonical spec JSON.

## Quick start

1) Install deps (Python 3.10+):

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
```

2) Run the server:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

3) Test endpoints:

```bash
curl -s http://127.0.0.1:8000/health
curl -s -X POST http://127.0.0.1:8000/transcode \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Add a REST client with retry and timeouts","verbosity":"normal"}' | jq .
```


