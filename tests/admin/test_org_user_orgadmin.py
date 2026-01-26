
from app.utils.utils import get_user_api
import time

API_KEY = "orgadmin_api_key"

def get_orgadmin_org_id(client):
    with client.application.app_context():
        return get_user_api(API_KEY).org_id

def create_user_as_admin(client, org_id=None):
    """Helper function to create a user using admin API key"""
    if org_id is None:
        org_id = get_orgadmin_org_id(client)
    
    email = f"test{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": "admin_api_key"},
                           json={"first_name": "test", "last_name": "test", "email": email, "password": "test", "role": 2, "org": org_id}
                          )
    return response

def create_org_as_admin(client):
    """Helper function to create an org using admin API key"""
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": "admin_api_key"},
                           json={"name": "Org for test"}
                          )
    return response

###########
## Users ##
###########

def test_create_user_in_own_org(client):
    """OrgAdmin should be able to create users in their own organization"""
    org_id = get_orgadmin_org_id(client)
    email = f"user{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": email, "password": "test", "role": 2, "org": org_id}
                        )
    assert response.status_code == 201
    assert "User created" in response.json["message"]

def test_create_user_in_different_org(client):
    """OrgAdmin should NOT be able to create users in other organizations"""
    with client.application.app_context():
        admin_user = get_user_api("admin_api_key")
        different_org_id = admin_user.org_id
    
    email = f"user{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": email, "password": "test", "role": 2, "org": different_org_id}
                        )
    assert response.status_code == 400
    assert b"OrgAdmin can only add users to their own organization" in response.data

def test_create_user_with_admin_role(client):
    """OrgAdmin should NOT be able to assign Admin role"""
    org_id = get_orgadmin_org_id(client)
    email = f"user{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": email, "password": "test", "role": 1, "org": org_id}
                        )
    assert response.status_code == 400
    assert b"OrgAdmin cannot assign Admin role" in response.data

def test_create_user_without_org(client):
    """OrgAdmin creating user without org should default to their own org"""
    org_id = get_orgadmin_org_id(client)
    email = f"user{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": email, "password": "test", "role": 2}
                        )
    assert response.status_code == 201
    user_id = response.json["id"]
    
    response = client.get(f"/api/admin/user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["org_id"] == org_id

def test_create_user_existing_email(client):
    """OrgAdmin should get proper error for duplicate email"""
    org_id = get_orgadmin_org_id(client)
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "admin@admin.admin", "password": "test", "role": 2, "org": org_id}
                        )
    assert response.status_code == 400
    assert b"Email already exists" in response.data

def test_edit_user_in_own_org(client):
    """OrgAdmin should be able to edit users in their own organization"""
    create_response = create_user_as_admin(client)
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

def test_edit_user_in_different_org(client):
    """OrgAdmin should NOT be able to edit users from other organizations"""
    with client.application.app_context():
        admin_user = get_user_api("admin_api_key")
        admin_user_id = admin_user.id
    
    response = client.post(f"/api/admin/edit_user/{admin_user_id}",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"last_name": "hacked"}
                        )
    assert response.status_code == 403
    assert b"OrgAdmin can only edit users from their own organization" in response.data

def test_edit_user_assign_admin_role(client):
    """OrgAdmin should NOT be able to assign Admin role when editing"""
    create_response = create_user_as_admin(client)
    user_id = create_response.json["id"]
    
    response = client.post(f"/api/admin/edit_user/{user_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"role": 1}
                        )
    assert response.status_code == 400
    assert b"OrgAdmin cannot assign Admin role" in response.data

def test_edit_user_move_to_different_org(client):
    """OrgAdmin should NOT be able to move users to different organization"""
    create_response = create_user_as_admin(client)
    user_id = create_response.json["id"]
    
    with client.application.app_context():
        admin_user = get_user_api("admin_api_key")
        different_org_id = admin_user.org_id
    
    response = client.post(f"/api/admin/edit_user/{user_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"org": different_org_id}
                        )
    assert response.status_code == 403
    assert b"OrgAdmin cannot move users to different organization" in response.data

def test_delete_user_in_own_org(client):
    """OrgAdmin should be able to delete users in their own organization"""
    create_response = create_user_as_admin(client)
    user_id = create_response.json["id"]
    
    response = client.get(f"/api/admin/delete_user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"User deleted" in response.data

def test_delete_user_in_different_org(client):
    """OrgAdmin should NOT be able to delete users from other organizations"""
    with client.application.app_context():
        admin_user = get_user_api("admin_api_key")
        admin_user_id = admin_user.id
    
    response = client.get(f"/api/admin/delete_user/{admin_user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403
    assert b"OrgAdmin can only delete users from their own organization" in response.data

def test_delete_self(client):
    """OrgAdmin should NOT be able to delete their own account"""
    with client.application.app_context():
        user = get_user_api(API_KEY)
        user_id = user.id
    
    response = client.get(f"/api/admin/delete_user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403
    assert b"You cannot delete your own account" in response.data

#########
## Org ##
#########

def test_create_org_forbidden(client):
    """OrgAdmin should NOT be able to create organisations"""
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for case"}
                        )
    assert response.status_code == 403

def test_edit_org_forbidden(client):
    """OrgAdmin should NOT be able to edit organisations"""
    create_response = create_org_as_admin(client)
    org_id = create_response.json["org_id"]
    
    response = client.post(f"/api/admin/edit_org/{org_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org modified"}
                        )
    assert response.status_code == 403

def test_delete_org_forbidden(client):
    """OrgAdmin should NOT be able to delete organisations"""
    create_response = create_org_as_admin(client)
    org_id = create_response.json["org_id"]
    
    response = client.get(f"/api/admin/delete_org/{org_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

###############
## Get Users ##
###############

def test_get_users_limited_to_org(client):
    """OrgAdmin should only see users from their own organization when LIMIT_USER_VIEW_TO_ORG is enabled"""
    # This test assumes LIMIT_USER_VIEW_TO_ORG config is True
    org_id = get_orgadmin_org_id(client)
    response = client.get("/api/admin/users", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    
    # Should only contain users from OrgAdmin's org
    users = response.json["users"]
    for user in users:
        print(user)
        assert user["org_id"] == org_id

def test_get_specific_user_in_own_org(client):
    """OrgAdmin should be able to get details of users in their own organization"""
    with client.application.app_context():
        user = get_user_api(API_KEY)
        user_id = user.id
        org_id = user.org_id
    
    response = client.get(f"/api/admin/user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["org_id"] == org_id

def test_get_orgs(client):
    """OrgAdmin should be able to list organisations"""
    response = client.get("/api/admin/orgs", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "orgs" in response.json

def test_get_roles(client):
    """OrgAdmin should be able to list roles"""
    response = client.get("/api/admin/roles", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "roles" in response.json
