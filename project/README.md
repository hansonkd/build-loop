# Glass

AI that shows its work.

## Quick Start

```bash
cd project
pip install -e .
glass
```

Open http://localhost:7777

## Backends

**Local (default):** Install [Ollama](https://ollama.com), pull a model (`ollama pull llama3.2`), and run `ollama serve`.

**Cloud (opt-in):** Set `ANTHROPIC_API_KEY` in your environment. A banner will indicate when data leaves your machine.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OLLAMA_BASE_URL` | `http://localhost:11434` | Ollama API URL |
| `OLLAMA_MODEL` | `llama3.2` | Ollama model name |
| `ANTHROPIC_API_KEY` | (none) | Enables Claude backend |
| `CLAUDE_MODEL` | `claude-sonnet-4-20250514` | Claude model to use |
| `GLASS_DB_PATH` | `glass.db` | SQLite database path |
| `GLASS_PORT` | `7777` | Server port |
