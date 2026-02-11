"""
Test cases for Case Admin user
Case Admin is an editor with case_admin privilege who can create and modify privileged cases
"""

API_KEY = "caseadmin_api_key"

def create_case(client):
    return client.post("/api/case/create", 
                       content_type='application/json',
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Test Case caseadmin"})

def create_privileged_case(client):
    return client.post("/api/case/create", 
                       content_type='application/json',
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "Test Privileged Case caseadmin", "privileged_case": True})

def test_create_case(client):
    response = create_case(client)
    assert response.status_code == 201
    assert "case_id" in response.json

def test_create_privileged_case(client):
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    assert create_response.status_code == 201
    
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
    assert f"Case {case_id} edited".encode() in response.data
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["privileged_case"] == True

def test_edit_privileged_case_to_non_privileged(client):
    """Test editing a privileged case to make it non-privileged"""
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"privileged_case": False}
                        )
    assert response.status_code == 200
    assert f"Case {case_id} edited".encode() in response.data
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["privileged_case"] == False

def test_get_privileged_case(client):
    """Test getting privileged case details"""
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["title"] == "Test Privileged Case caseadmin"
    assert response.json["privileged_case"] == True

def test_edit_other_user_case_to_privileged(client):
    from app.db_class.db import User
    response = client.post("/api/case/create", 
                           content_type='application/json',
                           headers={"X-API-KEY": "admin_api_key"},
                           json={"title": "Test Case admin"}
                        )
    assert response.status_code == 201
    case_id = response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": "admin_api_key"},
                           json={"oid": '5'}
                        )
    assert response.status_code == 200
    
    # Edit case to privileged as case admin
    response = client.post(f"/api/case/{case_id}/edit", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"privileged_case": True}
                        )
    assert response.status_code == 200
    assert f"Case {case_id} edited".encode() in response.data
    
    response = client.get(f"/api/case/{case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["privileged_case"] == True

def test_complete_case(client):
    """Test completing a case"""
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert f"Case {case_id} completed".encode() in response.data

def test_complete_privileged_case(client):
    """Test completing a privileged case"""
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.get(f"/api/case/{case_id}/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert f"Case {case_id} completed".encode() in response.data

def test_create_template(client):
    """Test creating template from case"""
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/create_template", headers={"X-API-KEY": API_KEY},
                           json={"title_template": "Template from case caseadmin"})
    assert response.status_code == 201
    assert response.json["template_id"] == 1

def test_create_template_from_privileged_case(client):
    """Test creating template from privileged case"""
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/create_template", headers={"X-API-KEY": API_KEY},
                           json={"title_template": "Template from privileged case caseadmin"})
    assert response.status_code == 201
    assert response.json["template_id"] == 1

def test_fork_case(client):
    """Test forking a regular case"""
    create_response = create_case(client)
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

def test_fork_privileged_case(client):
    """Test forking a privileged case"""
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/fork",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"case_title_fork": "Test fork privileged case"}
                        )
    assert response.status_code == 201
    new_case_id = response.json["new_case_id"]

    response = client.get(f"/api/case/{new_case_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["title"] == "Test fork privileged case"

##########
## TASK ##
##########

def test_create_task(client):
    """Test creating task in regular case"""
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task caseadmin"}
                        )
    assert response.status_code == 201
    assert b"Task 1 created for case id:" in response.data

def test_create_task_in_privileged_case(client):
    """Test creating task in privileged case"""
    create_response = create_privileged_case(client)
    case_id = create_response.json["case_id"]
    
    response = client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task in privileged case"}
                        )
    assert response.status_code == 201
    assert b"Task 1 created for case id:" in response.data

def test_edit_task(client):
    """Test editing a task"""
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    # Create a task first
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task caseadmin"})
    
    response = client.post("/api/task/1/edit",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test edit task caseadmin"}
                        )
    assert response.status_code == 200
    assert b"Task 1 edited" in response.data

    response = client.get("/api/task/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Test edit task caseadmin" in response.data

def test_complete_task(client):
    """Test completing a task"""
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    # Create a task first
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task caseadmin"})
    
    response = client.get("/api/task/1/complete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Task 1 completed" in response.data

def test_delete_task(client):
    """Test deleting a task"""
    create_response = create_case(client)
    case_id = create_response.json["case_id"]
    
    # Create a task first
    client.post(f"/api/case/{case_id}/create_task",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"title": "Test task caseadmin"})
    
    response = client.get("/api/task/1/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Task deleted" in response.data
