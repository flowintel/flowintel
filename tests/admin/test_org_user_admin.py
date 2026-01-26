
from app.utils.utils import get_user_api
import time

API_KEY = "admin_api_key"

def create_test_user(client):
    """Helper function to create a test user"""
    email = f"test{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": 2}
                        )
    return response

def create_test_org(client):
    """Helper function to create a test organisation"""
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for test"}
                        )
    return response

###########
## Users ##
###########

def test_create_user(client):
    """Admin should be able to create users"""
    response = create_test_user(client)
    assert response.status_code == 201
    assert "User created" in response.json["message"]
    assert "id" in response.json

def test_create_user_wrong_role(client):
    """Admin should get error when providing invalid role"""
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": "invalid"}
                        )
    assert response.status_code == 400
    assert b"Role not identified" in response.data

def test_create_user_existing_email(client):
    """Admin should get error when creating user with existing email"""
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "admin@admin.admin", "password": "test", "role": 2}
                        )
    assert response.status_code == 400
    assert b"Email already exists" in response.data

def test_create_user_missing_fields(client):
    """Admin should get error when required fields are missing"""
    # Missing email
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "password": "test", "role": 2}
                        )
    assert response.status_code == 400
    assert b"email" in response.data

def test_edit_user(client):
    """Admin should be able to edit users"""
    create_response = create_test_user(client)
    user_id = create_response.json["id"]
    
    response = client.post(f"/api/admin/edit_user/{user_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"last_name": "modified"}
                        )
    assert response.status_code == 200
    assert b"User edited" in response.data

    response = client.get(f"/api/admin/user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["last_name"] == "modified"

def test_edit_user_wrong_role(client):
    """Admin should get error when assigning invalid role"""
    create_response = create_test_user(client)
    user_id = create_response.json["id"]
    
    response = client.post(f"/api/admin/edit_user/{user_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"role": "invalid"}
                        )
    assert response.status_code == 400
    assert b"Role not identified" in response.data

def test_edit_user_existing_email(client):
    """Admin should get error when changing email to existing one"""
    create_response = create_test_user(client)
    user_id = create_response.json["id"]
    
    response = client.post(f"/api/admin/edit_user/{user_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"email": "admin@admin.admin"}
                        )
    assert response.status_code == 400
    assert b"Email already exists" in response.data

def test_edit_nonexistent_user(client):
    """Admin should get error when editing non-existent user"""
    response = client.post("/api/admin/edit_user/9999", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"last_name": "test"}
                        )
    assert response.status_code == 404
    assert b"User not found" in response.data

def test_delete_user(client):
    """Admin should be able to delete users"""
    create_response = create_test_user(client)
    user_id = create_response.json["id"]
    
    response = client.get(f"/api/admin/delete_user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"User deleted" in response.data

def test_delete_self(client):
    """Admin should NOT be able to delete their own account"""
    with client.application.app_context():
        admin_user = get_user_api(API_KEY)
        admin_id = admin_user.id
    
    response = client.get(f"/api/admin/delete_user/{admin_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403
    assert b"You cannot delete your own account" in response.data

def test_get_users(client):
    """Admin should be able to get all users"""
    response = client.get("/api/admin/users", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "users" in response.json

def test_get_specific_user(client):
    """Admin should be able to get specific user details"""
    create_response = create_test_user(client)
    user_id = create_response.json["id"]
    expected_email = create_response.json.get("email") or "test@test.test"
    
    response = client.get(f"/api/admin/user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "@test.test" in response.json["email"]

#########
## Org ##
#########

def test_create_org(client):
    """Admin should be able to create organisations"""
    response = create_test_org(client)
    assert response.status_code == 201
    assert b"Org created" in response.data

def test_create_org_duplicate_name(client):
    """Admin should get error when creating org with existing name"""
    create_test_org(client)
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for test"}
                        )
    assert response.status_code == 400
    assert b"Name already exists" in response.data

def test_edit_org(client):
    """Admin should be able to edit organisations"""
    create_response = create_test_org(client)
    # Extract org ID from response
    org_id = create_response.json["org_id"]
    
    response = client.post(f"/api/admin/edit_org/{org_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org modified"}
                        )
    assert response.status_code == 200
    assert b"Org edited" in response.data

    response = client.get(f"/api/admin/org/{org_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Org modified" in response.data

def test_delete_org(client):
    """Admin should be able to delete organisations"""
    create_response = create_test_org(client)
    org_id = create_response.json["org_id"]

    response = client.get(f"/api/admin/delete_org/{org_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Org deleted" in response.data

def test_get_orgs(client):
    """Admin should be able to list all organisations"""
    response = client.get("/api/admin/orgs", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "orgs" in response.json

##########
## Role ##
##########

def test_get_roles(client):
    """Admin should be able to list all roles"""
    response = client.get("/api/admin/roles", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "roles" in response.json
