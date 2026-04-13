import io

API_KEY = "editor_api_key"
READ_KEY = "read_api_key"


def create_case(client):
    return client.post("/api/case/create",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "File Test Case"})


def create_task(client, case_id):
    return client.post(f"/api/case/{case_id}/create_task",
                       content_type="application/json",
                       headers={"X-API-KEY": API_KEY},
                       json={"title": "File Test Task"})


def upload_file(client, url, api_key=API_KEY, filename="test.txt", content=b"hello world"):
    data = {"file": (io.BytesIO(content), filename)}
    return client.post(url,
                       content_type="multipart/form-data",
                       headers={"X-API-KEY": api_key},
                       data=data)


##########################
## Case file operations ##
##########################

def test_upload_case_file(client):
    """Editor should be able to upload a file to a case"""
    case_id = create_case(client).json["case_id"]

    response = upload_file(client, f"/api/case/{case_id}/upload_file")
    assert response.status_code == 200
    assert "File(s) added" in response.json["message"]


def test_list_case_files(client):
    """Editor should be able to list files on a case"""
    case_id = create_case(client).json["case_id"]
    upload_file(client, f"/api/case/{case_id}/upload_file")

    response = client.get(f"/api/case/{case_id}/files", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "files" in response.json
    assert len(response.json["files"]) == 1


def test_download_case_file(client):
    """Editor should be able to download a file from a case"""
    case_id = create_case(client).json["case_id"]
    upload_file(client, f"/api/case/{case_id}/upload_file")

    files = client.get(f"/api/case/{case_id}/files", headers={"X-API-KEY": API_KEY})
    file_id = files.json["files"][0]["id"]

    response = client.get(f"/api/case/{case_id}/download_file/{file_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"hello world" in response.data


def test_delete_case_file(client):
    """Editor should be able to delete a file from a case"""
    case_id = create_case(client).json["case_id"]
    upload_file(client, f"/api/case/{case_id}/upload_file")

    files = client.get(f"/api/case/{case_id}/files", headers={"X-API-KEY": API_KEY})
    file_id = files.json["files"][0]["id"]

    response = client.get(f"/api/case/{case_id}/delete_file/{file_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "File deleted" in response.json["message"]


def test_upload_case_file_no_content(client):
    """Uploading a file with no content should fail"""
    case_id = create_case(client).json["case_id"]

    data = {"file": (io.BytesIO(b""), "")}
    response = client.post(f"/api/case/{case_id}/upload_file",
                           content_type="multipart/form-data",
                           headers={"X-API-KEY": API_KEY},
                           data=data)
    assert response.status_code == 400


def test_upload_case_file_read_only_denied(client):
    """Read-only user should not be able to upload files"""
    case_id = create_case(client).json["case_id"]

    response = upload_file(client, f"/api/case/{case_id}/upload_file", api_key=READ_KEY)
    assert response.status_code == 403


def test_delete_case_file_read_only_denied(client):
    """Read-only user should not be able to delete files"""
    case_id = create_case(client).json["case_id"]
    upload_file(client, f"/api/case/{case_id}/upload_file")

    files = client.get(f"/api/case/{case_id}/files", headers={"X-API-KEY": API_KEY})
    file_id = files.json["files"][0]["id"]

    response = client.get(f"/api/case/{case_id}/delete_file/{file_id}",
                          headers={"X-API-KEY": READ_KEY})
    assert response.status_code == 403


def test_download_case_file_nonexistent(client):
    """Downloading a non-existent file should return 404"""
    case_id = create_case(client).json["case_id"]

    response = client.get(f"/api/case/{case_id}/download_file/9999",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 404


##########################
## Task file operations ##
##########################

def test_upload_task_file(client):
    """Editor should be able to upload a file to a task"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = upload_file(client, f"/api/task/{task_id}/upload_file")
    assert response.status_code == 200
    assert "File(s) added" in response.json["message"]


def test_list_task_files(client):
    """Editor should be able to list files on a task"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    upload_file(client, f"/api/task/{task_id}/upload_file")

    response = client.get(f"/api/task/{task_id}/files", headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "files" in response.json
    assert len(response.json["files"]) == 1


def test_download_task_file(client):
    """Editor should be able to download a file from a task"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    upload_file(client, f"/api/task/{task_id}/upload_file")

    files = client.get(f"/api/task/{task_id}/files", headers={"X-API-KEY": API_KEY})
    file_id = files.json["files"][0]["id"]

    response = client.get(f"/api/task/{task_id}/download_file/{file_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert b"hello world" in response.data


def test_delete_task_file(client):
    """Editor should be able to delete a file from a task"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]
    upload_file(client, f"/api/task/{task_id}/upload_file")

    files = client.get(f"/api/task/{task_id}/files", headers={"X-API-KEY": API_KEY})
    file_id = files.json["files"][0]["id"]

    response = client.get(f"/api/task/{task_id}/delete_file/{file_id}",
                          headers={"X-API-KEY": API_KEY})
    assert response.status_code == 200
    assert "File deleted" in response.json["message"]


def test_upload_task_file_read_only_denied(client):
    """Read-only user should not be able to upload files to tasks"""
    case_id = create_case(client).json["case_id"]
    task_id = create_task(client, case_id).json["task_id"]

    response = upload_file(client, f"/api/task/{task_id}/upload_file", api_key=READ_KEY)
    assert response.status_code == 403
