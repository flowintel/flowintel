import uuid
import datetime
from typing import List
from sqlalchemy import and_, desc

from .. import db
from ..db_class.db import *
from ..case.CommonAbstract import CommonAbstract
from ..case.FilteringAbstract import FilteringAbstract
from . import common_template_core as CommonModel
from ..custom_tags import custom_tags_core as CustomModel

class TaskTemplateCore(CommonAbstract, FilteringAbstract):
    def get_class(self) -> Task_Template:
        return Task_Template
    
    def get_tags(self) -> Task_Template_Tags:
        return Task_Template_Tags

    def get_tag_class_id(self) -> int:
        return Task_Template_Tags.task_id

    def get_galaxies(self) -> Task_Template_Galaxy_Tags:
        return Task_Template_Galaxy_Tags

    def get_galaxies_class_id(self) -> int:
        return Task_Template_Galaxy_Tags.template_id

    def get_custom_tags(self) -> Task_Template_Custom_Tags:
        return Task_Template_Custom_Tags

    def get_custom_tags_class_id(self) -> int:
        return Task_Template_Custom_Tags.task_template_id
    

    def get_assigned_tags(self, class_id) -> List:
        return [tag.name for tag in Tags.query.join(Task_Template_Tags, Task_Template_Tags.tag_id==Tags.id).filter_by(task_id=class_id).all()]

    def get_case_tags_both(self, class_id, tag_id):
        """Return a list of tags present in a case"""
        return Task_Template_Tags.query.filter_by(task_id=class_id, tag_id=tag_id).first()

    def get_assigned_clusters_uuid(self, class_id) -> List:
        """Return a list of clusters uuid present in a case template"""
        return [cluster.uuid for cluster in \
                Cluster.query.join(Task_Template_Galaxy_Tags, Task_Template_Galaxy_Tags.cluster_id==Cluster.id)\
                    .filter_by(template_id=class_id).all()]

    def get_assigned_custom_tags_name(self, class_id) -> List:
        c_ts = Custom_Tags.query\
            .join(Task_Template_Custom_Tags, Task_Template_Custom_Tags.custom_tag_id==Custom_Tags.id)\
            .where(Task_Template_Custom_Tags.task_template_id==class_id).all()
        return [c_t.name for c_t in c_ts]

    def add_tag(self, tag, class_id) -> str:
        task_tag = Task_Template_Tags(
            tag_id=tag.id,
            task_id=class_id
        )
        db.session.add(task_tag)
        db.session.commit()

    def delete_tag(self, tag, class_id) -> None:
        task_tag = CommonModel.get_task_template_tags_both(class_id, tag.id)
        Task_Template_Tags.query.filter_by(id=task_tag.id).delete()
        db.session.commit()

    def add_cluster(self, cluster, class_id) -> str:
        task_tag = Task_Template_Galaxy_Tags(
            cluster_id=cluster.id,
            template_id=class_id
        )
        db.session.add(task_tag)
        db.session.commit()

    def delete_cluster(self, cluster, class_id) -> None:
        task_cluster = CommonModel.get_task_template_clusters_both(class_id, cluster.id)
        Task_Template_Galaxy_Tags.query.filter_by(id=task_cluster.id).delete()
        db.session.commit()

    def add_custom_tag(self, custom_tag, class_id) -> str:
        c_t = Task_Template_Custom_Tags(
            task_template_id=class_id,
            custom_tag_id=custom_tag.id
        )
        db.session.add(c_t)
        db.session.commit()

    def delete_custom_tag(self, custom_tag, class_id) -> None:
        task_custom_tag = CommonModel.get_task_custom_tags_both(class_id, custom_tag_id=custom_tag.id)
        Task_Template_Custom_Tags.query.filter_by(id=task_custom_tag.id).delete()
        db.session.commit()
    
    




    def build_task_query(self, page, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None, title_filter=None):
        query, conditions = self._build_sort_query(None, tags, taxonomies, galaxies, clusters, custom_tags)

        if title_filter=='true':
            query = query.order_by('title')
        else:
            query = query.order_by(desc('last_modif'))
        
        return query.filter(and_(*conditions)).paginate(page=page, per_page=25, max_per_page=50)


    def sort_tasks(self, page, title_filter, taxonomies=[], galaxies=[], tags=[], clusters=[], custom_tags=[], or_and_taxo="true", or_and_galaxies="true"):
        if tags or taxonomies or galaxies or clusters or custom_tags:
            tasks = self.build_task_query(page, tags, taxonomies, galaxies, clusters, custom_tags, title_filter)
            nb_pages = tasks.pages
            tasks = self._sort(tasks, taxonomies, galaxies, tags, clusters, or_and_taxo, or_and_galaxies)
        else:
            query = Task_Template.query
            if title_filter=='true':
                query = query.order_by('title')
            else:
                query = query.order_by(desc('last_modif'))
            tasks = query.paginate(page=page, per_page=25, max_per_page=50)
            nb_pages = tasks.pages
        return tasks, nb_pages


    def add_task_template_core(self, form_dict):
        template = Task_Template(
            title=form_dict["title"],
            description=form_dict["description"],
            uuid=str(uuid.uuid4()),
            nb_notes=0,
            last_modif=datetime.datetime.now(tz=datetime.timezone.utc),
            time_required=form_dict["time_required"]
        )
        db.session.add(template)
        db.session.commit()

        for tag in form_dict["tags"]:
            tag = CommonModel.get_tag(tag)
            
            self.add_tag(tag, template.id)

        for cluster in form_dict["clusters"]:
            cluster = CommonModel.get_cluster_by_name(cluster)
            
            self.add_cluster(cluster, template.id)

        for custom_tag_name in form_dict["custom_tags"]:
            custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
            if custom_tag:
                self.add_custom_tag(custom_tag, template.id)
        
        return template

    def edit_task_template(self, form_dict, tid):
        template = CommonModel.get_task_template(tid)

        template.title=form_dict["title"]
        template.description=form_dict["description"]
        template.time_required = form_dict["time_required"]
        
        self._edit(form_dict, tid)

        CommonModel.update_last_modif_task(template.id)

        db.session.commit()


    def delete_task_template(self, tid):
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

    def create_note(self, tid):
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


    def modif_note_core(self, tid, notes, note_id):
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

    def delete_note(self, tid, note_id):
        """Delete a note by id"""
        note = CommonModel.get_task_note(note_id)
        if note:
            if note.template_id == int(tid):
                Note_Template.query.filter_by(id=note_id).delete()
                db.session.commit()
                CommonModel.update_last_modif_task(tid)
                return True
        return False

    def change_order(self, case, task, request_json):
        case_task_template = Case_Task_Template.query.filter_by(case_id=case.id).all()
        task_template = Case_Task_Template.query.filter_by(case_id=case.id, task_id=task.id).first()

        tasks = sorted(case_task_template, key=lambda t: t.case_order_id)
        target_task = None
        for task_db in tasks:
            if task_db.case_order_id == request_json["new-index"]+1:
                target_task = task_db
                break
        
        if target_task:
            # Find index where to insert
            target_index = tasks.index(target_task)

            # Remove the moving task from the list
            tasks.remove(task_template)

            # Insert the task before the target
            tasks.insert(target_index, task_template)
            
            # Reassign order IDs
            for i, loc_task in enumerate(tasks, start=1):
                loc_task.case_order_id = i

            db.session.commit() 

            return True
        return False

    ############
    # Subtasks #
    ############

    def create_subtask(self, tid, description):
        subtask = Subtask_Template(
            description=description,
            template_id=tid
        )
        db.session.add(subtask)
        db.session.commit()
        return subtask

    def edit_subtask(self, tid, sid, description):
        subtask = CommonModel.get_subtask_template(sid)
        if subtask:
            if subtask.template_id == int(tid):
                subtask.description = description
                db.session.commit()
                return True
        return False

    def delete_subtask(self, tid, sid):
        subtask = CommonModel.get_subtask_template(sid)
        if subtask:
            if subtask.template_id == int(tid):
                db.session.delete(subtask)
                db.session.commit()
                return True
        return False
    
    
    ##############
    # Urls/Tools #
    ##############

    def get_url_tool_template(self, utid):
        return Task_Template_Url_Tool.query.get(utid)

    def delete_url_tool(self, tid, utid):
        url_tool = self.get_url_tool_template(utid)
        if url_tool:
            if url_tool.task_id == int(tid):
                db.session.delete(url_tool)
                db.session.commit()
                return True
        return False

    def create_url_tool(self, tid, url_tool_name):
        url_tool = Task_Template_Url_Tool(
            name=url_tool_name,
            task_id=tid
        )
        db.session.add(url_tool)
        db.session.commit()

        return url_tool

    def edit_url_tool(self, tid, utid, url_tool_name):
        url_tool = self.get_url_tool_template(utid)
        if url_tool:
            if url_tool.task_id == int(tid):
                url_tool.name = url_tool_name
                db.session.commit()

                return True
        return False


TaskModel = TaskTemplateCore()