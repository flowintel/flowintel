import os, re
import shutil
import datetime
import subprocess
from typing import List
import uuid

from flask import send_file
from .. import db
from ..db_class.db import *
from ..utils.utils import get_modules_list, isUUID, create_specific_dir
from sqlalchemy import desc, func, or_
from ..utils import utils
from ..custom_tags import custom_tags_core as CustomModel

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
TEMP_FOLDER = os.path.join(os.getcwd(), "temp")
HISTORY_DIR = os.environ.get("HISTORY_DIR", "history")


def get_present_in_case(case_id: int, current_user: User) -> bool:
    """Return if current user is present in a case"""
    orgs_in_case = get_orgs_in_case(case_id)

    present_in_case = False
    if len(orgs_in_case) > 0:
        for org in orgs_in_case:
            if org.id == current_user.org_id:
                present_in_case = True
                break

    return present_in_case

def check_user_in_private_cases(cases: List[Case], current_user: User) -> List[Case]:
    if current_user.is_admin(): # admin have access to all cases
        return cases

    loc_case = list()
    for case in cases:
        if case.is_private:
            if get_present_in_case(case.id, current_user):
                loc_case.append(case)
        else:
            loc_case.append(case)
    return loc_case

def get_case(cid):
    """Return a case by is id"""
    if isUUID(cid):
        case = Case.query.filter_by(uuid=cid).first()
    elif str(cid).isdigit():
        case = Case.query.get(cid)
    else:
        case = None
    return case

def get_task(tid):
    """Return a task by is id"""
    if isUUID(tid):
        case = Task.query.filter_by(uuid=tid).first()
    elif str(tid).isdigit():
        case = Task.query.get(tid)
    else:
        case = None
    return case

def get_all_cases(current_user: User) -> List[Case]:
    """Return all cases"""
    cases = Case.query.filter_by(completed=False).order_by(desc(Case.last_modif))
    return check_user_in_private_cases(cases, current_user)

def get_case_by_completed(completed, current_user: User) -> List[Case]:
    """Return a list of case depending on completed"""
    cases = Case.query.filter_by(completed=completed).all()
    return check_user_in_private_cases(cases, current_user)


def get_case_by_title(title: str, current_user: User):
    """Return a case by its title"""
    case = Case.query.filter_by(title = title).first()
    if case:
        if case.is_private:
            if get_present_in_case(case.id, current_user):
                return case
            return None
        return case
    return None

def check_case_title(title: str):
    """Check if a case already exist with the title"""
    return Case.query.where(func.lower(Case.title) == func.lower(title)).first()

def get_task_by_title(title, current_user):
    """Return a tas by its title"""
    task = Task.query.filter_by(title=title).first()
    if task:
        case = get_case(task.case_id)
        if case.is_private:
            if get_present_in_case(case.id, current_user):
                return task
            return None
        return task
    return None


def get_case_template_by_title(title: str):
    """Return a case template by its title"""
    return Case_Template.query.where(func.lower(Case_Template.title)==func.lower(title)).first()


def get_task_templates():
    """Return a list of task template"""
    return Task_Template.query.all()

def search(text: str, current_user: User) -> List[Case]:
    """Return cases containing text"""
    cases = Case.query.where(Case.title.contains(text), Case.completed==False).paginate(page=1, per_page=30, max_per_page=50)
    return check_user_in_private_cases(cases, current_user)

def get_all_org_case(case):
    """Return a list of all orgs in a case"""
    return Org.query.join(Case_Org, Case_Org.case_id==case.id).where(Case_Org.org_id==Org.id).all()


def get_role(user):
    """Return role for the current user"""
    return Role.query.get(user.role_id)


def get_org(oid):
    """Return an org by is id"""
    return Org.query.get(oid)

def get_orgs():
    """Return all orgs"""
    return Org.query.all()

def get_org_by_name(name):
    """Return an org by is name"""
    return Org.query.filter_by(name=name).first()

def get_org_order_by_name():
    """Return all orgs order by name"""
    return Org.query.order_by("name")

