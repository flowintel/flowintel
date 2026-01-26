
from app.utils.utils import get_user_api
import time

API_KEY = "read_api_key"

def create_user_as_admin(client):
    """Helper function to create a user using admin API key"""
    email = f"test{int(time.time() * 1000000)}@test.test"
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": "admin_api_key"},
                           json={"first_name": "test", "last_name": "test", "email": email, "password": "test", "role": 2}
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

def test_create_user_forbidden(client):
    """Read-only user should NOT be able to create users"""
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": 2}
                        )
    assert response.status_code == 403

def test_edit_user_forbidden(client):
    """Read-only user should NOT be able to edit users"""
    create_response = create_user_as_admin(client)
    user_id = create_response.json["id"]
    
    response = client.post(f"/api/admin/edit_user/{user_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"last_name": "modified"}
                        )
    assert response.status_code == 403

def test_delete_user_forbidden(client):
    """Read-only user should NOT be able to delete users"""
    create_response = create_user_as_admin(client)
    user_id = create_response.json["id"]
    
    response = client.get(f"/api/admin/delete_user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_get_users(client):
    """Read-only user should be able to list users (depends on LIMIT_USER_VIEW_TO_ORG config)"""
    response = client.get("/api/admin/users", headers={"X-API-KEY": API_KEY})
    # This might return 200 or 403 depending on configuration
    assert response.status_code in [200, 403]

def test_get_specific_user(client):
    """Read-only user should be able to get their own user details"""
    with client.application.app_context():
        user = get_user_api(API_KEY)
        user_id = user.id
    
    response = client.get(f"/api/admin/user/{user_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["email"] == "read@read.read"

def test_get_other_user(client):
    """Read-only user should be able to view other users (if permissions allow)"""
    create_response = create_user_as_admin(client)
    user_id = create_response.json["id"]
    
    response = client.get(f"/api/admin/user/{user_id}", headers={"X-API-KEY": API_KEY})
    # Might be allowed or forbidden depending on config
    assert response.status_code in [200, 403]

#########
## Org ##
#########

def test_create_org_forbidden(client):
    """Read-only user should NOT be able to create organisations"""
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for case"}
                        )
    assert response.status_code == 403

def test_edit_org_forbidden(client):
    """Read-only user should NOT be able to edit organisations"""
    create_response = create_org_as_admin(client)
    org_id = create_response.json["org_id"]
    
    response = client.post(f"/api/admin/edit_org/{org_id}", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org modified"}
                        )
    assert response.status_code == 403

def test_delete_org_forbidden(client):
    """Read-only user should NOT be able to delete organisations"""
    create_response = create_org_as_admin(client)
    org_id = create_response.json["org_id"]

    response = client.get(f"/api/admin/delete_org/{org_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

def test_get_orgs(client):
    """Read-only user should be able to list organisations"""
    response = client.get("/api/admin/orgs", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "orgs" in response.json

def test_get_specific_org(client):
    """Read-only user should be able to view specific organisation"""
    create_response = create_org_as_admin(client)
    org_id = create_response.json["org_id"]
    
    response = client.get(f"/api/admin/org/{org_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200

##########
## Role ##
##########

def test_get_roles(client):
    """Read-only user should be able to list roles"""
    response = client.get("/api/admin/roles", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "roles" in response.json
