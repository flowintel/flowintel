ADMIN_API_KEY = "admin_api_key"
TEMPLATE_EDITOR_API_KEY = "template_editor_api_key"
EDITOR_API_KEY = "editor_api_key"


def create_task_template(client):
    return client.post("/api/templating/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_API_KEY},
                       json={"title": "URL Tools Task Template"})


def create_url_tool(client, task_id, name="https://example.com"):
    return client.post(f"/api/templating/task/{task_id}/create_url_tool",
                       content_type="application/json",
                       headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                       json={"name": name})


######################
## Create URL/Tools ##
######################

def test_create_url_tool(client):
    """Template editor should be able to create a URL/Tool"""
    task_id = create_task_template(client).json["message"].split(": ")[1]

    response = create_url_tool(client, task_id)
    assert response.status_code == 201
    assert "url_tool_id" in response.json


def test_create_url_tool_no_name(client):
    """Creating a URL/Tool without a name should fail"""
    task_id = create_task_template(client).json["message"].split(": ")[1]

    response = client.post(f"/api/templating/task/{task_id}/create_url_tool",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={})
    assert response.status_code == 400


def test_create_url_tool_nonexistent_task(client):
    """Creating a URL/Tool on a non-existent task template should return 404"""
    response = create_url_tool(client, 9999)
    assert response.status_code == 404


def test_create_url_tool_editor_denied(client):
    """Regular editor should not be able to create template URL/Tools"""
    task_id = create_task_template(client).json["message"].split(": ")[1]

    response = client.post(f"/api/templating/task/{task_id}/create_url_tool",
                           content_type="application/json",
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"name": "https://example.com"})
    assert response.status_code == 403


####################
## Edit URL/Tools ##
####################

def test_edit_url_tool(client):
    """Template editor should be able to edit a URL/Tool"""
    task_id = create_task_template(client).json["message"].split(": ")[1]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.post(f"/api/templating/{task_id}/edit_url_tool/{ut_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"name": "https://edited.com"})
    assert response.status_code == 200
    assert "Url/Tool edited" in response.json["message"]


def test_edit_url_tool_no_name(client):
    """Editing a URL/Tool without a name should fail"""
    task_id = create_task_template(client).json["message"].split(": ")[1]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.post(f"/api/templating/{task_id}/edit_url_tool/{ut_id}",
                           content_type="application/json",
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={})
    assert response.status_code == 400


#############################
## List and get URL/Tools ##
#############################

def test_list_urls_tools(client):
    """Should be able to list URL/Tools on a task template"""
    task_id = create_task_template(client).json["message"].split(": ")[1]
    create_url_tool(client, task_id, name="https://first.com")
    create_url_tool(client, task_id, name="https://second.com")

    response = client.get(f"/api/templating/{task_id}/list_urls_tools",
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 200
    assert "urls_tools" in response.json
    assert len(response.json["urls_tools"]) == 2


def test_get_url_tool(client):
    """Should be able to get a specific URL/Tool"""
    task_id = create_task_template(client).json["message"].split(": ")[1]
    ut_id = create_url_tool(client, task_id, name="https://specific.com").json["url_tool_id"]

    response = client.get(f"/api/templating/{task_id}/url_tool/{ut_id}",
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 200
    assert response.json["name"] == "https://specific.com"


def test_list_urls_tools_nonexistent_task(client):
    """Listing URL/Tools on a non-existent task template should return 404"""
    response = client.get("/api/templating/9999/list_urls_tools",
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 404


######################
## Delete URL/Tools ##
######################

def test_delete_url_tool(client):
    """Template editor should be able to delete a URL/Tool"""
    task_id = create_task_template(client).json["message"].split(": ")[1]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.get(f"/api/templating/{task_id}/delete_url_tool/{ut_id}",
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 200
    assert "Url/Tool deleted" in response.json["message"]


def test_delete_url_tool_nonexistent(client):
    """Deleting a non-existent URL/Tool should return 404"""
    task_id = create_task_template(client).json["message"].split(": ")[1]

    response = client.get(f"/api/templating/{task_id}/delete_url_tool/9999",
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 404


def test_delete_url_tool_editor_denied(client):
    """Regular editor should not be able to delete template URL/Tools"""
    task_id = create_task_template(client).json["message"].split(": ")[1]
    ut_id = create_url_tool(client, task_id).json["url_tool_id"]

    response = client.get(f"/api/templating/{task_id}/delete_url_tool/{ut_id}",
                          headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 403
