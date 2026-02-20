import { display_toast } from '../toaster.js'
import edition_select from './edition_select.js'
import { getTextColor, mapIcon } from '/static/js/utils.js'
const { ref } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: {
        current_case: Object,
        type_object: String,
        can_edit: Boolean
    },
    components: {
        edition_select
    },
    setup(props) {
        const selected_tags = ref([])
        const selected_clusters = ref([])
        const selected_custom_tags = ref([])

        async function change_tags() {
            let tags_select = []
            let clusters_select = []
            let custom_select = []
            $.each(selected_clusters.value, function (i, v) {
                clusters_select.push(v.uuid)
            });
            $.each(selected_tags.value, function (i, v) {
                tags_select.push(v.name)
            });
            $.each(selected_custom_tags.value, function (i, v) {
                custom_select.push(v.name)
            });

            let url

            if (props.type_object == 'case')
                url = '/case/edit_tags/'
            else if (props.type_object == 'case_template')
                url = '/templating/case/edit_tags/'
            url += props.current_case.id

            const res_msg = await fetch(
                url, {
                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                method: "POST",
                body: JSON.stringify({
                    "tags_select": tags_select,
                    "clusters_select": clusters_select,
                    "custom_select": custom_select
                })
            }
            )

            if (await res_msg.status == 200) {
                props.current_case.tags = selected_tags.value
                props.current_case.clusters = selected_clusters.value
                props.current_case.custom_tags = selected_custom_tags.value

                var myModalEl = document.getElementById('ModalEditTags');
                var modal = bootstrap.Modal.getInstance(myModalEl)
                modal.hide();
            }
            await display_toast(res_msg)
        }


        return {
            getTextColor,
            mapIcon,
            selected_tags,
            selected_clusters,
            selected_custom_tags,
            change_tags
        }
    },
    template: `
    <div class="case-tags-style">
        <button v-if="can_edit" type="button" class="btn btn-outline-primary btn-sm float-end" data-bs-toggle="modal" data-bs-target="#ModalEditTags">
            <i class="fa-solid fa-pen fa-sm"></i>
        </button>
        <h6 class="section-title mb-0"><i class="fa-solid fa-tags fa-sm me-2"></i>Tags, taxonomies and galaxies</h6>
        <hr class="fading-line-2 mt-2 mb-2">
        <div v-if="current_case.custom_tags" style="display: flex; flex-wrap: wrap; margin-bottom: 5px;">
            <template v-for="tag in current_case.custom_tags">
                <div class="tag" :style="{'background-color': tag.color, 'color': getTextColor(tag.color)}">
                    <i v-if="tag.icon" :class="tag.icon" style="font-size: 0.75rem;"></i>
                    [[tag.name]]
                </div>
            </template>
        </div>

        <div v-if="current_case.tags" style="display: flex; flex-wrap: wrap; margin-bottom: 5px;">
            <template v-for="tag in current_case.tags">
                <div class="tag" :title="tag.description" :style="{'background-color': tag.color, 'color': getTextColor(tag.color)}">
                    <i class="fa-solid fa-tag fa-sm" style="margin-right: 3px; margin-left: 3px;"></i>
                    [[tag.name]]
                </div>
            </template>
        </div>

        <template v-if="current_case.clusters">
            <template v-for="cluster in current_case.clusters">
                <div class="mb-1" :title="'Description: '+cluster.description+' \\nMetadata: '+cluster.meta">
                    <span class="cluster">
                        <span v-html="mapIcon(cluster.icon)"></span>
                        [[cluster.tag]]
                    </span>
                </div>
            </template>
        </template>
    </div>
    

    <!-- Modal -->
    <div class="modal fade" id="ModalEditTags" tabindex="-1" aria-labelledby="ModalEditTags" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="exampleModalLabel">Edit Tags</h1>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <edition_select 
                        :type_object="type_object"
                        @st="(msg) => selected_tags=selected_tags.concat(msg)"
                        @sc="(msg) => selected_clusters=selected_clusters.concat(msg)"
                        @sct="(msg) => selected_custom_tags=selected_custom_tags.concat(msg)"
                        @delete_st="(msg) => selected_tags.splice(msg, 1)"
                        @delete_sc="(msg) => selected_clusters.splice(msg, 1)"
                        @delete_sct="(msg) => selected_custom_tags.splice(msg, 1)"
                    >
                    </edition_select>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" @click="change_tags()">Save changes</button>
                </div>
            </div>
        </div>
    </div>
    `
}