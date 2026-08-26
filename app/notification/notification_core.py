import datetime

from sqlalchemy import asc, desc

from app.extensions import db
from app.db_class.db import Notification, Case, Case_Org, Org, User, Task, Task_User, Role

DATE_FORMAT = '%Y-%m-%d'
DEFAULT_CATEGORY = "general"
DEFAULT_NOTIFICATION_TYPE = "info"

ICON_NOTIFICATION_METADATA = {
    "fa-solid fa-hand": ("task", "assignment"),
    "fa-solid fa-handshake-slash": ("task", "unassignment"),
    "fa-solid fa-check": ("task", "completion"),
    "fa-solid fa-square-check": ("case", "completion"),
    "fa-solid fa-heart-circle-plus": ("case", "revival"),
    "fa-solid fa-heart-circle-bolt": ("task", "revival"),
    "fa-solid fa-trash": ("case", "deletion"),
    "fa-solid fa-sitemap": ("organisation", "membership"),
    "fa-solid fa-hand-holding-hand": ("organisation", "ownership"),
    "fa-solid fa-door-open": ("organisation", "membership"),
    "fa-solid fa-radiation": ("deadline", "deadline"),
    "fa-solid fa-skull-crossbones": ("deadline", "deadline"),
    "fa-solid fa-clock": ("deadline", "reminder"),
    "fa-solid fa-bell": ("task", "manual_notice"),
    "fa-solid fa-key": ("admin", "password_reset"),
    "fa-solid fa-user-shield": ("admin", "provisioning"),
    "fa-solid fa-circle-check": ("task", "approval"),
    "fa-solid fa-circle-xmark": ("task", "rejection"),
    "fa-solid fa-circle-exclamation": ("task", "request"),
    "fa-solid fa-magnifying-glass": ("task", "review"),
    "fa-solid fa-circle-info": ("task", "status"),
    "fa-solid fa-triangle-exclamation": ("alerting", "external_alert"),
    "fa-solid fa-code-compare": ("misp_sync", "collision"),
}


def infer_notification_metadata(message=None, html_icon=None, case_id=None, category=None, notification_type=None):
    """Return stable notification metadata from explicit values or legacy icon/message conventions."""
    inferred_category, inferred_type = ICON_NOTIFICATION_METADATA.get(
        html_icon,
        (DEFAULT_CATEGORY, DEFAULT_NOTIFICATION_TYPE)
    )
    message_text = (message or "").lower()

    try:
        if case_id is not None and int(case_id) < 0:
            inferred_category, inferred_type = "admin", "password_reset"
    except (TypeError, ValueError):
        pass

    if "password reset" in message_text:
        inferred_category, inferred_type = "admin", "password_reset"
    elif "keycloak user" in message_text or "entra user" in message_text or "single sign-on" in message_text or "provisioned" in message_text:
        inferred_category, inferred_type = "admin", "provisioning"
    elif "new alert received" in message_text:
        inferred_category, inferred_type = "alerting", "external_alert"
    elif "misp sync collision" in message_text:
        inferred_category, inferred_type = "misp_sync", "collision"
    elif "analyser run finished" in message_text or "analyzer run finished" in message_text:
        inferred_category, inferred_type = "analyzer", "analysis_completed"
    elif "days remains" in message_text or "deadline" in message_text:
        inferred_category, inferred_type = "deadline", "deadline"
    elif "reminder" in message_text:
        inferred_category, inferred_type = "deadline", "reminder"
    elif "assigned to" in message_text:
        inferred_category, inferred_type = "task", "assignment"
    elif "assignment have been removed" in message_text or "assignment has been removed" in message_text:
        inferred_category, inferred_type = "task", "unassignment"
    elif "approved" in message_text:
        inferred_category, inferred_type = "task", "approval"
    elif "rejected" in message_text:
        inferred_category, inferred_type = "task", "rejection"
    elif "submitted for review" in message_text or "request review" in message_text:
        inferred_category, inferred_type = "task", "review"
    elif "requested" in message_text:
        inferred_category, inferred_type = "task", "request"
    elif "completed" in message_text:
        inferred_category = "task" if "task" in message_text else "case"
        inferred_type = "completion"
    elif "revived" in message_text:
        inferred_category = "task" if "task" in message_text else "case"
        inferred_type = "revival"
    elif "deleted" in message_text:
        inferred_category = "task" if "task" in message_text else "case"
        inferred_type = "deletion"
    elif "owner of case" in message_text:
        inferred_category, inferred_type = "organisation", "ownership"
    elif " add to case" in message_text or " added to case" in message_text or "removed from case" in message_text:
        inferred_category, inferred_type = "organisation", "membership"
    elif "notify for task" in message_text:
        inferred_category, inferred_type = "task", "manual_notice"
    elif "task" in message_text:
        inferred_category, inferred_type = "task", "status"
    elif "case" in message_text:
        inferred_category, inferred_type = "case", "info"

    return category or inferred_category, notification_type or inferred_type


