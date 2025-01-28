from abc import ABC, abstractmethod
from typing import List

from . import common_core as CommonModel
from ..db_class.db import *
from ..custom_tags import custom_tags_core as CustomModel


class CommonAbstract(ABC):
    @abstractmethod
    def get_assigned_tags(self, class_id) -> List:
        pass

    @abstractmethod
    def get_assigned_clusters_uuid(self, class_id) -> List:
        pass

    @abstractmethod
    def get_assigned_custom_tags_name(self, class_id) -> List:
        pass

    @abstractmethod
    def add_tag(self, tag, class_id) -> None:
        pass

    @abstractmethod
    def delete_tag(self, tag, class_id) -> None:
        pass

    @abstractmethod
    def add_cluster(self, cluster, class_id) -> None:
        pass

    @abstractmethod
    def delete_cluster(self, cluster, class_id) -> None:
        pass

    @abstractmethod
    def add_custom_tag(self, custom_tag, class_id) -> None:
        pass

    @abstractmethod
    def delete_custom_tag(self, custom_tag, class_id) -> None:
        pass


    def update_tags(self, class_id, tags_list):
        case_tag_db = self.get_assigned_tags(class_id)
        for tag_name in tags_list:
            if tag_name not in case_tag_db:
                tag = CommonModel.get_tag(tag_name)
                self.add_tag(tag, class_id)
                case_tag_db.append(tag_name)
        for tag_name in case_tag_db:
            if tag_name not in tags_list:
                tag = CommonModel.get_tag(tag_name)
                self.delete_tag(tag, class_id)

    def update_clusters(self, class_id, clusters_list):
        case_cluster_db = self.get_assigned_clusters_uuid(class_id)
        for cluster_uuid in clusters_list:
            if not cluster_uuid in case_cluster_db:
                cluster = CommonModel.get_cluster_by_uuid(cluster_uuid)
                self.add_cluster(cluster, class_id)
                case_cluster_db.append(cluster_uuid)
        for cluster_uuid in case_cluster_db:
            if not cluster_uuid in clusters_list:
                cluster = CommonModel.get_cluster_by_uuid(cluster_uuid)
                self.delete_cluster(cluster, class_id)

    def update_custom_tags(self, class_id, custom_tags_list):
        case_custom_tags_db = self.get_assigned_custom_tags_name(class_id)
        for custom_tag_name in custom_tags_list:
            if not custom_tag_name in case_custom_tags_db:
                custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
                self.add_custom_tag(custom_tag, class_id)
                case_custom_tags_db.append(custom_tag_name)
        for custom_tag_name in case_custom_tags_db:
            if not custom_tag_name in custom_tags_list:
                custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
                self.delete_custom_tag(custom_tag, class_id)
                

    def _edit(self, form_dict, class_id):

        # Update tags
        self.update_tags(
            class_id,
            form_dict["tags"]
        )

        # Update clusters
        self.update_clusters(
            class_id,
            form_dict["clusters"]
        )

        # Update custom tags
        self.update_custom_tags(
            class_id,
            form_dict["custom_tags"]
        )
