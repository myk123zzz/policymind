import io

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def auth_headers() -> dict:
    from policymind.auth.security import create_access_token

    token = create_access_token(
        data={"sub": "1", "tenant_id": 1, "role": "employee", "access_level": 1},
    )
    return {"Authorization": f"Bearer {token}"}


def test_upload_markdown_accepted(
    client: TestClient, auth_headers: dict, tmp_path
) -> None:
    # 在临时目录创建 ./data/ 供 LocalObjectStorage 使用
    import os

    old = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        content = b"# Test Policy\n\nThis is a test document."
        response = client.post(
            "/api/v1/documents",
            files={"file": ("test.md", io.BytesIO(content), "text/markdown")},
            headers=auth_headers,
        )
        assert response.status_code == 202
        assert "version_id" in response.json()
    finally:
        os.chdir(old)


def test_upload_rejects_invalid(client: TestClient, auth_headers: dict) -> None:
    with pytest.raises(ValueError, match="empty"):
        client.post(
            "/api/v1/documents",
            files={"file": ("empty.pdf", io.BytesIO(b""), "application/pdf")},
            headers=auth_headers,
        )


def test_get_job_status(
    client: TestClient, auth_headers: dict, tmp_path
) -> None:
    import os

    old = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        content = b"# Job Test\n\nContent here."
        upload_resp = client.post(
            "/api/v1/documents",
            files={"file": ("job.md", io.BytesIO(content), "text/markdown")},
            headers=auth_headers,
        )
        version_id = upload_resp.json()["version_id"]
        response = client.get(
            f"/api/v1/documents/jobs/{version_id}", headers=auth_headers
        )
        assert response.status_code == 200
        assert response.json()["stage"] == "ready"
    finally:
        os.chdir(old)


def test_list_documents(
    client: TestClient, auth_headers: dict, tmp_path
) -> None:
    import os

    old = os.getcwd()
    os.chdir(str(tmp_path))
    try:
        client.post(
            "/api/v1/documents",
            files={
                "file": ("list.md", io.BytesIO(b"# List\n\nDoc."), "text/markdown")
            },
            headers=auth_headers,
        )
        response = client.get("/api/v1/documents", headers=auth_headers)
        assert response.status_code == 200
    finally:
        os.chdir(old)