def build_notification(message, is_read, user_id, case_id, html_icon, creation_date=None, category=None, notification_type=None, target_url=None):
    category, notification_type = infer_notification_metadata(
        message=message,
        html_icon=html_icon,
        case_id=case_id,
        category=category,
        notification_type=notification_type
    )
    return Notification(
        message=message,
        is_read=is_read,
        user_id=user_id,
        case_id=case_id,
        creation_date=creation_date or datetime.datetime.now(tz=datetime.timezone.utc),
        html_icon=html_icon,
        category=category,
        notification_type=notification_type,
        target_url=target_url
    )


def get_notif(nid):
    return Notification.query.get(nid)

def get_user_notif(user, unread_read, category=None, notification_type=None, sort="newest"):
    unread_only = str(unread_read).lower() == "true"
    query = Notification.query.where(
        Notification.user_id == user.id,
        Notification.is_read == (not unread_only)
    )
    if category and category != "all":
        query = query.where(Notification.category == category)
    if notification_type and notification_type != "all":
        query = query.where(Notification.notification_type == notification_type)

    order_column = Notification.creation_date
    if sort == "oldest":
        return query.order_by(asc(order_column)).all()
    if sort == "category":
        return query.order_by(asc(Notification.category), desc(order_column)).all()
    if sort == "type":
        return query.order_by(asc(Notification.notification_type), desc(order_column)).all()
    return query.order_by(desc(order_column)).all()

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


def create_notification_for_admins(message, html_icon, case_id=None, user_id_for_redirect=None, org_id=None, category=None, notification_type=None, target_url=None):
    """Create a notification for all admins. If org_id is given, also notify Org Admins of that organisation."""
    admin_roles = Role.query.filter_by(admin=True).all()
    admin_role_ids = [role.id for role in admin_roles]
    admin_users = User.query.filter(User.role_id.in_(admin_role_ids)).all() if admin_role_ids else []

    org_admin_users = []
    if org_id:
        org_admin_roles = Role.query.filter_by(org_admin=True).all()
        org_admin_role_ids = [role.id for role in org_admin_roles]
        if org_admin_role_ids:
            org_admin_users = User.query.filter(
                User.role_id.in_(org_admin_role_ids),
                User.org_id == org_id
            ).all()

    # Deduplicate by user id
    recipients = {u.id: u for u in admin_users}
    for u in org_admin_users:
        recipients.setdefault(u.id, u)

    if not recipients:
        return False

    stored_case_id = None
    if user_id_for_redirect:
        # Store user_id as negative to distinguish from case IDs
        stored_case_id = -abs(user_id_for_redirect)
    elif case_id:
        stored_case_id = case_id
    
    for user in recipients.values():
        notif = build_notification(
            message=message,
            is_read=False,
            user_id=user.id,
            case_id=stored_case_id,
            html_icon=html_icon,
            category=category,
            notification_type=notification_type,
            target_url=target_url
        )
        db.session.add(notif)
    
    db.session.commit()
    return True


