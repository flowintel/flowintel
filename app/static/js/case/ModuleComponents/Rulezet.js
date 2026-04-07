import { display_toast } from '../../toaster.js'
const { ref, onMounted } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        cases_info: Object,
        connector_instances: Array,
        connector_type: String
    },
    setup(props) {
        const selected_instance = ref(props.connector_instances && props.connector_instances.length ? props.connector_instances[0] : null)
        const query_input = ref('')
        const is_loading = ref(false)
        const results = ref([])
        const modules = ref({})
        const module_selected = ref('None')

        onMounted(async () => {
            // fetch available modules for this case to populate the selector
            const res = await fetch(`/case/get_case_modules`)
            if (res.status === 200) {
                const data = await res.json()
                modules.value = data.modules || {}
            }
            // load existing rules for selected instance
            fetch_rules()
        })

        async function fetch_rules() {
            if (!selected_instance.value) return
            const url = `/case/${props.case_id}/rulezet_rules?instance_id=${selected_instance.value.details.id}`
            const r = await fetch(url)
            if (r.status === 200) {
                const d = await r.json()
                results.value = d.rules || []
            }
        }

        async function run_query() {
            if (!selected_instance.value) return display_toast({message: 'No connector instance selected', toast_class: 'warning-subtle'})
            if (!query_input.value || query_input.value.trim().length === 0) return display_toast({message: 'Please enter a query', toast_class: 'warning-subtle'})

            is_loading.value = true
            results.value = []
            try {
                if (!module_selected.value || module_selected.value === 'None') return display_toast({message: 'Select a module', toast_class: 'warning-subtle'})
                const url = `/case/${props.case_id}/call_module_case`
                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': $('#csrf_token').val() },
                    body: JSON.stringify({ module: module_selected.value, case_task_instance_id: selected_instance.value.case_task_instance_id, query: query_input.value })
                })

                if (res.status === 200) {
                    // Module ran successfully; fetch stored rules from DB
                    await fetch_rules()
                    display_toast({message: 'Rule fetched and stored', toast_class: 'success-subtle'})
                } else {
                    display_toast(res)
                }
            } catch (e) {
                display_toast({message: 'Request failed', toast_class: 'danger-subtle'})
            }
            is_loading.value = false
        }

        function select_instance(ev) {
            const iid = parseInt(ev.target.value)
            const found = props.connector_instances.find(c => c.details.id === iid)
            if (found) selected_instance.value = found
        }

        function getOriginalUrl(r) {
            try {
                const remote = r.remote_id || r.id || r.uuid
                if (!remote) return '#'
                // try to find instance by id
                let inst = null
                if (r.instance_id) {
                    inst = props.connector_instances.find(c => c.details.id === parseInt(r.instance_id))
                }
                if (!inst && selected_instance.value) inst = selected_instance.value
                if (!inst) return '#'
                const base = inst.details.url || inst.details.instance_url || ''
                if (!base) return '#'
                const sep = base.endsWith('/') ? '' : '/'
                return base + sep + 'rule/detail_rule/' + encodeURIComponent(remote)
            } catch (e) {
                return '#'
            }
        }

        return {
            selected_instance,
            query_input,
            is_loading,
            results,
            run_query,
            select_instance,
            getOriginalUrl,
            modules,
            module_selected
        }
    },
    template: `
        <div class="case-core-style p-3">
            <div class="row mb-2">
                <div class="col-md-4">
                    <label class="form-label">Connector instance</label>
                    <select class="form-select" @change="select_instance($event)">
                        <option v-for="inst in connector_instances" :key="inst.case_task_instance_id" :value="inst.details.id">[[ inst.details.name ]] ([[ inst.details.url ]])</option>
                    </select>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Module</label>
                    <select class="form-select" v-model="module_selected">
                        <option value="None">--</option>
                        <template v-for="(m, key) in modules">
                            <option v-if="m.config && m.config.connector == 'rulezet'" :value="key">[[ key ]]</option>
                        </template>
                    </select>
                    <div class="case-core-style mt-2" v-if="module_selected && module_selected != 'None'">
                        <small class="text-muted">[[ modules[module_selected]?.config?.description ]]</small>
                    </div>
                </div>
            </div>
            <div class="row mb-3">
                <div class="col-md-6">
                    <label class="form-label">Query (IP / input)</label>
                    <input class="form-control" v-model="query_input" placeholder="Enter IP or query" />
                </div>
                <div class="col-md-2 d-flex align-items-end">
                    <button class="btn btn-primary w-100" @click="run_query()" :disabled="is_loading">
                        <span v-if="is_loading" class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>
                        <span v-if="!is_loading">Query</span>
                        <span v-else>Searching...</span>
                    </button>
                </div>
            </div>

            <div v-if="results && results.length">
                <h6>Results ([[ results.length ]])</h6>
                <div class="list-group">
                    <div v-for="(r, idx) in results" :key="idx" class="list-group-item">
                        <div class="d-flex w-100 justify-content-between align-items-center">
                            <h5 class="mb-1">
                                <a :href="getOriginalUrl(r)" target="_blank" rel="noopener">
                                    [[ r.title || r.name || r.id || 'Result ' + (idx+1) ]]
                                </a>
                            </h5>
                            <button class="btn btn-sm btn-outline-secondary" type="button" :data-bs-toggle="'collapse'" :data-bs-target="'#rule-' + idx" aria-expanded="true" :aria-controls="'rule-' + idx">
                                Toggle
                            </button>
                        </div>

                        <div :id="'rule-' + idx" class="collapse show mt-2">
                            <div class="mb-1">
                                <strong>Description: </strong> 
                                <span class="text-muted">[[ r.description || r.desc || '' ]]</span>
                            </div>
                            <div class="mb-1">
                                <strong>Format:</strong> <span class="text-muted">[[ r.format || '' ]]</span>
                            </div>
                            <div class="mb-1">
                                <strong>Date:</strong> <span class="text-muted">[[ r.date_added || r.date || '' ]]</span>
                            </div>
                            <div class="mb-1">
                                <strong>Version:</strong> <span class="text-muted">[[ r.version || '' ]]</span>
                            </div>
                            <div class="mt-2">
                                <strong>Content:</strong>
                                <pre class="p-2 bg-light" style="white-space: pre-wrap">[[ r.content || r.to_string || JSON.stringify(r, null, 2) ]]</pre>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div v-else class="text-muted">No results yet.</div>
        </div>
    `
}
