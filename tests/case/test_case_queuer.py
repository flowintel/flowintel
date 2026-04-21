# Tests for the Queuer / QueueAdmin four-eye task approval workflow.
# In a privileged case a Queuer's tasks start in "Requested" status and
# can only be approved, rejected or edited by a QueueAdmin (or Admin).

ADMIN_KEY = "admin_api_key"
QUEUER_KEY = "queuer_api_key"
QUEUE_ADMIN_KEY = "queue_admin_api_key"

# Queuer is user 8, org 8
QUEUER_ORG_ID = 8
# QueueAdmin is user 7, org 7
QUEUE_ADMIN_ORG_ID = 7

# Status IDs
STATUS_CREATED = 1
STATUS_ONGOING = 2
STATUS_REQUESTED = 7
STATUS_APPROVED = 8
STATUS_REJECTED = 5


def create_privileged_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"title": "Privileged Case for queuer test",
                             "privileged_case": True})


def create_normal_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"title": "Normal Case for queuer test"})


def add_org_to_case(client, case_id, org_id):
    return client.post(f"/api/case/{case_id}/add_org",
                       content_type="application/json",
                       headers={"X-API-KEY": ADMIN_KEY},
                       json={"oid": str(org_id)})


def create_task_as(client, case_id, api_key, title="Test task"):
    return client.post(f"/api/case/{case_id}/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": api_key},
                       json={"title": title})


def setup_privileged_case_with_queuer(client):
    resp = create_privileged_case(client)
    case_id = resp.json["case_id"]
    add_org_to_case(client, case_id, QUEUER_ORG_ID)
    return case_id


def setup_privileged_case_with_queue_admin(client):
    resp = create_privileged_case(client)
    case_id = resp.json["case_id"]
    add_org_to_case(client, case_id, QUEUE_ADMIN_ORG_ID)
    return case_id


def setup_privileged_case_with_both(client):
    resp = create_privileged_case(client)
    case_id = resp.json["case_id"]
    add_org_to_case(client, case_id, QUEUER_ORG_ID)
    add_org_to_case(client, case_id, QUEUE_ADMIN_ORG_ID)
    return case_id


########################################
## Queuer: task creation in priv case ##
########################################

def test_queuer_task_in_privileged_case_gets_requested_status(client):
    case_id = setup_privileged_case_with_queuer(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Queuer requested task")
    assert resp.status_code == 201
    task_id = resp.json["task_id"]

    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUER_KEY})
    assert resp.status_code == 200
    assert resp.json["task"]["status_id"] == STATUS_REQUESTED


def test_queuer_task_in_normal_case_gets_created_status(client):
    resp = create_normal_case(client)
    case_id = resp.json["case_id"]
    add_org_to_case(client, case_id, QUEUER_ORG_ID)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Queuer normal task")
    assert resp.status_code == 201
    task_id = resp.json["task_id"]

    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUER_KEY})
    assert resp.status_code == 200
    assert resp.json["task"]["status_id"] == STATUS_CREATED


###########################################
## Queuer: restricted task modifications ##
###########################################

def test_queuer_edit_requested_task_denied(client):
    case_id = setup_privileged_case_with_queuer(client)

    resp = create_task_as(client, case_id, QUEUER_KEY)
    task_id = resp.json["task_id"]

    resp = client.post(f"/api/task/{task_id}/edit",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUER_KEY},
                       json={"title": "Queuer tries to edit"})
    assert resp.status_code == 403
    assert b"Requested or Rejected status" in resp.data


def test_queuer_complete_requested_task_denied(client):
    case_id = setup_privileged_case_with_queuer(client)

    resp = create_task_as(client, case_id, QUEUER_KEY)
    task_id = resp.json["task_id"]

    resp = client.get(f"/api/task/{task_id}/complete",
                      headers={"X-API-KEY": QUEUER_KEY})
    assert resp.status_code == 403
    assert b"restricted status" in resp.data


def test_queuer_delete_requested_task_denied(client):
    case_id = setup_privileged_case_with_queuer(client)

    resp = create_task_as(client, case_id, QUEUER_KEY)
    task_id = resp.json["task_id"]

    resp = client.get(f"/api/task/{task_id}/delete",
                      headers={"X-API-KEY": QUEUER_KEY})
    assert resp.status_code == 403
    assert b"restricted status" in resp.data


def test_queuer_change_status_requested_task_denied(client):
    case_id = setup_privileged_case_with_queuer(client)

    resp = create_task_as(client, case_id, QUEUER_KEY)
    task_id = resp.json["task_id"]

    resp = client.post(f"/api/task/{task_id}/change_status",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUER_KEY},
                       json={"status_id": STATUS_ONGOING})
    assert resp.status_code == 403
    assert b"restricted status" in resp.data


############################################
## QueueAdmin: task creation in priv case ##
############################################

