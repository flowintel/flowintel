import datetime
from ..db_class.db import *
import uuid
import ast
from .. import db
from . import common_template_core as CommonModel
from sqlalchemy import and_, desc
from ..custom_tags import custom_tags_core as CustomModel


def build_task_query(page, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None, title_filter=None):
    query = Task_Template.query
    conditions = []

    if tags or taxonomies:
        query = query.join(Task_Template_Tags, Task_Template_Tags.task_id == Task_Template.id)
        query = query.join(Tags, Task_Template_Tags.tag_id == Tags.id)
        if tags:
            conditions.append(Tags.name.in_(list(tags)))

        if taxonomies:
            query = query.join(Taxonomy, Taxonomy.id == Tags.taxonomy_id)
            conditions.append(Taxonomy.name.in_(list(taxonomies)))

    if clusters or galaxies:
        query = query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.template_id == Task_Template.id)
        query = query.join(Cluster, Task_Template_Galaxy_Tags.cluster_id == Cluster.id)
        if clusters:
            conditions.append(Cluster.name.in_(list(clusters)))

        if galaxies:
            query = query.join(Galaxy, Galaxy.id == Cluster.galaxy_id)
            conditions.append(Galaxy.name.in_(list(galaxies)))

    if custom_tags:
        query = query.join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.task_template_id == Task_Template.id)
        query = query.join(Custom_Tags, Task_Template_Custom_Tags.custom_tag_id == Custom_Tags.id)
        conditions.append(Custom_Tags.name.in_(list(custom_tags)))

    if title_filter=='true':
        query = query.order_by('title')
    else:
        query = query.order_by(desc('last_modif'))
    
    return query.filter(and_(*conditions)).paginate(page=page, per_page=25, max_per_page=50)


