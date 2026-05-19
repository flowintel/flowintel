import { display_toast, create_message } from '/static/js/toaster.js'
const { ref, onMounted, computed } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        task: Object,
        cases_info: Object
    },
    setup(props) {
        const case_misp_objects = ref([])
        const is_loading = ref(false)
        const can_manage_case_misp_objects = computed(() => {
            const permission = props.cases_info ? props.cases_info.permission : null
            if (!permission) return false
            return Boolean(permission.admin || permission.misp_editor)
        })

        async function fetch_case_misp_objects() {
            const res = await fetch('/case/' + props.task.case_id + '/get_case_misp_object')
            if (res.status === 200) {
                const loc = await res.json()
                case_misp_objects.value = loc['misp-object'] || []
            }
        }

        function is_linked(misp_object_id) {
            return props.task.misp_object_links &&
                props.task.misp_object_links.some(l => l.misp_object_id === misp_object_id)
        }

        async function link_misp_object(obj) {
            const res = await fetch('/case/' + props.task.case_id + '/task/' + props.task.id + '/link_misp_object', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': $('#csrf_token').val(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ misp_object_id: obj.object_id })
            })
            if (res.status === 200) {
                const loc = await res.json()
                if (!props.task.misp_object_links) props.task.misp_object_links = []
                props.task.misp_object_links.push(loc.link)
                create_message('MISP object linked', 'success-subtle', false, 'fas fa-link')
            } else {
                await display_toast(res)
            }
        }

        async function unlink_misp_object(obj) {
            const res = await fetch('/case/' + props.task.case_id + '/task/' + props.task.id + '/unlink_misp_object/' + obj.id)
            if (res.status === 200) {
                const idx = props.task.misp_object_links.findIndex(l => l.misp_object_id === obj.id)
                if (idx > -1) props.task.misp_object_links.splice(idx, 1)
                create_message('MISP object unlinked', 'success-subtle', false, 'fas fa-unlink')
            } else {
                await display_toast(res)
            }
        }

        function show_object(obj) {
            const objectId = obj.object_id || obj.misp_object_id || obj.id
            if (!objectId) return
            window.dispatchEvent(new CustomEvent('navigate-to-misp-object', { detail: { object_id: objectId } }))
        }

        function format_object_label(obj) {
            if (!obj) return ''
            const objectName = obj.misp_object_name || obj.object_name || ''
            return objectName
        }

        function format_attribute_preview(obj) {
            const preview = obj && obj.attributes_preview ? obj.attributes_preview : []
            if (!preview.length) return ''
            return preview.join(' · ')
        }

        function format_case_object_label(obj) {
            if (!obj) return ''
            return format_object_label({
                misp_object_name: obj.object_name,
                misp_object_template_uuid: obj.object_uuid,
            })
        }

        function format_case_object_preview(obj) {
            const attributes = obj && obj.attributes ? obj.attributes : []
            if (!attributes.length) return ''
            return attributes.slice(0, 3).map(attr => attr.object_relation + ':' + attr.value).join(' · ')
        }

        onMounted(() => {
            fetch_case_misp_objects()
        })

        return {
            case_misp_objects,
            is_loading,
            can_manage_case_misp_objects,
            is_linked,
            link_misp_object,
            unlink_misp_object,
            show_object,
            format_object_label,
            format_attribute_preview,
            format_case_object_label,
            format_case_object_preview
        }
    },
    template: `
    <div class="col">
        <div class="task-section">
            <div class="task-section-header">
                <i class="fa-solid fa-shield-halved fa-sm me-1"></i>
                <span class="section-title">MISP Objects linked to this task</span>
            </div>
            <div class="task-section-body">
                <div v-if="!can_manage_case_misp_objects" class="alert alert-warning py-2 px-3 mb-3">
                    <small>
                        <i class="fa-solid fa-triangle-exclamation me-1"></i>
                        You can view and link existing MISP objects here, but creating or editing case objects requires MISP Editor permissions.
                    </small>
                </div>
                <template v-if="task.misp_object_links && task.misp_object_links.length">
                    <div v-for="link in task.misp_object_links" :key="link.misp_object_id" class="d-flex align-items-center mb-1">
                        <i class="fa-solid fa-cube me-2 text-secondary"></i>
                        <span class="me-2 flex-grow-1">
                            <a href="javascript:void(0)" @click="show_object(link)"><strong>[[format_object_label(link)]]</strong></a>
                            <small class="text-muted ms-1">([[link.misp_object_template_uuid]])</small>
                            <small v-if="format_attribute_preview(link)" class="text-muted d-block">[[format_attribute_preview(link)]]</small>
                        </span>
                        <template v-if="task.can_edit && cases_info.present_in_case || cases_info.permission.admin">
                            <button @click="unlink_misp_object({id: link.misp_object_id})" class="btn btn-danger btn-sm ms-auto" title="Unlink this MISP object">
                                <i class="fa-solid fa-link-slash"></i>
                            </button>
                        </template>
                    </div>
                </template>
                <template v-else>
                    <p class="text-muted"><i>No MISP objects linked</i></p>
                </template>
            </div>
        </div>

        <template v-if="task.can_edit && cases_info.present_in_case || cases_info.permission.admin">
            <div class="task-section mt-3">
                <div class="task-section-header d-flex align-items-center">
                    <i class="fa-solid fa-plus fa-sm me-1"></i>
                    <span class="section-title">Link a MISP object from this case</span>
                    <button class="btn btn-sm btn-outline-secondary ms-auto" type="button" data-bs-toggle="collapse" :data-bs-target="'#misp-link-collapse-'+task.id" aria-expanded="false" :aria-controls="'misp-link-collapse-'+task.id">
                        <i class="fa-solid fa-chevron-down"></i>
                    </button>
                </div>
                <div class="task-section-body">
                    <div :id="'misp-link-collapse-'+task.id" class="collapse">
                        <template v-if="case_misp_objects.length">
                            <div v-for="obj in case_misp_objects" :key="obj.object_id" class="d-flex align-items-center mb-1">
                                <i class="fa-solid fa-cube me-2 text-secondary"></i>
                                <span class="me-2 flex-grow-1">
                                    <a href="javascript:void(0)" @click="show_object(obj)"><strong>[[format_case_object_label(obj)]]</strong></a>
                                    <small class="text-muted ms-1">([[obj.object_uuid]])</small>
                                    <small v-if="format_case_object_preview(obj)" class="text-muted d-block">[[format_case_object_preview(obj)]]</small>
                                </span>
                                <template v-if="is_linked(obj.object_id)">
                                    <span class="badge text-bg-success ms-auto"><i class="fa-solid fa-check me-1"></i>Linked</span>
                                </template>
                                <template v-else>
                                    <button @click="link_misp_object(obj)" class="btn btn-primary btn-sm ms-auto" title="Link this MISP object to the task">
                                        <i class="fa-solid fa-link"></i> Link
                                    </button>
                                </template>
                            </div>
                        </template>
                        <template v-else>
                            <p class="text-muted"><i>No MISP objects in this case yet</i></p>
                        </template>
                    </div>
                </div>
            </div>
        </template>
    </div>
    `
}
