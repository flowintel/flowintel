API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client, title="Calendar Test Case"):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": title})


def create_task(client, case_id, title="Calendar Test Task"):
    return client.post(f"/api/case/{case_id}/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": title})


######################
## Calendar feed ##
######################

def test_calendar_feed(client):
    """Editor should be able to download the calendar feed"""
    create_case(client)

    response = client.get("/api/calendar/feed",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "BEGIN:VCALENDAR" in body
    assert "END:VCALENDAR" in body


def test_calendar_feed_contains_case(client):
    """Feed should contain the case title as a VEVENT"""
    create_case(client, "My Calendar Case")

    response = client.get("/api/calendar/feed",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "[Case] My Calendar Case" in body
    assert "BEGIN:VEVENT" in body


def test_calendar_feed_contains_task(client):
    """Feed should contain tasks assigned to the user"""
    case_id = create_case(client, "Task Parent Case").json["case_id"]
    task_resp = create_task(client, case_id, "My Calendar Task")
    task_id = task_resp.json["task_id"]

    # Assign current user to the task so it appears in their feed
    assign = client.get(f"/api/task/{task_id}/take_task",
                        headers={"X-API-KEY": API_KEY})
    assert assign.status_code == 200

    response = client.get("/api/calendar/feed",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "[Task] My Calendar Task" in body


def test_calendar_feed_empty(client):
    """Feed with no cases or tasks should still be valid ICS"""
    response = client.get("/api/calendar/feed",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "BEGIN:VCALENDAR" in body
    assert "VEVENT" not in body


def test_calendar_feed_no_api_key(client):
    """Accessing the feed without an API key should be denied"""
    response = client.get("/api/calendar/feed")
    assert response.status_code == 403


def test_calendar_feed_read_only(client):
    """Read-only user should also be able to access the feed"""
    response = client.get("/api/calendar/feed",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "BEGIN:VCALENDAR" in body
