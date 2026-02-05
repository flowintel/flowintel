from flask import url_for

API_KEY = "editor_api_key"

def create_case_as_admin(client):
    return client.post("/api/case/create", 
                       content_type='application/json',
                       headers={"X-API-KEY": "admin_api_key"},
                       json={"title": "Test Case admin"})

def test_create_case_no_api(client):
    response = client.post("/api/case/create", data={
        'title': "Test Case editor"
    })
    assert response.status_code == 403

def test_create_case(client):
    """Case created by an other user"""
    response = create_case_as_admin(client)
    assert response.status_code == 201
    assert "case_id" in response.json
    assert response.json["case_id"] >= 1

def test_edit_case_to_privileged_denied_not_in_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"privileged_case": True}
                        )
    assert response.status_code == 403
    

def test_get_all_cases(client):
    response = client.get("/api/case/all", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_get_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_complete_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_create_template(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/create_template", headers={"X-API-KEY": API_KEY},
                           json={"title_template": "Template from case 1 editor"})
    assert response.status_code == 201
    assert response.json["template_id"] == 1


def test_case_recurring_once(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"once": "2023-09-11"})
    assert response.status_code == 403

def test_case_recurring_daily(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"daily": "True"})
    assert response.status_code == 403

def test_case_recurring_weekly(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"weekly": "2023-09-09"})
    assert response.status_code == 403

def test_case_recurring_monthly(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/recurring", headers={"X-API-KEY": API_KEY},
                           json={"monthly": "2023-09-09"})
    assert response.status_code == 403


def test_edit_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test edit Case editor"}
                        )
    assert response.status_code == 403

    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Test edit Case editor" not in response.data

def test_add_org_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"oid": "1"}
                        )
    assert response.status_code == 403


def test_remove_org_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}/remove_org/2", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_get_all_users(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}/get_all_users", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200


def test_delete_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_get_all_notes(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}/all_notes", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_modif_case_note(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/modify_case_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note"}
                        )
    assert response.status_code == 403 

def test_get_case_note(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.get(f"/api/case/{case_id}/get_note", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 


def test_fork_case(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/fork",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"case_title_fork": "Test fork case"}
                        )
    assert response.status_code == 201
    new_case_id = response.json["new_case_id"]

    response = client.get(f"/api/case/{new_case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["title"] == "Test fork case"


##########
## TASK ##
##########

def test_create_task_editor(client, flag=True):
    if flag:
        create_response = create_case_as_admin(client)
        case_id = create_response.json["case_id"]
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task editor"}
                        )
    assert response.status_code == 403

def test_create_task(client, flag=True, multiple=False):
    if flag:
        create_response = create_case_as_admin(client)
        case_id = create_response.json["case_id"]
    else:
        # Reuse existing case
        case_id = 1
        
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": "admin_api_key"},
                           json={"title": "Test task admin"}
                        )
    if not multiple:
        assert response.status_code == 201
        assert "Task 1 created for case id:" in response.json["message"]
    else:
        assert response.status_code == 201
        assert "Task 2 created for case id:" in response.json["message"]

def test_get_all_tasks(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
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
                           json={"title": "Test edit task editor"}
                        )
    assert response.status_code == 403

    response = client.get("/api/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Test edit task editor" not in response.data


def test_complete_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_create_note_task(client):
    test_create_task(client)
    response = client.post("/api/task/1/modif_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note", "note_id": "-1"}
                        )
    assert response.status_code == 403

def test_modif_note(client):
    test_create_note_task(client)
    response = client.post("/api/task/1/modif_note",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"note": "Test super note", "note_id": "1"}
                        )
    assert response.status_code == 403

def test_get_all_notes_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/get_all_notes", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

def test_get_note_task(client):
    test_create_note_task(client)
    response = client.get("/api/task/1/get_note?note_id=1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_take_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/take_task", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_remove_assign_task(client):
    test_take_task(client)
    response = client.get("/api/task/1/remove_assignment", headers={"X-API-KEY": API_KEY})
    print(response.text)
    assert response.status_code == 403

def test_assign_user_task(client):
    test_add_org_case(client)
    test_create_task(client, False)
    response = client.post("/api/task/1/assign_users",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"users_id": [1]}
                        )
    assert response.status_code == 403

def test_remove_assign_user_task(client):
    test_assign_user_task(client)
    response = client.post("/api/task/1/remove_assign_user",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"user_id": "1"}
                        )
    assert response.status_code == 403

def test_change_status(client):
    test_create_task(client)
    response = client.post("/api/task/1/change_status",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"status_id": "2"}
                        )
    assert response.status_code == 403

def test_list_status(client):
    response = client.get("/api/case/list_status", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert len(response.json) == 6

def test_delete_task(client):
    test_create_task(client)
    response = client.get("/api/task/1/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_change_order(client):
    create_response = create_case_as_admin(client)
    case_id = create_response.json["case_id"]
    test_create_task(client, flag=False)
    test_create_task(client, flag=False, multiple=True)
    response = client.post(f"/api/case/{case_id}/change_order/2",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"new-index": 1}
                        )
    assert response.status_code == 403
    assert b"Permission denied" in response.data

    response = client.get("/api/task/2", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["task"]["case_order_id"] == 2


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
    assert response.status_code == 403

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


def test_edit_subtask(client):
    test_create_subtask(client)
    
    response = client.post("/api/task/1/edit_subtask/1",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"description": "Test edit subtask"}
                        )
    assert response.status_code == 403

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404

def test_complete_subtask(client):
    test_create_subtask(client)
    
    response = client.get("/api/task/1/complete_subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404

def test_delete_subtask(client):
    test_create_subtask(client)
    
    response = client.get("/api/task/1/delete_subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

    response = client.get("/api/task/1/subtask/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404