from datetime import datetime, timedelta
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from dateutil import relativedelta
import schedule
import time

from ..db_class.db import Case, Notification, Recurring_Notification

engine = create_engine("sqlite:///instance/flowintel-cm.sqlite")

session = Session(engine)

def create_notification(case, message, html_icon):
    stmt = select(Recurring_Notification).where(Recurring_Notification.case_id == case.id)
    recur_notif = session.scalars(stmt).all()
    for r_n in recur_notif:
        notif = Notification(
            message=message,
            is_read=False,
            user_id=r_n.user_id,
            case_id=str(case.id),
            creation_date=datetime.now(),
            html_icon=html_icon
        )
        session.add(notif)
        session.commit()


def job():
    today = datetime.today()
    print(f"[+] {today.strftime('%Y-%m-%d %H:%M')}")
    cp = 0
    stmt = select(Case)
    for case in session.scalars(stmt):
        if case.recurring_type:
            if case.recurring_type == "once":
                if case.recurring_date.date() == today.date():
                    create_notification(case, f"Unique reminder for '{case.id}-{case.title}'", "fa-solid fa-clock")
                    case.recurring_type = None
                    case.recurring_date = None
                    cp += 1
            elif case.recurring_type == "daily":
                create_notification(case, f"Daily reminder for '{case.id}-{case.title}'", "fa-solid fa-clock")
                case.recurring_date = datetime.today() + timedelta(days=1)
                cp += 1
            elif case.recurring_type == "weekly":
                if case.recurring_date.date() == today.date():
                    create_notification(case, f"Weekly reminder for '{case.id}-{case.title}'", "fa-solid fa-clock")
                    case.recurring_date = case.recurring_date + datetime.timedelta(days=(case.recurring_date.weekday() - case.recurring_date.weekday() + 7))
                    cp += 1
            elif case.recurring_type == "monthly":
                if case.recurring_date.date() == today.date():
                    create_notification(case, f"Monthly reminder for '{case.id}-{case.title}'", "fa-solid fa-clock")
                    case.recurring_date = case.recurring_date + relativedelta.relativedelta(months=1)
                    cp += 1
            session.commit()
    print(f"[+] Finished. {cp} new notifications")

# job()
print("[+] Started...")
schedule.every().day.at("02:00").do(job)

while True:
    schedule.run_pending()
    time.sleep(1)