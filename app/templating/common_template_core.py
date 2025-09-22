import datetime
from typing import Optional
from ..db_class.db import *
from sqlalchemy import func
from ..case.common_core import get_instance_by_name

def get_all_case_templates():
    return Case_Template.query.all()

def get_all_task_templates():
    return Task_Template.query.all()

def get_case_template(cid) -> Optional[Case_Template]:
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

def get_case_template_tags_json(cid):
    return [tag.to_json() for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=cid).all()]

def get_case_template_tags_both(case_id, tag_id):
    """Return a list of tags present in a case"""
    return Case_Template_Tags.query.filter_by(case_id=case_id, tag_id=tag_id).first()

def get_task_template_tags(tid):
    return [tag.name for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_task_template_tags_json(tid):
    return [tag.to_json() for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_task_template_tags_both(task_id, tag_id):
    """Return a list of tags present in a task"""
    return Task_Template_Tags.query.filter_by(task_id=task_id, tag_id=tag_id).first()

def get_tag(tag):
    return Tags.query.filter_by(name=tag).first()


def get_cluster_by_name(cluster):
    return Cluster.query.filter_by(name=cluster).first()
def get_cluster_by_uuid(cluster):
    return Cluster.query.filter_by(uuid=cluster).first()

def get_case_template_clusters_name(cid):
    """Return a list of clusters name present in a case template"""
    return [cluster.name for cluster in \
            Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                   .filter_by(template_id=cid).all()]

def get_case_template_clusters_uuid(cid):
    """Return a list of clusters uuid present in a case template"""
    return [cluster.uuid for cluster in \
            Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                   .filter_by(template_id=cid).all()]

def get_case_template_clusters_both(case_id, cluster_id):
    """Return a list of clusters present in a case template"""
    return Case_Template_Galaxy_Tags.query.filter_by(template_id=case_id, cluster_id=cluster_id).first()

def get_task_template_clusters_name(tid):
    """Return a list of clusters name present in a task template"""
    return [cluster.name for cluster in \
            Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                   .filter_by(template_id=tid).all()]

def get_task_template_clusters_uuid(tid):
    """Return a list of clusters uuid present in a task template"""
    return [cluster.uuid for cluster in \
            Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                   .filter_by(template_id=tid).all()]

def get_task_template_clusters_both(task_id, cluster_id):
    """Return a list of clusters present in a task template"""
    return Task_Template_Galaxy_Tags.query.filter_by(template_id=task_id, cluster_id=cluster_id).first()

def get_case_custom_tags(case_id):
    return Case_Template_Custom_Tags.query.filter_by(case_template_id=case_id).all()

def get_case_custom_tags_name(case_id):
    c_ts = Custom_Tags.query.join(Case_Template_Custom_Tags, Case_Template_Custom_Tags.custom_tag_id==Custom_Tags.id).where(Case_Template_Custom_Tags.case_template_id==case_id).all()
    return [c_t.name for c_t in c_ts]

def get_case_custom_tags_json(case_id):
    c_ts = Custom_Tags.query.join(Case_Template_Custom_Tags, Case_Template_Custom_Tags.custom_tag_id==Custom_Tags.id).where(Case_Template_Custom_Tags.case_template_id==case_id).all()
    return [c_t.to_json() for c_t in c_ts]

def get_case_custom_tags_both(case_id, custom_tag_id):
    return Case_Template_Custom_Tags.query.filter_by(case_template_id=case_id, custom_tag_id=custom_tag_id).first()

def get_task_custom_tags(task_id):
    return Task_Template_Custom_Tags.query.filter_by(task_template_id=task_id).all()

def get_task_custom_tags_name(task_id):
    c_ts = Custom_Tags.query.join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.custom_tag_id==Custom_Tags.id).where(Task_Template_Custom_Tags.task_template_id==task_id).all()
    return [c_t.name for c_t in c_ts]

def get_task_custom_tags_json(task_id):
    c_ts = Custom_Tags.query.join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.custom_tag_id==Custom_Tags.id).where(Task_Template_Custom_Tags.task_template_id==task_id).all()
    return [c_t.to_json() for c_t in c_ts]

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

def get_galaxies_from_clusters(clusters):
    """Get a list of galaxies from a list of clusters
    Change also clusters to json format
    """
    galaxies = []
    if clusters:
        for cluster in clusters:
            loc_g = get_galaxy(cluster.galaxy_id)
            if not loc_g in galaxies:
                galaxies.append(loc_g.to_json())
            index = clusters.index(cluster)
            clusters[index] = cluster.to_json()
    return clusters, galaxies

def get_taxonomies_from_tags(tags):
    """Get a list of taxonomies from a list of tags"""
    taxonomies = []
    if tags:
        for tag in tags:
            if not tag["name"].split(":")[0] in taxonomies:
                taxonomies.append(tag["name"].split(":")[0])
    return taxonomies


##############
# Connectors #
##############
def get_case_template_connector_instances(ctid):
    """Return a list of all connectors present in a case template"""
    return Case_Template_Connector_Instance.query.filter_by(case_template_id=ctid).all()

def add_connector_instances_to_case_template(ctid, connector_instances) -> bool:
    """Add connector instance to case template"""
    for connector_instance in connector_instances:
        c = Case_Template_Connector_Instance(
            case_template_id=ctid,
            connector_instance_id=connector_instance["id"],
            identifier=connector_instance['identifier']
        )
        db.session.add(c)
    db.session.commit()
    return True

def edit_connector_instances_of_case_template(ctid, identifier) -> bool:
    """Edit identifier of connector instance"""
    c = Case_Template_Connector_Instance.query.get(ctid)
    if c:
        c.identifier = identifier
        db.session.commit()
        return True
    return False

def remove_connector_instance_from_case_template(ctid):
    """Remove connector instance from a case template"""
    c = Case_Template_Connector_Instance.query.get(ctid)
    if c:
        db.session.delete(c)
        db.session.commit()
        return True
    return False