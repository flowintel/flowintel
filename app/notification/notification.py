from flask import Blueprint, render_template, redirect, jsonify, request, flash
from flask_login import login_required, current_user
from . import notification_core as NotifModel

notification_blueprint = Blueprint(
    'notification',
    __name__,
    template_folder='templates',
    static_folder='static'
)


##########
# Render #
##########


@notification_blueprint.route("/", methods=['GET'])
@login_required
def index():
    return render_template("notification/notification.html")


@notification_blueprint.route("/get_user_notifications", methods=['GET'])
@login_required
def get_user_notifications():
    """Return notification for current_user"""
    data_dict = dict(request.args)
    unread_read = data_dict["unread_read"]
    user_notif = NotifModel.get_user_notif(current_user, unread_read)
    user_notif_list = list()
    for notif in user_notif:
        user_notif_list.append(notif.to_json())
    return {"notif": user_notif_list}

@notification_blueprint.route("/get_user_notifications_len", methods=['GET'])
@login_required
def get_user_notifications_len():
    """Return notification for current_user"""
    NotifModel.create_notification_dead_line(current_user)
    user_notif = NotifModel.get_user_notif(current_user, "true")
    return {"notif": len(user_notif)}


@notification_blueprint.route("/read_notification/<nid>", methods=['GET'])
@login_required
def read_notification(nid):
    """Read Notification"""
    
    return {"message": NotifModel.read_notification_core(nid)}

@notification_blueprint.route("/delete/<nid>", methods=['GET'])
@login_required
def delete_notification(nid):
    """Delete Notification"""
    
    return {"message": NotifModel.delete_notification_core(nid)}



@notification_blueprint.route("/mark_all_read", methods=['GET'])
@login_required
def mark_all_read():
    NotifModel.mark_all_read(current_user)
    return redirect("/notification")