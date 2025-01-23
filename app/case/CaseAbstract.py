from abc import ABC, abstractmethod

from . import common_core as CommonModel
from ..db_class.db import *
from ..custom_tags import custom_tags_core as CustomModel

class CaseAbstract(ABC):
    @abstractmethod
    def get_case(self, case_id):
        pass

    @abstractmethod
    def create_case(self, form_dict):
        pass

    @abstractmethod
    def delete_case(self, cid, **kwargs):
        pass

    @abstractmethod
    def get_case_tags(self, case_id) -> list:
        pass

    @abstractmethod
    def get_case_clusters_uuid(self, case_id) -> list:
        pass

    @abstractmethod
    def get_case_custom_tags_name(self, case_id) -> list:
        pass

    @abstractmethod
    def add_tag_to_case(self, tag, case_id) -> None:
        pass

    @abstractmethod
    def delete_tag_from_case(self, tag, case_id) -> None:
        pass

    @abstractmethod
    def add_cluster_to_case(self, cluster, case_id) -> None:
        pass

    @abstractmethod
    def delete_cluster_from_case(self, cluster, case_id) -> None:
        pass

    @abstractmethod
    def add_custom_tag_to_case(self, custom_tag, case_id) -> None:
        pass

    @abstractmethod
    def delete_custom_tag_from_case(self, custom_tag, case_id) -> None:
        pass


    def update_tags(self, case_id, tags_list):
        case_tag_db = self.get_case_tags(case_id)
        for tag_name in tags_list:
            if tag_name not in case_tag_db:
                tag = CommonModel.get_tag(tag_name)
                self.add_tag_to_case(tag, case_id)
                case_tag_db.append(tag_name)
        for tag_name in case_tag_db:
            if tag_name not in tags_list:
                tag = CommonModel.get_tag(tag_name)
                self.delete_tag_from_case(tag, case_id)

    def update_clusters(self, case_id, clusters_list):
        case_cluster_db = self.get_case_clusters_uuid(case_id)
        for cluster_uuid in clusters_list:
            if not cluster_uuid in case_cluster_db:
                cluster = CommonModel.get_cluster_by_uuid(cluster_uuid)
                self.add_cluster_to_case(cluster, case_id)
                case_cluster_db.append(cluster_uuid)
        for cluster_uuid in case_cluster_db:
            if not cluster_uuid in clusters_list:
                cluster = CommonModel.get_cluster_by_uuid(cluster_uuid)
                self.delete_cluster_from_case(cluster, case_id)

    def update_custom_tags(self, case_id, custom_tags_list):
        case_custom_tags_db = self.get_case_custom_tags_name(case_id)
        for custom_tag_name in custom_tags_list:
            if not custom_tag_name in case_custom_tags_db:
                custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
                self.add_custom_tag_to_case(custom_tag, case_id)
                case_custom_tags_db.append(custom_tag_name)
        for custom_tag_name in case_custom_tags_db:
            if not custom_tag_name in custom_tags_list:
                custom_tag = CustomModel.get_custom_tag_by_name(custom_tag_name)
                self.delete_custom_tag_from_case(custom_tag, case_id)

    

    @abstractmethod
    def update_case_time_modification(case, current_user=None):
        pass

    @abstractmethod
    def edit(self, form_dict, cid):
        pass

    def _edit(self, form_dict, case_id):

        # Update tags
        self.update_tags(
            case_id,
            form_dict["tags"]
        )

        # Update clusters
        self.update_clusters(
            case_id,
            form_dict["clusters"]
        )

        # Update custom tags
        self.update_custom_tags(
            case_id,
            form_dict["custom_tags"]
        )


    def _sort_cases(self, cases, taxonomies=[], galaxies=[], tags=[], clusters=[], or_and_taxo="true", or_and_galaxies="true"):
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

        return cases