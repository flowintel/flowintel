import datetime
import time

import schedule

from app import create_app, db
from app.case.CaseCore import CaseModel
from app.case import common_core as CommonModel
from app.connectors import connectors_core as ConnectorModel
from app.db_class.db import Case_Misp_Sync_Schedule, User
from app.utils.logger import flowintel_log


app = create_app()


def run_due_misp_sync_schedules():
    now = datetime.datetime.now(tz=datetime.timezone.utc)
    print(f"[+] MISP sync tick {now.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    ran = 0
    failed = 0

    with app.app_context():
        schedules = ConnectorModel.get_due_misp_sync_schedules(now=now, limit=50)
        for schedule in schedules:
            case = CommonModel.get_case(schedule.case_id)
            if not case or case.completed:
                continue

            user = User.query.get(schedule.created_by_id) if schedule.created_by_id else None
            if not user:
                failed += 1
                flowintel_log(
                    "warning",
                    400,
                    "Scheduled MISP sync skipped: no schedule owner",
                    CaseId=schedule.case_id,
                    ConnectorInstanceId=schedule.case_connector_instance_id,
                    ScheduleId=schedule.id,
                    Direction=schedule.direction
                )
                continue

            payload = dict(schedule.payload or {})
            module_name = schedule.module_name or ("misp_object_event" if schedule.direction == "send" else "receive_misp_object")
            payload["module"] = module_name
            payload["case_task_instance_id"] = schedule.case_connector_instance_id

            try:
                result = CaseModel.call_module_case(
                    module_name,
                    schedule.case_connector_instance_id,
                    case,
                    user,
                    payload=payload
                )
                if result:
                    failed += 1
                    flowintel_log(
                        "warning",
                        400,
                        f"Scheduled MISP sync failed: {result.get('message', 'unknown error')}",
                        User=user.email,
                        CaseId=schedule.case_id,
                        ConnectorInstanceId=schedule.case_connector_instance_id,
                        ScheduleId=schedule.id,
                        Direction=schedule.direction
                    )
                else:
                    ran += 1
                    db.session.commit()
            except Exception as exc:
                db.session.rollback()
                failed += 1
                flowintel_log(
                    "error",
                    500,
                    f"Scheduled MISP sync raised an exception: {exc}",
                    User=getattr(user, "email", None),
                    CaseId=schedule.case_id,
                    ConnectorInstanceId=schedule.case_connector_instance_id,
                    ScheduleId=schedule.id,
                    Direction=schedule.direction
                )

    print(f"[+] MISP sync finished. ran={ran} failed={failed}")


print("[+] Started recurring MISP sync worker...")
schedule.every().day.at("03:00").do(run_due_misp_sync_schedules)

while True:
    schedule.run_pending()
    time.sleep(1)
