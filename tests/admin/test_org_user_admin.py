
API_KEY = "admin_api_key"

def test_create_user(client):
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": "2"}
                        )
    assert response.status_code == 201 and response.json["message"] == "User created 4" and response.json["id"] == 4

def test_create_user_wrong_role(client):
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": "test"}
                        )
    assert response.status_code == 400 and b"Role not identified" in response.data

def test_create_user_existing_email(client):
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "admin@admin.admin", "password": "test", "role": "2"}
                        )
    assert response.status_code == 400 and b"Email already exist" in response.data

def test_edit_user(client):
    test_create_user(client)
    response = client.post("/api/admin/edit_user/4", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"last_name": "tes"}
                        )
    assert response.status_code == 200 and b"User edited" in response.data

    response = client.get("/api/admin/user/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and response.json["last_name"] == "tes"

def test_edit_user_wrong_role(client):
    test_create_user(client)
    response = client.post("/api/admin/edit_user/4", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"role": "test"}
                        )
    assert response.status_code == 400 and b"Role not identified" in response.data

    response = client.get("/api/admin/user/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and not response.json["role_id"] == "test"

def test_edit_user_existing_email(client):
    test_create_user(client)
    response = client.post("/api/admin/edit_user/4", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"email": "admin@admin.admin"}
                        )
    assert response.status_code == 400 and b"Email already exist" in response.data

    response = client.get("/api/admin/user/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and not response.json["email"] == "admin@admin.admin"

def test_delete_user(client):
    test_create_user(client)
    response = client.get("/api/admin/delete_user/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"User deleted" in response.data

# #########
# ## Org ##
# #########

def test_create_org(client):
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for case"}
                        )
    assert response.status_code == 201 and b"Org created: 4" in response.data


def test_edit_org(client):
    test_create_org(client)
    response = client.post("/api/admin/edit_org/4", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for test"}
                        )
    assert response.status_code == 200 and b"Org edited" in response.data

    response = client.get("/api/admin/org/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Org for test" in response.data

def test_delete_user(client):
    test_create_org(client)

    response = client.get("/api/admin/delete_org/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and b"Org deleted" in response.data