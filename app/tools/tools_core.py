from ..db_class.db import *
import uuid
import ast
import json
from .. import db
import datetime
from ..utils import utils
from ..case import case_core
from ..case import task_core
from sqlalchemy import and_
from . import common_template_core as CommonModel
from . import task_template_core as TaskModel

def build_case_query(page, tags=None, taxonomies=None, galaxies=None, clusters=None, title_filter=None):
    query = Case_Template.query
    conditions = []

    if tags or taxonomies:
        query = query.join(Case_Template_Tags, Case_Template_Tags.case_id == Case_Template.id)
        query = query.join(Tags, Case_Template_Tags.tag_id == Tags.id)
        if tags:
            tags = ast.literal_eval(tags)
            conditions.append(Tags.name.in_(list(tags)))

        if taxonomies:
            taxonomies = ast.literal_eval(taxonomies)
            query = query.join(Taxonomy, Taxonomy.id == Tags.taxonomy_id)
            conditions.append(Taxonomy.name.in_(list(taxonomies)))

    if clusters or galaxies:
        query = query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.template_id == Case_Template.id)
        query = query.join(Cluster, Case_Template_Galaxy_Tags.cluster_id == Cluster.id)
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


def get_page_case_templates(page, title_filter, taxonomies=[], galaxies=[], tags=[], clusters=[], or_and_taxo="true", or_and_galaxies="true"):
    cases = build_case_query(page, tags, taxonomies, galaxies, clusters, title_filter)
    nb_pages = cases.pages

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

            for case in cases:
                tags_db = case.to_json()["tags"]
                loc_tag = [tag["name"] for tag in tags_db]
                taxo_list = [Taxonomy.query.get(tag["taxonomy_id"]).name for tag in tags_db]

                if (not tags or all(item in loc_tag for item in tags)) and \
                (not taxonomies or all(item in taxo_list for item in taxonomies)):
                    glob_list.append(case)

            cases = glob_list
        if or_and_galaxies == "false":
            glob_list = []

            for case in cases:
                clusters_db = case.to_json()["clusters"]
                loc_cluster = [cluster["name"] for cluster in clusters_db]
                galaxies_list = [Galaxy.query.get(cluster["galaxy_id"]).name for cluster in clusters_db]

                if (not clusters or all(item in loc_cluster for item in clusters)) and \
                (not galaxies or all(item in galaxies_list for item in galaxies)):
                    glob_list.append(case)

            cases = glob_list
    else:
        if title_filter == 'true':
            cases = Case_Template.query.order_by(('title')).paginate(page=page, per_page=25, max_per_page=50)
        else:
            cases = Case_Template.query.paginate(page=page, per_page=25, max_per_page=50)
        nb_pages = cases.pages
    return cases, nb_pages



def create_case_template(form_dict):
    case_template = Case_Template(
        title=form_dict["title"],
        description=form_dict["description"],
        uuid=str(uuid.uuid4())
    )
    db.session.add(case_template)
    db.session.commit()

    for tag in form_dict["tags"]:
        tag = CommonModel.get_tag(tag)
        
        case_tag = Case_Template_Tags(
            tag_id=tag.id,
            case_id=case_template.id
        )
        db.session.add(case_tag)
        db.session.commit()

    for cluster in form_dict["clusters"]:
        cluster = CommonModel.get_cluster_by_name(cluster)
        
        case_tag = Case_Template_Galaxy_Tags(
            cluster_id=cluster.id,
            template_id=case_template.id
        )
        db.session.add(case_tag)
        db.session.commit()

    for instance in form_dict["connectors"]:
        instance = CommonModel.get_instance_by_name(instance)
        case_instance = Case_Template_Connector_Instance(
            template_id=case_template.id,
            instance_id=instance.id
        )
        db.session.add(case_instance)
        db.session.commit()

    cp = 1
    for tid in form_dict["tasks"]:
        case_task_template = Case_Task_Template(
            case_id=case_template.id,
            task_id=tid,
            case_order_id = cp
        )
        db.session.add(case_task_template)
        db.session.commit()
        cp += 1
    return case_template




def add_task_case_template(form_dict, cid):
    count_task = len(Case_Task_Template.query.filter_by(case_id=cid).all())
    count_task += 1
    if form_dict["tasks"]:
        for tid in form_dict["tasks"]:
            if not Case_Task_Template.query.filter_by(case_id=cid, task_id=tid).first():
                case_task_template = Case_Task_Template(
                    case_id=cid,
                    task_id=tid,
                    case_order_id=count_task
                )
                db.session.add(case_task_template)
                db.session.commit()
                count_task += 1
    elif form_dict["title"]:
        template = TaskModel.add_task_template_core(form_dict)
        case_task_template = Case_Task_Template(
                case_id=cid,
                task_id=template.id,
                case_order_id=count_task
            )
        db.session.add(case_task_template)
        db.session.commit()
    else:
        return "No info"
    



