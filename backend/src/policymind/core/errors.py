class PolicyMindError(Exception):
    """PolicyMind 领域错误基类。"""

    code: str = "INTERNAL_ERROR"
    status_code: int = 500
    public_message: str = "An internal error occurred."

    def __init__(self, detail: str = "") -> None:
        self.detail = detail
        super().__init__(detail or self.public_message)


class InvalidDocument(PolicyMindError):
    code = "INVALID_DOCUMENT"
    status_code = 400
    public_message = "The document is invalid."


class DependencyUnavailable(PolicyMindError):
    code = "DEPENDENCY_UNAVAILABLE"
    status_code = 503
    public_message = "A required service is unavailable."


class AuthorizationDenied(PolicyMindError):
    code = "AUTHORIZATION_DENIED"
    status_code = 401
    public_message = "Authorization denied."


class EmbeddingUnavailable(PolicyMindError):
    code = "EMBEDDING_UNAVAILABLE"
    status_code = 503
    public_message = "Embedding service is unavailable."


class ApprovalRequired(PolicyMindError):
    code = "APPROVAL_REQUIRED"
    status_code = 409
    public_message = "Human approval is required for this action."


class AgentBudgetExceeded(PolicyMindError):
    code = "BUDGET_EXCEEDED"
    status_code = 422
    public_message = "Agent step or token budget exceeded."
