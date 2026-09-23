import io

import pytest

from app.case.TaskCore import (
    BULK_TASK_MAX_BYTES,
    BULK_TASK_MAX_COUNT,
    BulkTaskImportError,
    TaskModel,
)
from app.db_class.db import Task


ADMIN_API_KEY = "admin_api_key"


def create_case(client):
    response = client.post(
        "/api/case/create",
        headers={"X-API-KEY": ADMIN_API_KEY},
        json={"title": "Bulk task test case"},
    )
    assert response.status_code == 201
    return response.json["case_id"]


def login_as(client, user_id):
    with client.session_transaction() as session:
        session["_user_id"] = str(user_id)
        session["_fresh"] = True


def test_parse_bulk_tasks_supports_optional_description_and_semicolons():
    tasks = TaskModel.parse_bulk_tasks(
        "First title\nSecond title;A description\n\nThird;keep;these;semicolons\n"
    )

    assert tasks == [
        {"title": "First title", "description": ""},
        {"title": "Second title", "description": "A description"},
        {"title": "Third", "description": "keep;these;semicolons"},
    ]


@pytest.mark.parametrize(
    ("content", "message"),
    [
        (";missing title", "Line 1 has no task title"),
        ("x" * 256, "title longer than 255"),
        ("safe title;bad\x00value", "unsupported control characters"),
        ("safe title;spoof\u202eevil", "unsupported control characters"),
        ("\n\n", "at least one non-empty task line"),
    ],
)
def test_parse_bulk_tasks_rejects_invalid_content(content, message):
    with pytest.raises(BulkTaskImportError, match=message):
        TaskModel.parse_bulk_tasks(content)


def test_parse_bulk_tasks_enforces_size_and_task_count_limits():
    with pytest.raises(BulkTaskImportError, match="larger than 256 KiB"):
        TaskModel.parse_bulk_tasks("x" * (BULK_TASK_MAX_BYTES + 1))

    content = "\n".join(f"Task {number}" for number in range(BULK_TASK_MAX_COUNT + 1))
    with pytest.raises(BulkTaskImportError, match="at most"):
        TaskModel.parse_bulk_tasks(content)


def test_bulk_create_tasks_from_pasted_text(client, app):
    case_id = create_case(client)
    login_as(client, 1)

    response = client.post(
        f"/case/{case_id}/bulk_create_tasks",
        data={
            "tasks_text": (
                "Investigate alert;Review <script>alert(1)</script> safely\n"
                "Contact owner\n"
                "Report;Findings; recommendations"
            )
        },
        follow_redirects=False,
    )

    assert response.status_code == 302
    assert response.headers["Location"].endswith(f"/case/{case_id}")
    with app.app_context():
        tasks = Task.query.filter_by(case_id=case_id).order_by(Task.id).all()
        assert [(task.title, task.description) for task in tasks] == [
            ("Investigate alert", "Review <script>alert(1)</script> safely"),
            ("Contact owner", ""),
            ("Report", "Findings; recommendations"),
        ]


def test_bulk_create_tasks_from_utf8_file(client, app):
    case_id = create_case(client)
    login_as(client, 1)

    response = client.post(
        f"/case/{case_id}/bulk_create_tasks",
        data={"tasks_file": (io.BytesIO("Tâche;Résumé\nOnly title".encode()), "tasks.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 302
    with app.app_context():
        tasks = Task.query.filter_by(case_id=case_id).order_by(Task.id).all()
        assert [(task.title, task.description) for task in tasks] == [
            ("Tâche", "Résumé"),
            ("Only title", ""),
        ]


def test_bulk_create_rejects_invalid_file_without_partial_import(client, app):
    case_id = create_case(client)
    login_as(client, 1)

    response = client.post(
        f"/case/{case_id}/bulk_create_tasks",
        data={"tasks_file": (io.BytesIO(b"Valid task\n;Invalid task"), "tasks.txt")},
        content_type="multipart/form-data",
    )

    assert response.status_code == 200
    assert b"Line 2 has no task title" in response.data
    with app.app_context():
        assert Task.query.filter_by(case_id=case_id).count() == 0


def test_bulk_create_requires_one_source_and_safe_file_type(client, app):
    case_id = create_case(client)
    login_as(client, 1)

    both_response = client.post(
        f"/case/{case_id}/bulk_create_tasks",
        data={
            "tasks_text": "Pasted task",
            "tasks_file": (io.BytesIO(b"File task"), "tasks.txt"),
        },
        content_type="multipart/form-data",
    )
    invalid_file_response = client.post(
        f"/case/{case_id}/bulk_create_tasks",
        data={"tasks_file": (io.BytesIO(b"Task"), "tasks.exe")},
        content_type="multipart/form-data",
    )

    assert both_response.status_code == 200
    assert b"Choose exactly one source" in both_response.data
    assert invalid_file_response.status_code == 200
    assert b"Only .txt and .csv files are accepted" in invalid_file_response.data
    with app.app_context():
        assert Task.query.filter_by(case_id=case_id).count() == 0


def test_bulk_create_requires_editor_permission(client):
    case_id = create_case(client)
    login_as(client, 3)

    response = client.get(f"/case/{case_id}/bulk_create_tasks")

    assert response.status_code == 403