def get_org_in_case(org_id, case_id):
    """Return an instance of Case_org"""
    return Case_Org.query.filter_by(case_id=case_id, org_id=org_id).first()

def get_org_in_case_by_case_id(case_id):
    """Return an instance of Case_org depending of a case id"""
    return Case_Org.query.filter_by(case_id=case_id).all()

def get_orgs_in_case(case_id):
    """Return orgs present in a case"""
    case_org = Case_Org.query.filter_by(case_id=case_id).all()
    return [Org.query.get(c_o.org_id) for c_o in case_org ]


def get_file(fid):
    """Return a file"""
    return File.query.get(fid)

def get_all_status():
    """Return a list of all status"""
    return Status.query.all()

def get_status(sid):
    """Return a status"""
    return Status.query.get(sid)


def get_recu_notif_user(case_id, user_id):
    """Return a notification for a case for a user"""
    return Recurring_Notification.query.filter_by(case_id=case_id, user_id=user_id).first()


def get_taxonomies():
    """Return a list of all taxonomies"""
    return [taxo.to_json() for taxo in Taxonomy.query.filter_by(exclude=False).all()]

def get_galaxy(galaxy_id):
    """Return a galaxy"""
    return Galaxy.query.get(galaxy_id)

def get_galaxies():
    """Return a list of all galaxies"""
    return [galax.to_json() for galax in Galaxy.query.filter_by(exclude=False).order_by('name').all()]

def get_clusters():
    """Return a list of all clusters"""
    return [cluster.to_json() for cluster in Cluster.query.all()]

def get_cluster_by_name(cluster):
    """Return a cluster by its name"""
    return Cluster.query.filter_by(name=cluster).first()

def get_cluster_by_uuid(cluster_uuid):
    """Return a cluster by its uuid"""
    return Cluster.query.filter_by(uuid=cluster_uuid).first()

def get_clusters_galaxy(galaxies) -> dict:
    """Return a dictionary with each clusters for each galaxies"""
    out = dict()
    for galaxy in galaxies:
        out[galaxy] = [cluster.to_json() for cluster in \
                       Cluster.query.join(Galaxy, Galaxy.id==Cluster.galaxy_id)\
                        .where(Galaxy.name==galaxy).all() if not cluster.exclude]
    return out


def get_tags(taxos) -> dict:
    """Return a dictionary with each tags for each taxonomies"""
    out = dict()
    for taxo in taxos:
        out[taxo] = [tag.to_json() for tag in Taxonomy.query.filter_by(name=taxo).first().tags if not tag.exclude]
    return out

def get_tag(tag):
    """Return a tag by its name"""
    return Tags.query.filter_by(name=tag).first()


def get_case_tags(cid):
    """Return a list of tags present in a case"""
    return [tag.name for tag in Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=cid).all()]

def get_case_tags_json(cid):
    """Return a list of tags present in a case"""
    return [tag.to_json() for tag in Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=cid).all()]

def get_case_tags_both(case_id, tag_id):
    """Return a list of tags present in a case"""
    return Case_Tags.query.filter_by(case_id=case_id, tag_id=tag_id).first()

def get_case_clusters(cid):
    """Return a list of clusters present in a case"""
    return [cluster for cluster in \
            Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(case_id=cid).all()]

def get_case_clusters_both(case_id, cluster_id):
    """Return a list of clusters present in a case"""
    return Case_Galaxy_Tags.query.filter_by(case_id=case_id, cluster_id=cluster_id).first()

def get_case_clusters_name(cid):
    """Return a list of clusters name present in a case"""
    return [cluster.name for cluster in \
            Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(case_id=cid).all()]

def get_case_clusters_uuid(cid):
    """Return a list of clusters uuid present in a case"""
    return [cluster.uuid for cluster in \
            Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(case_id=cid).all()]

