from typing import List, Union
from ..db_class.db import *
import uuid
from .. import db
import datetime
from ..case import common_core
from ..case.CommonAbstract import CommonAbstract
from ..case.FilteringAbstract import FilteringAbstract
from sqlalchemy import and_, desc
from . import common_template_core as CommonModel
from .TaskTemplateCore import TaskModel
from ..custom_tags import custom_tags_core as CustomModel

class TemplateCase(CommonAbstract, FilteringAbstract):
    def get_class(self) -> Case_Template:
        return Case_Template
    
    def get_tags(self) -> Case_Template_Tags:
        return Case_Template_Tags

    def get_tag_class_id(self) -> int:
        return Case_Template_Tags.case_id

    def get_galaxies(self) -> Case_Template_Galaxy_Tags:
        return Case_Template_Galaxy_Tags

    def get_galaxies_class_id(self) -> int:
        return Case_Template_Galaxy_Tags.template_id

    def get_custom_tags(self) -> Case_Template_Custom_Tags:
        return Case_Template_Custom_Tags

    def get_custom_tags_class_id(self) -> int:
        return Case_Template_Custom_Tags.case_template_id

    def create_case(self, form_dict):
        case_template = Case_Template(
            title=form_dict["title"],
            description=form_dict["description"],
            uuid=str(uuid.uuid4()),
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
            time_required=form_dict["time_required"]
        )
        db.session.add(case_template)
        db.session.commit()

        for tag in form_dict["tags"]:
            tag = CommonModel.get_tag(tag)
            
            self.add_tag(tag, case_template.id)

        for cluster in form_dict["clusters"]:
            cluster = CommonModel.get_cluster_by_name(cluster)
            
            self.add_cluster(cluster, case_template.id)

        for custom_tag_name in form_dict["custom_tags"]:
            custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
            if custom_tag:
                self.add_custom_tag(custom_tag, case_template.id)

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

    def delete_case(self, case_id):
        to_deleted = Case_Task_Template.query.filter_by(case_id=case_id).all()
        for to_do in to_deleted:
            db.session.delete(to_do)
            db.session.commit()
        Case_Template_Tags.query.filter_by(case_id=case_id).delete() 
        Case_Template_Galaxy_Tags.query.filter_by(template_id=case_id).delete()
        Case_Template_Custom_Tags.query.filter_by(case_template_id=case_id).delete()
        Case_Template_Connector_Instance.query.filter_by(case_template_id=case_id).delete()
        template = CommonModel.get_case_template(case_id)
        db.session.delete(template)
        db.session.commit()
        return True

    def get_assigned_tags(self, class_id) -> List:
        return [tag.name for tag in Tags.query.join(Case_Template_Tags, Case_Template_Tags.tag_id==Tags.id).filter_by(case_id=class_id).all()]

    def get_case_tags_both(self, class_id, tag_id):
        """Return a list of tags present in a case"""
        return Case_Template_Tags.query.filter_by(case_id=class_id, tag_id=tag_id).first()

    def get_assigned_clusters_uuid(self, class_id) -> List:
        """Return a list of clusters uuid present in a case template"""
        return [cluster.uuid for cluster in \
                Cluster.query.join(Case_Template_Galaxy_Tags, Case_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                    .filter_by(template_id=class_id).all()]

    def get_assigned_custom_tags_name(self, class_id) -> List:
        c_ts = Custom_Tags.query\
            .join(Case_Template_Custom_Tags, Case_Template_Custom_Tags.custom_tag_id==Custom_Tags.id)\
            .where(Case_Template_Custom_Tags.case_template_id==class_id).all()
        return [c_t.name for c_t in c_ts]

    def add_tag(self, tag, class_id) -> str:
        case_tag = Case_Template_Tags(
            tag_id=tag.id,
            case_id=class_id
        )
        db.session.add(case_tag)
        db.session.commit()

    def delete_tag(self, tag, class_id) -> None:
        case_tag = CommonModel.get_case_template_tags_both(class_id, tag.id)
        Case_Template_Tags.query.filter_by(id=case_tag.id).delete()
        db.session.commit()

    def add_cluster(self, cluster, class_id) -> str:
        case_tag = Case_Template_Galaxy_Tags(
            cluster_id=cluster.id,
            template_id=class_id
        )
        db.session.add(case_tag)
        db.session.commit()

    def delete_cluster(self, cluster, class_id) -> None:
        case_cluster = CommonModel.get_case_template_clusters_both(class_id, cluster.id)
        Case_Template_Galaxy_Tags.query.filter_by(id=case_cluster.id).delete()
        db.session.commit()

    def add_custom_tag(self, custom_tag, class_id) -> str:
        c_t = Case_Template_Custom_Tags(
            case_template_id=class_id,
            custom_tag_id=custom_tag.id
        )
        db.session.add(c_t)
        db.session.commit()

    def delete_custom_tag(self, custom_tag, class_id) -> None:
        case_custom_tag = CommonModel.get_case_custom_tags_both(class_id, custom_tag_id=custom_tag.id)
        Case_Template_Custom_Tags.query.filter_by(id=case_custom_tag.id).delete()
        db.session.commit()

    def update_case_time_modification(self, case):
        CommonModel.update_last_modif(case.id)

        db.session.commit()

    def edit(self, form_dict, cid):
        template = CommonModel.get_case_template(cid)

        template.title=form_dict["title"]
        template.description=form_dict["description"]
        template.time_required = form_dict["time_required"]

        self.update_case_time_modification(template)

    def edit_tags(self, form_dict, cid):
        template = CommonModel.get_case_template(cid)
        self._edit(form_dict, cid)
        self.update_case_time_modification(template)
        

    def build_case_query(self, page, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None, title_filter=None):
        query, conditions = self._build_sort_query(None, tags, taxonomies, galaxies, clusters, custom_tags)

        if title_filter=='true':
            query = query.order_by('title')
        else:
            query = query.order_by(desc('last_modif'))
        
        return query.filter(and_(*conditions)).paginate(page=page, per_page=25, max_per_page=50)

    def sort_cases(self, page, title_filter, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true"):
        if tags or taxonomies or galaxies or clusters or custom_tags:
            cases = self.build_case_query(page, tags, taxonomies, galaxies, clusters, custom_tags, title_filter)
            nb_pages = cases.pages
            cases = self._sort(cases, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies)
        else:
            query = Case_Template.query
            if title_filter == 'true':
                query = query.order_by('title')
            else:
                query = query.order_by(desc('last_modif'))
            cases = query.paginate(page=page, per_page=25, max_per_page=50)
            nb_pages = cases.pages
        return cases, nb_pages
    


    def add_task_case_template(self, form_dict, cid):
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
            CommonModel.update_last_modif(cid)
        elif form_dict["title"]:
            template = TaskModel.add_task_template_core(form_dict)
            case_task_template = Case_Task_Template(
                    case_id=cid,
                    task_id=template.id,
                    case_order_id=count_task
                )
            db.session.add(case_task_template)
            db.session.commit()
            CommonModel.update_last_modif(cid)
        else:
            return "No info"
        

    def reorder_tasks(self, case_id, template):
        case_task_template = Case_Task_Template.query.filter_by(case_id=case_id).all()
        # Filter out the task to delete
        remaining_tasks = [t for t in case_task_template if t.task_id != template]

        # Sort remaining tasks by case_order_id
        remaining_tasks = sorted(remaining_tasks, key=lambda t: t.case_order_id)

        # Reassign order IDs sequentially starting from 1
        for i, task in enumerate(remaining_tasks, start=1):
            task.case_order_id = i
            
        # Commit changes to DB
        db.session.commit()
        
    def remove_task_case(self, cid, tid):
        template = Case_Task_Template.query.filter_by(case_id=cid, task_id=tid).first()
        self.reorder_tasks(cid, template)
        db.session.delete(template)
        db.session.commit()
        CommonModel.update_last_modif(cid)
        return True


    def create_case_from_template(self, cid: int, case_title_fork: str, user: User):
        case_title_stored = Case.query.filter_by(title=case_title_fork.strip()).first()
        if case_title_stored:
            return {"message": "Error, title already exist"}
        
        case_template = CommonModel.get_case_template(cid)
        case_tasks = CommonModel.get_all_tasks_by_case(cid)

        case = Case(
            title=case_title_fork.strip(),
            description=case_template.description,
            uuid=str(uuid.uuid4()),
            creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
            status_id=1,
            owner_org_id=user.org_id,
            nb_tasks=len(case_tasks),
            notes=case_template.notes
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

        ## Case Custom Tags
        for c_t in CommonModel.get_case_custom_tags(case_template.id):
            case_custom_tags = Case_Custom_Tags(
                case_id=case.id,
                custom_tag_id=c_t.custom_tag_id
            )
            db.session.add(case_custom_tags)
            db.session.commit()
            
        ## Case Connector Instance
        for connector_instances in case_template.to_json()['connector_instances']:
            c_c_i = Case_Connector_Instance(
                case_id=case.id,
                instance_id=connector_instances['instance']['id'],
                identifier=connector_instances['identifier']
            )
            db.session.add(c_c_i)
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

            for t_url_tool in task.urls_tools:
                url_tool = Task_Url_Tool(
                    task_id=t.id,
                    name=t_url_tool.name
                )
                db.session.add(url_tool)
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

            ## Task Custom Tags
            for c_t in CommonModel.get_task_custom_tags(task.id):
                task_custom_tags = Task_Custom_Tags(
                    task_id=t.id,
                    custom_tag_id=c_t.custom_tag_id
                )
                db.session.add(task_custom_tags)
                db.session.commit()

            ## Task subtasks
            for sub in task.subtasks:
                subtask = Subtask(
                    task_id=t.id,
                    description=sub.description
                )
                db.session.add(subtask)
                db.session.commit()
        
        common_core.save_history(case.uuid, user, f"Case created from template: {case_template.id} - {case_template.title}")
        return case




    def modif_note_core(self, cid, notes):
        case = CommonModel.get_case_template(cid)
        if case:
            case.notes = notes
            db.session.commit()
            return True
        return False


    def regroup_task_info(self,template, current_user):
        loc_template = template.to_json()
        loc_template["current_user_permission"] = CommonModel.get_role(current_user).to_json()
        loc_template["subtasks"] = [subtask.to_json() for subtask in template.subtasks]
        return loc_template
    

TemplateModel = TemplateCase()