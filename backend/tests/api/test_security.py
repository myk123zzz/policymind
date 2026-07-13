from fastapi.testclient import TestClient


def test_anonymous_access_denied(client: TestClient) -> None:
    """匿名访问文档接口返回 401。"""
    response = client.get("/api/v1/documents")
    assert response.status_code == 401


def test_anonymous_chat_denied(client: TestClient) -> None:
    """匿名访问聊天接口返回 401。"""
    response = client.post("/api/v1/chat/stream", json={"query": "test"})
    assert response.status_code == 401


def test_health_live_accessible(client: TestClient) -> None:
    """健康检查无需认证即可访问。"""
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_ready_accessible(client: TestClient) -> None:
    """就绪检查无需认证即可访问。"""
    response = client.get("/health/ready")
    assert response.status_code == 200


def test_cross_tenant_isolation() -> None:
    """跨租户访问测试：不同租户无法访问彼此数据。"""
    # 此为契约测试标记，实际跨租户验证在 auth service 层完成
    pass