def get_page_task_templates(page, title_filter, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true"):
    

    if tags:
        tags = ast.literal_eval(tags)
    if taxonomies:
        taxonomies = ast.literal_eval(taxonomies)

    if galaxies:
        galaxies = ast.literal_eval(galaxies)
    if clusters:
        clusters = ast.literal_eval(clusters)

    if custom_tags:
        custom_tags = ast.literal_eval(custom_tags)

    tasks = build_task_query(page, tags, taxonomies, galaxies, clusters, custom_tags, title_filter)
    nb_pages = tasks.pages

    if tags or taxonomies or galaxies or clusters or custom_tags:
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
        query = Task_Template.query
        if title_filter=='true':
           query = query.order_by('title')
        else:
            query = query.order_by(desc('last_modif'))
        tasks = query.paginate(page=page, per_page=25, max_per_page=50)
        nb_pages = tasks.pages
    return tasks, nb_pages


def add_task_template_core(form_dict):
    template = Task_Template(
        title=form_dict["title"],
        description=form_dict["body"],
        url=form_dict["url"],
        uuid=str(uuid.uuid4()),
        nb_notes=0,
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        time_required=form_dict["time_required"]
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

    for custom_tag_name in form_dict["custom_tags"]:
        custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
        if custom_tag:
            task_custom_tag = Task_Template_Custom_Tags(
                task_template_id=template.id,
                custom_tag_id=custom_tag.id
            )
            db.session.add(task_custom_tag)
            db.session.commit()
    
    return template

def edit_task_template(form_dict, tid):
    template = CommonModel.get_task_template(tid)

    template.title=form_dict["title"]
    template.description=form_dict["body"]
    template.url=form_dict["url"]
    template.time_required = form_dict["time_required"]
    
    ## Tags
    task_tag_db = CommonModel.get_task_template_tags(tid)
    for tags in form_dict["tags"]:
        if not tags in task_tag_db:
            tag = CommonModel.get_tag(tags)
            task_tag = Task_Template_Tags(
                tag_id=tag.id,
                task_id=template.id
            )
            db.session.add(task_tag)
            db.session.commit()
            task_tag_db.append(tags)
    for c_t_db in task_tag_db:
        if not c_t_db in form_dict["tags"]:
            tag = CommonModel.get_tag(c_t_db)
            task_tag = CommonModel.get_task_template_tags_both(tid, tag.id)
            Task_Template_Tags.query.filter_by(id=task_tag.id).delete()
            db.session.commit()

    ## Clusters
    task_cluster_db = CommonModel.get_task_template_clusters_uuid(tid)
    for clusters in form_dict["clusters"]:
        if not clusters in task_cluster_db:
            cluster = CommonModel.get_cluster_by_uuid(clusters)
            task_tag = Task_Template_Galaxy_Tags(
                cluster_id=cluster.id,
                template_id=template.id
            )
            db.session.add(task_tag)
            db.session.commit()
            task_cluster_db.append(clusters)
    for c_t_db in task_cluster_db:
        if not c_t_db in form_dict["clusters"]:
            cluster = CommonModel.get_cluster_by_uuid(c_t_db)
            task_cluster = CommonModel.get_task_template_clusters_both(tid, cluster.id)
            Task_Template_Galaxy_Tags.query.filter_by(id=task_cluster.id).delete()
            db.session.commit()

    # Custom tags
    task_custom_tags_db = CommonModel.get_task_custom_tags_name(template.id)
    for custom_tag in form_dict["custom_tags"]:
        if not custom_tag in task_custom_tags_db:
            custom_tag_id = CustomModel.get_custom_tag_by_name(custom_tag).id
            c_t = Task_Template_Custom_Tags(
                task_template_id=template.id,
                custom_tag_id=custom_tag_id
            )
            db.session.add(c_t)
            db.session.commit()
            task_custom_tags_db.append(custom_tag)
    for c_t_db in task_custom_tags_db:
        if not c_t_db in form_dict["custom_tags"]:
            custom_tag = CustomModel.get_custom_tag_by_name(c_t_db)
            task_custom_tag = CommonModel.get_task_custom_tags_both(template.id, custom_tag_id=custom_tag.id)
            Task_Template_Custom_Tags.query.filter_by(id=task_custom_tag.id).delete()
            db.session.commit()

    CommonModel.update_last_modif_task(template.id)

    db.session.commit()


def delete_task_template(tid):
    to_deleted = Case_Task_Template.query.filter_by(task_id=tid).all()
    for to_do in to_deleted:
        db.session.delete(to_do)
        db.session.commit()
    Task_Template_Tags.query.filter_by(task_id=tid).delete()
    Task_Template_Galaxy_Tags.query.filter_by(template_id=tid).delete()
    Task_Template_Custom_Tags.query.filter_by(task_template_id=tid).delete()
    Note_Template.query.filter_by(template_id=tid)
    template = CommonModel.get_task_template(tid)
    db.session.delete(template)
    db.session.commit()
    return True

def create_note(tid):
    """Create a new empty note in the template"""
    template = CommonModel.get_task_template(tid)
    if template:
        note = Note_Template(
            uuid=str(uuid.uuid4()),
            note="",
            template_id=tid,
            template_order_id=template.nb_notes+1
        )
        template.nb_notes += 1
        db.session.add(note)
        db.session.commit()
        CommonModel.update_last_modif_task(template.id)
        return note
    return False


def modif_note_core(tid, notes, note_id):
    """Modify a noe of a task to the DB"""
    template = CommonModel.get_task_template(tid)
    if note_id == "-1":
        note = Note_Template(
            uuid=str(uuid.uuid4()),
            note=notes,
            template_id=tid,
            template_order_id=template.nb_notes+1
        )
        template.nb_notes += 1
        db.session.add(note)
        db.session.commit()

        CommonModel.update_last_modif_task(template.id)
    else:
        note = CommonModel.get_task_note(note_id)
        if note:
            if note.template_id == int(tid):
                note.note = notes
                db.session.commit()
                CommonModel.update_last_modif_task(template.id)
            else:
                return {"message": f"This note is not in template {tid}"}
        else:
            return {"message": "Note not found"}
    return note

def delete_note(tid, note_id):
    """Delete a note by id"""
    note = CommonModel.get_task_note(note_id)
    if note:
        if note.template_id == int(tid):
            Note_Template.query.filter_by(id=note_id).delete()
            db.session.commit()
            CommonModel.update_last_modif_task(tid)
            return True
    return False

def change_order(case, task, up_down):
    case_task_template = Case_Task_Template.query.filter_by(case_id=case.id).all()
    task_template = Case_Task_Template.query.filter_by(case_id=case.id, task_id=task.id).first()
    for task_db in case_task_template:
        # A task move up, case_order_id decrease by one
        if up_down == "true":
            if task_db.case_order_id == task_template.case_order_id - 1:
                task_db.case_order_id += 1
                task_template.case_order_id -= 1
                break
        else:
            if task_db.case_order_id == task_template.case_order_id + 1:
                task_db.case_order_id -= 1
                task_template.case_order_id += 1
                break

    db.session.commit()


def create_subtask(tid, description):
    subtask = Subtask_Template(
        description=description,
        template_id=tid
    )
    db.session.add(subtask)
    db.session.commit()
    return subtask

def edit_subtask(tid, sid, description):
    subtask = CommonModel.get_subtask_template(sid)
    if subtask:
        if subtask.template_id == int(tid):
            subtask.description = description
            db.session.commit()
            return True
    return False

def delete_subtask(tid, sid):
    subtask = CommonModel.get_subtask_template(sid)
    if subtask:
        if subtask.template_id == int(tid):
            db.session.delete(subtask)
            db.session.commit()
            return True
    return False
