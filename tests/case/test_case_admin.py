from flask import url_for

API_KEY = "admin_api_key"

def create_case(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case admin"}
                        )
    return response

def test_create_case_no_api(client):
    response = client.post("/api/case/create", data={
        'title': "Test Case admin"
    })
    assert response.status_code == 403

def test_create_case(client):
    response = create_case(client)
    assert response.status_code == 201
    assert b"Case created" in response.data
    assert "case_id" in response.json

def test_create_privileged_case(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Privileged Case admin", "privileged_case": True}
                        )
    assert response.status_code == 201
    assert b"Case created" in response.data
    case_id = response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["privileged_case"] == True

def test_edit_case_to_privileged(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"privileged_case": True}
                        )
    assert response.status_code == 200
    assert b"edited" in response.data
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["privileged_case"] == True

def test_edit_privileged_case_to_non_privileged(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Privileged Case admin", "privileged_case": True}
                        )
    case_id = response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"privileged_case": False}
                        )
    assert response.status_code == 200
    assert b"edited" in response.data
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["privileged_case"] == False

def test_create_case_empty_title(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": ""}
                        )
    assert response.status_code == 400
    assert b"Please give a title" in response.data

def test_create_case_no_data(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={}
                        )
    assert response.status_code == 400
    assert b"Please give data" in response.data

def test_create_case_deadline(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case admin", "description": "Test case", "deadline_date": "2023-09-30"}
                        )
    assert response.status_code == 201
    assert b"Case created" in response.data

def test_create_case_wrong_deadline(client):
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case admin", "description": "Test case", "deadline_date": "2023/09/30"}
                        )
    assert response.status_code == 400
    assert b"deadline_date bad format" in response.data

def test_create_case_existing_title(client):
    create_case(client)
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case admin"}
                        )
    assert response.status_code == 400
    assert b"Title already exist" in response.data
    

def test_get_all_cases(client):
    response = client.get("/api/case/all", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_get_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_complete_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"completed" in response.data

def test_create_template(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/create_template", headers={"X-API-KEY": API_KEY},
                           json={"title_template": "Template from case 1 admin"})
    assert response.status_code == 201
    assert "template_id" in response.json


def test_case_recurring_once(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"once": "2023-09-11"})
    assert response.status_code == 200
    assert b'Recurring changed' in response.data
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["recurring_type"]
    assert response.json["recurring_date"]

def test_case_recurring_daily(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"daily": "True"})
    assert response.status_code == 200
    assert b'Recurring changed' in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["recurring_type"]

def test_case_recurring_weekly(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"weekly": "2023-09-09"})
    assert response.status_code == 200
    assert b'Recurring changed' in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["recurring_type"]
    assert response.json["recurring_date"]

def test_case_recurring_monthly(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"monthly": "2023-09-09"})
    assert response.status_code == 200
    assert b'Recurring changed' in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["recurring_type"]
    assert response.json["recurring_date"]

def test_case_recurring_remove(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"monthly": "2023-09-09"})
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"remove": "True"})
    assert response.status_code == 200 and b'Recurring changed' in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and not response.json["recurring_type"] and not response.json["recurring_date"]


def test_edit_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test edit Case admin"}
                        )
    assert response.status_code == 200 and b"edited" in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test edit Case admin" in response.data

def test_create_edit_empty_title(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": ""}
                        )
    assert response.status_code == 200 and b"edited" in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["title"] == "Test Case admin"

def test_create_edit_no_data(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={}
                        )
    assert response.status_code == 400 and b"Please give data" in response.data

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["title"] == "Test Case admin"

def test_edit_case_exist_title(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case 2 admin"}
                        )
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test Case 2 admin"}
                        )
    assert response.status_code == 400 and b"Title already exist" in response.data

def test_add_org_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"oid": "2"}
                        )
    assert response.status_code == 200 and b"Org added to case" in response.data

def test_add_org_case_wrong_org(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"oid": "6"}
                        )
    assert response.status_code == 404


def test_remove_org_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    client.post(f"/api/case/{case_id}/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"oid": "2"})
    
    response = client.get(f"/api/case/{case_id}/remove_org/2", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Org deleted from case" in response.data

def test_get_all_users(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}/get_all_users", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200


def test_delete_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Case deleted" in response.data



##########
## TASK ##
##########

def test_create_task(client, flag=True, multiple=False):
    if flag:
        create_response = create_case(client)
        case_id = create_response.json["case_id"]
    else:
        case_id = 1
    
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin"}
                        )
    if not multiple:
        assert response.status_code == 201 and "Task 1 created for case id:" in response.json["message"]
    else:
        assert response.status_code == 201 and "Task 2 created for case id:" in response.json["message"]
    

def test_create_task_deadline(client, flag=True):
    if flag:
        create_response = create_case(client)
        case_id = create_response.json["case_id"]
    else:
        case_id = 1
    
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin", "description": "Test", "url": "test", "deadline_date": "2023-09-30"}
                        )
    assert response.status_code == 201 and "Task 1 created for case id:" in response.json["message"]

