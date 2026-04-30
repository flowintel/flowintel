import { display_toast, create_message } from '../toaster.js'
const { ref, computed, watch } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        instance: Object,      // connector instance (from case_task_connectors_list)
        direction: String,     // 'send' or 'receive'
        modules: Object,
        modal_id: String
    },
    emits: ['sync_done'],
    setup(props, { emit }) {
        const local_objects = ref([])
        const local_search = ref('')
        const local_type_filter = ref('')
        const selected_local_ids = ref([])
        const is_loading_local = ref(false)

        const remote_objects = ref([])
        const remote_search = ref('')
        const remote_type_filter = ref('')
        const selected_remote_uuids = ref([])
        const is_loading_remote = ref(false)

        const module_name = ref('')
        const module_desc = ref('')
        const is_submitting = ref(false)
        const is_importing_report = ref(false)

        const filtered_local = computed(() => {
            let objs = local_objects.value
            const q = local_search.value.trim().toLowerCase()
            const t = local_type_filter.value
            if (q) {
                objs = objs.filter(o =>
                    o.object_name.toLowerCase().includes(q) ||
                    o.attributes.some(a => String(a.value).toLowerCase().includes(q))
                )
            }
            if (t) objs = objs.filter(o => o.object_name === t)
            return objs
        })

        const local_type_options = computed(() =>
            [...new Set(local_objects.value.map(o => o.object_name))].sort()
        )

        const filtered_remote = computed(() => {
            let objs = remote_objects.value
            const q = remote_search.value.trim().toLowerCase()
            const t = remote_type_filter.value
            if (q) {
                objs = objs.filter(o =>
                    o.name.toLowerCase().includes(q) ||
                    o.attributes_preview.some(a => String(a.value).toLowerCase().includes(q))
                )
            }
            if (t) objs = objs.filter(o => o.name === t)
            return objs
        })

        const remote_type_options = computed(() =>
            [...new Set(remote_objects.value.map(o => o.name))].sort()
        )

        function is_synced_locally(uuid) {
            return local_objects.value.some(lo =>
                lo.synced_instances && lo.synced_instances.some(si => si.object_uuid === uuid)
            )
        }

        async function load_local_objects() {
            is_loading_local.value = true
            local_objects.value = []
            try {
                const res = await fetch('/case/' + props.case_id + '/get_case_misp_object')
                if (res.status === 200) {
                    const loc = await res.json()
                    local_objects.value = loc['misp-object'] || []
                    if (props.direction === 'send') {
                        selected_local_ids.value = local_objects.value.map(o => o.object_id)
                    }
                } else {
                    display_toast(res)
                }
            } finally {
                is_loading_local.value = false
            }
        }

        async function load_remote_objects() {
            if (!props.instance) return
            is_loading_remote.value = true
            remote_objects.value = []
            try {
                const res = await fetch('/case/' + props.case_id + '/connectors/' + props.instance.case_task_instance_id + '/misp_objects_preview')
                if (res.status === 200) {
                    const loc = await res.json()
                    remote_objects.value = loc['objects'] || []
                    if (props.direction === 'receive') {
                        selected_remote_uuids.value = remote_objects.value.map(o => o.uuid)
                    }
                } else {
                    display_toast(res)
                }
            } finally {
                is_loading_remote.value = false
            }
        }

        function toggle_local_all() {
            if (selected_local_ids.value.length === filtered_local.value.length) {
                selected_local_ids.value = []
            } else {
                selected_local_ids.value = filtered_local.value.map(o => o.object_id)
            }
        }

        function toggle_remote_all() {
            if (selected_remote_uuids.value.length === filtered_remote.value.length) {
                selected_remote_uuids.value = []
            } else {
                selected_remote_uuids.value = filtered_remote.value.map(o => o.uuid)
            }
        }

        function on_module_change() {
            if (props.modules && module_name.value && props.modules[module_name.value]) {
                module_desc.value = props.modules[module_name.value]?.config?.description || ''
            } else {
                module_desc.value = ''
            }
        }

        async function on_show() {
            module_name.value = ''
            module_desc.value = ''
            local_search.value = ''
            remote_search.value = ''
            local_type_filter.value = ''
            remote_type_filter.value = ''
            selected_local_ids.value = []
            selected_remote_uuids.value = []
            remote_objects.value = []
            await load_local_objects()
        }

        async function submit() {
            if (!module_name.value) {
                create_message("Select a module first", "warning-subtle")
                return
            }
            is_submitting.value = true
            const url = '/case/' + props.case_id + '/call_module_case'
            const body = {
                module: module_name.value,
                case_task_instance_id: props.instance.case_task_instance_id
            }
            if (props.direction === 'send' && module_name.value === 'misp_object_event') {
                body.selected_objects = selected_local_ids.value
            }
            if (props.direction === 'receive' && module_name.value === 'receive_misp_object') {
                body.selected_objects = selected_remote_uuids.value
            }
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            is_submitting.value = false
            if (res.status === 200) {
                emit('sync_done', { direction: props.direction, instance: props.instance })
                bootstrap.Modal.getInstance(document.getElementById(props.modal_id))?.hide()
            }
            display_toast(res)
        }

        async function import_event_report() {
            is_importing_report.value = true
            const res = await fetch('/case/' + props.case_id + '/connectors/' + props.instance.case_task_instance_id + '/import_event_report', {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify({})
            })
            is_importing_report.value = false
            display_toast(res, true)
        }

        return {
            local_objects, local_search, local_type_filter, selected_local_ids, is_loading_local,
            remote_objects, remote_search, remote_type_filter, selected_remote_uuids, is_loading_remote,
            module_name, module_desc, is_submitting, is_importing_report,
            filtered_local, filtered_remote, local_type_options, remote_type_options,
            load_remote_objects, toggle_local_all, toggle_remote_all,
            submit, import_event_report, on_show, on_module_change, is_synced_locally
        }
    },
    template: `
    <div class="modal fade" :id="modal_id" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i v-if="direction === 'send'" class="fa-solid fa-arrow-up me-2"></i>
                        <i v-else class="fa-solid fa-arrow-down me-2"></i>
                        [[ direction === 'send' ? 'Send to MISP' : 'Receive from MISP' ]]
                        <span v-if="instance" class="ms-2 text-muted small">[[ instance.details.name ]]</span>
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">
                    <!-- Module selector -->
                    <div class="row mb-3">
                        <div class="col-md-5">
                            <label class="form-label fw-semibold mb-1">Module</label>
                            <select class="form-select form-select-sm" v-model="module_name" @change="on_module_change">
                                <option value="">-- select module --</option>
                                <template v-for="(mod, key) in modules">
                                    <option v-if="direction === 'send' ? mod.type === 'send_to' : mod.type === 'receive_from'" :value="key">[[ key ]]</option>
                                </template>
                            </select>
                        </div>
                        <div class="col-md-7 text-muted small" v-if="module_desc" style="padding-top:1.75rem;">
                            [[ module_desc ]]
                        </div>
                    </div>

                    <!-- Two-column object panels -->
                    <div class="row g-3">
                        <!-- LEFT: Local objects -->
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-header d-flex justify-content-between align-items-center py-2">
                                    <span class="fw-semibold">
                                        Local objects
                                        <span class="badge bg-secondary ms-1">[[ filtered_local.length ]]</span>
                                        <span v-if="direction === 'send'" class="badge bg-primary ms-1">[[ selected_local_ids.length ]] selected</span>
                                    </span>
                                    <button v-if="direction === 'send'" type="button" class="btn btn-link btn-sm py-0" @click="toggle_local_all()">
                                        [[ selected_local_ids.length === filtered_local.length && filtered_local.length > 0 ? 'Deselect all' : 'Select all' ]]
                                    </button>
                                </div>
                                <div class="card-body p-2">
                                    <div class="d-flex gap-1 mb-2">
                                        <input v-model="local_search" class="form-control form-control-sm" placeholder="Search by name or value…" type="text">
                                        <select v-model="local_type_filter" class="form-select form-select-sm" style="max-width:130px;">
                                            <option value="">All types</option>
                                            <option v-for="t in local_type_options" :key="t" :value="t">[[ t ]]</option>
                                        </select>
                                    </div>
                                    <div v-if="is_loading_local" class="text-center py-3">
                                        <span class="spinner-border spinner-border-sm me-2"></span>Loading…
                                    </div>
                                    <div v-else style="max-height:380px; overflow-y:auto;">
                                        <div v-if="!filtered_local.length" class="text-muted small p-2">No local objects.</div>
                                        <div v-for="obj in filtered_local" :key="obj.object_id"
                                             class="border-bottom py-1 px-1"
                                             :class="{ 'bg-body-secondary': direction === 'receive' }">
                                            <div class="form-check mb-0">
                                                <input class="form-check-input" type="checkbox" :value="obj.object_id"
                                                       v-model="selected_local_ids" :id="'lobj-'+modal_id+'-'+obj.object_id"
                                                       :disabled="direction === 'receive'">
                                                <label class="form-check-label" :for="'lobj-'+modal_id+'-'+obj.object_id">
                                                    <span class="fw-semibold">[[ obj.object_name ]]</span>
                                                    <span class="text-muted ms-1" style="font-size:0.8em;">([[ obj.attributes.length ]] attrs)</span>
                                                    <template v-if="obj.synced_instances && obj.synced_instances.length">
                                                        <span v-for="si in obj.synced_instances" :key="si.instance_id"
                                                              class="badge bg-info text-dark ms-1"
                                                              style="font-size:0.65em;"
                                                              :title="'Synced with '+si.instance_name+' — UUID: '+si.object_uuid">
                                                            <i class="fa-solid fa-cloud me-1"></i>[[ si.instance_name ]]
                                                        </span>
                                                    </template>
                                                </label>
                                            </div>
                                            <div v-if="obj.attributes.length" class="text-muted ms-4" style="font-size:0.75em;">
                                                <template v-for="(a,i) in obj.attributes.slice(0,3)">
                                                    <span v-if="i>0"> · </span>[[ a.object_relation ]]: [[ a.value.length > 40 ? a.value.substring(0,40)+'…' : a.value ]]
                                                </template>
                                                <span v-if="obj.attributes.length > 3" class="ms-1">+[[ obj.attributes.length - 3 ]] more</span>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- RIGHT: Remote objects -->
                        <div class="col-md-6">
                            <div class="card h-100">
                                <div class="card-header d-flex justify-content-between align-items-center py-2">
                                    <span class="fw-semibold">
                                        Remote (MISP)
                                        <span class="badge bg-secondary ms-1">[[ filtered_remote.length ]]</span>
                                        <span v-if="direction === 'receive'" class="badge bg-primary ms-1">[[ selected_remote_uuids.length ]] selected</span>
                                    </span>
                                    <div class="d-flex gap-2 align-items-center">
                                        <button v-if="direction === 'receive' && remote_objects.length" type="button" class="btn btn-link btn-sm py-0" @click="toggle_remote_all()">
                                            [[ selected_remote_uuids.length === filtered_remote.length && filtered_remote.length > 0 ? 'Deselect all' : 'Select all' ]]
                                        </button>
                                        <button type="button" class="btn btn-sm btn-outline-secondary py-0" @click="load_remote_objects()" :disabled="is_loading_remote">
                                            <span v-if="is_loading_remote" class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>
                                            <i v-else class="fa-solid fa-rotate me-1"></i>
                                            [[ remote_objects.length ? 'Reload' : 'Load from MISP' ]]
                                        </button>
                                    </div>
                                </div>
                                <div class="card-body p-2">
                                    <div class="d-flex gap-1 mb-2">
                                        <input v-model="remote_search" class="form-control form-control-sm" placeholder="Search by name or value…" type="text">
                                        <select v-model="remote_type_filter" class="form-select form-select-sm" style="max-width:130px;">
                                            <option value="">All types</option>
                                            <option v-for="t in remote_type_options" :key="t" :value="t">[[ t ]]</option>
                                        </select>
                                    </div>
                                    <div v-if="is_loading_remote" class="text-center py-3">
                                        <span class="spinner-border spinner-border-sm me-2"></span>Loading from MISP…
                                    </div>
                                    <div v-else style="max-height:380px; overflow-y:auto;">
                                        <div v-if="!remote_objects.length" class="text-muted small p-2">
                                            Click "Load from MISP" to fetch remote objects.
                                        </div>
                                        <div v-else-if="!filtered_remote.length" class="text-muted small p-2">No objects match the filter.</div>
                                        <div v-for="obj in filtered_remote" :key="obj.uuid"
                                             class="border-bottom py-1 px-1"
                                             :class="{ 'bg-body-secondary': direction === 'send' }">
                                            <div class="form-check mb-0">
                                                <input class="form-check-input" type="checkbox" :value="obj.uuid"
                                                       v-model="selected_remote_uuids" :id="'robj-'+modal_id+'-'+obj.uuid"
                                                       :disabled="direction === 'send'">
                                                <label class="form-check-label" :for="'robj-'+modal_id+'-'+obj.uuid">
                                                    <span class="fw-semibold">[[ obj.name ]]</span>
                                                    <span class="text-muted ms-1" style="font-size:0.8em;">([[ obj.attribute_count ]] attrs)</span>
                                                    <span v-if="is_synced_locally(obj.uuid)" class="badge bg-success text-white ms-1" style="font-size:0.65em;" title="Already synced locally">
                                                        <i class="fa-solid fa-check me-1"></i>Synced
                                                    </span>
                                                </label>
                                            </div>
                                            <div v-if="obj.attributes_preview.length" class="text-muted ms-4" style="font-size:0.75em;">
                                                <template v-for="(a,i) in obj.attributes_preview">
                                                    <span v-if="i>0"> · </span>[[ a.relation ]]: [[ a.value ]]
                                                </template>
                                            </div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Event report import (receive + MISP only) -->
                    <template v-if="direction === 'receive' && instance && instance.is_misp_connector">
                        <hr class="my-3">
                        <div class="d-flex align-items-center gap-3 flex-wrap">
                            <span class="fw-semibold"><i class="fa-solid fa-file-lines me-1"></i>Event report</span>
                            <button type="button" class="btn btn-sm btn-outline-info" :disabled="is_importing_report" @click="import_event_report()">
                                <span v-if="is_importing_report" class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>
                                <i v-else class="fa-solid fa-file-import me-1"></i>
                                Import event report as case note
                            </button>
                            <span class="text-muted small">Appends the MISP event's report(s) to the case note.</span>
                        </div>
                    </template>
                </div>
                <div class="modal-footer">
                    <div class="text-muted small me-auto">
                        <template v-if="direction === 'send'">
                            <i class="fa-solid fa-arrow-up me-1"></i>[[ selected_local_ids.length ]] local object(s) selected
                        </template>
                        <template v-else>
                            <i class="fa-solid fa-arrow-down me-1"></i>[[ selected_remote_uuids.length ]] remote object(s) selected
                        </template>
                    </div>
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                    <button type="button" class="btn btn-primary" :disabled="is_submitting" @click="submit()">
                        <span v-if="is_submitting" class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>
                        [[ direction === 'send' ? 'Send to MISP' : 'Receive from MISP' ]]
                    </button>
                </div>
            </div>
        </div>
    </div>
    `
}
