import { display_toast, create_message } from '../toaster.js'
const { ref, computed, watch, reactive } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        instance: Object,      // connector instance (from case_task_connectors_list)
        direction: String,     // 'send' or 'receive'
        modules: Object,
        case_misp_objects_list: { type: Array, default: null },
        cases_info: { type: Object, default: null },
    },
    emits: ['sync_done', 'close'],
    setup(props, { emit }) {
        const local_objects = ref([])
        const local_standalone_attrs = ref([])
        const local_search = ref('')
        const local_type_filter = ref('')
        const selected_local_ids = ref([])
        const selected_local_sa_ids = ref([])
        const is_loading_local = ref(false)

        const show_unsynced_only = ref(false)

        const remote_objects = ref([])
        const remote_standalone_attrs = ref([])
        const remote_search = ref('')
        const remote_type_filter = ref('')
        const selected_remote_uuids = ref([])
        const selected_remote_sa_uuids = ref([])
        const is_loading_remote = ref(false)

        const module_name = ref('')
        const module_desc = ref('')
        const is_submitting = ref(false)
        const is_importing_report = ref(false)

        // Panels: 'objects' | 'case_tasks'
        const active_panel = ref('objects')

        // Case & Task selection state
        const case_fields = reactive({ title: true, description: false, notes: true, tags: false, clusters: false, files: false })
        const selected_tasks_map = ref({})
        const tasks = computed(() => (props.cases_info && props.cases_info.tasks) ? props.cases_info.tasks : [])
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
            if (show_unsynced_only.value && props.direction === 'send') {
                objs = objs.filter(o =>
                    !o.synced_instances || !o.synced_instances.some(si =>
                        si.instance_id === props.instance?.details?.id
                    )
                )
            }
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
            if (show_unsynced_only.value && props.direction === 'receive') {
                objs = objs.filter(o => !is_synced_locally(o.uuid))
            }
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
            if (props.case_misp_objects_list !== null) {
                local_objects.value = props.case_misp_objects_list
                if (props.direction === 'send') {
                    selected_local_ids.value = local_objects.value.map(o => o.object_id)
                }
                // Also load standalone attrs
                await load_local_standalone_attrs()
                return
            }
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
            await load_local_standalone_attrs()
        }

        async function load_local_standalone_attrs() {
            try {
                const res = await fetch('/case/' + props.case_id + '/get_case_misp_attributes')
                if (res.status === 200) {
                    const loc = await res.json()
                    local_standalone_attrs.value = loc['attributes'] || []
                    if (props.direction === 'send') {
                        selected_local_sa_ids.value = local_standalone_attrs.value.map(a => a.id)
                    }
                }
            } catch (e) { /* ignore */ }
        }

        async function load_remote_objects() {
            if (!props.instance) return
            is_loading_remote.value = true
            remote_objects.value = []
            remote_standalone_attrs.value = []
            try {
                const res = await fetch('/case/' + props.case_id + '/connectors/' + props.instance.case_task_instance_id + '/misp_objects_preview')
                if (res.status === 200) {
                    const loc = await res.json()
                    remote_objects.value = loc['objects'] || []
                    remote_standalone_attrs.value = loc['standalone_attributes'] || []
                    if (props.direction === 'receive') {
                        selected_remote_uuids.value = remote_objects.value.map(o => o.uuid)
                        selected_remote_sa_uuids.value = remote_standalone_attrs.value.map(a => a.uuid)
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

        function toggle_local_sa_all() {
            if (selected_local_sa_ids.value.length === local_standalone_attrs.value.length) {
                selected_local_sa_ids.value = []
            } else {
                selected_local_sa_ids.value = local_standalone_attrs.value.map(a => a.id)
            }
        }

        function toggle_remote_all() {
            if (selected_remote_uuids.value.length === filtered_remote.value.length) {
                selected_remote_uuids.value = []
            } else {
                selected_remote_uuids.value = filtered_remote.value.map(o => o.uuid)
            }
        }

        function toggle_remote_sa_all() {
            if (selected_remote_sa_uuids.value.length === remote_standalone_attrs.value.length) {
                selected_remote_sa_uuids.value = []
            } else {
                selected_remote_sa_uuids.value = remote_standalone_attrs.value.map(a => a.uuid)
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
            selected_local_sa_ids.value = []
            selected_remote_uuids.value = []
            selected_remote_sa_uuids.value = []
            remote_objects.value = []
            remote_standalone_attrs.value = []
            show_unsynced_only.value = false
            // default module depending on panel
            module_name.value = active_panel.value === 'objects' ? 'misp_object_event' : ''
            // initialize selected_tasks_map from provided case tasks
            selected_tasks_map.value = {}
            for (const t of tasks.value) {
                selected_tasks_map.value[t.uuid] = { include: false, include_notes: true, include_resources: true }
            }
            await load_local_objects()
        }

        async function submit() {
            if (!module_name.value) {
                create_message("Select a module first", "warning-subtle")
                return
            }

            // If user is on Case & Task panel, submit a payload with selected fields/tasks
            if (active_panel.value === 'case_tasks') {
                await submit_case_tasks()
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
                body.selected_standalone_attrs = selected_local_sa_ids.value
            }
            if (props.direction === 'receive' && module_name.value === 'receive_misp_object') {
                body.selected_objects = selected_remote_uuids.value
                body.selected_standalone_attrs = selected_remote_sa_uuids.value
            }
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            is_submitting.value = false
            if (res.status === 200) {
                emit('sync_done', { direction: props.direction, instance: props.instance })
                emit('close')
            }
            display_toast(res)
        }

        async function submit_case_tasks() {
            is_submitting.value = true
            const url = '/case/' + props.case_id + '/call_module_case'
            const body = {
                module: module_name.value,
                case_task_instance_id: props.instance.case_task_instance_id,
                selected_case_fields: [],
                selected_tasks: []
            }

            for (const k of Object.keys(case_fields)) {
                if (case_fields[k]) body.selected_case_fields.push(k)
            }

            for (const t of tasks.value) {
                const sel = selected_tasks_map.value[t.uuid]
                if (sel && sel.include) {
                    body.selected_tasks.push({ uuid: t.uuid, include_notes: !!sel.include_notes, include_resources: !!sel.include_resources })
                }
            }

            const res = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify(body)
            })
            is_submitting.value = false
            if (res.status === 200) {
                emit('sync_done', { direction: props.direction, instance: props.instance })
                emit('close')
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

        // Ensure selected_tasks_map has entries for existing tasks (watch for case info changes)
        watch(tasks, (nt) => {
            if (!selected_tasks_map.value) selected_tasks_map.value = {}
            for (const t of nt || []) {
                if (!selected_tasks_map.value[t.uuid]) selected_tasks_map.value[t.uuid] = { include: false, include_notes: true, include_resources: true }
            }
        }, { immediate: true })

        return {
            local_objects, local_standalone_attrs, local_search, local_type_filter, selected_local_ids, selected_local_sa_ids, is_loading_local,
            remote_objects, remote_standalone_attrs, remote_search, remote_type_filter, selected_remote_uuids, selected_remote_sa_uuids, is_loading_remote,
            module_name, module_desc, is_submitting, is_importing_report,
            filtered_local, filtered_remote, local_type_options, remote_type_options,
            show_unsynced_only,
            load_remote_objects, toggle_local_all, toggle_local_sa_all, toggle_remote_all, toggle_remote_sa_all,
            submit, import_event_report, on_show, on_module_change, is_synced_locally,
            // new panel state
            active_panel, case_fields, selected_tasks_map, tasks
        }
    },
    template: `
    <div>
        <!-- Panel switch -->
        <div class="mb-2">
            <div class="btn-group" role="group">
                <button type="button" class="btn btn-sm" :class="active_panel==='objects' ? 'btn-primary' : 'btn-outline-secondary'" @click="active_panel='objects'">Objects & Attributes</button>
                <button type="button" class="btn btn-sm" :class="active_panel==='case_tasks' ? 'btn-primary' : 'btn-outline-secondary'" @click="active_panel='case_tasks'">Case & Task</button>
            </div>
        </div>

        <template v-if="active_panel === 'objects'">
            <!-- Module selector -->
            <div class="row mb-3">
                <div class="col-md-5">
                    <label class="form-label fw-semibold mb-1">Module</label>
                    <select class="form-select form-select-sm" v-model="module_name" @change="on_module_change">
                        <option value="">-- select module --</option>
                        <template v-for="(mod, key) in modules">
                            <option v-if="(direction === 'send' ? mod.type === 'send_to' : mod.type === 'receive_from') && mod.config?.connector === 'misp'" :value="key">[[ key ]]</option>
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
                            <div class="d-flex align-items-center gap-2">
                                <button v-if="direction === 'send'" type="button"
                                        :class="['btn btn-sm py-0', show_unsynced_only ? 'btn-warning' : 'btn-outline-secondary']"
                                        @click="show_unsynced_only = !show_unsynced_only"
                                        title="Toggle: show only objects not yet synced to this instance">
                                    <i class="fa-solid fa-filter me-1"></i>Unsynced only
                                </button>
                                <button v-if="direction === 'send'" type="button" class="btn btn-link btn-sm py-0" @click="toggle_local_all()">
                                    [[ selected_local_ids.length === filtered_local.length && filtered_local.length > 0 ? 'Deselect all' : 'Select all' ]]
                                </button>
                            </div>
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
                                               v-model="selected_local_ids" :id="'lobj-'+instance.case_task_instance_id+'-'+obj.object_id"
                                               :disabled="direction === 'receive'">
                                        <label class="form-check-label" :for="'lobj-'+instance.case_task_instance_id+'-'+obj.object_id">
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
                            <!-- Standalone attributes in local panel -->
                            <div v-if="local_standalone_attrs.length" class="mt-2 pt-2 border-top">
                                <div class="d-flex align-items-center justify-content-between mb-1">
                                    <span class="text-muted small fw-semibold"><i class="fa-solid fa-tag me-1"></i>Standalone attributes ([[ local_standalone_attrs.length ]])</span>
                                    <button v-if="direction === 'send'" type="button" class="btn btn-link btn-sm py-0" @click="toggle_local_sa_all()">
                                        [[ selected_local_sa_ids.length === local_standalone_attrs.length ? 'Deselect all' : 'Select all' ]]
                                    </button>
                                </div>
                                <div v-for="sa in local_standalone_attrs" :key="'lsa-'+sa.id" class="border-bottom py-1 px-1">
                                    <div class="form-check mb-0">
                                        <input class="form-check-input" type="checkbox" :value="sa.id"
                                               v-model="selected_local_sa_ids" :id="'lsa-'+instance.case_task_instance_id+'-'+sa.id"
                                               :disabled="direction === 'receive'">
                                        <label class="form-check-label" :for="'lsa-'+instance.case_task_instance_id+'-'+sa.id" style="font-size:0.8em;">
                                            <span class="badge bg-secondary me-1">[[ sa.type ]]</span>
                                            <span>[[ sa.value.length > 50 ? sa.value.substring(0,50)+'…' : sa.value ]]</span>
                                            <span v-if="sa.synced_instances && sa.synced_instances.length" class="badge bg-success ms-1" style="font-size:0.65em;">synced</span>
                                        </label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header d-flex justify-content-between align-items-center py-2">
                            <span class="fw-semibold">
                                Remote (MISP)
                                <span class="badge bg-secondary ms-1">[[ filtered_remote.length ]]</span>
                                <span v-if="direction === 'receive'" class="badge bg-primary ms-1">[[ selected_remote_uuids.length ]] selected</span>
                            </span>
                            <div class="d-flex gap-2 align-items-center">
                                <button v-if="direction === 'receive' && remote_objects.length" type="button"
                                        :class="['btn btn-sm py-0', show_unsynced_only ? 'btn-warning' : 'btn-outline-secondary']"
                                        @click="show_unsynced_only = !show_unsynced_only"
                                        title="Toggle: show only objects not yet synced locally">
                                    <i class="fa-solid fa-filter me-1"></i>Unsynced only
                                </button>
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
                                                v-model="selected_remote_uuids" :id="'robj-'+instance.case_task_instance_id+'-'+obj.uuid"
                                                :disabled="direction === 'send'">
                                        <label class="form-check-label" :for="'robj-'+instance.case_task_instance_id+'-'+obj.uuid">
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
                                <!-- Standalone attributes in remote panel -->
                                <div v-if="remote_standalone_attrs.length" class="mt-2 pt-2 border-top">
                                    <div class="d-flex align-items-center justify-content-between mb-1">
                                        <span class="text-muted small fw-semibold"><i class="fa-solid fa-tag me-1"></i>Standalone attributes ([[ remote_standalone_attrs.length ]])</span>
                                        <button v-if="direction === 'receive'" type="button" class="btn btn-link btn-sm py-0" @click="toggle_remote_sa_all()">
                                            [[ selected_remote_sa_uuids.length === remote_standalone_attrs.length ? 'Deselect all' : 'Select all' ]]
                                        </button>
                                    </div>
                                    <div v-for="sa in remote_standalone_attrs" :key="'rsa-'+sa.uuid" class="border-bottom py-1 px-1">
                                        <div class="form-check mb-0">
                                            <input class="form-check-input" type="checkbox" :value="sa.uuid"
                                                    v-model="selected_remote_sa_uuids" :id="'rsa-'+instance.case_task_instance_id+'-'+sa.uuid"
                                                    :disabled="direction === 'send'">
                                            <label class="form-check-label" :for="'rsa-'+instance.case_task_instance_id+'-'+sa.uuid" style="font-size:0.8em;">
                                                <span class="badge bg-secondary me-1">[[ sa.type ]]</span>
                                                <span>[[ sa.value.length > 50 ? sa.value.substring(0,50)+'…' : sa.value ]]</span>
                                            </label>
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
                <div class="d-flex align-items-center justify-content-end gap-2 mt-3 pt-2 border-top">
                    <div class="text-muted small me-auto">
                        <template v-if="direction === 'send'">
                            <i class="fa-solid fa-arrow-up me-1"></i>[[ selected_local_ids.length ]] object(s) + [[ selected_local_sa_ids.length ]] attribute(s) selected
                        </template>
                        <template v-else>
                            <i class="fa-solid fa-arrow-down me-1"></i>[[ selected_remote_uuids.length ]] remote object(s) + [[ selected_remote_sa_uuids.length ]] attribute(s) selected
                        </template>
                    </div>
                    <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancel</button>
                    <button type="button" class="btn btn-primary" :disabled="is_submitting" @click="submit()">
                        <span v-if="is_submitting" class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>
                        [[ direction === 'send' ? 'Send to MISP' : 'Receive from MISP' ]]
                    </button>
                </div>
            </div>
        </template>

        <template v-else>
            <!-- Case & Task selection -->
            <div class="row g-3">
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header py-2"><span class="fw-semibold">Case fields</span></div>
                        <div class="card-body">
                            <div class="form-check" v-for="(val,key) in case_fields" :key="key">
                                <input class="form-check-input" type="checkbox" :id="'case-field-'+key" v-model="case_fields[key]">
                                <label class="form-check-label" :for="'case-field-'+key">[[ key ]]</label>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="col-md-6">
                    <div class="card h-100">
                        <div class="card-header py-2"><span class="fw-semibold">Tasks</span></div>
                        <div class="card-body" style="max-height:380px; overflow-y:auto;">
                            <div v-if="!tasks.length" class="text-muted small p-2">No tasks in this case.</div>
                            <div v-for="t in tasks" :key="t.uuid" class="border-bottom py-1 px-1">
                                <div class="form-check mb-1">
                                    <input class="form-check-input" type="checkbox" :id="'task-select-'+t.uuid" v-model="selected_tasks_map[t.uuid].include">
                                    <label class="form-check-label" :for="'task-select-'+t.uuid">
                                        <span class="fw-semibold">[[ t.title || t.uuid ]]</span>
                                    </label>
                                </div>
                                <div class="ms-3 small text-muted d-flex gap-3">
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" :id="'task-notes-'+t.uuid" v-model="selected_tasks_map[t.uuid].include_notes">
                                        <label class="form-check-label" :for="'task-notes-'+t.uuid">Include notes</label>
                                    </div>
                                    <div class="form-check">
                                        <input class="form-check-input" type="checkbox" :id="'task-res-'+t.uuid" v-model="selected_tasks_map[t.uuid].include_resources">
                                        <label class="form-check-label" :for="'task-res-'+t.uuid">Include resources</label>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>

            <!-- Module selector for Case/Task -->
            <div class="row mb-3 mt-3">
                <div class="col-md-5">
                    <label class="form-label fw-semibold mb-1">Module</label>
                    <select class="form-select form-select-sm" v-model="module_name" @change="on_module_change">
                        <option value="">-- select module --</option>
                        <template v-for="(mod, key) in modules">
                            <option v-if="(direction === 'send' ? mod.type === 'send_to' : mod.type === 'receive_from') && mod.config?.connector === 'misp'" :value="key">[[ key ]]</option>
                        </template>
                    </select>
                </div>
                <div class="col-md-7 text-muted small" v-if="module_desc" style="padding-top:1.75rem;">
                    [[ module_desc ]]
                </div>
            </div>

            <div class="d-flex align-items-center justify-content-end gap-2 mt-3 pt-2 border-top">
                <div class="text-muted small me-auto">Prepare a selective export of case and tasks</div>
                <button type="button" class="btn btn-secondary" @click="$emit('close')">Cancel</button>
                <button type="button" class="btn btn-primary" :disabled="is_submitting || !module_name" @click="submit()">
                    <span v-if="is_submitting" class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>
                    Send to MISP
                </button>
            </div>
        </template>
    </div>
    `
}
