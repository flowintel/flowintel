API_KEY = "admin_api_key"

def test_add(client):
    response = client.post(
        "/api/custom_tags/add",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={
            'name': "Test custom tag",
            "color": "#FFFFFF"
        }
    )
    assert response.status_code == 201

def test_delete(client):
    test_add(client)
    response = client.get("/api/custom_tags/1/delete", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and "Custom Tag deleted" in response.json["message"]

def test_edit(client):
    test_add(client)
    response = client.post(
        "/api/custom_tags/1/edit",
        content_type='application/json',
        headers={"X-API-KEY": API_KEY},
        json={
            'name': "Edit Test custom tag",
            "color": "#FFFFF3"
        }
    )
    assert response.status_code == 200 and "Custom tag edited" in response.json["message"]

    response = client.get("/api/custom_tags/1", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200 and "Edit Test custom tag" in response.json["name"] and "#FFFFF3" == response.json["color"]
