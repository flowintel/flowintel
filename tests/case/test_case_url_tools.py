API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "URL Tools Test Case"})


def create_task(client, case_id):
    return client.post(f"/api/case/{case_id}/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "URL Tools Test Task"})


def create_url_tool(client, task_id, name="https://example.com"):
    return client.post(f"/api/task/{task_id}/create_url_tool",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"name": name})


######################
## Create URL/Tools ##
######################

def test_create_url_tool(client):
    """Editor should be able to create a URL/Tool on a task"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = create_url_tool(client, task_id)
    assert response.status_code == 201
    assert "url_tool_id" in response.json


def test_create_url_tool_no_name(client):
    """Creating a URL/Tool without a name should fail"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/create_url_tool",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


def test_create_url_tool_read_only_denied(client):
    """Read-only user should not be able to create URL/Tools"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.post(f"/api/task/{task_id}/create_url_tool",
                           content_type="application/json",
                           headers={"X-API-KEY": READ_KEY},
                           json={"name": "https://example.com"})
    assert response.status_code == 403


def test_create_url_tool_nonexistent_task(client):
    """Creating a URL/Tool on a non-existent task should return 404"""
    response = create_url_tool(client, 9999)
    assert response.status_code == 404


####################
## Edit URL/Tools ##
####################

def test_edit_url_tool(client):
    """Editor should be able to edit a URL/Tool"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.post(f"/api/task/{task_id}/edit_url_tool/{ut_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "https://edited.com"})
    assert response.status_code == 200
    assert "Url/Tool edited" in response.json["message"]


def test_edit_url_tool_no_name(client):
    """Editing a URL/Tool without a name should fail"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.post(f"/api/task/{task_id}/edit_url_tool/{ut_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": API_KEY},
                           json={})
    assert response.status_code == 400


#############################
## List and get URL/Tools ##
#############################

def test_list_urls_tools(client):
    """Editor should be able to list URL/Tools on a task"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    create_url_tool(client, task_id, name="https://first.com")
    create_url_tool(client, task_id, name="https://second.com")

    response = client.get(f"/api/task/{task_id}/list_urls_tools",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "urls_tools" in response.json
    assert len(response.json["urls_tools"]) == 2


def test_list_urls_tools_empty(client):
    """Listing URL/Tools on a task with none should return empty list"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.get(f"/api/task/{task_id}/list_urls_tools",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["urls_tools"] == []


def test_get_url_tool(client):
    """Editor should be able to get a specific URL/Tool"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    ut_id = create_url_tool(client, task_id, name="https://specific.com").json["url_tool_id"]

    response = client.get(f"/api/task/{task_id}/url_tool/{ut_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["name"] == "https://specific.com"


######################
## Delete URL/Tools ##
######################

def test_delete_url_tool(client):
    """Editor should be able to delete a URL/Tool"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.get(f"/api/task/{task_id}/delete_url_tool/{ut_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "Url/Tool deleted" in response.json["message"]


def test_delete_url_tool_nonexistent(client):
    """Deleting a non-existent URL/Tool should return 404"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = client.get(f"/api/task/{task_id}/delete_url_tool/9999",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_delete_url_tool_read_only_denied(client):
    """Read-only user should not be able to delete URL/Tools"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.get(f"/api/task/{task_id}/delete_url_tool/{ut_id}",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403