def test_create_task_wrong_deadline(client, flag=True):
    if flag:
        create_response = create_case(client)
        case_id = create_response.json["case_id"]
    else:
        case_id = 1
    
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin", "description": "Test", "url": "test", "deadline_date": "2023/09/30"}
                        )
    assert response.status_code == 400 and b"deadline_date bad format" in response.data

def test_get_all_tasks(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin"})
    
    response = client.get(f"/api/case/{case_id}/tasks", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_get_task(client):
    test_create_task(client)
    response = client.get("/api/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200


def test_edit_task(client):
    test_create_task(client)
    response = client.post("/api/task/1/edit",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test edit task admin"}
                        )

    assert response.status_code == 200 and b"Task 1 edited" in response.data

    response = client.get("/api/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test edit task admin" in response.data


def test_complete_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Task 1 completed" in response.data


def test_create_note_task(client):
    test_create_task(client)
    response = client.post("/api/task/1/modif_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note", "note_id": "-1"}
                        )
    assert response.status_code == 200 and b"Note for task 1 edited" in response.data

def test_modif_note(client):
    test_create_note_task(client)
    response = client.post("/api/task/1/modif_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note", "note_id": "1"}
                        )
    assert response.status_code == 200 and b"Note for task 1 edited" in response.data

def test_get_all_notes_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/get_all_notes", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_get_note_task(client):
    test_create_note_task(client)
    response = client.get("/api/task/1/get_note?note_id=1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test super note" in response.data


def test_take_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/take_task", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Task Take" in response.data

def test_remove_assign_task(client):
    test_take_task(client)
    response = client.get("/api/task/1/remove_assignment", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Removed from assignment" in response.data

def test_assign_user_task(client):
    test_add_org_case(client)
    test_create_task(client, False)
    response = client.post("/api/task/1/assign_users",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"users_id": [2]}
                        )
    assert response.status_code == 200 and b"Users Assigned" in response.data

def test_remove_assign_user_task(client):
    test_assign_user_task(client)
    response = client.post("/api/task/1/remove_assign_user",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"user_id": "2"}
                        )
    assert response.status_code == 200 and b"User Removed from assignment" in response.data

def test_change_status(client):
    test_create_task(client)
    response = client.post("/api/task/1/change_status",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"status_id": "2"}
                        )
    assert response.status_code == 200 and b"Status changed" in response.data

def test_list_status(client):
    response = client.get("/api/case/list_status", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and len(response.json) == 6

def test_delete_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Task deleted" in response.data

def test_change_order(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    # Create first task
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin"})
    # Create second task
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin"})
    
    response = client.post(f"/api/case/{case_id}/change_order/2",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"new-index": 1}
                        )
    assert response.status_code == 200 and b"Order changed" in response.data

    response = client.get("/api/task/2", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["task"]["case_order_id"] == 1


def test_get_all_notes(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    # Create task and add note
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task admin"})
    client.post("/api/task/1/modif_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note", "note_id": "-1"})
    client.post("/api/task/1/modif_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note", "note_id": "1"})
    
    response = client.get(f"/api/case/{case_id}/all_notes", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test super note" in response.data

def test_modif_case_note(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/modify_case_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note"}
                        )
    assert response.status_code == 200 and b"Note for Case" in response.data and b"edited" in response.data

def test_get_case_note(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    client.post(f"/api/case/{case_id}/modify_case_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note"})
    
    response = client.get(f"/api/case/{case_id}/get_note", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Test super note" in response.data

def test_fork_case(client):
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/fork",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"case_title_fork": "Test fork case"}
                        )
    assert response.status_code == 201

    # The forked case will have a new ID
    forked_case_id = response.json["new_case_id"]
    response = client.get(f"/api/case/{forked_case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["title"] == "Test fork case"

###########
# Subtask #
###########

def test_create_subtask(client):
    test_create_task(client, True)
    
    response = client.post("/api/task/1/create_subtask",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"description": "Test create subtask"}
                        )
    assert response.status_code == 201

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["description"] == "Test create subtask"


def test_edit_subtask(client):
    test_create_subtask(client)
    
    response = client.post("/api/task/1/edit_subtask/1",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"description": "Test edit subtask"}
                        )
    assert response.status_code == 200

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["description"] == "Test edit subtask"

def test_complete_subtask(client):
    test_create_subtask(client)
    
    response = client.get("/api/task/1/complete_subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["completed"] == True

def test_delete_subtask(client):
    test_create_subtask(client)
    
    response = client.get("/api/task/1/delete_subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404