def edit_case_template(form_dict, cid):
    template = CommonModel.get_case_template(cid)

    template.title=form_dict["title"]
    template.description=form_dict["description"]

    ## Tags
    case_tag_db = Case_Template_Tags.query.filter_by(case_id=template.id).all()
    for tag in form_dict["tags"]:
        tag = CommonModel.get_tag(tag)

        if not tag in case_tag_db:
            case_tag = Case_Template_Tags(
                tag_id=tag.id,
                case_id=template.id
            )
            db.session.add(case_tag)
            db.session.commit()
    
    for c_t_db in case_tag_db:
        if not c_t_db in form_dict["tags"]:
            Case_Template_Tags.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

    ## Clusters
    case_tag_db = Case_Template_Galaxy_Tags.query.filter_by(template_id=template.id).all()
    for cluster in form_dict["clusters"]:
        cluster = CommonModel.get_cluster_by_name(cluster)

        if not cluster in case_tag_db:
            case_tag = Case_Template_Galaxy_Tags(
                cluster_id=cluster.id,
                template_id=template.id
            )
            db.session.add(case_tag)
            db.session.commit()
    
    for c_t_db in case_tag_db:
        if not c_t_db in form_dict["clusters"]:
            Case_Template_Galaxy_Tags.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

     ## Connectors
    case_connector_db = Case_Template_Connector_Instance.query.filter_by(template_id=template.id).all()
    for connectors in form_dict["connectors"]:
        instance = CommonModel.get_instance_by_name(connectors)

        if not connectors in case_connector_db:
            case_tag = Case_Template_Connector_Instance(
                instance_id=instance.id,
                template_id=template.id
            )
            db.session.add(case_tag)
            db.session.commit()
    
    for c_t_db in case_connector_db:
        if not c_t_db in form_dict["connectors"]:
            Case_Template_Connector_Instance.query.filter_by(id=c_t_db.id).delete()
            db.session.commit()

    db.session.commit()


def delete_case_template(cid):
    to_deleted = Case_Task_Template.query.filter_by(case_id=cid).all()
    for to_do in to_deleted:
        db.session.delete(to_do)
        db.session.commit()
    Case_Template_Tags.query.filter_by(case_id=cid).delete() 
    Case_Template_Galaxy_Tags.query.filter_by(template_id=cid).delete() 
    Case_Template_Connector_Instance.query.filter_by(template_id=cid).delete()
    template = CommonModel.get_case_template(cid)
    db.session.delete(template)
    db.session.commit()
    return True

def remove_task_case(cid, tid):
    template = Case_Task_Template.query.filter_by(case_id=cid, task_id=tid).first()
    db.session.delete(template)
    db.session.commit()
    return True


def create_case_from_template(cid, case_title_fork, user):
    case_title_stored = Case.query.filter_by(title=case_title_fork).first()
    if case_title_stored:
        return {"message": "Error, title already exist"}
    
    case_template = CommonModel.get_case_template(cid)
    case_tasks = CommonModel.get_all_tasks_by_case(cid)

    case = Case(
        title=case_title_fork,
        description=case_template.description,
        uuid=str(uuid.uuid4()),
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        status_id=1,
        owner_org_id=user.org_id,
        nb_tasks=len(case_tasks)
    )
    db.session.add(case)
    db.session.commit()

    ## Case Tags
    for c_t in Case_Template_Tags.query.filter_by(case_id=case_template.id).all():
        case_tag = Case_Tags(
            case_id=case.id,
            tag_id=c_t.tag_id
        )
        db.session.add(case_tag)
        db.session.commit()

    ## Case Clusters
    for c_t in Case_Template_Galaxy_Tags.query.filter_by(template_id=case_template.id).all():
        case_cluster = Case_Galaxy_Tags(
            case_id=case.id,
            cluster_id=c_t.cluster_id
        )
        db.session.add(case_cluster)
        db.session.commit()

    ## Case Connectors
    for c_t in Case_Template_Connector_Instance.query.filter_by(template_id=case_template.id).all():
        case_connector = Case_Connector_Instance(
            case_id=case.id,
            instance_id=c_t.instance_id
        )
        db.session.add(case_connector)
        db.session.commit()

    # Add the current user's org to the case
    case_org = Case_Org(
        case_id=case.id, 
        org_id=user.org_id
    )

    db.session.add(case_org)
    db.session.commit()

    task_case_template = CommonModel.get_task_by_case(cid)
    for task in task_case_template:
        task_in_case = CommonModel.get_task_by_case_class(cid, task.id)
        t = Task(
            uuid=str(uuid.uuid4()),
            title=task.title,
            description=task.description,
            url=task.url,
            creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
            case_id=case.id,
            status_id=1,
            case_order_id=task_in_case.case_order_id,
            nb_notes=task.nb_notes
        )
        db.session.add(t)
        db.session.commit()

        for t_note in task.notes:
            note = Note(
                uuid=str(uuid.uuid4()),
                note=t_note.note,
                task_id=t.id,
                task_order_id=task.nb_notes+1
            )
            db.session.add(note)
            db.session.commit()

        ## Task Tags
        for t_t in Task_Template_Tags.query.filter_by(task_id=task.id).all():
            task_tag = Task_Tags(
                task_id=t.id,
                tag_id=t_t.tag_id
            )
            db.session.add(task_tag)
            db.session.commit()
        
        ## Task Clusters
        for t_t in Task_Template_Galaxy_Tags.query.filter_by(template_id=task.id).all():
            task_cluster = Task_Galaxy_Tags(
                task_id=t.id,
                cluster_id=t_t.cluster_id
            )
            db.session.add(task_cluster)
            db.session.commit()

        ## Task Connectors
        for t_c in Task_Template_Connector_Instance.query.filter_by(template_id=task.id).all():
            task_connector = Task_Connector_Instance(
                task_id=t.id,
                instance_id=t_c.instance_id
            )
            db.session.add(task_connector)
            db.session.commit()
    
    return case

