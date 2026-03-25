def test_health_endpoint(client):
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["ok"] is True


def test_projects_crud_basic(client):
    create_resp = client.post("/projects", json={
        "title": "Build Mnemosyne",
        "description": "Memory-first AI",
        "priority": "high"
    })
    assert create_resp.status_code == 200

    list_resp = client.get("/projects")
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "projects" in data
    assert len(data["projects"]) >= 1


def test_evals_run_endpoint(client):
    response = client.get("/evals/run")
    assert response.status_code == 200

    data = response.json()
    assert "overall" in data
    assert "score" in data["overall"]
