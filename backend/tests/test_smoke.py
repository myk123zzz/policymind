import pytest
from fastapi.testclient import TestClient

from policymind.main import app, create_app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_package_version() -> None:
    import policymind

    assert policymind.__version__ == "0.1.0"


def test_module_app_is_instantiated() -> None:
    """验证模块级 app 存在，确保 uvicorn policymind.main:app 可用。"""
    assert app is not None
    assert app.title == "PolicyMind"


def test_health_live(client: TestClient) -> None:
    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_ready(client: TestClient) -> None:
    response = client.get("/health/ready")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert "dependencies" in data


def test_create_app_returns_fastapi() -> None:
    """验证 create_app() 可独立调用，为后续 DI 注入预留路径。"""
    app_instance = create_app()
    assert app_instance is not None
    assert app_instance.title == "PolicyMind"
