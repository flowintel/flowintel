import { display_toast, create_message } from '/static/js/toaster.js'
const { ref, onMounted, computed, onBeforeUnmount } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        task: Object,
        cases_info: Object
    },
    setup(props) {
        const case_misp_objects = ref([])
        const case_misp_attributes = ref([])
        const is_loading = ref(false)
        const can_manage_case_misp_objects = computed(() => {
            const permission = props.cases_info ? props.cases_info.permission : null
            if (!permission) return false
            return Boolean(permission.admin || permission.misp_editor)
        })
        const can_manage_links = computed(() => {
            return (props.task.can_edit && props.cases_info.present_in_case) || props.cases_info.permission.admin
        })

        async function fetch_case_misp_objects() {
            const res = await fetch('/case/' + props.task.case_id + '/get_case_misp_object')
            if (res.status === 200) {
                const loc = await res.json()
                case_misp_objects.value = loc['misp-object'] || []
            }
        }

        async function fetch_case_misp_attributes() {
            const res = await fetch('/case/' + props.task.case_id + '/get_case_misp_attributes')
            if (res.status === 200) {
                const loc = await res.json()
                case_misp_attributes.value = loc.attributes || []
            }
        }

        function is_linked(misp_object_id) {
            return props.task.misp_object_links &&
                props.task.misp_object_links.some(l => l.misp_object_id === misp_object_id)
        }

        function is_attribute_linked(misp_attribute_id) {
            return props.task.misp_attribute_links &&
                props.task.misp_attribute_links.some(l => l.misp_attribute_id === misp_attribute_id)
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
                try {
                    const modalEl = document.getElementById('misp-link-modal-' + props.task.id)
                    if (modalEl) {
                        const modalInst = window.bootstrap && window.bootstrap.Modal ? (window.bootstrap.Modal.getInstance(modalEl) || new window.bootstrap.Modal(modalEl)) : null
                        if (modalInst) modalInst.hide()
                    }
                } catch (e) {
                    // ignore modal hide errors
                }
            } else {
                await display_toast(res)
            }
        }

        async function link_misp_attribute(attr) {
            const res = await fetch('/case/' + props.task.case_id + '/task/' + props.task.id + '/link_misp_attribute', {
                method: 'POST',
                headers: {
                    'X-CSRFToken': $('#csrf_token').val(),
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ misp_attribute_id: attr.id })
            })
            if (res.status === 200) {
                const loc = await res.json()
                if (!props.task.misp_attribute_links) props.task.misp_attribute_links = []
                props.task.misp_attribute_links.push(loc.link)
                create_message('Standalone MISP attribute linked', 'success-subtle', false, 'fas fa-link')
                try {
                    const modalEl = document.getElementById('misp-attribute-link-modal-' + props.task.id)
                    if (modalEl) {
                        const modalInst = window.bootstrap && window.bootstrap.Modal ? (window.bootstrap.Modal.getInstance(modalEl) || new window.bootstrap.Modal(modalEl)) : null
                        if (modalInst) modalInst.hide()
                    }
                } catch (e) {
                    // ignore modal hide errors
                }
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

        async function unlink_misp_attribute(attr) {
            const res = await fetch('/case/' + props.task.case_id + '/task/' + props.task.id + '/unlink_misp_attribute/' + attr.id)
            if (res.status === 200) {
                const idx = props.task.misp_attribute_links.findIndex(l => l.misp_attribute_id === attr.id)
                if (idx > -1) props.task.misp_attribute_links.splice(idx, 1)
                create_message('Standalone MISP attribute unlinked', 'success-subtle', false, 'fas fa-unlink')
            } else {
                await display_toast(res)
            }
        }

        function get_attribute_label(attr) {
            const attrType = attr.misp_attribute_type || attr.type || 'unknown'
            const attrValue = attr.misp_attribute_value || attr.value || ''
            return attrType + ': ' + attrValue
        }

        function get_attribute_type(attr) {
            return attr.misp_attribute_type || attr.type || 'unknown'
        }

        function get_attribute_value(attr) {
            return attr.misp_attribute_value || attr.value || ''
        }

        function get_attribute_relation(attr) {
            return attr.misp_attribute_object_relation || attr.object_relation || ''
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
            fetch_case_misp_attributes()
            // Listen for newly created / deleted standalone attributes and update this task's links if needed
            window.addEventListener('misp-attribute-created', on_misp_attribute_created)
            window.addEventListener('misp-attribute-deleted', on_misp_attribute_deleted)
        })

        onBeforeUnmount(() => {
            try { window.removeEventListener('misp-attribute-created', on_misp_attribute_created) } catch(e) {}
            try { window.removeEventListener('misp-attribute-deleted', on_misp_attribute_deleted) } catch(e) {}
        })

        function on_misp_attribute_created(e) {
            try {
                const attr = e && e.detail && e.detail.attribute
                const task_ids = e && e.detail && e.detail.task_ids ? e.detail.task_ids : []
                if (!attr || !task_ids || !Array.isArray(task_ids)) return
                // If this task is among the linked task ids, add a link entry
                const tid = props.task.id
                if (task_ids.map(x => parseInt(x)).includes(parseInt(tid))) {
                    if (!props.task.misp_attribute_links) props.task.misp_attribute_links = []
                    // Add a minimal link object similar to Task_Misp_Attribute.to_json()
                    props.task.misp_attribute_links.push({
                        "misp_attribute_id": attr.id,
                        "misp_attribute_value": attr.value,
                        "misp_attribute_type": attr.type,
                        "misp_attribute_object_relation": attr.object_relation || null
                    })
                }
            } catch (e) {}
        }

        function on_misp_attribute_deleted(e) {
            try {
                const aid = e && e.detail && e.detail.attribute_id
                const task_ids = e && e.detail && e.detail.task_ids ? e.detail.task_ids : []
                if (!aid) return
                const tid = props.task.id
                if (!task_ids || !Array.isArray(task_ids)) return
                if (task_ids.map(x => parseInt(x)).includes(parseInt(tid))) {
                    if (!props.task.misp_attribute_links) return
                    const idx = props.task.misp_attribute_links.findIndex(l => parseInt(l.misp_attribute_id) === parseInt(aid))
                    if (idx > -1) props.task.misp_attribute_links.splice(idx, 1)
                }
            } catch (e) {}
        }

        return {
            case_misp_objects,
            case_misp_attributes,
            is_loading,
            can_manage_case_misp_objects,
            can_manage_links,
            is_linked,
            is_attribute_linked,
            link_misp_object,
            link_misp_attribute,
            unlink_misp_object,
            show_object,
            format_object_label,
            format_attribute_preview,
            format_case_object_label,
            format_case_object_preview,
            unlink_misp_attribute,
            get_attribute_label,
            get_attribute_type,
            get_attribute_value,
            get_attribute_relation,
            show_object
        }
    },
    template: `
    <div class="col">
        <div class="task-section">
            <div class="task-section-header">
                <i class="fa-solid fa-shield-halved fa-sm me-1"></i>
                <span class="section-title">MISP Objects linked to this task</span>
                <button class="btn btn-sm btn-outline-secondary ms-auto" type="button" data-bs-toggle="modal" :data-bs-target="'#misp-link-modal-'+task.id" aria-controls="'misp-link-modal-'+task.id">
                    <i class="fa-solid fa-list"></i>
                </button>
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
                        <template v-if="can_manage_links">
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

        <div class="task-section mt-3">
            <div class="task-section-header">
                <i class="fa-solid fa-tag fa-sm me-1"></i>
                <span class="section-title">Standalone MISP attributes linked to this task</span>
                <button class="btn btn-sm btn-outline-secondary ms-auto" type="button" data-bs-toggle="modal" :data-bs-target="'#misp-attribute-link-modal-'+task.id" aria-controls="'misp-attribute-link-modal-'+task.id">
                    <i class="fa-solid fa-list"></i>
                </button>
            </div>
            <div class="task-section-body">
                <template v-if="task.misp_attribute_links && task.misp_attribute_links.length">
                    <div v-for="link in task.misp_attribute_links" :key="link.misp_attribute_id" class="d-flex align-items-center mb-1">
                        <i class="fa-solid fa-tag me-2 text-secondary"></i>
                        <span class="me-2 d-flex align-items-center gap-1 flex-wrap text-break">
                            <span class="badge bg-light text-dark border">[[ get_attribute_type(link) ]]</span>
                            <strong>[[ get_attribute_value(link) ]]</strong>
                            <small v-if="get_attribute_relation(link)" class="text-muted">([[ get_attribute_relation(link) ]])</small>
                        </span>
                        <template v-if="can_manage_links">
                            <button @click="unlink_misp_attribute({id: link.misp_attribute_id})" class="btn btn-danger btn-sm ms-auto" title="Unlink this standalone MISP attribute">
                                <i class="fa-solid fa-link-slash"></i>
                            </button>
                        </template>
                    </div>
                </template>
                <template v-else>
                    <p class="text-muted"><i>No standalone MISP attributes linked</i></p>
                </template>
            </div>
        </div>

        <template v-if="can_manage_links">
            <!-- MISP object selection modal -->
            <div class="modal fade" :id="'misp-link-modal-'+task.id" tabindex="-1" :aria-labelledby="'misp-link-modal-label-'+task.id" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" :id="'misp-link-modal-label-'+task.id">Select a MISP object to link</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <template v-if="case_misp_objects.length">
                                <div v-for="obj in case_misp_objects" :key="obj.object_id" class="d-flex align-items-center mb-2">
                                    <i class="fa-solid fa-cube me-2 text-secondary"></i>
                                    <span class="me-2">
                                        <a href="javascript:void(0)" @click="show_object(obj)"><strong>[[obj.object_name]]</strong></a>
                                        <small class="text-muted ms-1">([[obj.object_uuid]])</small>
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
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Standalone MISP attribute selection modal -->
            <div class="modal fade" :id="'misp-attribute-link-modal-'+task.id" tabindex="-1" :aria-labelledby="'misp-attribute-link-modal-label-'+task.id" aria-hidden="true">
                <div class="modal-dialog modal-lg modal-dialog-scrollable">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h5 class="modal-title" :id="'misp-attribute-link-modal-label-'+task.id">Select a standalone MISP attribute to link</h5>
                            <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-body">
                            <template v-if="case_misp_attributes.length">
                                <div v-for="attr in case_misp_attributes" :key="attr.id" class="d-flex align-items-center mb-2">
                                    <i class="fa-solid fa-tag me-2 text-secondary"></i>
                                    <span class="me-2 d-flex align-items-center gap-1 flex-wrap text-break">
                                        <span class="badge bg-light text-dark border">[[ get_attribute_type(attr) ]]</span>
                                        <strong>[[ get_attribute_value(attr) ]]</strong>
                                        <small v-if="get_attribute_relation(attr)" class="text-muted">([[ get_attribute_relation(attr) ]])</small>
                                    </span>
                                    <template v-if="is_attribute_linked(attr.id)">
                                        <span class="badge text-bg-success ms-auto"><i class="fa-solid fa-check me-1"></i>Linked</span>
                                    </template>
                                    <template v-else>
                                        <button @click="link_misp_attribute(attr)" class="btn btn-primary btn-sm ms-auto" title="Link this standalone MISP attribute to the task">
                                            <i class="fa-solid fa-link"></i> Link
                                        </button>
                                    </template>
                                </div>
                            </template>
                            <template v-else>
                                <p class="text-muted"><i>No standalone MISP attributes in this case yet</i></p>
                            </template>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    </div>
    `
}
