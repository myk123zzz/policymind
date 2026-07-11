import uuid
from datetime import UTC, datetime

# --- MCP 工具函数 ---


def get_employee_profile(employee_id: str) -> dict[str, object]:
    """查询员工部门、岗位和职级。"""
    return {
        "employee_id": employee_id,
        "department": "R&D",
        "role": "Engineer",
        "level": 3,
        "access_level": 2,
    }


def get_approval_chain(
    process_type: str,
    department: str,
    amount: float,
    employee_level: int,
) -> dict[str, object]:
    """查询审批流程步骤。"""
    steps: list[dict[str, object]] = []
    if amount > 5000:
        steps.append({"step": 1, "approver": "Department Manager", "type": "required"})
    if amount > 10000:
        steps.append({"step": 2, "approver": "Finance Director", "type": "required"})
    steps.append({"step": len(steps) + 1, "approver": "HR Record", "type": "notification"})
    return {"process_type": process_type, "department": department, "steps": steps}


def list_required_materials(process_type: str) -> dict[str, object]:
    """查询所需材料清单。"""
    materials_map: dict[str, list[str]] = {
        "travel_reimbursement": ["Travel Request Form", "Receipts", "Approval Email"],
        "procurement": ["Purchase Request", "Quotation", "Budget Approval"],
    }
    return {
        "process_type": process_type,
        "materials": materials_map.get(process_type, ["Application Form"]),
    }


def get_policy_version(policy_name: str) -> dict[str, object]:
    """查询制度当前有效版本。"""
    now = datetime.now(UTC)
    return {
        "policy_name": policy_name,
        "current_version": "v3.2",
        "effective_from": now.isoformat(),
        "effective_to": None,
    }


def create_review_ticket(
    question: str,
    evidence: str,
    conflict: str,
    suggested_reviewer: str,
    approved: bool = False,
) -> dict[str, object]:
    """创建人工审核工单（需 HITL 批准）。"""
    if not approved:
        raise ValueError("Review ticket creation requires explicit approval")
    return {
        "ticket_id": f"ticket-{uuid.uuid4().hex[:8]}",
        "status": "created",
        "question": question,
        "suggested_reviewer": suggested_reviewer,
    }
