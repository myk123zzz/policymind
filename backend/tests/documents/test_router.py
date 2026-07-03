from fastapi.testclient import TestClient


def test_upload_document_accepted(client: TestClient) -> None:
    """上传文档返回 202 和 job ID。"""
    response = client.post(
        "/api/v1/documents",
        json={
            "logical_name": "test-policy",
            "category": "general",
            "version": "1.0",
            "content_hash": "abc123",
            "storage_key": "1/test.md",
            "mime_type": "text/markdown",
        },
    )
    assert response.status_code == 202
    data = response.json()
    assert "version_id" in data
    assert data["status"] in ("queued", "completed")


def test_get_job_status(client: TestClient) -> None:
    """查询任务状态返回正确信息。"""
    # 先上传一个文档
    upload_resp = client.post(
        "/api/v1/documents",
        json={
            "logical_name": "job-test",
            "category": "general",
            "version": "1.0",
            "content_hash": "def456",
            "storage_key": "2/test.md",
            "mime_type": "text/markdown",
        },
    )
    version_id = upload_resp.json()["version_id"]

    # 查询任务状态
    response = client.get(f"/api/v1/documents/jobs/{version_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["stage"] in ("queued", "stored", "parsed", "ready")
    assert "status" in data


def test_list_documents(client: TestClient) -> None:
    """列出文档返回列表。"""
    response = client.get("/api/v1/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)
