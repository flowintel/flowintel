API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client, title="Merge Test Case"):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": title})


def create_task(client, case_id, title="Merge Test Task"):
    return client.post(f"/api/case/{case_id}/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": title})


##################
## Merge case ##
##################

def test_merge_case(client):
    """Editor should be able to merge one case into another"""
    source_id = create_case(client, "Source Case").json["case_id"]
    target_id = create_case(client, "Target Case").json["case_id"]

    # Add a task to the source so there is something to merge
    create_task(client, source_id, "Task to merge")

    response = client.get(f"/api/case/{source_id}/merge/{target_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "Case is merged" in response.json["message"]

    # Source case should be deleted after merge
    check = client.get(f"/api/case/{source_id}",
                       headers={"X-API-KEY": API_KEY})
    assert check.status_code == 404


def test_merge_case_nonexistent_source(client):
    """Merging a non-existent source case should return 404"""
    target_id = create_case(client, "Target Only").json["case_id"]

    response = client.get(f"/api/case/9999/merge/{target_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_merge_case_nonexistent_target(client):
    """Merging into a non-existent target case should return 404"""
    source_id = create_case(client, "Source Only").json["case_id"]

    response = client.get(f"/api/case/{source_id}/merge/9999",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_merge_case_read_only_denied(client):
    """Read-only user should not be able to merge cases"""
    source_id = create_case(client, "RO Source").json["case_id"]
    target_id = create_case(client, "RO Target").json["case_id"]

    response = client.get(f"/api/case/{source_id}/merge/{target_id}",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403