def core_read_json_file(case, current_user):
    if not utils.validateCaseJson(case):
        return {"message": f"Case '{case['title']}' format not okay"}
    for task in case["tasks"]:
        if not utils.validateTaskJson(task):
            return {"message": f"Task '{task['title']}' format not okay"}


    #######################
    ## Case Verification ##
    #######################

    ## Caseformat is valid
    # title
    if Case.query.filter_by(title=case["title"]).first():
        return {"message": f"Case Title '{case['title']}' already exist"}
    # deadline
    if case["deadline"]:
        try:
            loc_date = datetime.datetime.strptime(case["deadline"], "%Y-%m-%d %H:%M")
            case["deadline_date"] = loc_date.date()
            case["deadline_time"] = loc_date.time()
        except Exception as e:
            print(e)
            return {"message": f"Case '{case['title']}': deadline bad format, %Y-%m-%d %H:%M"}
    else:
        case["deadline_date"] = ""
        case["deadline_time"] = ""
    # recurring_date
    if case["recurring_date"]:
        if case["recurring_type"]:
            try:
                datetime.datetime.strptime(case["recurring_date"], "%Y-%m-%d %H:%M")
            except:
                return {"message": f"Case '{case['title']}': recurring_date bad format, %Y-%m-%d"}
        else:
            return {"message": f"Case '{case['title']}': recurring_type is missing"}
    # recurring_type
    if case["recurring_type"] and not case["recurring_date"]:
        return {"message": f"Case '{case['title']}': recurring_date is missing"}
    # uuid
    if Case.query.filter_by(uuid=case["uuid"]).first():
        case["uuid"] = str(uuid.uuid4())

    # tags
    for tag in case["tags"]:
        if not utils.check_tag(tag):
            return {"message": f"Case '{case['title']}': tag '{tag}' doesn't exist"}
        
    
    #######################
    ## Task Verification ##
    #######################

    ## Task format is valid
    for task in case["tasks"]:
        if Task.query.filter_by(uuid=task["uuid"]).first():
            task["uuid"] = str(uuid.uuid4())

        if task["deadline"]:
            try:
                loc_date = datetime.datetime.strptime(task["deadline"], "%Y-%m-%d %H:%M")
                task["deadline_date"] = loc_date.date()
                task["deadline_time"] = loc_date.time()
            except:
                return {"message": f"Task '{task['title']}': deadline bad format, %Y-%m-%d %H:%M"}
        else:
            task["deadline_date"] = ""
            task["deadline_time"] = ""

        for tag in task["tags"]:
            if not utils.check_tag(tag):
                return {"message": f"Task '{task['title']}': tag '{tag}' doesn't exist"}


    #################
    ## DB Creation ##
    ################

    ## Case creation
    case_created = case_core.create_case(case, current_user)

    ## Task creation
    for task in case["tasks"]:
        task_created = task_core.create_task(task, case_created.id, current_user)
        if task["notes"]:
            task_core.modif_note_core(task_created.id, current_user, task["notes"])

    
def read_json_file(files_list, current_user):
    for file in files_list:
        if files_list[file].filename:
            try:
                file_data = json.loads(files_list[file].read().decode())
                if type(file_data) == list:
                    for case in file_data:
                        res = core_read_json_file(case, current_user)
                        if res: return res
                else:
                    return core_read_json_file(file_data, current_user)
            except Exception as e:
                print(e)
                return {"message": "Something went wrong"}
            