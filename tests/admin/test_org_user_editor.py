
API_KEY = "editor_api_key"

def create_user(client):
    client.post("/api/admin/add_user", 
                content_type='application/json',
                headers={"X-API-KEY": "admin_api_key"},
                json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": "2"}
            )

def test_create_user_editor(client):
    response = client.post("/api/admin/add_user", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"first_name": "test", "last_name": "test", "email": "test@test.test", "password": "test", "role": "2"}
                        )
    assert response.status_code == 403

def test_edit_user(client):
    create_user(client)
    response = client.post("/api/admin/edit_user/4", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"last_name": "tes"}
                        )
    assert response.status_code == 403

def test_delete_user(client):
    create_user(client)
    response = client.get("/api/admin/delete_user/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403

#########
## Org ##
#########

def create_org(client):
    client.post("/api/admin/add_org", 
                content_type='application/json',
                headers={"X-API-KEY": "admin_api_key"},
                json={"name": "Org for case"}
            )

def test_create_org_editor(client):
    response = client.post("/api/admin/add_org", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for case"}
                        )
    assert response.status_code == 403


def test_edit_org(client):
    create_org(client)
    response = client.post("/api/admin/edit_org/4", 
                           content_type='application/json',
                           headers={"X-API-KEY": API_KEY},
                           json={"name": "Org for test"}
                        )
    assert response.status_code == 403

def test_delete_user(client):
    create_org(client)

    response = client.get("/api/admin/delete_org/4", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 403