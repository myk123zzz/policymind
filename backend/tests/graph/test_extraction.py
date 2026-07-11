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


def test_validate_extraction_rejects_invalid_entity_type() -> None:
    from policymind.graph.extraction import validate_extraction

    raw = {
        "entities": [
            {"id": "e1", "type": "UnknownType", "name": "Bad"}
        ],
        "relations": [],
    }
    result = validate_extraction(raw, source_chunk_id="c1", tenant_id=1, document_version_id=1)
    assert len(result.entities) == 0


def test_validate_extraction_rejects_relation_with_missing_endpoint() -> None:
    from policymind.graph.extraction import validate_extraction

    raw = {
        "entities": [
            {"id": "e1", "type": "Department", "name": "R&D"}
        ],
        "relations": [
            {"source": "e1", "target": "e2", "type": "OWNED_BY"}
        ],
    }
    result = validate_extraction(raw, source_chunk_id="c1", tenant_id=1, document_version_id=1)
    assert len(result.relations) == 0


async def test_graph_extractor_from_chunk_text() -> None:
    from policymind.graph.extraction import GraphExtractor

    chunk_text = '''
    ```json
    {
        "entities": [
            {"id": "dept-fin", "type": "Department", "name": "Finance"},
            {"id": "proc-a", "type": "Process", "name": "Procurement"}
        ],
        "relations": [
            {"source": "proc-a", "target": "dept-fin", "type": "APPLIES_TO"}
        ]
    }
    ```
    '''
    extractor = GraphExtractor()
    result = await extractor.extract(
        chunk_text=chunk_text, chunk_id="c1",
        tenant_id=1, document_version_id=10,
    )
    assert len(result.entities) == 2
    assert len(result.relations) == 1
    assert result.entities[0]["tenant_id"] == 1
    assert result.entities[0]["source_document_version_id"] == 10
