import json

import pytest

from gesso.pp import loads_assistant_json


def test_loads_raw_json():
    assert loads_assistant_json('{"a": 1, "b": "x"}') == {"a": 1, "b": "x"}


def test_loads_json_markdown_fence():
    text = """```json
{
  "title": "Retrieve",
  "artist": "Himanshu Jamad",
  "year": "",
  "image_url": "https://x.test"
}
```"""
    out = loads_assistant_json(text)
    assert out["title"] == "Retrieve"
    assert out["artist"] == "Himanshu Jamad"
    assert out["image_url"] == "https://x.test"


def test_loads_json_with_preamble():
    text = """Here you go:

```json
{"ok": true}
```
"""
    assert loads_assistant_json(text) == {"ok": True}


def test_loads_raises_on_garbage():
    with pytest.raises(json.JSONDecodeError):
        loads_assistant_json("not json at all")
