import datetime
from ..db_class.db import *
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

def get_task_note(note_id):
    return Note_Template.query.get(note_id)


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

def get_case_template_tags_both(case_id, tag_id):
    """Return a list of tags present in a case"""
    return Case_Template_Tags.query.filter_by(case_id=case_id, tag_id=tag_id).first()

def get_task_template_tags(tid):
    return [tag.name for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_task_template_tags_both(task_id, tag_id):
    """Return a list of tags present in a task"""
    return Task_Template_Tags.query.filter_by(task_id=task_id, tag_id=tag_id).first()

def get_tag(tag):
    return Tags.query.filter_by(name=tag).first()


def get_cluster_by_name(cluster):
    return Cluster.query.filter_by(name=cluster).first()

def get_case_template_clusters_name(cid):
    """Return a list of clusters present in a case template"""
    return [cluster.name for cluster in \
            Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                   .filter_by(template_id=cid).all()]

def get_case_template_clusters_both(case_id, cluster_id):
    """Return a list of clusters present in a case template"""
    return Case_Template_Galaxy_Tags.query.filter_by(template_id=case_id, cluster_id=cluster_id).first()

def get_task_template_clusters_name(tid):
    """Return a list of clusters present in a task template"""
    return [cluster.name for cluster in \
            Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                   .filter_by(template_id=tid).all()]

def get_task_template_clusters_both(task_id, cluster_id):
    """Return a list of clusters present in a task template"""
    return Task_Template_Galaxy_Tags.query.filter_by(template_id=task_id, cluster_id=cluster_id).first()

def get_connectors():
    return Connector.query.all()

def get_instance(iid):
    return Connector_Instance.query.get(iid)

def get_instance_by_name(name):
    return Connector_Instance.query.filter_by(name=name).first()

def get_case_connectors(cid):
    return Case_Template_Connector_Instance.query.filter_by(template_id=cid).all()

def get_case_template_connectors_name(cid):
    """Return a list of name connectors present in a case"""
    return [instance.name for instance in \
            Connector_Instance.query.join(Case_Template_Connector_Instance, Case_Template_Connector_Instance.instance_id==Connector_Instance.id)\
                .filter_by(template_id=cid).all()]

def get_case_template_connectors_both(case_id, instance_id):
    """Return an instance of Case_Template_Connector_Instance depending of a case template id and an instance id"""
    return Case_Template_Connector_Instance.query.filter_by(template_id=case_id, instance_id=instance_id).first()

def get_task_connectors(tid):
    return Task_Template_Connector_Instance.query.filter_by(template_id=tid).all()

def get_task_template_connectors_name(tid):
    """Return a list of name connectors present in a task"""
    return [instance.name for instance in \
            Connector_Instance.query.join(Task_Template_Connector_Instance, Task_Template_Connector_Instance.instance_id==Connector_Instance.id)\
                .filter_by(template_id=tid).all()]

def get_task_template_connectors_both(task_id, instance_id):
    """Return an instance of Task_Template_Connector_Instance depending of a task template id and an instance id"""
    return Task_Template_Connector_Instance.query.filter_by(template_id=task_id, instance_id=instance_id).first()

def get_case_custom_tags(case_id):
    return Case_Template_Custom_Tags.query.filter_by(case_template_id=case_id).all()

def get_case_custom_tags_name(case_id):
    c_ts = Custom_Tags.query.join(Case_Template_Custom_Tags, Case_Template_Custom_Tags.custom_tag_id==Custom_Tags.id).where(Case_Template_Custom_Tags.case_template_id==case_id).all()
    return [c_t.name for c_t in c_ts]

def get_case_custom_tags_both(case_id, custom_tag_id):
    return Case_Template_Custom_Tags.query.filter_by(case_template_id=case_id, custom_tag_id=custom_tag_id).first()

def get_task_custom_tags(task_id):
    return Task_Template_Custom_Tags.query.filter_by(task_template_id=task_id).all()

def get_task_custom_tags_name(task_id):
    c_ts = Custom_Tags.query.join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.custom_tag_id==Custom_Tags.id).where(Task_Template_Custom_Tags.task_template_id==task_id).all()
    return [c_t.name for c_t in c_ts]

def get_task_custom_tags_both(task_id, custom_tag_id):
    return Task_Template_Custom_Tags.query.filter_by(task_template_id=task_id, custom_tag_id=custom_tag_id).first()


def get_subtask_template(sid):
    return Subtask_Template.query.get(sid)


def update_last_modif(case_id):
    """Update 'last_modif' of a case"""
    case = Case_Template.query.get(case_id)
    case.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()

def update_last_modif_task(task_id):
    """Update 'last_modif' of a task"""
    if task_id:
        task = Task_Template.query.get(task_id)
        task.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
        db.session.commit()
