import pytest
from starlette.testclient import TestClient

from policymind.main import create_app


@pytest.fixture
def client() -> TestClient:
    app = create_app()
    return TestClient(app)


def test_package_and_health(client: TestClient) -> None:
    import policymind

    assert policymind.__version__ == "0.1.0"

    response = client.get("/health/live")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
