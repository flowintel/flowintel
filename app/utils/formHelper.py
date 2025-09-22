from ..case import common_core as CommonModel

def prepare_tags(request):
    tag_list = request.form.getlist("tags_select")
    cluster_list = request.form.getlist("clusters_select")
    custom_tags_list = request.form.getlist("custom_select")
    instance_id_list = request.form.getlist("connector_instances")
    if isinstance(CommonModel.check_tag(tag_list), bool):
        if isinstance(CommonModel.check_cluster(cluster_list), bool):
            connector_instances = []
            for instance_id in instance_id_list:
                instance_identifier = request.form.get(f"identifier_{instance_id}")

                connector_instances.append({
                    "id": instance_id,
                    "identifier": instance_identifier
                })

            return {
                "tags": tag_list,
                "clusters": cluster_list,
                "custom_tags": custom_tags_list,
                "connector_instances": connector_instances
            }
        return "cluster error"
    return "tag error"
