import { display_toast, create_message } from '../toaster.js'
const { ref, computed, onMounted, watch, nextTick } = Vue

const MISP_ATTRIBUTE_TYPES = ref([])

async function fetch_attr_types() {
    try {
        const res = await fetch('/case/get_misp_attribute_types')
        if (res.status === 200) {
            const data = await res.json()
            MISP_ATTRIBUTE_TYPES.value = data.types || []
        } else {
            display_toast(res)
        }
    } catch (e) {
        console.warn('fetch_attr_types error', e)
    }
}

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        cases_info: Object,
    },
    emits: ['attr_count', 'modif_misp_attrs'],
    setup(props, { emit }) {
        const attrs = ref([])
        const show_add = ref(false)
        const new_state = ref({ type: '', value: '', comment: '', ids_flag: false, disable_correlation: false, first_seen: '', last_seen: '', task_ids: [] })
        const new_attr_task_ids = ref([])
        const editing_id = ref(null)
        const edit_state = ref({})
        const search_query = ref('')
        const type_filter = ref('')
        const show_unsynced_only = ref(false)
        const is_loading = ref(false)
        const compact_view = ref(true)
        const tab_view = ref(false)
        const active_tab_type = ref('')
        const assigning_attr_id = ref(null)
        const assign_task_state = ref({})

        const can_edit = computed(() => {
            if (!props.cases_info) return false
            const p = props.cases_info.permission
            if (p && p.read_only) return false
            if (p && p.admin) return true
            return props.cases_info.present_in_case
        })

        const filtered_attrs = computed(() => {
            let list = attrs.value
            const q = search_query.value.trim().toLowerCase()
            const t = type_filter.value
            if (q) {
                list = list.filter(a =>
                    String(a.value).toLowerCase().includes(q) ||
                    String(a.type).toLowerCase().includes(q) ||
                    String(a.comment || '').toLowerCase().includes(q)
                )
            }
            if (t) list = list.filter(a => a.type === t)
            if (show_unsynced_only.value) {
                list = list.filter(a => !a.synced_instances || !a.synced_instances.length)
            }
            return list
        })

        const grouped_attrs = computed(() => {
            const grouped = {}
            for (const a of filtered_attrs.value) {
                const t = a.type || 'unknown'
                if (!grouped[t]) grouped[t] = []
                grouped[t].push(a)
            }
            return Object.keys(grouped)
                .sort((a, b) => a.localeCompare(b))
                .map(type => ({ type, attrs: grouped[type] }))
        })

        const tab_types = computed(() => grouped_attrs.value.map(g => g.type))

        const active_tab_attrs = computed(() => {
            const group = grouped_attrs.value.find(g => g.type === active_tab_type.value)
            return group ? group.attrs : []
        })

        const visible_column_count = computed(() => {
            const base = compact_view.value ? 3 : 8
            return base + (can_edit.value ? 1 : 0)
        })

        const type_options = computed(() => (MISP_ATTRIBUTE_TYPES.value || []).slice().sort())

        function sync_active_tab_type() {
            const types = tab_types.value
            if (!types.length) {
                active_tab_type.value = ''
                return
            }
            if (!types.includes(active_tab_type.value)) {
                active_tab_type.value = types[0]
            }
        }

        function tab_count_for(type) {
            const group = grouped_attrs.value.find(g => g.type === type)
            return group ? group.attrs.length : 0
        }

        watch(tab_types, () => {
            sync_active_tab_type()
        }, { immediate: true })

        function toggle_compact_view() {
            compact_view.value = !compact_view.value
        }

        function toggle_tab_view() {
            tab_view.value = !tab_view.value
            if (tab_view.value) sync_active_tab_type()
        }

        async function fetch_attrs() {
            is_loading.value = true
            try {
                const res = await fetch(`/case/${props.case_id}/get_case_misp_attributes`)
                if (res.status === 200) {
                    const loc = await res.json()
                    attrs.value = loc.attributes || []
                    emit('attr_count', attrs.value.length)
                } else {
                    display_toast(res)
                }
            } finally {
                is_loading.value = false
            }
        }

        let hasJQuery = false
        let hasSelect2 = false
        try {
            hasJQuery = (typeof $ !== 'undefined')
            hasSelect2 = hasJQuery && $.fn && $.fn.select2
        } catch(e) {}

        function reset_add() {
            try {
                if (hasSelect2) {
                    const sel = document.getElementById('new-attr-task-select')
                    if (sel && $(sel).data('select2')) $(sel).select2('destroy')
                }
            } catch(e) {}
            try {
                const sel = document.getElementById('new-attr-task-select')
                if (sel) {
                    // Clear native select option selections
                    for (let i = 0; i < sel.options.length; i++) sel.options[i].selected = false
                    // If jQuery/select2 present, clear its value as well
                    try { if (hasSelect2 && $(sel).data('select2')) $(sel).val(null).trigger('change') } catch (e) {}
                }
            } catch (e) {}
            new_attr_task_ids.value = []
            new_state.value = { type: '', value: '', comment: '', ids_flag: false, disable_correlation: false, first_seen: '', last_seen: '', task_ids: [] }
            show_add.value = false
        }

        async function create_attr() {
            if (!new_state.value.type) {
                create_message('Select a type', 'warning-subtle')
                return
            }
            if (!new_state.value.value) {
                create_message('Enter a value', 'warning-subtle')
                return
            }
            // ensure task ids from select2 (if used) are included
            new_state.value.task_ids = new_attr_task_ids.value.slice()

            const res = await fetch(`/case/${props.case_id}/create_misp_attribute`, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify(new_state.value)
            })
            if (res.status === 201) {
                const body = await res.json()
                // copy task ids before reset
                const linked_task_ids = new_attr_task_ids.value ? new_attr_task_ids.value.slice() : []
                await fetch_attrs()
                // notify other components (tasks) about the new attribute and its linked tasks
                try {
                    window.dispatchEvent(new CustomEvent('misp-attribute-created', { detail: { attribute: body.attribute, task_ids: linked_task_ids } }))
                } catch (e) {}
                reset_add()
                // display toast using parsed body to avoid consuming the response twice
                await display_toast(body)
            } else {
                await display_toast(res)
            }
        }

        function start_edit(sa) {
            editing_id.value = sa.id
            edit_state.value = {
                type: sa.type,
                value: sa.value,
                comment: sa.comment || '',
                ids_flag: sa.ids_flag || false,
                disable_correlation: sa.disable_correlation || false,
                first_seen: sa.first_seen ? sa.first_seen.replace(' ', 'T') : '',
                last_seen: sa.last_seen ? sa.last_seen.replace(' ', 'T') : ''
            }
        }

        function cancel_edit() {
            editing_id.value = null
            edit_state.value = {}
        }

        async function save_edit(aid) {
            if (!edit_state.value.value) {
                create_message('Enter a value', 'warning-subtle')
                return
            }
            const res = await fetch(`/case/${props.case_id}/misp_attribute/${aid}/edit_misp_attribute`, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify(edit_state.value)
            })
            if (res.status === 200) {
                cancel_edit()
                await fetch_attrs()
            }
            display_toast(res)
        }

        async function delete_attr(aid) {
            // capture linked task ids before deletion so we can notify other components
            const attr = attrs.value.find(a => a.id === aid)
            const linked_task_ids = attr && attr.tasks ? (attr.tasks.map(t => t.id)) : []

            const res = await fetch(`/case/${props.case_id}/misp_attribute/${aid}/delete_misp_attribute`)
            if (res.status === 200) {
                attrs.value = attrs.value.filter(a => a.id !== aid)
                emit('attr_count', attrs.value.length)
                try {
                    window.dispatchEvent(new CustomEvent('misp-attribute-deleted', { detail: { attribute_id: aid, task_ids: linked_task_ids } }))
                } catch (e) {}
            }
            display_toast(res)
        }

        function scroll_to_task(task_id) {
            const el = document.getElementById('task-' + task_id)
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' })
            } else {
                window.location.hash = 'task-' + task_id
            }
        }

        function toggle_assign_tasks(sa) {
            if (assigning_attr_id.value === sa.id) {
                assigning_attr_id.value = null
                return
            }
            assign_task_state.value[sa.id] = (sa.tasks || []).map(t => t.id)
            assigning_attr_id.value = sa.id
        }

        async function save_assign_tasks(aid) {
            const sel = assign_task_state.value[aid] || []
            const res = await fetch(`/case/${props.case_id}/misp_attribute/${aid}/set_tasks`, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_ids: sel })
            })
            if (res.status === 200) {
                const tasks_map = {}
                if (props.cases_info && props.cases_info.tasks) {
                    for (const t of props.cases_info.tasks) tasks_map[t.id] = t
                }
                const idx = attrs.value.findIndex(a => a.id === aid)
                if (idx > -1) {
                    attrs.value[idx].tasks = sel.map(id => ({
                        id: id,
                        title: tasks_map[id] ? tasks_map[id].title : `Task ${id}`
                    }))
                }
                assigning_attr_id.value = null
                emit('modif_misp_attrs', true)
                create_message('Tasks linked to standalone attribute', 'success-subtle', false, 'fa-solid fa-list-check')
            }
            display_toast(res)
        }

        onMounted(async () => {
            reset_add()
            assigning_attr_id.value = null
            await fetch_attr_types()
            await fetch_attrs()
        })

        // Initialize select2 when the add panel is shown
        watch(() => show_add.value, async (nv) => {
            if (!nv) return
            await nextTick()
            try {
                const sel = document.getElementById('new-attr-task-select')
                if (!sel) return

                // Ensure no option is pre-selected by clearing native selections before initializing select2
                try {
                    for (let i = 0; i < sel.options.length; i++) sel.options[i].selected = false
                    if (hasSelect2) { try { $(sel).val(null).trigger('change') } catch(e) {} }
                } catch(e) {}

                const updateTaskSelection = function(el) {
                    try {
                        if (hasSelect2 && $(el).data('select2')) {
                            new_attr_task_ids.value = $(el).select2('data').map(item => parseInt(item.id))
                        } else {
                            new_attr_task_ids.value = Array.from(el.selectedOptions || []).map(o => parseInt(o.value))
                        }
                        new_state.value.task_ids = new_attr_task_ids.value.slice()
                    } catch (e) {}
                }

                try { sel.removeEventListener && sel.removeEventListener('change', sel._fi_updateTaskSelection) } catch(e) {}
                sel._fi_updateTaskSelection = function() { updateTaskSelection(this) }
                sel.addEventListener('change', sel._fi_updateTaskSelection)

                if (hasSelect2) {
                    try { if ($(sel).data('select2')) $(sel).select2('destroy') } catch(e) {}
                    $(sel).select2({ theme: 'bootstrap-5', dropdownParent: $('body'), placeholder: 'Select tasks...', allowClear: true })
                    $(sel).on('change.select2', function() { updateTaskSelection(this) })
                }
            } catch(e) {}
        })

        return {
            MISP_ATTRIBUTE_TYPES,
            attrs,
            filtered_attrs,
            grouped_attrs,
            tab_types,
            active_tab_attrs,
            type_options,
            show_add,
            new_state,
            editing_id,
            edit_state,
            search_query,
            type_filter,
            show_unsynced_only,
            is_loading,
            compact_view,
            tab_view,
            active_tab_type,
            visible_column_count,
            can_edit,
            fetch_attrs,
            create_attr,
            reset_add,
            start_edit,
            cancel_edit,
            save_edit,
            delete_attr,
            assigning_attr_id,
            assign_task_state,
            scroll_to_task,
            toggle_assign_tasks,
            save_assign_tasks,
            toggle_compact_view,
            toggle_tab_view,
            tab_count_for
        }
    },

    template: `
    <div>
        <div class="d-flex align-items-center gap-2 mb-3">
            <button v-if="can_edit" class="btn btn-primary btn-sm" @click="show_add = !show_add" title="Add attribute">
                <i class="fa-solid fa-plus me-1"></i>Add attribute
            </button>
            <input v-model="search_query" class="form-control form-control-sm" placeholder="Search value, type, comment..." style="max-width:220px;" />
            <select v-model="type_filter" class="form-select form-select-sm" style="max-width:160px;">
                <option value="">All types</option>
                <option v-for="t in type_options" :key="t" :value="t">[[ t ]]</option>
            </select>
            <button type="button"
                    :class="['btn btn-sm', show_unsynced_only ? 'btn-warning' : 'btn-outline-secondary']"
                    @click="show_unsynced_only = !show_unsynced_only"
                    title="Show only attributes not synced to any MISP instance">
                <i class="fa-solid fa-filter me-1"></i>Unsynced only
            </button>
            <a class="btn btn-outline-primary btn-sm"
               :href="'/analyzer/misp-modules?case_id='+case_id+'&misp_attribute=True'"
               title="Run analyzer modules from standalone attributes">
                <i class="fa-solid fa-puzzle-piece me-1"></i>Analyser
            </a>
            <button type="button" class="btn btn-outline-secondary btn-sm ms-auto" @click="toggle_compact_view()" :title="compact_view ? 'Show all columns' : 'Show compact view'">
                <i :class="compact_view ? 'fa-solid fa-expand' : 'fa-solid fa-compress'"></i>
                <span class="d-none d-sm-inline ms-1">[[ compact_view ? 'Detailed' : 'Compact' ]]</span>
            </button>
            <button type="button" class="btn btn-outline-secondary btn-sm" @click="toggle_tab_view()" :title="tab_view ? 'Switch to table view' : 'Switch to tab view'">
                <i :class="tab_view ? 'fa-solid fa-table-list' : 'fa-solid fa-folder'"></i>
                <span class="d-none d-sm-inline ms-1">[[ tab_view ? 'Table' : 'Tabs' ]]</span>
            </button>
            <button class="btn btn-sm btn-outline-secondary" @click="fetch_attrs()" title="Refresh">
                <i class="fa-solid fa-rotate"></i>
            </button>
        </div>

        <div v-if="show_add && can_edit" class="card mb-3">
            <div class="card-header d-flex justify-content-between align-items-center">
                <span class="fw-bold">New attribute</span>
                <button type="button" class="btn-close" @click="reset_add()" aria-label="Close"></button>
            </div>
            <div class="card-body">
                <div class="row g-2">
                    <div class="col-md-3">
                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Type <span class="text-danger">*</span></label>
                        <select v-model="new_state.type" class="form-select form-select-sm">
                            <option value="">-- select type --</option>
                            <option v-for="t in MISP_ATTRIBUTE_TYPES" :key="t" :value="t">[[ t ]]</option>
                        </select>
                    </div>
                    <div class="col-md-4">
                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Value <span class="text-danger">*</span></label>
                        <input v-model="new_state.value" class="form-control form-control-sm" placeholder="Attribute value" />
                    </div>
                    <div class="col-md-5">
                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Comment</label>
                        <input v-model="new_state.comment" class="form-control form-control-sm" placeholder="Comment" />
                    </div>
                    <div class="col-md-12">
                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Link to tasks (optional)</label>
                        <select id="new-attr-task-select" class="form-select form-select-sm" multiple data-placeholder="Select tasks...">
                            <option v-for="task in (cases_info && cases_info.tasks ? cases_info.tasks : [])" :key="task.id" :value="task.id">[[ task.title ]]</option>
                        </select>
                        <div class="small text-muted mt-1">Select one or more tasks to link this attribute to upon creation.</div>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">First seen</label>
                        <input type="datetime-local" v-model="new_state.first_seen" class="form-control form-control-sm" />
                    </div>
                    <div class="col-md-3">
                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Last seen</label>
                        <input type="datetime-local" v-model="new_state.last_seen" class="form-control form-control-sm" />
                    </div>
                    <div class="col-auto d-flex align-items-end gap-3 pb-1">
                        <div class="form-check">
                            <input type="checkbox" v-model="new_state.ids_flag" class="form-check-input" id="sa-ids-new" />
                            <label class="form-check-label" for="sa-ids-new" style="font-size:0.875rem;">IDS</label>
                        </div>
                        <div class="form-check">
                            <input type="checkbox" v-model="new_state.disable_correlation" class="form-check-input" id="sa-nocorr-new" />
                            <label class="form-check-label" for="sa-nocorr-new" style="font-size:0.875rem;">No correlation</label>
                        </div>
                    </div>
                </div>
                <div class="mt-3 d-flex gap-2">
                    <button class="btn btn-secondary btn-sm" @click="reset_add()">Cancel</button>
                    <button class="btn btn-primary btn-sm" @click="create_attr()">Add</button>
                </div>
            </div>
        </div>

        <div v-if="is_loading" class="text-center py-4">
            <span class="spinner-border spinner-border-sm me-2"></span>Loading...
        </div>

        <div v-else-if="!filtered_attrs.length" class="text-muted small fst-italic py-2">
            <span v-if="attrs.length">No attributes match the filter.</span>
            <span v-else>No standalone attributes yet.</span>
        </div>

        <template v-else-if="!tab_view">
            <div class="card">
                <div class="table-responsive">
                    <table class="table table-sm table-hover align-middle mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="ps-3">Value</th>
                                <th>Type</th>
                                <th v-show="!compact_view" style="width:55px;" title="IDS flag">IDS</th>
                                <th v-show="!compact_view" style="width:75px;" title="Disable correlation">No corr.</th>
                                <th v-show="!compact_view">Comment</th>
                                <th v-show="!compact_view">Correlations</th>
                                <th v-show="!compact_view">Synced</th>
                                <th>Tasks</th>
                                <th v-if="can_edit" style="width:110px;"></th>
                            </tr>
                        </thead>
                        <tbody>
                            <template v-for="sa in filtered_attrs" :key="sa.id">
                                <tr v-if="editing_id !== sa.id">
                                    <td class="ps-3" style="font-size:0.825rem; word-break:break-all; max-width:280px;">[[ sa.value ]]</td>
                                    <td><span class="badge bg-light text-dark border">[[ sa.type ]]</span></td>
                                    <td v-show="!compact_view" style="text-align:center;">
                                        <i v-if="sa.ids_flag" class="fa-solid fa-check text-success fa-sm"></i>
                                        <span v-else class="text-muted">-</span>
                                    </td>
                                    <td v-show="!compact_view" style="text-align:center;">
                                        <i v-if="sa.disable_correlation" class="fa-solid fa-link-slash text-muted fa-sm" title="Correlation disabled"></i>
                                        <span v-else class="text-muted">-</span>
                                    </td>
                                    <td v-show="!compact_view" class="small text-muted">
                                        <template v-if="sa.comment">[[ sa.comment ]]</template>
                                        <span v-else>-</span>
                                    </td>
                                    <td v-show="!compact_view" class="small">
                                        <template v-if="sa.correlation_list && sa.correlation_list.length">
                                            <template v-for="(cid, idx) in sa.correlation_list" :key="cid + '-' + idx">
                                                <template v-if="idx < 4">
                                                    <a :href="'/case/'+cid" class="badge bg-light text-dark me-1" target="_blank">Case [[ cid ]]</a>
                                                </template>
                                            </template>
                                            <button v-if="sa.correlation_list.length > 4" class="btn btn-link p-0 ms-1 small" type="button"
                                                    data-bs-toggle="collapse" :data-bs-target="'#attr-corr-'+sa.id" aria-expanded="false">
                                                [[ sa.correlation_list.length - 4 ]] more
                                            </button>
                                            <div class="collapse mt-1" :id="'attr-corr-'+sa.id">
                                                <template v-for="(cid, idx) in sa.correlation_list" :key="'more-'+cid+'-'+idx">
                                                    <template v-if="idx >= 4">
                                                        <a :href="'/case/'+cid" class="badge bg-light text-dark me-1" target="_blank">Case [[ cid ]]</a>
                                                    </template>
                                                </template>
                                            </div>
                                        </template>
                                        <span v-else class="text-muted">-</span>
                                    </td>
                                    <td v-show="!compact_view" class="small">
                                        <span v-for="s in sa.synced_instances" :key="s.instance_id" class="badge bg-info text-dark me-1" :title="'UUID: ' + s.uuid">
                                            <i class="fa-solid fa-link me-1 fa-sm"></i>#[[ s.instance_id ]]
                                        </span>
                                        <span v-if="!sa.synced_instances || !sa.synced_instances.length" class="text-muted">-</span>
                                    </td>
                                    <td class="small">
                                        <template v-if="sa.tasks && sa.tasks.length">
                                            <span v-for="task in sa.tasks" :key="'sa-task-'+sa.id+'-'+task.id"
                                                  class="badge bg-secondary me-1"
                                                  style="cursor:pointer;"
                                                  :title="'Go to task: ' + task.title"
                                                  @click="scroll_to_task(task.id)">
                                                <i class="fa-solid fa-list-check me-1 fa-sm"></i>[[ task.title ]]
                                            </span>
                                        </template>
                                        <span v-else class="text-muted">-</span>
                                    </td>
                                    <td v-if="can_edit" class="text-end pe-2" style="white-space:nowrap;">
                                        <button class="btn btn-link btn-sm p-0 me-2 text-secondary" title="Assign tasks" @click="toggle_assign_tasks(sa)">
                                            <i class="fa-solid fa-tasks fa-sm"></i>
                                        </button>
                                        <button class="btn btn-link btn-sm p-0 me-2 text-primary" title="Edit" @click="start_edit(sa)">
                                            <i class="fa-solid fa-pen-to-square fa-sm"></i>
                                        </button>
                                        <button class="btn btn-link btn-sm p-0 text-danger" title="Delete" @click="delete_attr(sa.id)">
                                            <i class="fa-solid fa-trash fa-sm"></i>
                                        </button>
                                    </td>
                                </tr>

                                <tr v-if="editing_id !== sa.id && can_edit && assigning_attr_id === sa.id">
                                    <td :colspan="visible_column_count" class="p-3 bg-light border-top-0">
                                        <div v-if="cases_info && cases_info.tasks && cases_info.tasks.length">
                                            <div class="d-flex flex-wrap gap-3 mb-2">
                                                <div v-for="task in cases_info.tasks" :key="'assign-sa-'+sa.id+'-'+task.id" class="form-check form-check-inline m-0">
                                                    <input class="form-check-input" type="checkbox"
                                                           :id="'assign-sa-'+sa.id+'-'+task.id"
                                                           :value="task.id"
                                                           v-model="assign_task_state[sa.id]">
                                                    <label class="form-check-label small" :for="'assign-sa-'+sa.id+'-'+task.id">[[ task.title ]]</label>
                                                </div>
                                            </div>
                                            <button class="btn btn-primary btn-sm" @click="save_assign_tasks(sa.id)">Save</button>
                                            <button class="btn btn-secondary btn-sm ms-1" @click="assigning_attr_id = null">Cancel</button>
                                        </div>
                                        <div v-else class="text-muted small">No tasks available in this case.</div>
                                    </td>
                                </tr>

                                <tr v-if="editing_id === sa.id">
                                    <td :colspan="visible_column_count" class="p-3 bg-light">
                                        <div class="row g-2 mb-2">
                                            <div class="col-md-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Type</label>
                                                <select v-model="edit_state.type" class="form-select form-select-sm">
                                                    <option v-for="t in MISP_ATTRIBUTE_TYPES" :key="t" :value="t">[[ t ]]</option>
                                                </select>
                                            </div>
                                            <div class="col-md-5">
                                                <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Value</label>
                                                <input v-model="edit_state.value" class="form-control form-control-sm" />
                                            </div>
                                            <div class="col-md-4">
                                                <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Comment</label>
                                                <input v-model="edit_state.comment" class="form-control form-control-sm" />
                                            </div>
                                        </div>
                                        <div class="row g-2 mb-3">
                                            <div class="col-md-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">First seen</label>
                                                <input type="datetime-local" v-model="edit_state.first_seen" class="form-control form-control-sm" />
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Last seen</label>
                                                <input type="datetime-local" v-model="edit_state.last_seen" class="form-control form-control-sm" />
                                            </div>
                                            <div class="col-md-2 d-flex align-items-end">
                                                <div class="form-check">
                                                    <input type="checkbox" v-model="edit_state.ids_flag" class="form-check-input" :id="'sa-edit-ids-'+sa.id" />
                                                    <label class="form-check-label" :for="'sa-edit-ids-'+sa.id" style="font-size:0.875rem;">IDS</label>
                                                </div>
                                            </div>
                                            <div class="col-md-3 d-flex align-items-end">
                                                <div class="form-check">
                                                    <input type="checkbox" v-model="edit_state.disable_correlation" class="form-check-input" :id="'sa-edit-corr-'+sa.id" />
                                                    <label class="form-check-label" :for="'sa-edit-corr-'+sa.id" style="font-size:0.875rem;">No correlation</label>
                                                </div>
                                            </div>
                                        </div>
                                        <div class="d-flex gap-2">
                                            <button class="btn btn-sm btn-secondary" @click="cancel_edit()">Cancel</button>
                                            <button class="btn btn-sm btn-primary" @click="save_edit(sa.id)">Save</button>
                                        </div>
                                    </td>
                                </tr>
                            </template>
                        </tbody>
                    </table>
                </div>
            </div>
        </template>

        <template v-else>
            <div v-if="!tab_types.length" class="text-muted p-2"><i>No attributes match the current filter.</i></div>
            <template v-else>
                <ul class="nav nav-tabs mb-0" style="flex-wrap: wrap;">
                    <li v-for="t in tab_types" :key="'tab-'+t" class="nav-item flex-shrink-0">
                        <button class="nav-link py-1 px-3" :class="{active: active_tab_type === t}" @click="active_tab_type = t" type="button">
                            [[ t ]]
                            <span class="badge text-bg-secondary ms-1">[[ tab_count_for(t) ]]</span>
                        </button>
                    </li>
                </ul>
                <div class="tab-content border border-top-0 rounded-bottom">
                    <div class="tab-pane active show">
                        <div class="table-responsive">
                            <table class="table table-sm table-hover align-middle mb-0">
                                <thead class="table-light">
                                    <tr>
                                        <th class="ps-3">Value</th>
                                        <th>Type</th>
                                        <th v-show="!compact_view" style="width:55px;" title="IDS flag">IDS</th>
                                        <th v-show="!compact_view" style="width:75px;" title="Disable correlation">No corr.</th>
                                        <th v-show="!compact_view">Comment</th>
                                        <th v-show="!compact_view">Correlations</th>
                                        <th v-show="!compact_view">Synced</th>
                                        <th>Tasks</th>
                                        <th v-if="can_edit" style="width:110px;"></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <template v-for="sa in active_tab_attrs" :key="'tab-row-'+sa.id">
                                        <tr v-if="editing_id !== sa.id">
                                            <td class="ps-3" style="font-size:0.825rem; word-break:break-all; max-width:280px;">[[ sa.value ]]</td>
                                            <td><span class="badge bg-light text-dark border">[[ sa.type ]]</span></td>
                                            <td v-show="!compact_view" style="text-align:center;">
                                                <i v-if="sa.ids_flag" class="fa-solid fa-check text-success fa-sm"></i>
                                                <span v-else class="text-muted">-</span>
                                            </td>
                                            <td v-show="!compact_view" style="text-align:center;">
                                                <i v-if="sa.disable_correlation" class="fa-solid fa-link-slash text-muted fa-sm" title="Correlation disabled"></i>
                                                <span v-else class="text-muted">-</span>
                                            </td>
                                            <td v-show="!compact_view" class="small text-muted">
                                                <template v-if="sa.comment">[[ sa.comment ]]</template>
                                                <span v-else>-</span>
                                            </td>
                                            <td v-show="!compact_view" class="small">
                                                <template v-if="sa.correlation_list && sa.correlation_list.length">
                                                    <template v-for="(cid, idx) in sa.correlation_list" :key="'tab-'+cid+'-'+idx">
                                                        <template v-if="idx < 4">
                                                            <a :href="'/case/'+cid" class="badge bg-light text-dark me-1" target="_blank">Case [[ cid ]]</a>
                                                        </template>
                                                    </template>
                                                    <button v-if="sa.correlation_list.length > 4" class="btn btn-link p-0 ms-1 small" type="button"
                                                            data-bs-toggle="collapse" :data-bs-target="'#attr-tab-corr-'+sa.id" aria-expanded="false">
                                                        [[ sa.correlation_list.length - 4 ]] more
                                                    </button>
                                                    <div class="collapse mt-1" :id="'attr-tab-corr-'+sa.id">
                                                        <template v-for="(cid, idx) in sa.correlation_list" :key="'tab-more-'+cid+'-'+idx">
                                                            <template v-if="idx >= 4">
                                                                <a :href="'/case/'+cid" class="badge bg-light text-dark me-1" target="_blank">Case [[ cid ]]</a>
                                                            </template>
                                                        </template>
                                                    </div>
                                                </template>
                                                <span v-else class="text-muted">-</span>
                                            </td>
                                            <td v-show="!compact_view" class="small">
                                                <span v-for="s in sa.synced_instances" :key="'tab-sync-'+s.instance_id" class="badge bg-info text-dark me-1" :title="'UUID: ' + s.uuid">
                                                    <i class="fa-solid fa-link me-1 fa-sm"></i>#[[ s.instance_id ]]
                                                </span>
                                                <span v-if="!sa.synced_instances || !sa.synced_instances.length" class="text-muted">-</span>
                                            </td>
                                            <td class="small">
                                                <template v-if="sa.tasks && sa.tasks.length">
                                                    <span v-for="task in sa.tasks" :key="'tab-sa-task-'+sa.id+'-'+task.id"
                                                          class="badge bg-secondary me-1"
                                                          style="cursor:pointer;"
                                                          :title="'Go to task: ' + task.title"
                                                          @click="scroll_to_task(task.id)">
                                                        <i class="fa-solid fa-list-check me-1 fa-sm"></i>[[ task.title ]]
                                                    </span>
                                                </template>
                                                <span v-else class="text-muted">-</span>
                                            </td>
                                            <td v-if="can_edit" class="text-end pe-2" style="white-space:nowrap;">
                                                <button class="btn btn-link btn-sm p-0 me-2 text-secondary" title="Assign tasks" @click="toggle_assign_tasks(sa)">
                                                    <i class="fa-solid fa-tasks fa-sm"></i>
                                                </button>
                                                <button class="btn btn-link btn-sm p-0 me-2 text-primary" title="Edit" @click="start_edit(sa)">
                                                    <i class="fa-solid fa-pen-to-square fa-sm"></i>
                                                </button>
                                                <button class="btn btn-link btn-sm p-0 text-danger" title="Delete" @click="delete_attr(sa.id)">
                                                    <i class="fa-solid fa-trash fa-sm"></i>
                                                </button>
                                            </td>
                                        </tr>

                                        <tr v-if="editing_id !== sa.id && can_edit && assigning_attr_id === sa.id">
                                            <td :colspan="visible_column_count" class="p-3 bg-light border-top-0">
                                                <div v-if="cases_info && cases_info.tasks && cases_info.tasks.length">
                                                    <div class="d-flex flex-wrap gap-3 mb-2">
                                                        <div v-for="task in cases_info.tasks" :key="'assign-tab-sa-'+sa.id+'-'+task.id" class="form-check form-check-inline m-0">
                                                            <input class="form-check-input" type="checkbox"
                                                                   :id="'assign-tab-sa-'+sa.id+'-'+task.id"
                                                                   :value="task.id"
                                                                   v-model="assign_task_state[sa.id]">
                                                            <label class="form-check-label small" :for="'assign-tab-sa-'+sa.id+'-'+task.id">[[ task.title ]]</label>
                                                        </div>
                                                    </div>
                                                    <button class="btn btn-primary btn-sm" @click="save_assign_tasks(sa.id)">Save</button>
                                                    <button class="btn btn-secondary btn-sm ms-1" @click="assigning_attr_id = null">Cancel</button>
                                                </div>
                                                <div v-else class="text-muted small">No tasks available in this case.</div>
                                            </td>
                                        </tr>

                                        <tr v-if="editing_id === sa.id">
                                            <td :colspan="visible_column_count" class="p-3 bg-light">
                                                <div class="row g-2 mb-2">
                                                    <div class="col-md-3">
                                                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Type</label>
                                                        <select v-model="edit_state.type" class="form-select form-select-sm">
                                                            <option v-for="t in MISP_ATTRIBUTE_TYPES" :key="t" :value="t">[[ t ]]</option>
                                                        </select>
                                                    </div>
                                                    <div class="col-md-5">
                                                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Value</label>
                                                        <input v-model="edit_state.value" class="form-control form-control-sm" />
                                                    </div>
                                                    <div class="col-md-4">
                                                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Comment</label>
                                                        <input v-model="edit_state.comment" class="form-control form-control-sm" />
                                                    </div>
                                                </div>
                                                <div class="row g-2 mb-3">
                                                    <div class="col-md-3">
                                                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">First seen</label>
                                                        <input type="datetime-local" v-model="edit_state.first_seen" class="form-control form-control-sm" />
                                                    </div>
                                                    <div class="col-md-3">
                                                        <label class="form-label fw-semibold mb-1" style="font-size:0.875rem;">Last seen</label>
                                                        <input type="datetime-local" v-model="edit_state.last_seen" class="form-control form-control-sm" />
                                                    </div>
                                                    <div class="col-md-2 d-flex align-items-end">
                                                        <div class="form-check">
                                                            <input type="checkbox" v-model="edit_state.ids_flag" class="form-check-input" :id="'sa-edit-tab-ids-'+sa.id" />
                                                            <label class="form-check-label" :for="'sa-edit-tab-ids-'+sa.id" style="font-size:0.875rem;">IDS</label>
                                                        </div>
                                                    </div>
                                                    <div class="col-md-3 d-flex align-items-end">
                                                        <div class="form-check">
                                                            <input type="checkbox" v-model="edit_state.disable_correlation" class="form-check-input" :id="'sa-edit-tab-corr-'+sa.id" />
                                                            <label class="form-check-label" :for="'sa-edit-tab-corr-'+sa.id" style="font-size:0.875rem;">No correlation</label>
                                                        </div>
                                                    </div>
                                                </div>
                                                <div class="d-flex gap-2">
                                                    <button class="btn btn-sm btn-secondary" @click="cancel_edit()">Cancel</button>
                                                    <button class="btn btn-sm btn-primary" @click="save_edit(sa.id)">Save</button>
                                                </div>
                                            </td>
                                        </tr>
                                    </template>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </template>
        </template>
    </div>
    `
}
