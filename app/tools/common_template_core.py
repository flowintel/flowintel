from flask import flash
from ..db_class.db import *
from ..utils import utils
from sqlalchemy import func

def get_all_case_templates():
    return Case_Template.query.all()

def get_all_task_templates():
    return Task_Template.query.all()

def get_case_template(cid):
    return Case_Template.query.get(cid)

def get_case_by_title(title):
    return Case_Template.query.where(func.lower(Case_Template.title)==func.lower(title)).first()

def get_task_template(tid):
    return Task_Template.query.get(tid)

def get_case_clusters(cid):
    return [cluster for cluster in Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.cluster_id==Cluster.id).filter_by(template_id=cid).all()]

def get_task_clusters(tid):
    return [cluster for cluster in Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.cluster_id==Cluster.id).filter_by(template_id=tid).all()]

def get_galaxy(galaxy_id):
    return Galaxy.query.get(galaxy_id)

def check_cluster_db(cluster):
    return Cluster.query.filter_by(name=cluster).first()


def get_role(user):
    """Return role for the current user"""
    return Role.query.get(user.role_id)

def get_all_tasks_by_case(cid):
    """Return all tasks in case template"""
    return Case_Task_Template.query.filter_by(case_id=cid).order_by(Case_Task_Template.case_order_id).all()

def get_task_by_case(cid):
    """Return all tasks in case template with data"""
    case_task_template = get_all_tasks_by_case(cid)
    return [get_task_template(case_task.task_id) for case_task in case_task_template]

def get_task_by_case_class(cid, template_id):
    return Case_Task_Template.query.filter_by(case_id=cid, task_id=template_id).first()


def get_case_template_tags(cid):
    return [tag.name for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=cid).all()]

def get_task_template_tags(tid):
    return [tag.name for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_tag(tag):
    return Tags.query.filter_by(name=tag).first()


def get_cluster_by_name(cluster):
    return Cluster.query.filter_by(name=cluster).first()


def get_connectors():
    return Connector.query.all()

def get_instance(iid):
    return Connector_Instance.query.get(iid)

def get_instance_by_name(name):
    return Connector_Instance.query.filter_by(name=name).first()

def get_case_connectors(cid):
    return Case_Template_Connector_Instance.query.filter_by(template_id=cid).all()

def get_task_connectors(tid):
    return Task_Template_Connector_Instance.query.filter_by(template_id=tid).all()



def check_tag(tag_list):
    flag = True
    for tag in tag_list:
        if not utils.check_tag(tag):
            flag = False
    if not flag:
        flash("tag doesn't exist")
    return flag

def check_cluster(cluster_list):
    flag = True
    for cluster in cluster_list:
        if not check_cluster_db(cluster):
            flag = False
    if not flag:
        flash("cluster doesn't exist")
    return flag

def check_connector(connector_list):
    flag = True
    for connector in connector_list:
        if not get_instance_by_name(connector):
            flag = False
    if not flag:
        flash("Connector doesn't exist")
    return flag
