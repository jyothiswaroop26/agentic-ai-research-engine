# Agentic AI Research Engine

## OpenAI Integration

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. API configuration

Set these environment variables:

- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `OPENAI_BASE_URL` (optional)
- `OPENAI_TIMEOUT_SECONDS` (optional, default: `30.0`)

Example PowerShell:

```powershell
$env:OPENAI_API_KEY="your-key"
$env:OPENAI_MODEL="gpt-4o-mini"
```

### 3. Run API

```bash
uvicorn app.main:app --reload
```

### 4. Verify connectivity

```bash
curl http://127.0.0.1:8000/api/openai/connectivity
```

Expected response:

```json
{"status":"connected"}
```

### 5. Test LLM response

```bash
curl -X POST "http://127.0.0.1:8000/api/llm/respond" \
	-H "Content-Type: application/json" \
	-d '{"prompt":"Summarize AI agents in one sentence."}'
```

### 6. Run tests

```bash
pytest -q
```