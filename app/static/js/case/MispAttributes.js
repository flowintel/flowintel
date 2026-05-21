import { display_toast, create_message } from '../toaster.js'
const { ref, computed, onMounted } = Vue

const MISP_ATTRIBUTE_TYPES = ref([])

async function fetch_attr_types() {
    try {
        const res = await fetch(`/case/get_misp_attribute_types`)
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
    emits: ['attr_count'],
    setup(props, { emit }) {
        const attrs = ref([])
        const show_add = ref(false)
        const new_state = ref({ type: '', value: '', comment: '', ids_flag: false, disable_correlation: false, first_seen: '', last_seen: '' })
        const editing_id = ref(null)
        const edit_state = ref({})
        const search_query = ref('')
        const type_filter = ref('')
        const is_loading = ref(false)

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
            if (q) list = list.filter(a => String(a.value).toLowerCase().includes(q) || a.type.toLowerCase().includes(q) || (a.comment || '').toLowerCase().includes(q))
            if (t) list = list.filter(a => a.type === t)
            return list
        })

        const type_options = computed(() => (MISP_ATTRIBUTE_TYPES.value || []).slice().sort())

        async function fetch_attrs() {
            is_loading.value = true
            try {
                const res = await fetch(`/case/${props.case_id}/get_case_misp_attributes`)
                if (res.status === 200) {
                    const loc = await res.json()
                    attrs.value = loc['attributes'] || []
                    emit('attr_count', attrs.value.length)
                } else {
                    display_toast(res)
                }
            } finally {
                is_loading.value = false
            }
        }

        function reset_add() {
            new_state.value = { type: '', value: '', comment: '', ids_flag: false, disable_correlation: false, first_seen: '', last_seen: '' }
            show_add.value = false
        }

        async function create_attr() {
            if (!new_state.value.type) { create_message("Select a type", "warning-subtle"); return }
            if (!new_state.value.value) { create_message("Enter a value", "warning-subtle"); return }
            const res = await fetch(`/case/${props.case_id}/create_misp_attribute`, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify(new_state.value)
            })
            if (res.status === 201) {
                await fetch_attrs()
                reset_add()
            }
            display_toast(res)
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
            if (!edit_state.value.value) { create_message("Enter a value", "warning-subtle"); return }
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
            const res = await fetch(`/case/${props.case_id}/misp_attribute/${aid}/delete_misp_attribute`)
            if (res.status === 200) {
                attrs.value = attrs.value.filter(a => a.id !== aid)
                emit('attr_count', attrs.value.length)
            }
            display_toast(res)
        }

        onMounted(async () => {
            await fetch_attr_types()
            await fetch_attrs()
        })

        return {
            MISP_ATTRIBUTE_TYPES,
            attrs, filtered_attrs, type_options,
            show_add, new_state, editing_id, edit_state,
            search_query, type_filter, is_loading,
            can_edit,
            fetch_attrs, create_attr, reset_add,
            start_edit, cancel_edit, save_edit, delete_attr
        }
    },

    template: `
    <div>
        <!-- Toolbar -->
        <div class="d-flex align-items-center gap-2 mb-3">
            <button v-if="can_edit" class="btn btn-primary btn-sm" @click="show_add = !show_add" title="Add attribute">
                <i class="fa-solid fa-plus me-1"></i>Add attribute
            </button>
            <input v-model="search_query" class="form-control form-control-sm" placeholder="Search value, type, comment…" style="max-width:220px;" />
            <select v-model="type_filter" class="form-select form-select-sm" style="max-width:160px;">
                <option value="">All types</option>
                <option v-for="t in type_options" :key="t" :value="t">[[ t ]]</option>
            </select>
            <button class="btn btn-sm btn-outline-secondary ms-auto" @click="fetch_attrs()" title="Refresh">
                <i class="fa-solid fa-rotate"></i>
            </button>
        </div>

        <!-- Add form -->
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

        <!-- Loading -->
        <div v-if="is_loading" class="text-center py-4">
            <span class="spinner-border spinner-border-sm me-2"></span>Loading…
        </div>

        <!-- Empty state -->
        <div v-else-if="!filtered_attrs.length" class="text-muted small fst-italic py-2">
            <span v-if="attrs.length">No attributes match the filter.</span>
            <span v-else>No standalone attributes yet.</span>
        </div>

        <!-- Table -->
        <div v-else class="table-responsive">
            <table class="table table-sm table-hover align-middle mb-0">
                <thead class="table-light">
                    <tr>
                        <th style="font-size:0.8rem; width:130px;">Type</th>
                        <th style="font-size:0.8rem;">Value</th>
                        <th style="font-size:0.8rem; width:180px;">Comment</th>
                        <th style="font-size:0.8rem; width:55px;" title="IDS flag">IDS</th>
                        <th style="font-size:0.8rem; width:65px;" title="Disable correlation">No corr.</th>
                        <th style="font-size:0.8rem;">Correlations</th>
                        <th style="font-size:0.8rem;">Synced</th>
                        <th v-if="can_edit" style="width:80px;"></th>
                    </tr>
                </thead>
                <tbody>
                    <template v-for="sa in filtered_attrs" :key="sa.id">

                        <!-- ── View row ── -->
                        <tr v-if="editing_id !== sa.id">
                            <td style="font-size:0.825rem;">
                                <span class="badge bg-secondary">[[ sa.type ]]</span>
                            </td>
                            <td style="font-size:0.825rem; word-break:break-all; max-width:260px;">[[ sa.value ]]</td>
                            <td style="font-size:0.825rem;">[[ sa.comment || '' ]]</td>
                            <td style="font-size:0.825rem; text-align:center;">
                                <i v-if="sa.ids_flag" class="fa-solid fa-check text-success"></i>
                                <i v-else class="fa-solid fa-xmark text-muted"></i>
                            </td>
                            <td style="font-size:0.825rem; text-align:center;">
                                <i v-if="sa.disable_correlation" class="fa-solid fa-check text-warning"></i>
                                <i v-else class="fa-solid fa-xmark text-muted"></i>
                            </td>
                            <td style="font-size:0.825rem;">
                                <a v-for="cid in sa.correlation_list" :key="cid"
                                   :href="'/case/'+cid" class="badge bg-info text-dark me-1" target="_blank">#[[ cid ]]</a>
                                <span v-if="!sa.correlation_list || !sa.correlation_list.length" class="text-muted">—</span>
                            </td>
                            <td style="font-size:0.825rem;">
                                <span v-for="s in sa.synced_instances" :key="s.instance_id"
                                      class="badge bg-success me-1" :title="'UUID: '+s.uuid">
                                    <i class="fa-solid fa-link me-1"></i>#[[ s.instance_id ]]
                                </span>
                                <span v-if="!sa.synced_instances || !sa.synced_instances.length" class="text-muted">—</span>
                            </td>
                            <td v-if="can_edit" class="text-end">
                                <button class="btn btn-sm btn-outline-secondary me-1" title="Edit" @click="start_edit(sa)">
                                    <i class="fa-solid fa-pen"></i>
                                </button>
                                <button class="btn btn-sm btn-outline-danger" title="Delete" @click="delete_attr(sa.id)">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </td>
                        </tr>

                        <!-- ── Edit row ── -->
                        <tr v-else class="table-warning">
                            <td>
                                <select v-model="edit_state.type" class="form-select form-select-sm">
                                    <option v-for="t in MISP_ATTRIBUTE_TYPES" :key="t" :value="t">[[ t ]]</option>
                                </select>
                            </td>
                            <td>
                                <input v-model="edit_state.value" class="form-control form-control-sm" />
                            </td>
                            <td>
                                <input v-model="edit_state.comment" class="form-control form-control-sm" />
                            </td>
                            <td style="text-align:center;">
                                <input type="checkbox" v-model="edit_state.ids_flag" class="form-check-input" />
                            </td>
                            <td style="text-align:center;">
                                <input type="checkbox" v-model="edit_state.disable_correlation" class="form-check-input" />
                            </td>
                            <td colspan="2">
                                <div class="d-flex gap-2">
                                    <input type="datetime-local" v-model="edit_state.first_seen" class="form-control form-control-sm"
                                           placeholder="First seen" style="max-width:170px;" />
                                    <input type="datetime-local" v-model="edit_state.last_seen" class="form-control form-control-sm"
                                           placeholder="Last seen" style="max-width:170px;" />
                                </div>
                            </td>
                            <td v-if="can_edit" class="text-end">
                                <button class="btn btn-sm btn-secondary me-1" @click="cancel_edit()">Cancel</button>
                                <button class="btn btn-sm btn-primary" @click="save_edit(sa.id)">Save</button>
                            </td>
                        </tr>

                    </template>
                </tbody>
            </table>
        </div>
    </div>
    `
}
