"""Tests for llm_client.py: extract_json logic."""

from glass.llm_client import extract_json


def test_extract_json_markdown_fences():
    """JSON wrapped in markdown code fences."""
    text = '''Here is the result:

```json
[{"text": "claim 1", "status": "consistent"}]
```

That's all.'''
    result = extract_json(text)
    assert result == '[{"text": "claim 1", "status": "consistent"}]'


def test_extract_json_bare_fences():
    """JSON in code fences without json language tag."""
    text = '''```
[{"index": 0, "status": "uncertain"}]
```'''
    result = extract_json(text)
    assert result == '[{"index": 0, "status": "uncertain"}]'


def test_extract_json_raw():
    """Raw JSON array with no fences."""
    text = '[{"a": 1}, {"b": 2}]'
    result = extract_json(text)
    assert result == '[{"a": 1}, {"b": 2}]'


def test_extract_json_garbage():
    """Garbage input with no JSON — returns the input stripped."""
    text = "  This is not JSON at all.  "
    result = extract_json(text)
    assert result == "This is not JSON at all."


def test_extract_json_embedded_array():
    """JSON array embedded in surrounding prose (no fences)."""
    text = 'The claims are: [{"text": "Earth is round"}] as shown above.'
    result = extract_json(text)
    assert '"Earth is round"' in result


def test_extract_json_empty_array():
    """Empty JSON array."""
    text = "[]"
    result = extract_json(text)
    assert result == "[]"