def get_task_tags(tid):
    """Return a list of tags present in a task"""
    return [tag.name for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_task_tags_json(tid):
    """Return a list of tags present in a task in json"""
    return [tag.to_json() for tag in Tags.query.join(Task_Tags, Task_Tags.tag_id==Tags.id).filter_by(task_id=tid).all()]

def get_task_tags_both(task_id, tag_id):
    """Return a list of tags present in a task"""
    return Task_Tags.query.filter_by(task_id=task_id, tag_id=tag_id).first()

def get_task_clusters(tid):
    """Return a list of clusters present in a task"""
    return [cluster for cluster in \
            Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(task_id=tid).all()]

def get_task_clusters_name(task_id):
    """Return a list of clusters name present in a task"""
    return [cluster.name for cluster in \
            Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(task_id=task_id).all()]

def get_task_clusters_uuid(task_id):
    """Return a list of clusters uuid present in a task"""
    return [cluster.uuid for cluster in \
            Cluster.query.join(Task_Galaxy_Tags, Task_Galaxy_Tags.cluster_id==Cluster.id)\
                .filter_by(task_id=task_id).all()]

def get_task_clusters_both(task_id, cluster_id):
    """Return a list of tags present in a task"""
    return Task_Galaxy_Tags.query.filter_by(task_id=task_id, cluster_id=cluster_id).first()

def get_connectors():
    """Return a list of all connectors"""
    return Connector.query.all()

def get_connector(cid):
    """Return a connector"""
    return Connector.query.get(cid)

def get_connector_by_name(name):
    """Return a connector by its name"""
    return Connector.query.where(Connector.name.like(name)).first()

def get_instance(iid):
    """Return an instance"""
    return Connector_Instance.query.get(iid)

def get_instance_by_name(name):
    """Return an instance by its name"""
    return Connector_Instance.query.filter_by(name=name).first()

def get_case_connectors(cid, current_user: User):
    """Return a list of all connectors present in a case"""
    return Case_Connector_Instance.query\
            .join(User_Connector_Instance, User_Connector_Instance.instance_id==Case_Connector_Instance.instance_id)\
            .join(Connector_Instance, Connector_Instance.id==Case_Connector_Instance.instance_id)\
            .where(
                or_(User_Connector_Instance.user_id==current_user.id, Connector_Instance.global_api_key.isnot(None)), 
                Case_Connector_Instance.case_id==cid)\
            .all()

def get_case_connectors_by_id(case_instance_id):
    """Return a case connector instance"""
    return Case_Connector_Instance.query.get(case_instance_id)

def get_case_connectors_name(cid):
    """Return a list of all name connectors present in a case"""
    return [instance.name for instance in \
            Connector_Instance.query.join(Case_Connector_Instance, Case_Connector_Instance.instance_id==Connector_Instance.id)\
                .filter_by(case_id=cid).all()]

def get_case_connectors_both(case_id, instance_id):
    """Return an instance of Case_Connector_Instance depending of a case id and an instance id"""
    return Case_Connector_Instance.query.filter_by(case_id=case_id, instance_id=instance_id).first()

def get_task_connectors(tid):
    """Return a list of all connectors present in a task"""
    return Task_Connector_Instance.query.filter_by(task_id=tid).all()

def get_task_connectors_by_id(task_instance_id):
    """Return a task connector instance"""
    return Task_Connector_Instance.query.get(task_instance_id)

def get_task_connectors_name(task_id):
    """Return a list of all name connectors present in a task"""
    return [instance.name for instance in \
            Connector_Instance.query.join(Task_Connector_Instance, Task_Connector_Instance.instance_id==Connector_Instance.id)\
                .filter_by(task_id=task_id).all()]

def get_task_connectors_both(task_id, instance_id):
    """Return an instance of Task_Connector_Instance depending of a task id and an instance id"""
    return Task_Connector_Instance.query.filter_by(task_id=task_id, instance_id=instance_id).first()

def get_user_instance_both(user_id, instance_id):
    """Return an instance of User_Connector_Instance depending of a user id and an instance id"""
    return User_Connector_Instance.query.filter_by(user_id=user_id, instance_id=instance_id).first()

def get_user_instance_by_instance(instance_id):
    """Return an instance of User_Connector_Instance depending of an instance id"""
    return User_Connector_Instance.query.filter_by(instance_id=instance_id).first()

def get_case_connector_id(instance_id, case_id):
    """Return an instance of Case_Connector_Instance depending of an instance id and a case id"""
    return Case_Connector_Instance.query.filter_by(case_id=case_id, instance_id=instance_id).first()

def get_task_connector_id(instance_id, task_id):
    """Return an instance of Task_Connector_Instance depending of an instance id and a task id"""
    return Task_Connector_Instance.query.filter_by(task_id=task_id, instance_id=instance_id).first()

def get_task_note(note_id):
    return Note.query.get(note_id)

def get_case_custom_tags(case_id):
    return Case_Custom_Tags.query.filter_by(case_id=case_id).all()

def get_case_custom_tags_name(case_id):
    return [c_t.name for c_t in \
            Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                .where(Case_Custom_Tags.case_id==case_id).all()]

def get_case_custom_tags_json(case_id):
    return [c_t.to_json() for c_t in \
            Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                .where(Case_Custom_Tags.case_id==case_id).all()]

def get_case_custom_tags_both(case_id, custom_tag_id):
    return Case_Custom_Tags.query.filter_by(case_id=case_id, custom_tag_id=custom_tag_id).first()

def get_task_custom_tags(task_id):
    return Task_Custom_Tags.query.filter_by(task_id=task_id).all()

def get_task_custom_tags_name(task_id):
    return [c_t.name for c_t in \
            Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                .where(Task_Custom_Tags.task_id==task_id).all()]

def get_task_custom_tags_json(task_id):
    return [c_t.to_json() for c_t in \
            Custom_Tags.query.join(Task_Custom_Tags, Task_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                .where(Task_Custom_Tags.task_id==task_id).all()]

def get_task_custom_tags_both(task_id, custom_tag_id):
    return Task_Custom_Tags.query.filter_by(task_id=task_id, custom_tag_id=custom_tag_id).first()


def get_history(case_uuid):
    """Return history of case by its uuid"""
    try:
        path_history = os.path.join(HISTORY_DIR, str(case_uuid))
        with open(path_history, "r") as read_file:
            loc_file = read_file.read().splitlines()
        return loc_file
    except OSError:
        return False
    
def save_history(case_uuid, current_user, message):
    """Save historic message of a case"""
    create_specific_dir(HISTORY_DIR)
    path_history = os.path.join(HISTORY_DIR, str(case_uuid))
    with open(path_history, "a") as write_history:
        now = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        write_history.write(f"[{now}]({current_user.first_name} {current_user.last_name}): {message.rstrip()}\n")

def append_history_file(case, merging):
    """Append case history to the merging case history"""
    create_specific_dir(HISTORY_DIR)
    path_case_history = os.path.join(HISTORY_DIR, str(case.uuid))
    path_merging_history = os.path.join(HISTORY_DIR, str(merging.uuid))
    with open(path_case_history, "r") as src, open(path_merging_history, "a") as dst:
        for line in src:
            dst.write(f"{line} (merge from {case.id} - {case.title})")


def update_last_modif(case_id):
    """Update 'last_modif' of a case"""
    case = Case.query.get(case_id)
    case.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
    db.session.commit()


def update_last_modif_task(task_id):
    """Update 'last_modif' of a task"""
    if task_id:
        task = Task.query.get(task_id)
        task.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
        db.session.commit()


def deadline_check(date, time):
    """Combine the date and the time if time exist"""
    deadline = None
    if date and time:
        deadline = datetime.datetime.combine(date, time)
    elif date:
        deadline = date
    
    return deadline


def delete_temp_folder():
    """Delete temp folder"""
    shutil.rmtree(TEMP_FOLDER)


def smart_escape_for_markdown_to_latex(text: str) -> str:
    # Only escape characters that break LaTeX via Pandoc
    escape_map = {
        '\\': r'\\',
        '{': r'\{',
        '}': r'\}',
        '$': r'\$',
        '&': r'\&',
        '_': r'\_',
        '%': r'\%',
        '^': r'\^{}',
        '~': r'\~{}',
    }

    def escape_text(t):
        pattern = re.compile('|'.join(re.escape(k) for k in escape_map))
        return pattern.sub(lambda m: escape_map[m.group()], t)

    # Regex patterns for fenced and inline code
    code_block_pattern = re.compile(r'```.*?```', re.DOTALL)
    inline_code_pattern = re.compile(r'`[^`\n]+`')

    # Temporarily replace code with placeholders
    all_code = []
    def placeholder(match):
        all_code.append(match.group())
        return f"§§CODE{len(all_code)}§§"

    temp = code_block_pattern.sub(placeholder, text)
    temp = inline_code_pattern.sub(placeholder, temp)

    # Escape only outside code
    escaped = escape_text(temp)

    # Restore code blocks
    def restore(match):
        index = int(match.group(1)) - 1
        return all_code[index]

    result = re.sub(r'§§CODE(\d+)§§', restore, escaped)
    return result

def convert_inline_code_to_verb(text: str) -> str:
    # Find all inline code spans: `like this`
    def replace_inline_code(match):
        content = match.group(0)[1:-1]  # Remove the backticks
        # If it starts with a LaTeX command, wrap it in \verb
        if content.strip().startswith("\\"):
            return r"\verb|" + content + r"|"
        else:
            return f"`{content}`"

    inline_code_pattern = re.compile(r'`[^`\n]+`')
    return inline_code_pattern.sub(replace_inline_code, text)


def export_notes(case_task: bool, case_task_id: int, type_req: str, note_id: int = None):
    """Export notes into a format like pdf or docx"""
    if not case_task:
        note = get_task_note(note_id).note
    else:
        note = get_case(case_task_id).notes

    return export_notes_core(case_task_id, type_req, note)

def export_notes_core(case_task_id: int, type_req: str, note: str, download_filename: str = None):
    if not os.path.isdir(TEMP_FOLDER):
        os.mkdir(TEMP_FOLDER)

    if not download_filename:
        download_filename = f"export_note_{case_task_id}.{type_req}"
    else:
        if not download_filename.endswith(f".{type_req}"):
            download_filename = f"{download_filename}.{type_req}"
    temp_md = os.path.join(TEMP_FOLDER, "index.md")
    temp_export = os.path.join(TEMP_FOLDER, f"output.{type_req}")

    loc_note = smart_escape_for_markdown_to_latex(note)
    loc_note = convert_inline_code_to_verb(loc_note)
    with open(temp_md, "w")as write_file:
        write_file.write(loc_note)
        
    if type_req == "pdf":
        process = subprocess.Popen(["pandoc", temp_md, "--pdf-engine=xelatex", \
                                    "-V", "colorlinks=true", \
                                    "-V", "linkcolor=blue", \
                                    "-V", "urlcolor=red", \
                                    "-V", "tocolor=gray",\
                                    "--number-sections", "--toc", \
                                    "--template", "eisvogel",\
                                    "-o", temp_export, \
                                    "--filter=pandoc-mermaid"], stdout=subprocess.PIPE)
    elif type_req == "docx":
        process = subprocess.Popen(["pandoc", temp_md, "-o", temp_export, "--filter=mermaid-filter"], stdout=subprocess.PIPE)
    process.wait()

    try:
        shutil.rmtree(os.path.join(os.getcwd(), "mermaid-images"))
    except OSError:
        pass

    if not os.path.isfile(temp_export):
        return {"message": "Error during export process", "toast_class": "danger-subtle"}
    
    return send_file(temp_export, as_attachment=True, download_name=download_filename)


def check_cluster_uuid_db(cluster):
    """Check if a cluster exist in db"""
    return Cluster.query.filter_by(uuid=cluster).first()

def check_cluster_tags_db(cluster):
    """Check if a cluster exist in db"""
    return Cluster.query.filter_by(tag=cluster).first()

def check_cluster_name_db(cluster):
    return Cluster.query.filter_by(name=cluster).first()

def check_tag(tag_list):
    """Check if a list of tags exist"""
    for tag in tag_list:
        if not utils.check_tag(tag):
            return tag
    return True

def check_cluster(cluster_list):
    """Check if a list of clusters exist by uuid"""
    for cluster in cluster_list:
        if isUUID(cluster):
            if not check_cluster_uuid_db(cluster):
                return cluster
        else:
            if not check_cluster_name_db(cluster):
                return cluster
    return True

def check_cluster_tags(cluster_list):
    """Check if a list of clusters exist by tags"""
    for cluster in cluster_list:
        if not check_cluster_tags_db(cluster):
            return cluster
    return True

def check_connector(connector_list):
    """Check if a list of connectors exist"""
    for connector in connector_list:
        if not get_instance_by_name(connector):
            return connector
    return True

def check_custom_tags(tags_list):
    """Check if a list of custom tags exist"""
    for tag in tags_list:
        if not CustomModel.get_custom_tag_by_name(tag):
            return tag
    return True


def create_task_from_template(template_id, cid):
    """Create a task from a task template"""
    template = Task_Template.query.get(template_id)
    case = get_case(cid)
    nb_tasks = 1
    if case.nb_tasks:
        nb_tasks = case.nb_tasks+1
    else:
        case.nb_tasks = 0
    task = Task(
        uuid=str(uuid.uuid4()),
        title=template.title,
        description=template.description,
        creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
        last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
        case_id=cid,
        status_id=1,
        case_order_id=nb_tasks,
        nb_notes=0
    )
    db.session.add(task)
    db.session.commit()

    for t_note in template.notes:
        note = Note(
            uuid=str(uuid.uuid4()),
            note=t_note.note,
            task_id=task.id,
            task_order_id=task.nb_notes + 1,
        )
        db.session.add(note)
        db.session.commit()

    for t_url_tool in template.urls_tools:
        url_tool = Task_Url_Tool(
            task_id=task.id,
            name=t_url_tool.name,
        )
        db.session.add(url_tool)
        db.session.commit()

    for t_t in Task_Template_Tags.query.filter_by(task_id=template.id).all():
        task_tag = Task_Tags(
            task_id=task.id,
            tag_id=t_t.tag_id
        )
        db.session.add(task_tag)
        db.session.commit()

    for t_t in Task_Template_Galaxy_Tags.query.filter_by(template_id=template.id).all():
        task_tag = Task_Galaxy_Tags(
            task_id=task.id,
            cluster_id=t_t.cluster_id
        )
        db.session.add(task_tag)
        db.session.commit()

    ## Task Custom Tags
    for c_t in Task_Template_Custom_Tags.query.filter_by(task_template_id=template.id).all():
        task_custom_tags = Task_Custom_Tags(
            task_id=task.id,
            custom_tag_id=c_t.custom_tag_id
        )
        db.session.add(task_custom_tags)
        db.session.commit()

    ## Task subtasks
    for sub in task.subtasks:
        subtask = Subtask(
            task_id=task.id,
            descritpion=sub.description
        )
        db.session.add(subtask)
        db.session.commit()

    return task


def get_instance_with_icon(instance_id):
    """Return an instance of a connector with its icon"""
    loc_instance = get_instance(instance_id).to_json()
    loc_instance["icon"] = Icon_File.query.join(Connector_Icon, Connector_Icon.file_icon_id==Icon_File.id)\
                                    .join(Connector, Connector.icon_id==Connector_Icon.id)\
                                    .join(Connector_Instance, Connector_Instance.connector_id==Connector.id)\
                                    .where(Connector_Instance.id==instance_id)\
                                    .first().uuid
    return loc_instance


def get_modules_by_case_task(case_task):
    """Return modules for task only"""
    _, res = get_modules_list()
    loc_list = {}
    for module in res:
        if res[module]["config"]["case_task"] == case_task:
            loc_list[module] = res[module]
    return loc_list


def module_error_check(event):
    if isinstance(event, dict):
        if "message" in event:
            return event
        if type(event["errors"][1]["errors"]) == dict:
            return {"message": event["errors"][1]["errors"]["value"][0]}
        else:
            loc = re.search(r"\{.*\}", event["errors"][1]["errors"])
            if loc:
                return {"message": json.loads(loc.group())["value"][0]}
            return {"message": event["errors"][1]["errors"]}
