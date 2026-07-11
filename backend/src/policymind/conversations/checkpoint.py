import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime

from policymind.agents.state import AgentState

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ReviewTask:
    id: int
    thread_id: str
    reason: str
    interrupt_payload_json: str
    status: str  # pending / approved / rejected
    reviewer_id: int | None = None
    decision: str | None = None
    comment: str | None = None


class MemoryCheckpointer:
    """内存 Checkpoint，用于测试和开发。"""

    def __init__(self) -> None:
        self._states: dict[str, dict[str, object]] = {}
        self._reviews: dict[str, ReviewTask] = {}

    async def put_state(self, thread_id: str, state: AgentState) -> None:
        self._states[thread_id] = {"state": dict(state), "updated_at": datetime.now(UTC)}

    async def get_state(self, thread_id: str) -> AgentState | None:
        entry = self._states.get(thread_id)
        if entry:
            return entry["state"]  # type: ignore[return-value]
        return None

    async def create_review(
        self, thread_id: str, reason: str, payload: dict[str, object]
    ) -> ReviewTask:
        rid = hash(f"{thread_id}-{datetime.now(UTC).timestamp()}") % 100000
        review = ReviewTask(
            id=rid, thread_id=thread_id, reason=reason,
            interrupt_payload_json=json.dumps(payload),
            status="pending",
        )
        self._reviews[str(rid)] = review
        return review

    async def approve_review(self, review_id: int, reviewer_id: int = 0) -> ReviewTask:
        r = self._reviews.get(str(review_id))
        if r:
            r.status = "approved"
            r.decision = "approved"
            r.reviewer_id = reviewer_id
        return r  # type: ignore[return-value]

    async def reject_review(self, review_id: int, comment: str = "") -> ReviewTask:
        r = self._reviews.get(str(review_id))
        if r:
            r.status = "rejected"
            r.decision = "rejected"
            r.comment = comment
        return r  # type: ignore[return-value]
