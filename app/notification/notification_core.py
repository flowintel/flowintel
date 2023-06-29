from .. import db
from ..db_class.db import Notification, Case, Case_Org, Org, User
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
            notif.read_date = datetime.datetime.now()
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
                creation_date=datetime.datetime.now(),
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
                    creation_date=datetime.datetime.now(),
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
        creation_date=datetime.datetime.now(),
        html_icon=html_icon
    )
    db.session.add(notif)
    db.session.commit()

    return True