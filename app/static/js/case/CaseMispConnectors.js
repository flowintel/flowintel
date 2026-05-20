import { display_toast } from '../toaster.js'
import MispSyncPanel from './MispSyncPanel.js'
const { ref, reactive, computed, nextTick, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: {
        case_task_connectors_list: Object,
        modules: Object,
        is_case: Boolean,
        object_id: Number,
        cases_info: Object,
        mode: { type: String, required: true },   // 'sync' | 'search'
        case_misp_objects_list: { type: Array, default: null }
    },
    emits: ['case_connectors', 'task_connectors', 'note_change', 'task_note_added'],
    components: { 'misp-sync-panel': MispSyncPanel },
    setup(props, { emit }) {
        const sidebar_visible = ref(true)

        // Sync state
        const sync_panel_ref = ref(null)
        const sync_direction = ref('send')
        const sync_instance_idx = ref(0)
        const sync_selected_instance = computed(() => {
            if (!props.case_task_connectors_list || !props.case_task_connectors_list.length) return null
            return props.case_task_connectors_list[Math.min(sync_instance_idx.value, props.case_task_connectors_list.length - 1)]
        })

        // Search state
        const search_instance_idx = ref(0)
        const search_selected_instance = computed(() => {
            if (!props.case_task_connectors_list || !props.case_task_connectors_list.length) return null
            return props.case_task_connectors_list[Math.min(search_instance_idx.value, props.case_task_connectors_list.length - 1)]
        })

        const misp_search_state = reactive({})

        function set_sync_direction(dir) {
            sync_direction.value = dir
        }

        function get_misp_search(instance_id) {
            if (!misp_search_state[instance_id]) {
                misp_search_state[instance_id] = {
                    query: '',
                    loading: false,
                    has_searched: false,
                    results: [],
                    appending: false
                }
            }
            return misp_search_state[instance_id]
        }

        function build_search_url(instance) {
            if (props.is_case) {
                return "/case/" + props.object_id + "/connectors/" + instance.case_task_instance_id + "/search_in_misp"
            }
            return "/case/task/" + props.object_id + "/connectors/" + instance.case_task_instance_id + "/search_in_misp"
        }

        function build_add_note_url() {
            if (props.is_case) {
                return "/case/" + props.object_id + "/append_note_case"
            }
            return "/case/" + props.cases_info.case.id + "/modif_note/" + props.object_id + "?note_id=-1"
        }

        async function submit_misp_search(instance) {
            const state = get_misp_search(instance.case_task_instance_id)
            const query = (state.query || '').trim()
            if (!query) return
            state.loading = true
            state.has_searched = true
            const res = await fetch(build_search_url(instance), {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(),
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ "query": query })
            })
            state.loading = false
            if (res.status == 200) {
                const loc = await res.json()
                state.results = loc.results || []
            } else {
                state.results = []
                display_toast(res)
            }
        }

        function format_search_results_as_note(instance, state) {
            const cell = (v) => (v === null || v === undefined || v === '') ? '' : String(v).replace(/\|/g, '\\|').replace(/\n/g, ' ')
            const lines = [
                `## MISP search on ${instance.details.name} - "${state.query || ''}"`,
                '',
                '| Event ID | Published | Organisation | Event title | Date | Type | Category | Value | IDS | Comment | Tags |',
                '| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |'
            ]
            for (const r of state.results) {
                lines.push(`| ${cell(r.event_id)} | ${r.event_published ? 'yes' : 'no'} | ${cell(r.organisation)} | ${cell(r.event_info)} | ${cell(r.date)} | ${cell(r.attribute_type)} | ${cell(r.attribute_category)} | ${cell(r.attribute_value)} | ${r.to_ids ? 'yes' : 'no'} | ${cell(r.comment)} | ${cell((r.tags || []).join(', '))} |`)
            }
            return '\n\n' + lines.join('\n') + '\n'
        }

        async function add_results_to_note(instance) {
            const state = get_misp_search(instance.case_task_instance_id)
            if (!state.results || !state.results.length) return
            state.appending = true
            const res = await fetch(build_add_note_url(), {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(),
                    "Content-Type": "application/json"
                },
                body: JSON.stringify({ "notes": format_search_results_as_note(instance, state) })
            })
            state.appending = false
            if (res.status == 200) {
                const loc = await res.clone().json()
                if (props.is_case && loc.notes !== undefined) {
                    emit('note_change', loc.notes)
                } else if (!props.is_case && loc.note) {
                    emit('task_note_added', loc.note)
                    document.getElementById('tab-task-notes-' + props.object_id)?.click()
                }
            }
            display_toast(res)
        }

        function on_sync_done({ direction, instance }) {
            if (props.is_case) {
                emit("case_connectors", true)
            } else {
                emit("task_connectors", true)
            }
        }

        // Auto-init MispSyncPanel when instance or direction changes
        watch([sync_selected_instance, sync_direction], async ([inst]) => {
            if (props.mode !== 'sync' || !inst) return
            await nextTick()
            sync_panel_ref.value?.on_show()
        }, { immediate: true })

        return {
            sidebar_visible,
            sync_panel_ref,
            sync_direction,
            sync_instance_idx,
            sync_selected_instance,
            search_instance_idx,
            search_selected_instance,
            set_sync_direction,
            get_misp_search,
            submit_misp_search,
            add_results_to_note,
            on_sync_done
        }
    },
    template: `
        <!-- MODE: sync (Send & Receive) -->
        <template v-if="mode === 'sync'">
            <div v-if="!case_task_connectors_list || !case_task_connectors_list.length" class="text-muted py-3">
                <i class="fa-solid fa-circle-info me-2"></i>No MISP connector linked to this case yet.
            </div>
            <template v-else>
                <div class="d-flex gap-3">
                    <!-- Left: instance list (collapsible) -->
                    <div v-show="sidebar_visible" class="border-end pe-3" style="min-width:180px; max-width:220px; flex-shrink:0;">
                        <div v-for="(inst, i) in case_task_connectors_list" :key="inst.case_task_instance_id"
                            :class="['d-flex align-items-center gap-2 p-2 rounded mb-1', sync_instance_idx === i ? 'bg-primary bg-opacity-10 text-primary fw-semibold' : 'text-muted']"
                            style="cursor:pointer;"
                            @click="sync_instance_idx = i">
                            <img :src="'/static/icons/'+inst.details.icon" style="max-width:20px; flex-shrink:0;">
                            <span class="text-truncate small">[[ inst.details.name ]]</span>
                        </div>
                    </div>
                    <!-- Right: content -->
                    <div class="flex-grow-1" style="min-width:0;">
                        <template v-if="sync_selected_instance">
                            <div class="d-flex align-items-start gap-2 mb-3 p-2 rounded" style="background:var(--bs-primary-bg-subtle);">
                                <button class="btn btn-sm btn-outline-secondary flex-shrink-0" @click="sidebar_visible = !sidebar_visible" :title="sidebar_visible ? 'Hide instances' : 'Show instances'">
                                    <i :class="sidebar_visible ? 'fa-solid fa-chevron-left fa-xs' : 'fa-solid fa-chevron-right fa-xs'"></i>
                                </button>
                                <div>
                                    <a :href="sync_selected_instance.details.url" class="text-primary small fw-semibold" target="_blank">[[ sync_selected_instance.details.url ]]</a>
                                    <div class="small mt-1" style="color:var(--bs-primary);">
                                        <i class="fa-solid fa-rotate fa-xs me-1"></i>
                                        <span v-if="sync_selected_instance.last_sync">Last sync: [[ sync_selected_instance.last_sync ]]</span>
                                        <span v-else class="fst-italic">Never synced</span>
                                    </div>
                                </div>
                            </div>
                            <!-- Direction tabs: Send / Receive -->
                            <ul class="nav nav-tabs mb-3">
                                <li class="nav-item">
                                    <button :class="['nav-link', {active: sync_direction === 'send'}]" @click="set_sync_direction('send')">
                                        <i class="fa-solid fa-arrow-up fa-sm me-1"></i>Send
                                    </button>
                                </li>
                                <li class="nav-item">
                                    <button :class="['nav-link', {active: sync_direction === 'receive'}]" @click="set_sync_direction('receive')">
                                        <i class="fa-solid fa-arrow-down fa-sm me-1"></i>Receive
                                    </button>
                                </li>
                            </ul>
                            <!-- MispSyncPanel -->
                            <misp-sync-panel
                                :ref="el => sync_panel_ref = el"
                                :case_id="object_id"
                                :instance="sync_selected_instance"
                                :direction="sync_direction"
                                :modules="modules"
                                :case_misp_objects_list="case_misp_objects_list"
                                @sync_done="(e) => on_sync_done(e)"
                                @close="">
                            </misp-sync-panel>
                        </template>
                    </div>
                </div>
            </template>
        </template><!-- end mode sync -->

        <!-- MODE: search -->
        <template v-else-if="mode === 'search'">
            <div v-if="!case_task_connectors_list || !case_task_connectors_list.length" class="text-muted py-3">
                <i class="fa-solid fa-circle-info me-2"></i>No MISP connector linked to this case yet.
            </div>
            <template v-else>
                <div class="d-flex gap-3">
                    <!-- Left: instance list (collapsible) -->
                    <div v-show="sidebar_visible" class="border-end pe-3" style="min-width:180px; max-width:220px; flex-shrink:0;">
                        <div v-for="(inst, i) in case_task_connectors_list" :key="inst.case_task_instance_id"
                            :class="['d-flex align-items-center gap-2 p-2 rounded mb-1', search_instance_idx === i ? 'bg-primary bg-opacity-10 text-primary fw-semibold' : 'text-muted']"
                            style="cursor:pointer;"
                            @click="search_instance_idx = i">
                            <img :src="'/static/icons/'+inst.details.icon" style="max-width:20px; flex-shrink:0;">
                            <span class="text-truncate small">[[ inst.details.name ]]</span>
                        </div>
                    </div>
                    <!-- Right: content -->
                    <div class="flex-grow-1" style="min-width:0;">
                        <template v-if="search_selected_instance">
                            <div class="d-flex align-items-center gap-2 mb-3 p-2 rounded" style="background:var(--bs-primary-bg-subtle);">
                                <button class="btn btn-sm btn-outline-secondary flex-shrink-0" @click="sidebar_visible = !sidebar_visible" :title="sidebar_visible ? 'Hide instances' : 'Show instances'">
                                    <i :class="sidebar_visible ? 'fa-solid fa-chevron-left fa-xs' : 'fa-solid fa-chevron-right fa-xs'"></i>
                                </button>
                                <a :href="search_selected_instance.details.url" class="text-primary small fw-semibold" target="_blank">[[ search_selected_instance.details.url ]]</a>
                            </div>
                            <div class="alert alert-info border-0 py-2 px-3 mb-2 d-flex align-items-start" style="background-color: #eaf4fb;">
                                <i class="fa-solid fa-circle-info mt-1 me-2 text-primary"></i>
                                <small class="mb-0">
                                    Searches <strong>attributes</strong> on this MISP instance using a <strong>partial match</strong> (e.g. <code>example.com</code> matches <code>https://example.com/foo</code>).
                                    Use <code>%</code> for explicit wildcard patterns.
                                    Results include attributes from both published and unpublished events &mdash; you can then append the table to your notes in one click.
                                </small>
                            </div>
                            <form @submit.prevent="submit_misp_search(search_selected_instance)" class="d-flex align-items-center mb-2">
                                <input type="text" class="form-control me-2" placeholder="Search attributes in MISP..."
                                    v-model="get_misp_search(search_selected_instance.case_task_instance_id).query"
                                    :disabled="get_misp_search(search_selected_instance.case_task_instance_id).loading">
                                <button type="submit" class="btn btn-primary"
                                    :disabled="get_misp_search(search_selected_instance.case_task_instance_id).loading || !get_misp_search(search_selected_instance.case_task_instance_id).query.trim()">
                                    <template v-if="get_misp_search(search_selected_instance.case_task_instance_id).loading">
                                        <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                        <span role="status">Searching...</span>
                                    </template>
                                    <template v-else>Submit</template>
                                </button>
                            </form>
                            <template v-if="get_misp_search(search_selected_instance.case_task_instance_id).has_searched && !get_misp_search(search_selected_instance.case_task_instance_id).loading">
                                <template v-if="get_misp_search(search_selected_instance.case_task_instance_id).results.length">
                                    <div class="table-responsive">
                                        <table class="table table-sm table-bordered">
                                            <thead>
                                                <tr>
                                                    <th>Event ID</th><th title="Whether the event has been published in MISP">Published</th>
                                                    <th>Organisation</th><th>Event title</th><th>Date</th>
                                                    <th>Attribute Type</th><th>Attribute category</th><th>Value</th>
                                                    <th title="to_ids flag in MISP">IDS</th><th>Comment</th><th>Tags</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="r in get_misp_search(search_selected_instance.case_task_instance_id).results">
                                                    <td><a :href="(search_selected_instance.details.url.endsWith('/') ? search_selected_instance.details.url : search_selected_instance.details.url + '/') + 'events/view/' + r.event_id" target="_blank">[[r.event_id]]</a></td>
                                                    <td><span v-if="r.event_published" class="badge bg-success">yes</span><span v-else class="badge bg-warning text-dark">no</span></td>
                                                    <td>[[r.organisation]]</td><td>[[r.event_info]]</td><td>[[r.date]]</td>
                                                    <td>[[r.attribute_type]]</td><td>[[r.attribute_category]]</td><td>[[r.attribute_value]]</td>
                                                    <td><span v-if="r.to_ids" class="badge bg-success">yes</span><span v-else class="badge bg-secondary">no</span></td>
                                                    <td>[[r.comment]]</td>
                                                    <td><span v-for="t in r.tags" class="badge bg-secondary me-1">[[t]]</span></td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <div class="d-flex justify-content-end">
                                        <button class="btn btn-outline-success btn-sm" @click="add_results_to_note(search_selected_instance)" :disabled="get_misp_search(search_selected_instance.case_task_instance_id).appending">
                                            <template v-if="get_misp_search(search_selected_instance.case_task_instance_id).appending">
                                                <span class="spinner-border spinner-border-sm"></span> Adding...
                                            </template>
                                            <template v-else><i class="fa-solid fa-plus"></i> Add as a [[ is_case ? 'case' : 'task' ]] note</template>
                                        </button>
                                    </div>
                                </template>
                                <div v-else class="text-muted"><i>No results found.</i></div>
                            </template>
                        </template>
                    </div>
                </div>
            </template>
        </template><!-- end mode search -->
    `
}
