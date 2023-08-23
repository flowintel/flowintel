from .. import db
from ..db_class.db import Notification, Case, Case_Org, Org, User, Task, Task_User
from sqlalchemy import desc
import datetime
import bleach


def get_notif(nid):
    return Notification.query.get(nid)

def get_user_notif(user, unread_read):
    if unread_read == "true":
        return Notification.query.where(Notification.user_id==user.id, Notification.is_read==False).order_by(desc(Notification.creation_date)).all()
    else:
        return Notification.query.where(Notification.user_id==user.id, Notification.is_read==True).order_by(desc(Notification.creation_date)).all()

def read_notification_core(notif_id):
    notif = get_notif(notif_id)
    if notif:
        notif.is_read = not notif.is_read
        if notif.is_read:
            notif.read_date = datetime.datetime.now(tz=datetime.timezone.utc)
        else:
            notif.read_date = None
        db.session.commit()
        return True
    return False

def delete_notification_core(nid):
    notif = get_notif(nid)
    if notif:
        db.session.delete(notif)
        db.session.commit()
        return True
    return False


def create_notification_org(message, case_id, org_id, html_icon, current_user):
    org = Org.query.get(org_id)
    for user in org.users:
        if not user == current_user:
            notif = Notification(
                message=bleach.clean(message),
                is_read=False,
                user_id=user.id,
                case_id=bleach.clean(str(case_id)),
                creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
                html_icon=html_icon
            )
            db.session.add(notif)
            db.session.commit()

    return True

def create_notification_all_orgs(message, case_id, html_icon, current_user):
    case_org = Case_Org.query.where(case_id==case_id).all()
    for c_o in case_org:
        org = Org.query.get(c_o.org_id)
        for user in org.users:
            if not user == current_user:
                notif = Notification(
                    message=bleach.clean(message),
                    is_read=False,
                    user_id=user.id,
                    case_id=bleach.clean(str(case_id)),
                    creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
                    html_icon=html_icon
                )
                db.session.add(notif)
                db.session.commit()

    return True

def create_notification_user(message, case_id, user_id, html_icon):
    notif = Notification(
        message=bleach.clean(message),
        is_read=False,
        user_id=bleach.clean(str(user_id)),
        case_id=bleach.clean(str(case_id)),
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        html_icon=html_icon
    )
    db.session.add(notif)
    db.session.commit()

    return notif


def case_task_deadline_notif(case_or_task, msg, html_icon, now, current_user, flag_task=False):
    if case_or_task.deadline:
        notif_deadline = None
        if case_or_task.notif_deadline_id:
            notif_deadline = get_notif(case_or_task.notif_deadline_id)

        case_deadline = datetime.datetime.strptime(case_or_task.deadline.strftime("%Y-%m-%d"), "%Y-%m-%d")
        loc = case_deadline - now

        if loc.days > 0:
            if loc.days <= 10:
                if notif_deadline:
                    if (case_deadline - notif_deadline.for_deadline).days > loc.days:
                        notif_deadline.message = f"{loc.days} {msg}"
                        notif_deadline.for_deadline = now
                        notif_deadline.is_read = False
                        db.session.commit()
                else:
                    if flag_task:
                        notif_deadline = create_notification_user(f"{loc.days} {msg}", case_or_task.case_id, current_user.id, html_icon)
                    else:
                        notif_deadline = create_notification_user(f"{loc.days} {msg}", case_or_task.id, current_user.id, html_icon)
                    notif_deadline.for_deadline = now
                    case_or_task.notif_deadline_id = notif_deadline.id
                    db.session.commit()


def create_notification_deadline(current_user):
    now = datetime.datetime.strptime(datetime.datetime.now(tz=datetime.timezone.utc).strftime("%Y-%m-%d"), "%Y-%m-%d")
    # now = datetime.datetime.strptime("2023-07-01", "%Y-%m-%d")

    cases = Case.query.join(Case_Org, Case_Org.org_id==current_user.org_id).all()
    for case in cases:
        msg = f"days remains for case '{case.id}-{case.title}'"
        case_task_deadline_notif(case, msg, "fa-solid fa-radiation", now, current_user)
    
    tasks = Task.query.join(Task_User, Task_User.user_id==current_user.id).all()
    for task in tasks:
        case = Case.query.get(task.case_id)
        msg = f"days remains for task '{task.title}' of case '{case.id}-{case.title}'"
        case_task_deadline_notif(task, msg, "fa-solid fa-skull-crossbones", now, current_user, True)

    return True


def mark_all_read(user):
    notif_list = get_user_notif(user, unread_read="true")

    for notif in notif_list:
        notif.is_read = True
        notif.read_date = datetime.datetime.now(tz=datetime.timezone.utc)
        db.session.commit()

    return True