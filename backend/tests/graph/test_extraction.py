def test_extract_json_from_markdown_block() -> None:
    from policymind.graph.extraction import extract_json_object

    text = '```json\n{"key": "value"}\n```'
    result = extract_json_object(text)
    assert result == {"key": "value"}


def test_extract_plain_json_object() -> None:
    from policymind.graph.extraction import extract_json_object

    text = '{"name": "test", "count": 42}'
    result = extract_json_object(text)
    assert result == {"name": "test", "count": 42}


def test_extract_json_with_surrounding_text() -> None:
    from policymind.graph.extraction import extract_json_object

    text = 'Here is the result: {"status": "ok", "code": 200} End.'
    result = extract_json_object(text)
    assert result == {"status": "ok", "code": 200}


def test_extract_json_nested_object() -> None:
    from policymind.graph.extraction import extract_json_object

    text = '{"outer": {"inner": "val"}}'
    result = extract_json_object(text)
    assert result == {"outer": {"inner": "val"}}


def test_extract_invalid_returns_empty() -> None:
    from policymind.graph.extraction import extract_json_object

    text = "Not JSON here at all."
    result = extract_json_object(text)
    assert result == {}
