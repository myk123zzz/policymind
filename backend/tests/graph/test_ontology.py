def test_valid_entity_types() -> None:
    from policymind.graph.ontology import ENTITY_TYPES

    assert "Policy" in ENTITY_TYPES
    assert "Department" in ENTITY_TYPES
    assert "Role" in ENTITY_TYPES


def test_valid_relation_types() -> None:
    from policymind.graph.ontology import RELATION_TYPES

    assert "APPLIES_TO" in RELATION_TYPES
    assert "OWNED_BY" in RELATION_TYPES
    assert "APPROVED_BY" in RELATION_TYPES
    assert "NEXT_STEP" in RELATION_TYPES
    assert "EXTRACTED_FROM" in RELATION_TYPES


def test_validate_entity_whitelist() -> None:
    from policymind.graph.ontology import is_valid_entity, is_valid_relation

    assert is_valid_entity("Policy")
    assert not is_valid_entity("UnknownType")
    assert is_valid_relation("APPLIES_TO")
    assert not is_valid_relation("INVALID_RELATION")
