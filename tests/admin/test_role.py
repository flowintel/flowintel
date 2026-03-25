
API_KEY = "admin_api_key"

def create_test_role(client, name="Test Role"):
    """Helper function to create a test role"""
    response = client.post("/api/admin/add_role",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={
                               "name": name,
                               "description": "Role for testing",
                               "case_admin": True,
                               "queuer": True
                           })
    return response


##########
## Role ##
##########

def test_create_role(client):
    """Admin should be able to create a role"""
    response = create_test_role(client)
    assert response.status_code == 201
    assert "Role created" in response.json["message"]
    assert "role_id" in response.json

def test_create_role_duplicate_name(client):
    """Admin should get error when creating role with existing name"""
    create_test_role(client)
    response = create_test_role(client)
    assert response.status_code == 400
    assert b"Name already exists" in response.data

def test_create_role_missing_name(client):
    """Admin should get error when name is missing"""
    response = client.post("/api/admin/add_role",
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"description": "No name"})
    assert response.status_code == 400
    assert b"Please give a name" in response.data

def test_create_role_permissions(client):
    """Created role should have the correct permissions"""
    create_response = create_test_role(client)
    role_id = create_response.json["role_id"]

    response = client.get("/api/admin/roles", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    roles = response.json["roles"]
    role = next(r for r in roles if r["id"] == role_id)
    assert role["name"] == "Test Role"
    assert role["case_admin"] is True
    assert role["queuer"] is True
    assert role["admin"] is False
    assert role["org_admin"] is False

def test_get_roles(client):
    """Admin should be able to list all roles"""
    response = client.get("/api/admin/roles", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "roles" in response.json
    # At least the 3 system roles should exist
    assert len(response.json["roles"]) >= 3

def test_delete_role(client):
    """Admin should be able to delete a role"""
    create_response = create_test_role(client)
    role_id = create_response.json["role_id"]

    response = client.get(f"/api/admin/delete_role/{role_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"Role deleted" in response.data

def test_delete_system_role(client):
    """Admin should NOT be able to delete a system role"""
    for role_id in [1, 2, 3]:
        response = client.get(f"/api/admin/delete_role/{role_id}", headers={"X-API-KEY": API_KEY})
        assert response.status_code == 400
        assert b"Cannot delete system role" in response.data

def test_delete_role_with_users(client):
    """Admin should NOT be able to delete a role that has users assigned"""
    create_response = create_test_role(client)
    role_id = create_response.json["role_id"]

    # Create a user with this role
    client.post("/api/admin/add_user",
                content_type='application/json',
                headers={"X-API-KEY": API_KEY},
                json={
                    "first_name": "role", "last_name": "test",
                    "email": "roletest@test.test", "password": "test",
                    "role": role_id
                })

    response = client.get(f"/api/admin/delete_role/{role_id}", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 400
    assert b"user(s) still assigned" in response.data

def test_delete_nonexistent_role(client):
    """Admin should get error when deleting non-existent role"""
    response = client.get("/api/admin/delete_role/9999", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404
    assert b"Role not found" in response.data

def test_create_role_no_auth(client):
    """Request without API key should be rejected"""
    response = client.post("/api/admin/add_role",
                           content_type='application/json',
                           json={"name": "Unauthorized Role"})
    assert response.status_code == 403

def test_create_role_non_admin(client):
    """Non-admin user should NOT be able to create a role"""
    response = client.post("/api/admin/add_role",
                           content_type='application/json',
                           headers={"X-API-KEY": "editor_api_key"},
                           json={"name": "Unauthorized Role"})
    assert response.status_code == 403

def test_delete_role_non_admin(client):
    """Non-admin user should NOT be able to delete a role"""
    response = client.get("/api/admin/delete_role/4",
                          headers={"X-API-KEY": "editor_api_key"})
    assert response.status_code == 403
