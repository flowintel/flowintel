from ..case import common_core as CommonModel

def prepare_tags(request):
    tag_list = request.form.getlist("tags_select")
    cluster_list = request.form.getlist("clusters_select")
    custom_tags_list = request.form.getlist("custom_select")
    if isinstance(CommonModel.check_tag(tag_list), bool):
        if isinstance(CommonModel.check_cluster(cluster_list), bool):

            return {
                "tags": tag_list,
                "clusters": cluster_list,
                "custom_tags": custom_tags_list
            }
        return "cluster error"
    return "tag error"
