from abc import ABC, abstractmethod
from typing import Union

from ..db_class.db import (
    Case, Case_Custom_Tags, Case_Galaxy_Tags, Case_Tags, Case_Template,
    Case_Template_Custom_Tags, Case_Template_Galaxy_Tags, Case_Template_Tags,
    Cluster, Custom_Tags, Galaxy, Tags, Task, Task_Custom_Tags, Task_Galaxy_Tags,
    Task_Tags, Task_Template, Task_Template_Custom_Tags, Task_Template_Galaxy_Tags,
    Task_Template_Tags, Taxonomy
)


class FilteringAbstract(ABC):
    @abstractmethod
    def get_class(self) -> Union[Case, Task, Case_Template, Task_Template]:
        pass

    @abstractmethod
    def get_tags(self) -> Union[Case_Tags, Task_Tags, Case_Template_Tags, Task_Template_Tags]:
        pass

    @abstractmethod
    def get_tag_class_id(self) -> int:
        pass

    @abstractmethod
    def get_galaxies(self) -> Union[Case_Galaxy_Tags, Task_Galaxy_Tags, Case_Template_Galaxy_Tags, Task_Template_Galaxy_Tags]:
        pass

    @abstractmethod
    def get_galaxies_class_id(self) -> int:
        pass

    @abstractmethod
    def get_custom_tags(self) -> Union[Case_Custom_Tags, Task_Custom_Tags, Case_Template_Custom_Tags, Task_Template_Custom_Tags]:
        pass

    @abstractmethod
    def get_custom_tags_class_id(self) -> int:
        pass
    

    def _build_sort_query(self, completed=None, tags=None, taxonomies=None, galaxies=None, clusters=None, custom_tags=None):
        query = self.get_class().query
        if isinstance(self.get_class(), Case ) or isinstance(self.get_class(), Task):
            conditions = [self.get_class().completed == completed]
        else:
            conditions = []

        if tags or taxonomies:
            query = query.join(self.get_tags(), self.get_tag_class_id() == self.get_class().id)
            query = query.join(Tags, self.get_tags().tag_id == Tags.id)
            if tags:
                conditions.append(Tags.name.in_(list(tags)))

            if taxonomies:
                query = query.join(Taxonomy, Taxonomy.id == Tags.taxonomy_id)
                conditions.append(Taxonomy.name.in_(list(taxonomies)))

        if clusters or galaxies:
            query = query.join(self.get_galaxies(), self.get_galaxies_class_id() == self.get_class().id)
            query = query.join(Cluster, self.get_galaxies().cluster_id == Cluster.id)
            if clusters:
                conditions.append(Cluster.name.in_(list(clusters)))

            if galaxies:
                query = query.join(Galaxy, Galaxy.id == Cluster.galaxy_id)
                conditions.append(Galaxy.name.in_(list(galaxies)))
        
        if custom_tags:
            query = query.join(self.get_custom_tags(), self.get_custom_tags_class_id() == self.get_class().id)
            query = query.join(Custom_Tags, self.get_custom_tags().custom_tag_id == Custom_Tags.id)
            conditions.append(Custom_Tags.name.in_(list(custom_tags)))

        return query, conditions

    def _sort(self, cases, taxonomies=[], galaxies=[], tags=[], clusters=[], or_and_taxo="true", or_and_galaxies="true"):
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