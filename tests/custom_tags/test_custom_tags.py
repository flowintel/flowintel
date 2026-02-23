API_KEY = "admin_api_key"

def create_custom_tag(client, name="Test custom tag", color="#FFFFFF", icon=None):
    """Helper function to create a test custom tag"""
    json_data = {
        'name': name,
        "color": color
    }
    if icon:
        json_data["icon"] = icon
    
    response = client.post(
        "/api/custom_tags/add",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json=json_data
    )
    return response

def test_create_custom_tag(client):
    """Admin should be able to create custom tags"""
    response = create_custom_tag(client)
    assert response.status_code == 201
    assert "New custom tag created" in response.json["message"]

def test_create_custom_tag_with_icon(client):
    """Admin should be able to create custom tags with icons"""
    response = create_custom_tag(client, name="Icon Tag", color="#FF0000", icon="fa-solid fa-tag")
    assert response.status_code == 201
    assert "New custom tag created" in response.json["message"]

def test_create_custom_tag_no_data(client):
    """Admin should get error when no data provided"""
    response = client.post(
        "/api/custom_tags/add",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={}
    )
    assert response.status_code == 400

def test_create_custom_tag_missing_name(client):
    """Admin should get error when name is missing"""
    response = client.post(
        "/api/custom_tags/add",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={"color": "#FFFFFF"}
    )
    assert response.status_code == 400

def test_create_custom_tag_missing_color(client):
    """Admin should get error when color is missing"""
    response = client.post(
        "/api/custom_tags/add",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={"name": "Test"}
    )
    assert response.status_code == 400

def test_get_all_custom_tags(client):
    """Admin should be able to get all custom tags"""
    create_custom_tag(client)
    response = client.get("/api/custom_tags/all", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert isinstance(response.json, list)

def test_get_custom_tag(client):
    """Admin should be able to get a specific custom tag"""
    create_response = create_custom_tag(client)
    assert create_response.status_code == 201
    
    response = client.get("/api/custom_tags/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "name" in response.json
    assert response.json["name"] == "Test custom tag"

def test_get_nonexistent_custom_tag(client):
    """Admin should get error when getting non-existent custom tag"""
    response = client.get("/api/custom_tags/9999", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404
    assert "doesn't exist" in response.json["message"]

def test_edit_custom_tag(client):
    """Admin should be able to edit custom tags"""
    create_response = create_custom_tag(client)
    assert create_response.status_code == 201
    
    response = client.post(
        "/api/custom_tags/1/edit",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={
            'name': "Edited Test custom tag",
            "color": "#FFFFF3"
        }
    )
    assert response.status_code == 200
    assert "Custom tag edited" in response.json["message"]

    # Verify the edit
    response = client.get("/api/custom_tags/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "Edited Test custom tag" in response.json["name"]
    assert "#FFFFF3" == response.json["color"]

def test_edit_custom_tag_with_icon(client):
    """Admin should be able to edit custom tags including icon"""
    create_response = create_custom_tag(client)
    assert create_response.status_code == 201
    
    response = client.post(
        "/api/custom_tags/1/edit",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={
            'name': "Edited with icon",
            "color": "#00FF00",
            "icon": "fa-solid fa-star"
        }
    )
    assert response.status_code == 200
    
    # Verify the edit
    response = client.get("/api/custom_tags/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert response.json["icon"] == "fa-solid fa-star"

def test_edit_nonexistent_custom_tag(client):
    """Admin should get error when editing non-existent custom tag"""
    response = client.post(
        "/api/custom_tags/9999/edit",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={
            'name': "Edit Test",
            "color": "#FFFFFF"
        }
    )
    assert response.status_code == 404
    assert "not found" in response.json["message"]

def test_edit_custom_tag_no_data(client):
    """Admin should get error when no data provided for edit"""
    create_response = create_custom_tag(client)
    assert create_response.status_code == 201
    
    response = client.post(
        "/api/custom_tags/1/edit",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={}
    )
    assert response.status_code == 400

def test_delete_custom_tag(client):
    """Admin should be able to delete custom tags"""
    create_response = create_custom_tag(client)
    assert create_response.status_code == 201
    
    response = client.get("/api/custom_tags/1/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "Custom Tag deleted" in response.json["message"]
    
    # Verify deletion
    response = client.get("/api/custom_tags/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404

def test_delete_nonexistent_custom_tag(client):
    """Admin should get error when deleting non-existent custom tag"""
    response = client.get("/api/custom_tags/9999/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404
    assert "doesn't exist" in response.json["message"]

def test_custom_tag_operations_no_api_key(client):
    """Operations should fail without API key"""
    # Test create without API key
    response = client.post("/api/custom_tags/add", json={"name": "Test", "color": "#FFFFFF"})
    assert response.status_code == 403
    
    # Test edit without API key
    response = client.post("/api/custom_tags/1/edit", json={"name": "Test", "color": "#FFFFFF"})
    assert response.status_code == 403
    
    # Test delete without API key
    response = client.get("/api/custom_tags/1/delete")
    assert response.status_code == 403

