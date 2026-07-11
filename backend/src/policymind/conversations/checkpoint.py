import logging

from policymind.agents.state import AgentState

logger = logging.getLogger(__name__)


class MemoryCheckpointer:
    """内存 Checkpoint，用于测试和开发。"""

    def __init__(self) -> None:
        self._storage: dict[str, dict[str, object]] = {}

    async def put(self, thread_id: str, state: AgentState) -> None:
        self._storage[thread_id] = {
            "state": state,
            "metadata": {"thread_id": thread_id},
        }

    async def get(self, thread_id: str) -> AgentState | None:
        entry = self._storage.get(thread_id)
        if entry:
            return entry["state"]  # type: ignore[return-value]
        return None

    async def list_threads(self) -> list[str]:
        return list(self._storage.keys())


async def interrupt_for_review(
    reason: str,
    tool_name: str,
    arguments_summary: str,
    checkpointer: MemoryCheckpointer,
    thread_id: str,
    state: AgentState,
) -> dict[str, object]:
    """触发 HITL 中断，保存状态到 Checkpoint。"""
    review_id = hash(f"{thread_id}-{tool_name}") % 100000
    state["pending_review_id"] = review_id
    await checkpointer.put(thread_id, state)

    return {
        "review_id": review_id,
        "reason": reason,
        "tool": tool_name,
        "arguments_summary": arguments_summary,
    }