def test_queue_admin_task_in_privileged_case_gets_created_status(client):
    case_id = setup_privileged_case_with_queue_admin(client)

    resp = create_task_as(client, case_id, QUEUE_ADMIN_KEY, "QueueAdmin task")
    assert resp.status_code == 201
    task_id = resp.json["task_id"]

    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUE_ADMIN_KEY})
    assert resp.status_code == 200
    assert resp.json["task"]["status_id"] == STATUS_CREATED


###########################################
## QueueAdmin: manage restricted tasks   ##
###########################################

def test_queue_admin_edit_requested_task(client):
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to edit")
    task_id = resp.json["task_id"]

    resp = client.post(f"/api/task/{task_id}/edit",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                       json={"title": "QueueAdmin edited this"})
    assert resp.status_code == 200
    assert b"edited" in resp.data

    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUE_ADMIN_KEY})
    assert resp.status_code == 200
    assert resp.json["task"]["title"] == "QueueAdmin edited this"


def test_queue_admin_approve_requested_task(client):
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to approve")
    task_id = resp.json["task_id"]

    # Verify it starts as Requested
    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUE_ADMIN_KEY})
    assert resp.json["task"]["status_id"] == STATUS_REQUESTED

    resp = client.post(f"/api/task/{task_id}/change_status",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                       json={"status_id": STATUS_APPROVED})
    assert resp.status_code == 200
    assert b"Status changed" in resp.data

    # Verify the status changed
    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUE_ADMIN_KEY})
    assert resp.json["task"]["status_id"] == STATUS_APPROVED


def test_queue_admin_reject_requested_task(client):
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to reject")
    task_id = resp.json["task_id"]

    resp = client.post(f"/api/task/{task_id}/change_status",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                       json={"status_id": STATUS_REJECTED})
    assert resp.status_code == 200
    assert b"Status changed" in resp.data

    resp = client.get(f"/api/task/{task_id}", headers={"X-API-KEY": QUEUE_ADMIN_KEY})
    assert resp.json["task"]["status_id"] == STATUS_REJECTED


def test_queue_admin_delete_requested_task(client):
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to delete")
    task_id = resp.json["task_id"]

    resp = client.get(f"/api/task/{task_id}/delete",
                      headers={"X-API-KEY": QUEUE_ADMIN_KEY})
    assert resp.status_code == 200
    assert b"Task deleted" in resp.data


####################################
## Queuer: rejected task handling ##
####################################

def test_queuer_edit_rejected_task_denied(client):
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to be rejected")
    task_id = resp.json["task_id"]

    # QueueAdmin rejects it
    client.post(f"/api/task/{task_id}/change_status",
                content_type="application/json",
                headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                json={"status_id": STATUS_REJECTED})

    # Queuer tries to edit the rejected task
    resp = client.post(f"/api/task/{task_id}/edit",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUER_KEY},
                       json={"title": "Queuer tries to fix rejected task"})
    assert resp.status_code == 403
    assert b"Requested or Rejected status" in resp.data


def test_queuer_change_status_rejected_task_denied(client):
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY)
    task_id = resp.json["task_id"]

    # QueueAdmin rejects it
    client.post(f"/api/task/{task_id}/change_status",
                content_type="application/json",
                headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                json={"status_id": STATUS_REJECTED})

    # Queuer tries to change status
    resp = client.post(f"/api/task/{task_id}/change_status",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUER_KEY},
                       json={"status_id": STATUS_ONGOING})
    assert resp.status_code == 403
    assert b"restricted status" in resp.data


########################################
## Queuer: approved task is unblocked ##
########################################

def test_queuer_can_edit_approved_task(client):
    """Approved task is no longer restricted, queuer can edit it."""
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to approve then edit")
    task_id = resp.json["task_id"]

    # QueueAdmin approves
    client.post(f"/api/task/{task_id}/change_status",
                content_type="application/json",
                headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                json={"status_id": STATUS_APPROVED})

    # Queuer can now edit
    resp = client.post(f"/api/task/{task_id}/edit",
                       content_type="application/json",
                       headers={"X-API-KEY": QUEUER_KEY},
                       json={"title": "Queuer edits approved task"})
    assert resp.status_code == 200
    assert b"edited" in resp.data


def test_queuer_can_complete_approved_task(client):
    """Approved task is no longer restricted, queuer can complete it."""
    case_id = setup_privileged_case_with_both(client)

    resp = create_task_as(client, case_id, QUEUER_KEY, "Task to approve then complete")
    task_id = resp.json["task_id"]

    # QueueAdmin approves
    client.post(f"/api/task/{task_id}/change_status",
                content_type="application/json",
                headers={"X-API-KEY": QUEUE_ADMIN_KEY},
                json={"status_id": STATUS_APPROVED})

    # Queuer can now complete
    resp = client.get(f"/api/task/{task_id}/complete",
                      headers={"X-API-KEY": QUEUER_KEY})
    assert resp.status_code == 200
    assert b"completed" in resp.data
