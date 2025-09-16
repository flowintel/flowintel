import os
from typing import List
import uuid
import datetime
import requests

from flask import send_file

from sqlalchemy import desc, and_
from dateutil import relativedelta

from .. import db
from ..db_class.db import *
from .CommonAbstract import CommonAbstract
from .FilteringAbstract import FilteringAbstract
from . import common_core as CommonModel
from . TaskCore import TaskModel
from ..utils.utils import MODULES, MODULES_CONFIG
from ..custom_tags import custom_tags_core as CustomModel
from ..notification import notification_core as NotifModel

from ..templating.TemplateCase import TemplateModel as CaseTemplateModel


class CaseCore(CommonAbstract, FilteringAbstract):
    def get_class(self) -> Case:
        return Case
    
    def get_tags(self) -> Case_Tags:
        return Case_Tags

    def get_tag_class_id(self) -> int:
        return Case_Tags.case_id

    def get_galaxies(self) -> Case_Galaxy_Tags:
        return Case_Galaxy_Tags

    def get_galaxies_class_id(self) -> int:
        return Case_Galaxy_Tags.case_id

    def get_custom_tags(self) -> Case_Custom_Tags:
        return Case_Custom_Tags

    def get_custom_tags_class_id(self) -> int:
        return Case_Custom_Tags.case_id


    def create_case(self, form_dict, user):
        if "template_select" in form_dict and not 0 in form_dict["template_select"]:
            pass
            for template in form_dict["template_select"]:
                if Case_Template.query.get(template):
                    case = CaseTemplateModel.create_case_from_template(template, form_dict["title_template"], user)
        else:
            deadline = CommonModel.deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])
            case = Case(
                title=form_dict["title"].strip(),
                description=form_dict["description"],
                uuid=str(uuid.uuid4()),
                creation_date=datetime.datetime.now(tz=datetime.timezone.utc),
                last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
                deadline=deadline,
                status_id=1,
                owner_org_id=user.org_id,
                time_required=form_dict["time_required"],
                is_private=form_dict["is_private"],
                ticket_id=form_dict["ticket_id"]
            )
            db.session.add(case)
            db.session.commit()

            for tags in form_dict["tags"]:
                tag = CommonModel.get_tag(tags)
                
                self.add_tag(tag, case.id)
            
            for clusters in form_dict["clusters"]:
                cluster = CommonModel.get_cluster_by_name(clusters)
                
                self.add_cluster(cluster, case.id)

            for custom_tag_name in form_dict["custom_tags"]:
                custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
                if custom_tag:
                    self.add_custom_tag(custom_tag, case.id)

            if "tasks_templates" in form_dict and not 0 in form_dict["tasks_templates"]:
                for tid in form_dict["tasks_templates"]:
                    CommonModel.create_task_from_template(tid, case.id)

            # Add the current user's org to the case
            case_org = Case_Org(
                case_id=case.id, 
                org_id=user.org_id
            )
            db.session.add(case_org)
            db.session.commit()

        CommonModel.save_history(case.uuid, user, "Case Created")

        return case

    def delete_case(self, case_id, current_user):
        """Delete a case by is id"""
        case = CommonModel.get_case(case_id)
        if case:
            # Delete all tasks in the case
            for task in case.tasks:
                TaskModel.delete_task(task.id, current_user, case_deleted=True)

            history_path = os.path.join(CommonModel.HISTORY_DIR, str(case.uuid))
            if os.path.isfile(history_path):
                try:
                    os.remove(history_path)
                except:
                    return False

            NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' was deleted", case_id, html_icon="fa-solid fa-trash", current_user=current_user)

            Case_Tags.query.filter_by(case_id=case.id).delete()
            Case_Galaxy_Tags.query.filter_by(case_id=case.id).delete()
            Case_Org.query.filter_by(case_id=case.id).delete()
            Case_Connector_Instance.query.filter_by(case_id=case.id).delete()
            Case_Custom_Tags.query.filter_by(case_id=case.id).delete()
            Case_Link_Case.query.filter_by(case_id_1=case.id).delete()
            Case_Link_Case.query.filter_by(case_id_2=case.id).delete()

            for obj in self.get_misp_object_by_case(case_id):
                self.delete_misp_object(obj.id)
            Case_Misp_Object.query.filter_by(case_id=case.id).delete()
            Case_Misp_Object_Connector_Instance.query.filter_by(case_id=case.id).delete()
            
            db.session.delete(case)
            db.session.commit()
            return True
        return False
    
    def delete_misp_object(self, oid):
        misp_object = self.get_misp_object(oid)
        if misp_object:
            for attr in misp_object.attributes:
                Misp_Attribute_Instance_Uuid.query.filter_by(misp_attribute_id=attr.id).delete()
                Misp_Attribute.query.filter_by(id=attr.id).delete()
            Misp_Object_Instance_Uuid.query.filter_by(misp_object_id=misp_object.id).delete()

    def get_assigned_tags(self, class_id) -> List:
        """Return a list of tags present in a case"""
        return [tag.name for tag in Tags.query.join(Case_Tags, Case_Tags.tag_id==Tags.id).filter_by(case_id=class_id).all()]

    def get_assigned_clusters_uuid(self, class_id) -> list:
        """Return a list of clusters uuid present in a case"""
        return [cluster.uuid for cluster in \
                Cluster.query.join(Case_Galaxy_Tags, Case_Galaxy_Tags.cluster_id==Cluster.id)\
                    .filter_by(case_id=class_id).all()]

    def get_assigned_custom_tags_name(self, class_id) -> list:
        return [c_t.name for c_t in \
            Custom_Tags.query.join(Case_Custom_Tags, Case_Custom_Tags.custom_tag_id==Custom_Tags.id)\
                .where(Case_Custom_Tags.case_id==class_id).all()]

    def add_tag(self, tag, class_id) -> None:
        case_tag = Case_Tags(
            tag_id=tag.id,
            case_id=class_id
        )
        db.session.add(case_tag)
        db.session.commit()

    def delete_tag(self, tag, class_id) -> None:
        case_tag = CommonModel.get_case_tags_both(class_id, tag.id)
        Case_Tags.query.filter_by(id=case_tag.id).delete()
        db.session.commit()

    def add_cluster(self, cluster, class_id) -> None:
        case_galaxy_tag = Case_Galaxy_Tags(
            cluster_id=cluster.id,
            case_id=class_id
        )
        db.session.add(case_galaxy_tag)
        db.session.commit()

    def delete_cluster(self, cluster, class_id) -> None:
        case_cluster = CommonModel.get_case_clusters_both(class_id, cluster.id)
        Case_Galaxy_Tags.query.filter_by(id=case_cluster.id).delete()
        db.session.commit()

    def add_custom_tag(self, custom_tag, class_id) -> None:
        c_t = Case_Custom_Tags(
            case_id=class_id,
            custom_tag_id=custom_tag.id
        )
        db.session.add(c_t)
        db.session.commit()

    def delete_custom_tag(self, custom_tag, class_id) -> None:
        case_custom_tag = CommonModel.get_case_custom_tags_both(class_id, custom_tag_id=custom_tag.id)
        Case_Custom_Tags.query.filter_by(id=case_custom_tag.id).delete()
        db.session.commit()        

    def edit(self, form_dict, cid, current_user):
        """Edit a case to the DB"""
        case = CommonModel.get_case(cid)
        deadline = CommonModel.deadline_check(form_dict["deadline_date"], form_dict["deadline_time"])

        case.title = form_dict["title"]
        case.description=form_dict["description"]
        case.deadline=deadline
        case.time_required=form_dict["time_required"]
        case.is_private = form_dict["is_private"]
        case.ticket_id = form_dict["ticket_id"]
        
        CommonModel.update_last_modif(case.id)
        db.session.commit()

        CommonModel.save_history(case.uuid, current_user, f"Case edited")

    def edit_tags(self, form_dict, cid, current_user):
        case = CommonModel.get_case(cid)
        self._edit(form_dict, cid)

        CommonModel.update_last_modif(case.id)
        db.session.commit()

        CommonModel.save_history(case.uuid, current_user, f"Case edited")

    def build_case_query(self, completed, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None, filter=None):
        """Build a case query depending on parameters"""
        query, conditions = self._build_sort_query(completed, tags, taxonomies, galaxies, clusters, custom_tags)

        if filter:
            query = query.order_by(desc(filter))
        
        return query.filter(and_(*conditions)).all()
    
    def paginate_cases(self, case_list: list, page: int):
        page_size = 25
        start = (page - 1) * page_size
        end = start + page_size
        paginated_cases = case_list[start:end]
        nb_pages = (len(case_list) + page_size - 1) // page_size

        return paginated_cases, nb_pages

    def sort_cases(self, page, completed, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true", filter=None, user: User = None):
        if tags or taxonomies or galaxies or clusters or custom_tags:
            cases = self.build_case_query(completed, tags, taxonomies, galaxies, clusters, custom_tags, filter)
            cases = self._sort(cases, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies)
        else:
            cases = Case.query.filter_by(completed=completed).order_by(desc(filter)).all()

        list_case_user_in = list()
        for case in cases:
            if case.is_private:
                if user.is_admin() or CommonModel.get_present_in_case(case.id, user):
                    list_case_user_in.append(case)
            else:
                list_case_user_in.append(case)

        if filter:
            loc = list()
            for case in list_case_user_in:
                if getattr(case, filter):
                    loc.append(case)
            loc, nb_pages = self.paginate_cases(loc, page)
            return loc, nb_pages
        
        list_case_user_in, nb_pages = self.paginate_cases(list_case_user_in, page)
        return list_case_user_in, nb_pages



    def complete_case(self, cid, current_user):
        """Complete case by is id"""
        case = CommonModel.get_case(cid)
        if case is not None:
            case.completed = not case.completed
            if case.completed:
                case.finish_date = datetime.datetime.now(tz=datetime.timezone.utc)
                case.status_id = Status.query.filter_by(name="Finished").first().id
                for task in case.tasks:
                    TaskModel.complete_task(task.id, current_user)
                NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' is now completed", cid, html_icon="fa-solid fa-square-check", current_user=current_user)
            else:
                case.finish_date = None
                case.status_id = Status.query.filter_by(name="Created").first().id
                NotifModel.create_notification_all_orgs(f"Case: '{case.id}-{case.title}' is now revived", cid, html_icon="fa-solid fa-heart-circle-plus", current_user=current_user)

            CommonModel.update_last_modif(cid)
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, "Case completed")
            return True
        return False

    def add_orgs_case(self, form_dict, cid, current_user):
        """Add orgs to case in th DB"""
        case = CommonModel.get_case(cid)
        for org_id in form_dict["org_id"]:
            org = CommonModel.get_org(org_id)
            if org:
                case_org = Case_Org(
                    case_id=cid, 
                    org_id=org_id
                )
                db.session.add(case_org)

                if case.recurring_type:
                    for user in org.users:
                        r_n = Recurring_Notification(case_id=case.id, user_id=user.id)
                        db.session.add(r_n)
                        db.session.commit()

                NotifModel.create_notification_org(f"{CommonModel.get_org(org_id).name} add to case: '{case.id}-{case.title}'", cid, org_id, html_icon="fa-solid fa-sitemap", current_user=current_user)
                CommonModel.save_history(case.uuid, current_user, f"Org {org_id} added")
            else:
                return False

        CommonModel.update_last_modif(cid)
        db.session.commit()
        return True


    def change_owner_core(self, org_id, cid, current_user):
        case = CommonModel.get_case(cid)
        if CommonModel.get_org(org_id):
            case.owner_org_id = org_id
            db.session.commit()
            NotifModel.create_notification_org(f"{CommonModel.get_org(org_id).name} is now owner of case: '{case.id}-{case.title}'", cid, org_id, html_icon="fa-solid fa-hand-holding-hand", current_user=current_user)
        else: 
            return False

        CommonModel.update_last_modif(cid)
        db.session.commit()
        CommonModel.save_history(case.uuid, current_user, f"Org {org_id} is now owner of this case")
        return True


    def remove_org_case(self, case_id, org_id, current_user):
        """Remove an org from a case"""
        case_org = Case_Org.query.filter_by(case_id=case_id, org_id=org_id).first()
        if case_org:
            db.session.delete(case_org)

            case = CommonModel.get_case(case_id)

            org = CommonModel.get_org(org_id)
            for user in org.users:
                for task in case.tasks:
                    task
                    t_u = Task_User.query.filter_by(user_id=user.id, task_id=task.id).first()
                    if t_u:
                        db.session.delete(t_u)

                Recurring_Notification.query.filter_by(user_id=user.id, case_id=case.id).delete()

            NotifModel.create_notification_org(f"{CommonModel.get_org(org_id).name} removed from case: '{case.id}-{case.title}'", case_id, org_id, html_icon="fa-solid fa-door-open", current_user=current_user)

            CommonModel.update_last_modif(case_id)
            db.session.commit()
            case = CommonModel.get_case(case_id)
            CommonModel.save_history(case.uuid, current_user, f"Org {org_id} removed")
            return True
        return False
    

    def change_status_core(self, status, case, current_user):
        """Change the status of a case"""
        case.status_id = status
        CommonModel.update_last_modif(case.id)
        db.session.commit()
        CommonModel.save_history(case.uuid, current_user, "Case Status changed")
        return True


    def regroup_case_info(self, cases, user, nb_pages=None):
        """Regroup all information if a case"""
        loc = dict()
        loc["cases"] = list()
        
        for case in cases:
            case_loc = case.to_json()
            case_loc["present_in_case"] = CommonModel.get_present_in_case(case.id, user)
            case_loc["current_user_permission"] = CommonModel.get_role(user).to_json()
            case_loc["open_tasks"], case_loc["closed_tasks"] = self.open_closed(case)
            loc["cases"].append(case_loc)


        if nb_pages:
            loc["nb_pages"] = nb_pages
        else:
            try:
                loc["nb_pages"] = cases.pages
            except:
                pass

        return loc

    def open_closed(self, case):
        cp_open = 0
        cp_closed = 0
        for task in case.tasks:
            if task.completed:
                cp_closed += 1
            else:
                cp_open += 1
        return cp_open, cp_closed
    

    def fork_case_core(self, cid, case_title_fork, user):
        """Fork a case into an other with nearly all informations"""
        case_title_stored = CommonModel.get_case_by_title(case_title_fork, user)
        if case_title_stored:
            return {"message": "Error, title already exist"}
        case = CommonModel.get_case(cid)

        case_json = case.to_json()
        case_json["title"] = case_title_fork

        if case.deadline:
            case_json["deadline_date"] = datetime.datetime.strptime(case_json["deadline"].split(" ")[0], "%Y-%m-%d").date()
            case_json["deadline_time"] = datetime.datetime.strptime(case_json["deadline"].split(" ")[1], "%H:%M").time()
        else:
            case_json["deadline_date"] = None
            case_json["deadline_time"] = None

        loc_tags = list()
        for tag in case_json["tags"]:
            loc_tags.append(tag["name"])
        case_json["tags"] = loc_tags

        loc_clusters = list()
        for cluster in case_json["clusters"]:
            loc_clusters.append(cluster["name"])
        case_json["clusters"] = loc_clusters

        loc_connectors = list()
        loc_connectors_keep = list()
        for connector in case_json["connectors"]:
            loc_connectors_keep.append(connector)
            loc_connectors.append(connector["name"])
        case_json["connectors"] = loc_connectors

        loc_identifiers_dict = dict()
        for connector in loc_connectors_keep:
            loc_identifier = CommonModel.get_case_connector_id(connector["id"], cid)
            loc_identifiers_dict[connector["name"]] = None
            if loc_identifier:
                loc_identifiers_dict[connector["name"]] = loc_identifier.identifier
        case_json["identifier"] = loc_identifiers_dict

        new_case = self.create_case(case_json, user)

        for task in case.tasks:
            task_json = task.to_json()
            if task.deadline:
                task_json["deadline_date"] = datetime.datetime.strptime(task_json["deadline"].split(" ")[0], "%Y-%m-%d").date()
                task_json["deadline_time"] = datetime.datetime.strptime(task_json["deadline"].split(" ")[1], "%H:%M").time()
            else:
                task_json["deadline_date"] = None
                task_json["deadline_time"] = None


            loc_tags = list()
            for tag in task_json["tags"]:
                loc_tags.append(tag["name"])
            task_json["tags"] = loc_tags

            loc_clusters = list()
            for cluster in task_json["clusters"]:
                loc_clusters.append(cluster["name"])
            task_json["clusters"] = loc_clusters
            

            loc_connectors = list()
            loc_connectors_keep = list()
            for connector in task_json["connectors"]:
                loc_connectors_keep.append(connector)
                loc_connectors.append(connector["name"])
            task_json["connectors"] = loc_connectors

            loc_identifiers_dict = dict()
            for connector in loc_connectors_keep:
                loc_identifier = CommonModel.get_task_connector_id(connector["id"], task.id)
                loc_identifiers_dict[connector["name"]] = None
                if loc_identifier:
                    loc_identifiers_dict[connector["name"]] = loc_identifier.identifier
            task_json["identifier"] = loc_identifiers_dict

            TaskModel.create_task(task_json, new_case.id, user)

        CommonModel.save_history(case.uuid, user, f"Case forked, {new_case.id} - {new_case.title}")
        return new_case
    
    def create_template_from_case(self, cid, case_title_template, current_user):
        """Create a case template from a case"""
        if Case_Template.query.filter_by(title=case_title_template).first():
            return {"message": "Error, title already exist"}
        
        case = CommonModel.get_case(cid)
        new_template = Case_Template(
            uuid=str(uuid.uuid4()),
            title=case_title_template,
            description=case.description,
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc)
        )
        db.session.add(new_template)
        db.session.commit()

        ## Tags
        for c_t in Case_Tags.query.filter_by(case_id=case.id).all():
            case_tag = Case_Template_Tags(
                case_id=new_template.id,
                tag_id=c_t.tag_id
            )
            db.session.add(case_tag)
            db.session.commit()

        ## Clusters
        for c_t in Case_Galaxy_Tags.query.filter_by(case_id=case.id).all():
            case_cluster = Case_Template_Galaxy_Tags(
                template_id=new_template.id,
                cluster_id=c_t.cluster_id
            )
            db.session.add(case_cluster)
            db.session.commit()

        ## Custom Tags
        for c_t in CommonModel.get_case_custom_tags(case.id):
            case_template_custom_tags = Case_Template_Custom_Tags(
                case_template_id=new_template.id,
                custom_tag_id=c_t.custom_tag_id
            )
            db.session.add(case_template_custom_tags)
            db.session.commit()

        ## Tasks of the case will become task template
        for task in case.tasks:
            task_exist = Task_Template.query.filter_by(title=task.title).first()
            if not task_exist:
                task_template = Task_Template(
                    uuid=str(uuid.uuid4()),
                    title=task.title,
                    description=task.description,
                    nb_notes=0,
                    last_modif=datetime.datetime.now(tz=datetime.timezone.utc)
                )
                db.session.add(task_template)
                db.session.commit()

                for t_url_tool in task.urls_tools:
                    url_tool = Task_Template_Url_Tool(
                        task_id=task_template.id,
                        name=t_url_tool.name
                    )
                    db.session.add(url_tool)
                    db.session.commit()

                ## Tags
                for t_t in Task_Tags.query.filter_by(task_id=task.id).all():
                    task_tag = Task_Template_Tags(
                        task_id=task_template.id,
                        tag_id=t_t.tag_id
                    )
                    db.session.add(task_tag)
                    db.session.commit()

                ## Clusters
                for t_t in Task_Galaxy_Tags.query.filter_by(task_id=task.id).all():
                    task_cluster = Task_Template_Galaxy_Tags(
                        template_id=task_template.id,
                        cluster_id=t_t.cluster_id
                    )
                    db.session.add(task_cluster)
                    db.session.commit()

                ## Task Custom tags
                for c_t in CommonModel.get_task_custom_tags(task.id):
                    task_template_custom_tags = Task_Template_Custom_Tags(
                        task_template_id=task_template.id,
                        custom_tag_id=c_t.custom_tag_id
                    )
                    db.session.add(task_template_custom_tags)
                    db.session.commit()

                ## Task subtasks
                for sub in task.subtasks:
                    subtask = Subtask_Template(
                        template_id=task_template.id,
                        description=sub.description
                    )
                    db.session.add(subtask)
                    db.session.commit()

                case_task_template = Case_Task_Template(
                        case_id=new_template.id,
                        task_id=task_template.id,
                        case_order_id=task.case_order_id
                    )
                db.session.add(case_task_template)
                db.session.commit()
            else:
                case_task_template = Case_Task_Template(
                        case_id=new_template.id,
                        task_id=task_exist.id,
                        case_order_id=task.case_order_id
                    )
                db.session.add(case_task_template)
                db.session.commit()

        CommonModel.save_history(case.uuid, current_user, f"Template created, {new_template.id} - {new_template.title}")

        return new_template
    
    def prepare_recurring_form(self, cid, orgs_in_case):
        # List orgs and users in and verify if all users of an org are currently notify
        orgs_to_return = list()
        for org in orgs_in_case:
            loc = org.to_json()
            loc["users"] = list()
            cp_checked_user = 0
            cp_users = 0
            for user in org.users:
                cp_users += 1
                loc_user = user.to_json()
                if CommonModel.get_recu_notif_user(cid, user.id):
                    loc_user["checked"] = True
                    cp_checked_user += 1
                else:
                    loc_user["checked"] = False
                loc["users"].append(loc_user)
            # if all users in an org are notify, then check the org checkbox
            if cp_checked_user == cp_users:
                loc["checked"] = True
            else:
                loc["checked"] = False
            orgs_to_return.append(loc)
        return  orgs_to_return


    def change_recurring(self, form_dict, cid, current_user):
        """Change the type of recurring and the date for a case"""
        case = CommonModel.get_case(cid)
        recurring_status = Status.query.filter_by(name="Recurring").first()
        created_status = Status.query.filter_by(name="Created").first()

        if "once" in form_dict and form_dict["once"]:
            case.recurring_type = "once"
            case.recurring_date = form_dict["once"]
            case.status_id = recurring_status.id
        elif "daily" in form_dict and form_dict["daily"]:
            case.recurring_type = "daily"
            case.recurring_date = datetime.datetime.today() + datetime.timedelta(days=1)
            case.status_id = recurring_status.id
        elif "weekly" in form_dict and form_dict["weekly"]:
            case.recurring_type = "weekly"
            if form_dict["weekly"]<datetime.datetime.today().date():
                case.recurring_date = datetime.datetime.today() + datetime.timedelta(
                    days=(form_dict["weekly"].weekday() - datetime.datetime.today().weekday() + 7)
                    )
            else:
                case.recurring_date = form_dict["weekly"]
            case.status_id = recurring_status.id
        elif "monthly" in form_dict and form_dict["monthly"]:
            case.recurring_type = "monthly"
            if form_dict["monthly"]<datetime.datetime.today().date():
                case.recurring_date = form_dict["monthly"] + relativedelta.relativedelta(months=1)
            else:
                case.recurring_date = form_dict["monthly"]
            case.status_id = recurring_status.id
        elif "remove" in form_dict and form_dict["remove"]:
            case.recurring_type = None
            case.recurring_date = None
            case.status_id = created_status.id

            for notif in Recurring_Notification.query.filter_by(case_id=cid).all():
                db.session.delete(notif)
                db.session.commit()
        else:
            return False

        db.session.commit()
        CommonModel.update_last_modif(cid)
        CommonModel.save_history(case.uuid, current_user, "Recurring changed")
        return True

    def notify_user(self, task, user_id):
        """Notify an user on task"""
        case = CommonModel.get_case(task.case_id)
        message = f"Notify for task '{task.id}-{task.title}' of case '{case.id}-{case.title}'"
        NotifModel.create_notification_user(message, task.case_id, user_id=user_id, html_icon="fa-solid fa-bell")
        return True


    def notify_user_recurring(self, form_dict, case_id, orgs):
        """Notify users for a recurring case"""
        for org in orgs:
            if f"check_{org.id}" in form_dict:
                for user in org.users:
                    if not Recurring_Notification.query.filter_by(case_id=case_id, user_id=user.id).first():
                        rec_notif = Recurring_Notification(case_id=case_id, user_id=user.id)
                        db.session.add(rec_notif)
                        db.session.commit()
            else:
                for user in org.users:
                    if f"check_{org.id}_user_{user.id}" in form_dict:
                        if not Recurring_Notification.query.filter_by(case_id=case_id, user_id=user.id).first():
                            rec_notif = Recurring_Notification(case_id=case_id, user_id=user.id)
                            db.session.add(rec_notif)
                            db.session.commit()
                    else:
                        notif = Recurring_Notification.query.filter_by(case_id=case_id, user_id=user.id).first()
                        if notif:
                            db.session.delete(notif)
                            db.session.commit()


    def get_all_notes(self, case):
        """Get all tasks' notes"""
        loc_notes = []
        for task in case.tasks:
            loc = ""
            task_notes = [note.to_json() for note in task.notes]
            if task_notes:
                loc += f"# {task.title}\n\n"
                loc_len = len(loc)
                for note in task_notes:
                    if note["note"]:
                        loc += f"---\n\n{note['note']}\n\n"
                    else:
                        continue
                if not len(loc) == loc_len:
                    loc_notes.append(loc)
        return loc_notes


    def modify_note_core(self, cid, current_user, notes):
        """Modify notes of a case"""
        case = CommonModel.get_case(cid)
        if case:
            case.notes = notes
            CommonModel.update_last_modif(cid)
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, f"Case's Notes modified")
            return True
        return False
    
    def append_note_core(self, cid, current_user, notes):
        """Modify notes of a case"""
        case = CommonModel.get_case(cid)
        if case:
            case.notes += notes
            CommonModel.update_last_modif(cid)
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, f"Case's Notes modified")
            return True
        return False

    def download_history(self, case):
        """Download a history"""
        history_path = os.path.join(CommonModel.HISTORY_DIR, str(case.uuid))
        if os.path.isfile(history_path):
            return send_file(history_path, as_attachment=True, download_name=f"{case.title}_history")
        else:
            return {"message": "History file not found", "toast_class": "danger-subtle"}, 404
        
    def add_new_link(self, form_dict, cid, current_user):
        """Add a new link to case in the DB"""
        case = CommonModel.get_case(cid)
        for loop_case_id in form_dict["case_id"]:
            case_link = CommonModel.get_case(loop_case_id)
            if case_link:
                case_link_case = Case_Link_Case(
                    case_id_1=cid, 
                    case_id_2=case_link.id
                )
                db.session.add(case_link_case)
                db.session.commit()

                case_link_case = Case_Link_Case(
                    case_id_1=case_link.id, 
                    case_id_2=cid
                )
                db.session.add(case_link_case)
                db.session.commit()

                CommonModel.save_history(case.uuid, current_user, f"Case linked to case '{case_link.id}- {case_link.title}' added")
                CommonModel.save_history(case_link.uuid, current_user, f"Case linked to case '{case.id}- {case.title}', from the other case")
            else:
                return False

        CommonModel.update_last_modif(cid)
        db.session.commit()
        return True

    def remove_case_link(self, case_id, case_link_id, current_user):
        """Remove an org from a case"""
        case_link_case = Case_Link_Case.query.filter_by(case_id_1=case_id, case_id_2=case_link_id).first()
        if case_link_case:
            case_link_case_2 = Case_Link_Case.query.filter_by(case_id_1=case_link_id, case_id_2=case_id).first()
            db.session.delete(case_link_case)
            db.session.delete(case_link_case_2)

            case = CommonModel.get_case(case_id)
            case_2 = CommonModel.get_case(case_link_id)

            CommonModel.update_last_modif(case_id)
            db.session.commit()
            case = CommonModel.get_case(case_id)
            CommonModel.save_history(case.uuid, current_user, f"Case link '{case_2.id}- {case_2.title}' removed")
            CommonModel.save_history(case_2.uuid, current_user, f"Case link '{case.id}- {case.title}' removed, from the other case")
            return True
        return False

    def change_hedgedoc_url(self, form_dict, cid, current_user):
        case = CommonModel.get_case(cid)
        loc_hedgedoc_url = form_dict["hedgedoc_url"]
        if loc_hedgedoc_url.endswith("#"):
            loc_hedgedoc_url = loc_hedgedoc_url[:-1]
        if loc_hedgedoc_url.endswith("?both"):
            loc_hedgedoc_url = loc_hedgedoc_url[:-5]
        if loc_hedgedoc_url.endswith("?edit"):
            loc_hedgedoc_url = loc_hedgedoc_url[:-5]

        case.hedgedoc_url = loc_hedgedoc_url
        CommonModel.update_last_modif(cid)
        db.session.commit()
        CommonModel.save_history(case.uuid, current_user, f"Hedgedoc url changed")
        return True

    def get_hedgedoc_notes(self, cid):
        case = CommonModel.get_case(cid)
        if case.hedgedoc_url:
            try:
                md = requests.get(f"{case.hedgedoc_url}/download")
                if md.status_code == 200:
                    return {"notes": md.text}, 200
                return {"message": "Notes not found", 'toast_class': "danger-subtle"}, 404
            except:
                return {"message": "Error with the url", 'toast_class': "warning-subtle"}, 400
        return {"notes": ""}, 200


    ##########
    # MODULE #
    ##########

    def get_modules(self):
        """Return all modules"""
        return MODULES_CONFIG

    def get_case_modules(self):
        """Return modules for case only"""
        loc_list = {}
        for module in MODULES_CONFIG:
            if MODULES_CONFIG[module]["config"]["case_task"] == 'case':
                loc_list[module] = MODULES_CONFIG[module]
        return loc_list

    def get_instance_module_core(self, module, type_module, case_id, user_id):
        """Return a list of connectors instances for a module"""
        if "connector" in MODULES_CONFIG[module]["config"]:
            connector = CommonModel.get_connector_by_name(MODULES_CONFIG[module]["config"]["connector"])
            instance_list = list()
            for instance in connector.instances:
                if CommonModel.get_user_instance_both(user_id=user_id, instance_id=instance.id):
                    if instance.type==type_module:
                        loc_instance = instance.to_json()
                        identifier = CommonModel.get_case_connector_id(instance.id, case_id)
                        loc_instance["identifier"] = identifier.identifier
                        instance_list.append(loc_instance)
            return instance_list
        return []


    ##############
    # Connectors #
    ##############

    def add_connector(self, cid, request_json, current_user) -> bool:
        for connector in request_json["connectors"]:
            instance = CommonModel.get_instance_by_name(connector["name"])
            if "identifier" in connector: loc_identfier = connector["identifier"]
            else: loc_identfier = ""
            c = Case_Connector_Instance(
                case_id=cid,
                instance_id=instance.id,
                identifier=loc_identfier
            )
            db.session.add(c)
            db.session.commit()
            case = CommonModel.get_case(cid)
            CommonModel.save_history(case.uuid, current_user, f"New Connector added")
            CommonModel.update_last_modif(cid)
        return True

    def remove_connector(self, case_instance_id):
        try:
            Case_Connector_Instance.query.filter_by(id=case_instance_id).delete()
            db.session.commit()
        except:
            return False
        return True

    def edit_connector(self, case_instance_id, request_json):
        c = Case_Connector_Instance.query.get(case_instance_id)
        if c:
            c.identifier = request_json["identifier"]
            db.session.commit()
            return True
        return False



    def call_module_case(self, module, case_instance_id, case, user):
        """Run a module"""
        org = CommonModel.get_org(case.owner_org_id)

        tasks = list()
        for task in case.tasks:
            loc_task = task.to_json()
            loc_task["status"] = CommonModel.get_status(task.status_id).name
            tasks.append(loc_task)

        case = case.to_json()
        case["org_name"] = org.name
        case["org_uuid"] = org.uuid
        case["tasks"] = tasks
        case["status"] = CommonModel.get_status(case["status_id"]).name

        case_instance = CommonModel.get_case_connectors_by_id(case_instance_id)
        instance = CommonModel.get_instance(case_instance.instance_id)

        user_instance = CommonModel.get_user_instance_both(user.id, instance.id)

        instance = instance.to_json()
        if user_instance:
            instance["api_key"] = user_instance.api_key
        instance["identifier"] = case_instance.identifier

        case["objects"] = self.get_misp_object_instance(case["id"], instance["id"])

        #######
        # RUN #
        #######
        event_id, object_uuid_list = MODULES[module].handler(instance, case, user)

        res = CommonModel.module_error_check(event_id)
        if res:
            return res

        ###########
        # RESULTS #
        ###########
        if not case_instance:
            cc_instance = Case_Connector_Instance(
                case_id=case["id"],
                instance_id=instance["id"],
                identifier=event_id
            )
            db.session.add(cc_instance)
            db.session.commit()
        elif not case_instance.identifier == event_id:
            case_instance.identifier = event_id
            db.session.commit()
        
        if object_uuid_list:
            self.result_misp_object_module(object_uuid_list, instance["id"])
            loc_instance = Case_Misp_Object_Connector_Instance.query.filter_by(case_id=case["id"], instance_id=instance["id"]).first()
            if loc_instance:
                if not loc_instance.identifier == event_id:
                    loc_instance.identifier = event_id
                    db.session.commit()                
        
        CommonModel.save_history(case["uuid"], user, f"Case Module {module} used on instance: {instance['name']}")

    ###############
    # MISP Object #
    ###############

    def create_misp_object(self, cid, request_json, current_user):
        """Create a new misp object"""
        case_misp_object = Case_Misp_Object(
            case_id=cid,
            template_uuid=request_json["object-template"]["uuid"],
            name=request_json["object-template"]["name"],
            creation_date = datetime.datetime.now(tz=datetime.timezone.utc),
            last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
        )
        db.session.add(case_misp_object)
        db.session.commit()

        self.add_attributes_object(cid, case_misp_object.id, request_json)

        case = CommonModel.get_case(cid)
        CommonModel.save_history(case.uuid, current_user, f"New MISP-Object created")
        CommonModel.update_last_modif(cid)
        return case_misp_object

    def get_misp_object_by_case(self, cid):
        return Case_Misp_Object.query.filter_by(case_id=cid).all()

    def get_misp_object(self, oid):
        """Get a misp object by id"""
        return Case_Misp_Object.query.get(oid)

    def get_misp_attribute(self, aid):
        """Get a misp attribute by id"""
        return Misp_Attribute.query.get(aid)
    
    def get_misp_attribute_by_value(self, value: str) -> list:
        """Get a list of misp attribute by value"""
        return Misp_Attribute.query.filter_by(value=value).all()


    def delete_object(self, cid, oid, current_user):
        """Delete a misp object"""
        misp_object = self.get_misp_object(oid)
        if int(cid) == misp_object.case_id:
            db.session.delete(misp_object)
            db.session.commit()

            case = CommonModel.get_case(int(cid))
            CommonModel.save_history(case.uuid, current_user, f"MISP-Object deleted")
            CommonModel.update_last_modif(cid)
            return True
        return False

    def add_attributes_object(self, cid, oid, request_json):
        misp_object = self.get_misp_object(oid)
        if int(cid) == misp_object.case_id:
            for attribute in request_json["attributes"]:
                first_seen = None
                last_seen = None
                ids_flag = False
                disable_correlation = False
                if attribute["first_seen"]:
                    first_seen = datetime.datetime.strptime(attribute["first_seen"], '%Y-%m-%dT%H:%M')
                if attribute["last_seen"]:
                    last_seen = datetime.datetime.strptime(attribute["last_seen"], '%Y-%m-%dT%H:%M')

                if attribute["ids_flag"] and attribute["ids_flag"] == 'true':
                    ids_flag = True

                if attribute["disable_correlation"] and attribute["disable_correlation"] == 'true':
                    disable_correlation = True

                attr = Misp_Attribute(
                    case_misp_object_id=misp_object.id,
                    value=attribute["value"],
                    type=attribute["type"],
                    object_relation=attribute["object_relation"],
                    first_seen=first_seen,
                    last_seen=last_seen,
                    comment=attribute["comment"],
                    ids_flag=ids_flag,
                    disable_correlation=disable_correlation,
                    creation_date = datetime.datetime.now(tz=datetime.timezone.utc),
                    last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
                )
                db.session.add(attr)
                db.session.commit()
            
            misp_object.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
            db.session.commit()
            return True
        return False

    def edit_attr(self, case_id, object_id, attr_id, request_json):
        misp_object = self.get_misp_object(object_id)
        if int(case_id) == misp_object.case_id:
            attribute = self.get_misp_attribute(attr_id)
            if attribute.case_misp_object_id == int(object_id):
                first_seen = None
                last_seen = None
                ids_flag = False
                disable_correlation = False
                if request_json["first_seen"]:
                    first_seen = datetime.datetime.strptime(request_json["first_seen"], '%Y-%m-%dT%H:%M')
                if request_json["last_seen"]:
                    last_seen = datetime.datetime.strptime(request_json["last_seen"], '%Y-%m-%dT%H:%M')

                if request_json["ids_flag"] and (request_json["ids_flag"] == 'true' or request_json["ids_flag"] == True):
                    ids_flag = True

                if request_json["disable_correlation"] and (request_json["disable_correlation"] == 'true' or request_json["disable_correlation"] == True):
                    disable_correlation = True

                attribute.value = request_json["value"]
                attribute.type = request_json["type"]
                attribute.object_relation = request_json["object_relation"]
                attribute.first_seen=first_seen
                attribute.last_seen=last_seen
                attribute.comment=request_json["comment"]
                attribute.ids_flag=ids_flag
                attribute.disable_correlation=disable_correlation
                attribute.last_modif=datetime.datetime.now(tz=datetime.timezone.utc)
                db.session.commit()

                misp_object.last_modif = datetime.datetime.now(tz=datetime.timezone.utc)
                db.session.commit()
                return {"message": "Attribute updated", "toast_class": "success-subtle"}, 200
            return {"message": "Attribute not found in this object", "toast_class": "warning-subtle"}, 404
        return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404


    def delete_attribute(self, case_id, object_id, attr_id):
        misp_object = self.get_misp_object(object_id)
        if int(case_id) == misp_object.case_id:
            attribute = self.get_misp_attribute(attr_id)
            if attribute.case_misp_object_id == int(object_id):
                db.session.delete(attribute)
                db.session.commit()
                return {"message": "Attribute deleted", "toast_class": "success-subtle"}, 200
            return {"message": "Attribute not found in this object", "toast_class": "warning-subtle"}, 404
        return {"message": "Object not found in this case", "toast_class": "warning-subtle"}, 404
    

    def check_correlation_attr(self, case_id: int, attribute: Misp_Attribute) -> list:
        """Get a list of case containing the same attribute value"""
        if not attribute.disable_correlation:
            attributes = Misp_Attribute.query.filter_by(value=attribute.value).all()
            loc = []
            for loc_attr in attributes:
                cid = Case_Misp_Object.query.get(loc_attr.case_misp_object_id).case_id
                if not cid in loc and not cid == case_id:
                    loc.append(cid)
            return loc
        return []
            

    def get_misp_object_connectors(self, cid) -> list:
        """Return all instances of connectors in json for misp object in a case"""
        return Case_Misp_Object_Connector_Instance.query.filter_by(case_id=cid).all()


    def add_misp_object_connector(self, cid, request_json, current_user) -> bool:
        for connector in request_json["connectors"]:
            instance = CommonModel.get_instance_by_name(connector["name"])
            if "identifier" in connector: loc_identfier = connector["identifier"]
            else: loc_identfier = ""
            c = Case_Misp_Object_Connector_Instance(
                case_id=cid,
                instance_id=instance.id,
                identifier=loc_identfier
            )
            db.session.add(c)
            db.session.commit()

            case = CommonModel.get_case(cid)
            CommonModel.save_history(case.uuid, current_user, f"Connector {instance.name} added")
            CommonModel.update_last_modif(cid)
        return True

    def remove_misp_connector(self, case_id, object_instance_id, current_user):
        try:
            case_object_instance = Case_Misp_Object_Connector_Instance.query.filter_by(id=object_instance_id).first()

            case = CommonModel.get_case(case_id)
            instance = CommonModel.get_instance(case_object_instance.instance_id)

            db.session.delete(case_object_instance)
            db.session.commit()

            CommonModel.save_history(case.uuid, current_user, f"Connector {instance.name} added")
            CommonModel.update_last_modif(case_id)
        except:
            return False
        return True

    def edit_misp_connector(self, object_instance_id, request_json):
        c = Case_Misp_Object_Connector_Instance.query.filter_by(id=object_instance_id).first()
        if c:
            c.identifier = request_json["identifier"]
            db.session.commit()
            return True
        return False

    def get_case_misp_object_by_case_id(self, case_id):
        return Case_Misp_Object.query.filter_by(case_id=case_id).all()

    def get_misp_object_instance_uuid(self, object_id, instance_id):
        return Misp_Object_Instance_Uuid.query.filter_by(misp_object_id=object_id, instance_id=instance_id).first()

    def get_misp_attribute_instance_uuid(self, attr_id, instance_id):
        return Misp_Attribute_Instance_Uuid.query.filter_by(misp_attribute_id=attr_id, instance_id=instance_id).first()


    def get_misp_connector_by_user(self, user_id):
        connector = CommonModel.get_connector_by_name("MISP")
        instances_list = []
        if connector:
            for instance in connector.instances:
                if CommonModel.get_user_instance_both(user_id, instance.id):
                    instances_list.append(instance.to_json())
        return instances_list


    def get_misp_object_instance(self, case_id, instance_id):
        """Get uuid of objects and attributes on a instance of MISP"""
        all_object = self.get_case_misp_object_by_case_id(case_id)
        object_list = list()
        for object in all_object:
            loc_object = object.to_json()
            # Get the uuid for the object for this specific instance
            loc_object["uuid"] = ""
            loc_object_uuid = self.get_misp_object_instance_uuid(object.id, instance_id)
            if loc_object_uuid:
                loc_object["uuid"] = loc_object_uuid.object_instance_uuid

            loc_object["attributes"] = list()
            for attribute in object.attributes:
                loc_attr = attribute.to_json()
                # Get the uuid for the attribute for this specific instance
                loc_attr["uuid"] = ""
                loc_attr_uuid = self.get_misp_attribute_instance_uuid(attribute.id, instance_id)
                if loc_attr_uuid:
                    loc_attr["uuid"] = loc_attr_uuid.attribute_instance_uuid

                loc_object["attributes"].append(loc_attr)
            object_list.append(loc_object)
        return object_list


    def result_misp_object_module(self, object_uuid_list, instance_id):
        """Save uuid of objects and attributes for a instance of MISP"""
        for object_id in object_uuid_list:
            loc_object_uuid = self.get_misp_object_instance_uuid(object_id, instance_id)
            if loc_object_uuid:
                loc_object_uuid.object_instance_uuid = object_uuid_list[object_id]["uuid"]
                db.session.commit()
            else:
                o = Misp_Object_Instance_Uuid(
                    instance_id=instance_id,
                    misp_object_id=object_id,
                    object_instance_uuid=object_uuid_list[object_id]["uuid"]
                )
                db.session.add(o)
                db.session.commit()

            for attr in object_uuid_list[object_id]["attributes"]:
                loc_attr_uuid = self.get_misp_attribute_instance_uuid(attr["attribute_id"], instance_id)
                if loc_attr_uuid:
                    loc_attr_uuid.attribute_instance_uuid = attr["uuid"]
                    db.session.commit()
                else:
                    a = Misp_Attribute_Instance_Uuid(
                        instance_id=instance_id,
                        misp_attribute_id=attr["attribute_id"],
                        attribute_instance_uuid=attr["uuid"]
                    )
                    db.session.add(a)
                    db.session.commit()

    def call_module_misp(self, object_instance_id, case, user):
        """Use to send objects to MISP"""
        object_instance = Case_Misp_Object_Connector_Instance.query.get(object_instance_id)
        instance = CommonModel.get_instance(object_instance.instance_id)
        user_instance = CommonModel.get_user_instance_both(user.id, instance.id)

        instance = instance.to_json()
        if user_instance:
            instance["api_key"] = user_instance.api_key
        instance["identifier"] = object_instance.identifier

        case = case.to_json()
        case["objects"] = self.get_misp_object_instance(case["id"], object_instance.id)

        #######
        # RUN #
        #######
        event_id, object_uuid_list = MODULES["misp_object_event"].handler(instance, case, user)

        res = CommonModel.module_error_check(event_id)
        if res:
            return res

        ###########
        # RESULTS #
        ###########

        if not object_instance.identifier == event_id:
            object_instance.identifier = event_id
            db.session.commit()
        if object_uuid_list:
            self.result_misp_object_module(object_uuid_list, object_instance.id)

        CommonModel.save_history(case["uuid"], user, f"Module 'misp_object_event' called with connector '{instance['name']}'")
        CommonModel.update_last_modif(case["id"])


    #################
    # Note Template #
    #################
    def get_note_template_model(self, template_id: int):
        """Return a note template model"""
        return Note_Template_Model.query.get(template_id)

    def get_case_note_template(self, case_id: int):
        """Return a case note template"""
        return Case_Note_Template_Model.query.filter_by(case_id=case_id).first()
    
    def create_note_template(self, case_id: int, request_json, current_user: User):
        c = self.get_case_note_template(case_id)
        if not c:
            note_template = self.get_note_template_model(request_json["template_id"])
            case = CommonModel.get_case(case_id)
            values = request_json["values"]
            if not values:
                for par in note_template.params.list:
                    values[par] = ""

            c = Case_Note_Template_Model(
                case_id=case_id,
                note_template_id=note_template.id,
                content = note_template.content,
                values={"list": values}
            )
            db.session.add(c)
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, f"Note Template created")
            CommonModel.update_last_modif(case.id)
            return c
        return False
    
    def modif_note_template(self, case_id: int, request_json, current_user: User):
        """Modify a note template of a case"""
        case = CommonModel.get_case(case_id)
        c = self.get_case_note_template(case_id)
        if c:
            c.values = request_json["values"]
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, f"Note Template modified")
            CommonModel.update_last_modif(case.id)
            return True
        return False
    
    def modif_content_note_template(self, case_id: int, request_json, current_user: User):
        """Modify content of note template of a case"""
        case = CommonModel.get_case(case_id)
        c = self.get_case_note_template(case_id)
        if c:
            c.content = request_json["content"]
            db.session.commit()
            CommonModel.save_history(case.uuid, current_user, f"Content Note Template modified")
            CommonModel.update_last_modif(case.id)
            return True
        return False
    
    def remove_note_template(self, case_id):
        """Remove a note template from a case"""
        c = self.get_case_note_template(case_id)
        if c:
            db.session.delete(c)
            db.session.commit()
            return True
        return False

CaseModel = CaseCore()