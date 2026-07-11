import pytest


def test_get_employee_profile_returns_data() -> None:
    from policymind.mcp.tools import get_employee_profile

    result = get_employee_profile(employee_id="emp-001")
    assert result["employee_id"] == "emp-001"
    assert "department" in result
    assert "role" in result


def test_get_approval_chain_returns_steps() -> None:
    from policymind.mcp.tools import get_approval_chain

    result = get_approval_chain(
        process_type="procurement", department="R&D", amount=7000, employee_level=3
    )
    assert "steps" in result
    assert len(result["steps"]) > 0


def test_list_required_materials_returns_list() -> None:
    from policymind.mcp.tools import list_required_materials

    result = list_required_materials(process_type="travel_reimbursement")
    assert "materials" in result
    assert len(result["materials"]) > 0


def test_get_policy_version_returns_date() -> None:
    from policymind.mcp.tools import get_policy_version

    result = get_policy_version(policy_name="Procurement Policy")
    assert result["policy_name"] == "Procurement Policy"
    assert "current_version" in result
    assert "effective_from" in result


def test_create_review_ticket_requires_approval() -> None:
    from policymind.mcp.tools import create_review_ticket

    with pytest.raises(ValueError, match="approval"):
        create_review_ticket(
            question="Test?",
            evidence="Some evidence",
            conflict="None",
            suggested_reviewer="admin",
            approved=False,
        )


def test_create_review_ticket_with_approval() -> None:
    from policymind.mcp.tools import create_review_ticket

    result = create_review_ticket(
        question="Test?",
        evidence="Some evidence",
        conflict="None",
        suggested_reviewer="admin",
        approved=True,
    )
    assert result["status"] == "created"
    assert "ticket_id" in result
