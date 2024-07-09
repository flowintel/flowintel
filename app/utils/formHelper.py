from ..case import common_core as CommonModel

def prepare_tags_connectors(request):
    tag_list = request.form.getlist("tags_select")
    cluster_list = request.form.getlist("clusters_select")
    connector_list = request.form.getlist("connectors_select")
    custom_tags_list = request.form.getlist("custom_select")
    if isinstance(CommonModel.check_tag(tag_list), bool):
        if isinstance(CommonModel.check_cluster(cluster_list), bool):
            identifier_dict = dict()
            for connector in connector_list:
                identifier_dict[connector] = request.form.get(f"identifier_{connector}")

            return {
                "tags": tag_list,
                "clusters": cluster_list,
                "connectors": connector_list,
                "identifier": identifier_dict,
                "custom_tags": custom_tags_list
            }
        return "cluster error"
    return "tag error"
