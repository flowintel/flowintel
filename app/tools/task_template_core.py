from ..db_class.db import *
import uuid
import ast
from .. import db
from . import common_template_core as CommonModel
from sqlalchemy import and_


def build_task_query(page, tags=None, taxonomies=None, galaxies=None, clusters=None, title_filter=None):
    query = Task_Template.query
    conditions = []

    if tags or taxonomies:
        query = query.join(Task_Template_Tags, Task_Template_Tags.task_id == Task_Template.id)
        query = query.join(Tags, Task_Template_Tags.tag_id == Tags.id)
        if tags:
            tags = ast.literal_eval(tags)
            conditions.append(Tags.name.in_(list(tags)))

        if taxonomies:
            taxonomies = ast.literal_eval(taxonomies)
            query = query.join(Taxonomy, Taxonomy.id == Tags.taxonomy_id)
            conditions.append(Taxonomy.name.in_(list(taxonomies)))

    if clusters or galaxies:
        query = query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.template_id == Task_Template.id)
        query = query.join(Cluster, Task_Template_Galaxy_Tags.cluster_id == Cluster.id)
        if clusters:
            clusters = ast.literal_eval(clusters)
            conditions.append(Cluster.name.in_(list(clusters)))

        if galaxies:
            galaxies = ast.literal_eval(galaxies)
            query = query.join(Galaxy, Galaxy.id == Cluster.galaxy_id)
            conditions.append(Galaxy.name.in_(list(galaxies)))

    if title_filter:
        query.order_by('title')
    
    return query.filter(and_(*conditions)).paginate(page=page, per_page=25, max_per_page=50)


def get_page_task_templates(page, title_filter, taxonomies=[], galaxies=[], tags=[], clusters=[], or_and_taxo="true", or_and_galaxies="true"):
    tasks = build_task_query(page, tags, taxonomies, galaxies, clusters, title_filter)
    nb_pages = tasks.pages

    if tags:
        tags = ast.literal_eval(tags)
    if taxonomies:
        taxonomies = ast.literal_eval(taxonomies)

    if galaxies:
        galaxies = ast.literal_eval(galaxies)
    if clusters:
        clusters = ast.literal_eval(clusters)

    if tags or taxonomies or galaxies or clusters:
        if or_and_taxo == "false":
            glob_list = []

            for task in tasks:
                tags_db = task.to_json()["tags"]
                loc_tag = [tag["name"] for tag in tags_db]
                taxo_list = [Taxonomy.query.get(tag["taxonomy_id"]).name for tag in tags_db]

                if (not tags or all(item in loc_tag for item in tags)) and \
                (not taxonomies or all(item in taxo_list for item in taxonomies)):
                    glob_list.append(task)

            tasks = glob_list
        if or_and_galaxies == "false":
            glob_list = []

            for task in tasks:
                clusters_db = task.to_json()["clusters"]
                loc_cluster = [cluster["name"] for cluster in clusters_db]
                galaxies_list = [Galaxy.query.get(cluster["galaxy_id"]).name for cluster in clusters_db]

                if (not clusters or all(item in loc_cluster for item in clusters)) and \
                (not galaxies or all(item in galaxies_list for item in galaxies)):
                    glob_list.append(task)

            tasks = glob_list
    else:
        tasks = Task_Template.query.paginate(page=page, per_page=25, max_per_page=50)
        nb_pages = tasks.pages
    return tasks, nb_pages


def add_task_template_core(form_dict):
    template = Task_Template(
        title=form_dict["title"],
        description=form_dict["body"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4())
    )
    db.session.add(template)
    db.session.commit()

    for tag in form_dict["tags"]:
        tag = CommonModel.get_tag(tag)
        
        task_tag = Task_Template_Tags(
            tag_id=tag.id,
            task_id=template.id
        )
        db.session.add(task_tag)
        db.session.commit()

    for cluster in form_dict["clusters"]:
        cluster = CommonModel.get_cluster_by_name(cluster)
        
        task_tag = Task_Template_Galaxy_Tags(
            cluster_id=cluster.id,
            template_id=template.id
        )
        db.session.add(task_tag)
        db.session.commit()
    
    return template

def edit_task_template(form_dict, tid):
    template = CommonModel.get_task_template(tid)

    template.title=form_dict["title"]
    template.description=form_dict["body"]
    template.url=form_dict["url"]
    
    ## Tags
    task_tag_db = Task_Template_Tags.query.filter_by(task_id=template.id).all()
    for tag in form_dict["tags"]:
        tag = CommonModel.get_tag(tag)

        if not tag in task_tag_db:
            task_tag = Task_Template_Tags(
                tag_id=tag.id,
                task_id=template.id
            )
            db.session.add(task_tag)
            db.session.commit()
    
    for c_t_db in task_tag_db:
        if not c_t_db in form_dict["tags"]:
            Task_Template_Tags.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

    ## Clusters
    task_tag_db = Task_Template_Galaxy_Tags.query.filter_by(template_id=template.id).all()
    for cluster in form_dict["clusters"]:
        cluster = CommonModel.get_cluster_by_name(cluster)

        if not cluster in task_tag_db:
            task_tag = Task_Template_Galaxy_Tags(
                cluster_id=cluster.id,
                template_id=template.id
            )
            db.session.add(task_tag)
            db.session.commit()
    
    for c_t_db in task_tag_db:
        if not c_t_db in form_dict["clusters"]:
            Task_Template_Galaxy_Tags.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

    db.session.commit()


def delete_task_template(tid):
    to_deleted = Case_Task_Template.query.filter_by(task_id=tid).all()
    for to_do in to_deleted:
        db.session.delete(to_do)
        db.session.commit()
    Task_Template_Tags.query.filter_by(task_id=tid).delete()
    Task_Template_Galaxy_Tags.query.filter_by(template_id=tid).delete()
    template = CommonModel.get_task_template(tid)
    db.session.delete(template)
    db.session.commit()
    return True
