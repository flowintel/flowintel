API_KEY = "admin_api_key"

def test_create_case_template(client):
    response = client.post("/api/template/create_case", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case template admin"}
                        )
    assert response.status_code == 201 and b"Template created, id: 1" in response.data

def test_create_case_template_empty_title(client):
    response = client.post("/api/template/create_case", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": ""}
                        )
    assert response.status_code == 400 and b"Please give a title to the case" in response.data

def test_create_case_template_no_data(client):
    response = client.post("/api/template/create_case", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={}
                        )
    assert response.status_code == 400 and b"Please give data" in response.data

def test_edit_case_template(client):
    test_create_case_template(client)
    response = client.post("/api/template/edit_case/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test edit Case template"}
                        )
    assert response.status_code == 200 and b"Template case edited" in response.data

    response = client.get("/api/template/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test edit Case template" in response.data

def test_edit_case_template_empty_title(client):
    test_create_case_template(client)
    response = client.post("/api/template/edit_case/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": ""}
                        )
    assert response.status_code == 200 and b"Template case edited" in response.data

    response = client.get("/api/template/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test Case template admin" in response.data

def test_edit_case_template_no_data(client):
    test_create_case_template(client)
    response = client.post("/api/template/edit_case/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={}
                        )
    assert response.status_code == 400 and b"Please give data" in response.data

    response = client.get("/api/template/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test Case template admin" in response.data

def test_delete_case_template(client):
    test_create_case_template(client)
    response = client.get("/api/template/delete_case/1", 
                           headers={"X-API-KEY": API_KEY}
                        )
    assert response.status_code == 200 and b"Case template deleted" in response.data

    response = client.get("/api/template/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404 and b"Case template not found" in response.data


def test_create_case_from_template(client):
    test_create_case_template(client)
    response = client.post("/api/template/create_case_from_template/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Case from template"}
                        )
    assert response.status_code == 201 and b"New case created, id: 1" in response.data

    response = client.get("/api/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["title"] == "Case from template"


##########
## Task ##
##########

def test_create_task_template(client, flag=True):
    response = client.post("/api/template/create_task", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task template admin"}
                        )
    if flag:
        assert response.status_code == 201 and b"Template created, id: 1" in response.data
    else:
        assert response.status_code == 201

def test_edit_task_template(client):
    test_create_task_template(client)
    response = client.post("/api/template/edit_task/1", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test edit task template"}
                        )
    assert response.status_code == 200 and b"Template edited" in response.data

    response = client.get("/api/template/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test edit task template" in response.data


def test_delete_task_template(client):
    test_create_task_template(client)
    response = client.get("/api/template/delete_task/1", 
                           headers={"X-API-KEY": API_KEY}
                        )
    assert response.status_code == 200 and b"Task template deleted" in response.data

    response = client.get("/api/template/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404 and b"Task template not found" in response.data

###########
# Subtask #
###########

def test_create_subtask(client):
    test_create_task_template(client)
    
    response = client.post("/api/template/task/1/create_subtask",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"description": "Test create subtask"}
                        )
    assert response.status_code == 201

    response = client.get("/api/template/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["description"] == "Test create subtask"

def test_edit_subtask(client):
    test_create_subtask(client)
    
    response = client.post("/api/template/task/1/edit_subtask/1",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"description": "Test edit subtask"}
                        )
    assert response.status_code == 200

    response = client.get("/api/template/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["description"] == "Test edit subtask"

def test_delete_subtask(client):
    test_create_subtask(client)
    
    response = client.get("/api/template/task/1/delete_subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

    response = client.get("/api/template/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404




########
# Task #
#  in  #
# Case #
########

def test_add_task_case(client):
    test_create_case_template(client)
    test_create_task_template(client)

    response = client.post("/api/template/case/1/add_tasks", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"tasks": [1]}
                        )
    assert response.status_code == 200 and b"Tasks added" in response.data

    response = client.get("/api/template/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and len(response.json["tasks"]) == 1

def test_remove_task_case(client):
    test_add_task_case(client)

    response = client.get("/api/template/case/1/remove_task/1", 
                           headers={"X-API-KEY": API_KEY}
                        )
    assert response.status_code == 200 and b"Task template removed" in response.data

    response = client.get("/api/template/case/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and len(response.json["tasks"]) == 0

def test_move_task_up(client):
    test_create_case_template(client)
    test_create_task_template(client)
    test_create_task_template(client, flag=False)

    response = client.post("/api/template/case/1/add_tasks", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"tasks": [1, 2]}
                        )
    assert response.status_code == 200 and b"Tasks added" in response.data

    response = client.get("/api/template/case/1/move_task_up/2", 
                           headers={"X-API-KEY": API_KEY}
                        )
    assert response.status_code == 200 and b"Order changed" in response.data

    response = client.get("/api/template/case/1/task/2", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["case_order_id"] == 1

def test_move_task_down(client):
    test_create_case_template(client)
    test_create_task_template(client)
    test_create_task_template(client, flag=False)

    response = client.post("/api/template/case/1/add_tasks", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"tasks": [1, 2]}
                        )
    assert response.status_code == 200 and b"Tasks added" in response.data

    response = client.get("/api/template/case/1/move_task_down/1", 
                           headers={"X-API-KEY": API_KEY}
                        )
    assert response.status_code == 200 and b"Order changed" in response.data

    response = client.get("/api/template/case/1/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["case_order_id"] == 2