def create_notification_org(message, case_id, org_id, html_icon, current_user, category=None, notification_type=None, target_url=None):
    org = Org.query.get(org_id)
    for user in org.users:
        if not user == current_user:
            stored_case_id = str(case_id) if case_id is not None else None
            notif = build_notification(
                message=message,
                is_read=False,
                user_id=user.id,
                case_id=stored_case_id,
                html_icon=html_icon,
                category=category,
                notification_type=notification_type,
                target_url=target_url
            )
            db.session.add(notif)
            db.session.commit()

    return True

def create_notification_all_orgs(message, case_id, html_icon, current_user, category=None, notification_type=None, target_url=None):
    case_org = Case_Org.query.where(Case_Org.case_id==case_id)
    for c_o in case_org:
        org = Org.query.get(c_o.org_id)
        for user in org.users:
            if not user == current_user:
                stored_case_id = str(case_id) if case_id is not None else None
                notif = build_notification(
                    message=message,
                    is_read=False,
                    user_id=user.id,
                    case_id=stored_case_id,
                    html_icon=html_icon,
                    category=category,
                    notification_type=notification_type,
                    target_url=target_url
                )
                db.session.add(notif)
                db.session.commit()

    return True

def create_notification_user(message, case_id, user_id, html_icon, category=None, notification_type=None, target_url=None):
    stored_case_id = str(case_id) if case_id is not None else None
    notif = build_notification(
        message=message,
        is_read=False,
        user_id=str(user_id),
        case_id=stored_case_id,
        html_icon=html_icon,
        category=category,
        notification_type=notification_type,
        target_url=target_url
    )
    db.session.add(notif)
    db.session.commit()

    return notif


def create_notification_for_users(message, users, html_icon, case_id=None, category=None, notification_type=None, target_url=None):
    recipients = {user.id: user for user in users if user}
    if not recipients:
        return False

    stored_case_id = str(case_id) if case_id is not None else None
    for user in recipients.values():
        notif = build_notification(
            message=message,
            is_read=False,
            user_id=user.id,
            case_id=stored_case_id,
            html_icon=html_icon,
            category=category,
            notification_type=notification_type,
            target_url=target_url
        )
        db.session.add(notif)

    db.session.commit()
    return True


def create_notification_for_approvers(message, case_id, org_id, html_icon, exclude_user_id=None, category=None, notification_type=None, target_url=None):
    """Create notification for users who can approve tasks (Admin, Case Admin, Queue Admin) in the owner org."""
    org = Org.query.get(org_id)
    if not org:
        return False
    
    approver_roles = Role.query.filter(
        (Role.admin == True) | 
        (Role.case_admin == True) | 
        (Role.queue_admin == True)
    ).all()
    
    if not approver_roles:
        return False
    
    approver_role_ids = [role.id for role in approver_roles]
    
    for user in org.users:
        if user.role_id in approver_role_ids and user.id != exclude_user_id:
            notif = build_notification(
                message=message,
                is_read=False,
                user_id=user.id,
                case_id=str(case_id),
            html_icon=html_icon,
            category=category,
            notification_type=notification_type,
            target_url=target_url
        )
            db.session.add(notif)
    
    db.session.commit()
    return True


def case_task_deadline_notif(case_or_task, msg, html_icon, now, current_user, flag_task=False):
    if case_or_task.deadline:
        notif_deadline = None
        if case_or_task.notif_deadline_id:
            notif_deadline = get_notif(case_or_task.notif_deadline_id)

        case_deadline = datetime.datetime.strptime(case_or_task.deadline.strftime(DATE_FORMAT), DATE_FORMAT)
        loc = case_deadline - now

        if loc.days > 0 and loc.days <= 10:
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
    now = datetime.datetime.strptime(datetime.datetime.now(tz=datetime.timezone.utc).strftime(DATE_FORMAT), DATE_FORMAT)

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

def mark_password_reset_notifications_as_read(user_id):
    """Mark all password reset notifications for a specific user as read."""
    negative_user_id = -abs(int(user_id))
    password_reset_notifs = Notification.query.filter_by(case_id=negative_user_id).all()
    
    for notif in password_reset_notifs:
        notif.is_read = True
        notif.read_date = datetime.datetime.now(tz=datetime.timezone.utc)
    
    db.session.commit()
    return True
