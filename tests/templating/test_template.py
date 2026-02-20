ADMIN_API_KEY = "admin_api_key"
TEMPLATE_EDITOR_API_KEY = "template_editor_api_key"
EDITOR_API_KEY = "editor_api_key"

def create_case_template(client, api_key=ADMIN_API_KEY):
    """Helper function to create a case template"""
    return client.post("/api/templating/create_case", 
                       content_type='application/json',
                       headers={"X-API-KEY": api_key},
                       json={"title": "Test Case template"})

def create_task_template(client, api_key=ADMIN_API_KEY):
    """Helper function to create a task template"""
    return client.post("/api/templating/create_task", 
                       content_type='application/json',
                       headers={"X-API-KEY": api_key},
                       json={"title": "Test task template"})


###################
# Admin User Tests
###################

def test_admin_create_case_template(client):
    """Admin should be able to create case templates"""
    response = create_case_template(client)
    assert response.status_code == 201
    assert b"Template created" in response.data

def test_admin_create_case_template_empty_title(client):
    """Admin should get error with empty title"""
    response = client.post("/api/templating/create_case", 
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"title": ""})
    assert response.status_code == 400
    assert b"Please give a title to the case" in response.data

def test_admin_create_case_template_no_data(client):
    """Admin should get error with no data"""
    response = client.post("/api/templating/create_case", 
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={})
    assert response.status_code == 400
    assert b"Please give data" in response.data

