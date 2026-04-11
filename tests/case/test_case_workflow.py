API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client, title="Workflow Test Case"):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": title})


#################
# Status changes
#################

def test_change_status(client):
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/change_status",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"status_id": 2})
    assert response.status_code == 200
    assert "Status changed" in response.json["message"]


def test_change_status_invalid(client):
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/change_status",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"status_id": 9999})
    assert response.status_code == 400


def test_change_status_missing_field(client):
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/change_status",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


def test_change_status_nonexistent_case(client):
    response = client.post("/api/case/9999/change_status",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"status_id": 1})
    assert response.status_code == 404


def test_change_status_read_only_denied(client):
    case_id = create_case(client).json["case_id"]

    response = client.post(f"/api/case/{case_id}/change_status",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"status_id": 2})
    assert response.status_code == 403


#####################
# Filtered listings
#####################

def test_not_completed(client):
    create_case(client)

    response = client.get("/api/case/not_completed", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "cases" in response.json
    assert isinstance(response.json["cases"], list)


def test_completed(client):
    response = client.get("/api/case/completed", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "cases" in response.json
    assert isinstance(response.json["cases"], list)


##########
# Search
##########

def test_search_found(client):
    create_case(client, title="UniqueSearchTarget42")

    response = client.post("/api/case/search",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"search": "UniqueSearchTarget42"})
    assert response.status_code == 200
    assert "cases" in response.json
    assert len(response.json["cases"]) >= 1


def test_search_not_found(client):
    response = client.post("/api/case/search",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"search": "ZZZNothingMatchesThis999"})
    assert response.status_code == 404


def test_search_missing_field(client):
    response = client.post("/api/case/search",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


###############
# Title check
###############

def test_check_title_exists(client):
    create_case(client, title="DuplicateTitleCheck")

    response = client.post("/api/case/check_case_title_exist",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "DuplicateTitleCheck"})
    assert response.status_code == 200
    assert response.json["title_already_exist"] is True


def test_check_title_not_exists(client):
    response = client.post("/api/case/check_case_title_exist",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "NeverUsedTitle999"})
    assert response.status_code == 200
    assert response.json["title_already_exist"] is False


def test_check_title_missing_field(client):
    response = client.post("/api/case/check_case_title_exist",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


###########
# History
###########

def test_history(client):
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/history",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "history" in response.json


def test_history_nonexistent_case(client):
    response = client.get("/api/case/9999/history",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404
