ENTITY_TYPES = frozenset(
    {
        "Policy",
        "Clause",
        "Department",
        "Role",
        "Process",
        "ApprovalStep",
        "Requirement",
        "Form",
    }
)

RELATION_TYPES = frozenset(
    {
        "APPLIES_TO",
        "OWNED_BY",
        "REQUIRES",
        "APPROVED_BY",
        "NEXT_STEP",
        "REFERENCES",
        "SUPERSEDES",
        "CONFLICTS_WITH",
        "EXTRACTED_FROM",
        "BELONGS_TO",  # 角色归属部门
    }
)


def is_valid_entity(entity_type: str) -> bool:
    return entity_type in ENTITY_TYPES


def is_valid_relation(relation_type: str) -> bool:
    return relation_type in RELATION_TYPES