def test_admin_edit_case_template(client):
    """Admin should be able to edit case templates"""
    create_response = create_case_template(client)
    template_id = 1
    
    response = client.post(f"/api/templating/edit_case/{template_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"title": "Updated Case template"})
    assert response.status_code == 200
    assert b"Template case edited" in response.data

    response = client.get(f"/api/templating/case/{template_id}", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert b"Updated Case template" in response.data

def test_admin_delete_case_template(client):
    """Admin should be able to delete case templates"""
    create_response = create_case_template(client)
    template_id = 1
    
    response = client.get(f"/api/templating/delete_case/{template_id}", 
                          headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert b"Case template deleted" in response.data

    response = client.get(f"/api/templating/case/{template_id}", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 404

def test_admin_create_case_from_template(client):
    """Admin should be able to create case from template"""
    create_case_template(client)
    
    response = client.post("/api/templating/create_case_from_template/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"title": "Case from template"})
    assert response.status_code == 201
    assert b"New case created" in response.data

    response = client.get("/api/case/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert response.json["title"] == "Case from template"


##########
## Task ##
##########

def test_admin_create_task_template(client):
    """Admin should be able to create task templates"""
    response = create_task_template(client)
    assert response.status_code == 201
    assert b"Template created" in response.data

def test_admin_edit_task_template(client):
    """Admin should be able to edit task templates"""
    create_task_template(client)
    
    response = client.post("/api/templating/edit_task/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"title": "Updated task template"})
    assert response.status_code == 200
    assert b"Template edited" in response.data

    response = client.get("/api/templating/task/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert b"Updated task template" in response.data

def test_admin_delete_task_template(client):
    """Admin should be able to delete task templates"""
    create_task_template(client)
    
    response = client.get("/api/templating/delete_task/1", 
                          headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert b"Task template deleted" in response.data

    response = client.get("/api/templating/task/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 404


###########
# Subtask #
###########

def test_admin_create_subtask(client):
    """Admin should be able to create subtasks"""
    create_task_template(client)
    
    response = client.post("/api/templating/task/1/create_subtask",
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"description": "Test subtask"})
    assert response.status_code == 201

    response = client.get("/api/templating/task/1/subtask/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert response.json["description"] == "Test subtask"

def test_admin_edit_subtask(client):
    """Admin should be able to edit subtasks"""
    create_task_template(client)
    client.post("/api/templating/task/1/create_subtask",
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"description": "Test subtask"})
    
    response = client.post("/api/templating/task/1/edit_subtask/1",
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"description": "Updated subtask"})
    assert response.status_code == 200

    response = client.get("/api/templating/task/1/subtask/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert response.json["description"] == "Updated subtask"

def test_admin_delete_subtask(client):
    """Admin should be able to delete subtasks"""
    create_task_template(client)
    client.post("/api/templating/task/1/create_subtask",
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"description": "Test subtask"})
    
    response = client.get("/api/templating/task/1/delete_subtask/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200

    response = client.get("/api/templating/task/1/subtask/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 404


########
# Task #
#  in  #
# Case #
########

def test_admin_add_task_to_case(client):
    """Admin should be able to add tasks to case templates"""
    create_case_template(client)
    create_task_template(client)

    response = client.post("/api/templating/case/1/add_tasks", 
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"tasks": [1]})
    assert response.status_code == 200
    assert b"Tasks added" in response.data

    response = client.get("/api/templating/case/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert len(response.json["tasks"]) == 1

def test_admin_remove_task_from_case(client):
    """Admin should be able to remove tasks from case templates"""
    create_case_template(client)
    create_task_template(client)
    client.post("/api/templating/case/1/add_tasks", 
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"tasks": [1]})

    response = client.get("/api/templating/case/1/remove_task/1", 
                          headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert b"Task template removed" in response.data

    response = client.get("/api/templating/case/1", headers={"X-API-KEY": ADMIN_API_KEY})
    assert response.status_code == 200
    assert len(response.json["tasks"]) == 0

def test_admin_change_task_order(client):
    """Admin should be able to change task order in case templates"""
    create_case_template(client)
    create_task_template(client)
    client.post("/api/templating/create_task", 
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"title": "Second task template"})

    client.post("/api/templating/case/1/add_tasks", 
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"tasks": [1, 2]})

    response = client.post("/api/templating/case/1/change_order/2",
                           content_type='application/json',
                           headers={"X-API-KEY": ADMIN_API_KEY},
                           json={"new-index": 1})
    assert response.status_code == 200
    assert b"Order changed" in response.data


##################
# Note Templates #
##################


def test_template_editor_create_case_template(client):
    """Template Editor should be able to create case templates"""
    response = create_case_template(client, TEMPLATE_EDITOR_API_KEY)
    assert response.status_code == 201
    assert b"Template created" in response.data

def test_template_editor_edit_case_template(client):
    """Template Editor should be able to edit case templates"""
    create_case_template(client, TEMPLATE_EDITOR_API_KEY)
    
    response = client.post("/api/templating/edit_case/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"title": "Updated by template editor"})
    assert response.status_code == 200
    assert b"Template case edited" in response.data

def test_template_editor_delete_case_template(client):
    """Template Editor should be able to delete case templates"""
    create_case_template(client, TEMPLATE_EDITOR_API_KEY)
    
    response = client.get("/api/templating/delete_case/1", 
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 200
    assert b"Case template deleted" in response.data

def test_template_editor_create_task_template(client):
    """Template Editor should be able to create task templates"""
    response = create_task_template(client, TEMPLATE_EDITOR_API_KEY)
    assert response.status_code == 201
    assert b"Template created" in response.data

def test_template_editor_edit_task_template(client):
    """Template Editor should be able to edit task templates"""
    create_task_template(client, TEMPLATE_EDITOR_API_KEY)
    
    response = client.post("/api/templating/edit_task/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"title": "Updated by template editor"})
    assert response.status_code == 200
    assert b"Template edited" in response.data

def test_template_editor_delete_task_template(client):
    """Template Editor should be able to delete task templates"""
    create_task_template(client, TEMPLATE_EDITOR_API_KEY)
    
    response = client.get("/api/templating/delete_task/1", 
                          headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY})
    assert response.status_code == 200
    assert b"Task template deleted" in response.data

def test_template_editor_create_subtask(client):
    """Template Editor should be able to create subtasks"""
    create_task_template(client, TEMPLATE_EDITOR_API_KEY)
    
    response = client.post("/api/templating/task/1/create_subtask",
                           content_type='application/json',
                           headers={"X-API-KEY": TEMPLATE_EDITOR_API_KEY},
                           json={"description": "Subtask by template editor"})
    assert response.status_code == 201


##################################
# Editor Without Permission Tests
##################################

def test_editor_create_case_template_forbidden(client):
    """Editor without Template Editor permission should not create case templates"""
    response = create_case_template(client, EDITOR_API_KEY)
    assert response.status_code == 403

def test_editor_edit_case_template_forbidden(client):
    """Editor should not be able to edit case templates"""
    create_case_template(client)
    
    response = client.post("/api/templating/edit_case/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"title": "Attempted edit"})
    assert response.status_code == 403

def test_editor_delete_case_template_forbidden(client):
    """Editor should not be able to delete case templates"""
    create_case_template(client)
    
    response = client.get("/api/templating/delete_case/1", 
                          headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 403

def test_editor_create_task_template_forbidden(client):
    """Editor should not be able to create task templates"""
    response = create_task_template(client, EDITOR_API_KEY)
    assert response.status_code == 403

def test_editor_edit_task_template_forbidden(client):
    """Editor should not be able to edit task templates"""
    create_task_template(client)
    
    response = client.post("/api/templating/edit_task/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"title": "Attempted edit"})
    assert response.status_code == 403

def test_editor_delete_task_template_forbidden(client):
    """Editor should not be able to delete task templates"""
    create_task_template(client)
    
    response = client.get("/api/templating/delete_task/1", 
                          headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 403

def test_editor_create_subtask_forbidden(client):
    """Editor should not be able to create subtasks"""
    create_task_template(client)
    
    response = client.post("/api/templating/task/1/create_subtask",
                           content_type='application/json',
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"description": "Attempted subtask"})
    assert response.status_code == 403

def test_editor_edit_subtask_forbidden(client):
    """Editor should not be able to edit subtasks"""
    create_task_template(client)
    client.post("/api/templating/task/1/create_subtask",
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"description": "Test subtask"})
    
    response = client.post("/api/templating/task/1/edit_subtask/1",
                           content_type='application/json',
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"description": "Attempted edit"})
    assert response.status_code == 403

def test_editor_delete_subtask_forbidden(client):
    """Editor should not be able to delete subtasks"""
    create_task_template(client)
    client.post("/api/templating/task/1/create_subtask",
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"description": "Test subtask"})
    
    response = client.get("/api/templating/task/1/delete_subtask/1", 
                          headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 403

def test_editor_add_task_to_case_forbidden(client):
    """Editor should not be able to add tasks to case templates"""
    create_case_template(client)
    create_task_template(client)
    
    response = client.post("/api/templating/case/1/add_tasks", 
                           content_type='application/json',
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"tasks": [1]})
    assert response.status_code == 403

def test_editor_remove_task_from_case_forbidden(client):
    """Editor should not be able to remove tasks from case templates"""
    create_case_template(client)
    create_task_template(client)
    client.post("/api/templating/case/1/add_tasks", 
                content_type='application/json',
                headers={"X-API-KEY": ADMIN_API_KEY},
                json={"tasks": [1]})
    
    response = client.get("/api/templating/case/1/remove_task/1", 
                          headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 403


###############################
# Editor Read Access Tests    #
###############################

def test_editor_can_view_case_templates(client):
    """Editor should be able to view case templates"""
    create_case_template(client)
    not
    response = client.get("/api/templating/case/1", headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 200

def test_editor_can_view_task_templates(client):
    """Editor should be able to view task templates"""
    create_task_template(client)
    
    response = client.get("/api/templating/task/1", headers={"X-API-KEY": EDITOR_API_KEY})
    assert response.status_code == 200

def test_editor_can_create_case_from_template(client):
    """Editor should be able to create cases from templates"""
    create_case_template(client)
    
    response = client.post("/api/templating/create_case_from_template/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": EDITOR_API_KEY},
                           json={"title": "Case from template by editor"})
    assert response.status_code == 201