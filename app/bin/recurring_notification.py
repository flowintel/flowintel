from datetime import datetime, timedelta, timezone
from dateutil import relativedelta
import schedule
import time

from sqlalchemy import select

from app import create_app
from app.extensions import db
from app.db_class.db import Case, Notification, Recurring_Notification


app = create_app()

REMINDER_ICON = "fa-solid fa-clock"

def create_notification(case, message, html_icon):
    stmt = select(Recurring_Notification).where(Recurring_Notification.case_id == case.id)
    recur_notif = db.session.scalars(stmt).all()

    for r_n in recur_notif:
        notif = Notification(
            message=message,
            is_read=False,
            user_id=r_n.user_id,
            case_id=str(case.id),
            creation_date=datetime.now(timezone.utc),
            html_icon=html_icon,
        )
        db.session.add(notif)

def job():
    with app.app_context():
        try:
            # Enter app context so db.session is available.
            # The job runs as one DB transaction unless an exception triggers rollback.
            today = datetime.today()
            print(f"[+] {today.strftime('%Y-%m-%d %H:%M')}")
            cp = 0
            stmt = select(Case)
            for case in db.session.scalars(stmt):
                if not case.completed and case.recurring_type:
                    if case.recurring_type == "once" and case.recurring_date.date() == today.date():
                        create_notification(case, f"Unique reminder for '{case.id}-{case.title}'", REMINDER_ICON)
                        case.recurring_type = None
                        case.recurring_date = None
                        cp += 1
                    elif case.recurring_type == "daily":
                        create_notification(case, f"Daily reminder for '{case.id}-{case.title}'", REMINDER_ICON)
                        case.recurring_date = datetime.today() + timedelta(days=1)
                        cp += 1
                    elif case.recurring_type == "weekly" and case.recurring_date.date() == today.date():
                        create_notification(case, f"Weekly reminder for '{case.id}-{case.title}'", REMINDER_ICON)
                        case.recurring_date = case.recurring_date + timedelta(days=7)
                        cp += 1
                    elif case.recurring_type == "monthly" and case.recurring_date.date() == today.date():
                        create_notification(case, f"Monthly reminder for '{case.id}-{case.title}'", REMINDER_ICON)
                        case.recurring_date = case.recurring_date + relativedelta.relativedelta(months=1)
                        cp += 1
            db.session.commit()
            print(f"[+] Finished. {cp} new notifications")
        except Exception as e:
            # Roll back uncommitted changes for the current job transaction.
            db.session.rollback()
            print(f"[!] Error while processing recurring notifications: {type(e).__name__}: {e}")
            raise

# job()
print("[+] Started...")
schedule.every().day.at("02:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)
