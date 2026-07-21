import { display_toast } from '../toaster.js'
import MispSyncPanel from './MispSyncPanel.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
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
    emits: ['case_connectors', 'note_change', 'task_note_added', 'modif_misp_objects'],
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

        // Sync logs state (keyed by case_task_instance_id)
        const sync_logs_map = ref({})

        // Inline identifier editing
        const identifier_editing = ref(false)
        const identifier_draft = ref('')
        const connector_info_expanded = ref(false)
        const can_view_extended_details = computed(() => {
            const permission = props.cases_info && props.cases_info.permission
            if (!permission) return false
            if (permission.admin) return true
            return !!(permission.case_admin && props.cases_info.present_in_case)
        })

        function start_edit_identifier() {
            if (!sync_selected_instance.value?.can_interact_connector) return
            identifier_draft.value = sync_selected_instance.value?.identifier || ''
            identifier_editing.value = true
        }

        function cancel_edit_identifier() {
            identifier_editing.value = false
            identifier_draft.value = ''
        }

        function getCaseId(){
            return props.is_case ? props.object_id : (props.cases_info && props.cases_info.case ? props.cases_info.case.id : props.object_id)
        }

        async function save_edit_identifier() {
            const inst = sync_selected_instance.value
            if (!inst || !inst.can_interact_connector) return
            const url = '/case/' + getCaseId() + '/connectors/' + inst.case_task_instance_id + '/edit_connector'
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ identifier: identifier_draft.value })
            })
            if (res.status === 200) {
                inst.identifier = identifier_draft.value
                touchCaseLastModif(props.cases_info)
                identifier_editing.value = false
                identifier_draft.value = ''
            }
            display_toast(res)
        }

        async function load_sync_logs(instance_id) {
            if (sync_logs_map.value[instance_id]) return  // already cached
            sync_logs_map.value[instance_id] = { loading: true, logs: [] }
            try {
                const url = '/case/' + getCaseId() + '/connectors/' + instance_id + '/sync_logs'
                const res = await fetch(url)
                if (res.status === 200) {
                    const data = await res.json()
                    sync_logs_map.value[instance_id] = { loading: false, logs: data.sync_logs || [] }
                } else {
                    sync_logs_map.value[instance_id] = { loading: false, logs: [] }
                    display_toast(res)
                }
            } catch (e) {
                sync_logs_map.value[instance_id] = { loading: false, logs: [] }
            }
        }

        async function refresh_sync_logs(instance_id) {
            delete sync_logs_map.value[instance_id]
            await load_sync_logs(instance_id)
        }

        function set_sync_direction(dir) {
            sync_direction.value = dir
            if (dir === 'logs' && sync_selected_instance.value) {
                load_sync_logs(sync_selected_instance.value.case_task_instance_id)
            }
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
            return "/case/" + getCaseId() + "/connectors/" + instance.case_task_instance_id + "/search_in_misp"
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
                touchCaseLastModif(props.cases_info)
                if (props.is_case && loc.notes !== undefined) {
                    emit('note_change', loc.notes)
                } else if (!props.is_case && loc.note) {
                    emit('note_change', loc.notes || [])
                }
            }
            display_toast(res)
        }

        function on_sync_done({ direction, instance }) {
            touchCaseLastModif(props.cases_info)
            emit('modif_misp_objects')
            emit("case_connectors", true)
        }

        // Auto-init MispSyncPanel when instance or direction changes; reset identifier edit on instance change
        watch(sync_selected_instance, () => {
            identifier_editing.value = false
            identifier_draft.value = ''
            connector_info_expanded.value = false
        })
        watch(search_selected_instance, () => {
            connector_info_expanded.value = false
        })
        watch([sync_selected_instance, sync_direction], async ([inst, dir]) => {
            if (props.mode !== 'sync' || !inst) return
            if (dir === 'logs') {
                load_sync_logs(inst.case_task_instance_id)
                return
            }
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
            sync_logs_map,
            identifier_editing,
            identifier_draft,
            connector_info_expanded,
            can_view_extended_details,
            set_sync_direction,
            refresh_sync_logs,
            start_edit_identifier,
            cancel_edit_identifier,
            save_edit_identifier,
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
                            <span v-if="!inst.can_use_connector" class="badge bg-light text-muted border ms-auto">view only</span>
                        </div>
                    </div>
                    <!-- Right: content -->
                    <div class="flex-grow-1" style="min-width:0;">
                        <template v-if="sync_selected_instance">
                            <div class="d-flex align-items-start gap-2 mb-3 p-2 rounded" style="background:var(--bs-primary-bg-subtle);">
                                <button class="btn btn-sm btn-outline-secondary flex-shrink-0" @click="sidebar_visible = !sidebar_visible" :title="sidebar_visible ? 'Hide instances' : 'Show instances'">
                                    <i :class="sidebar_visible ? 'fa-solid fa-chevron-left fa-xs' : 'fa-solid fa-chevron-right fa-xs'"></i>
                                </button>
                                <div class="d-flex">
                                    <div>
                                        <a :href="sync_selected_instance.details.url" class="text-primary small fw-semibold" target="_blank">
                                            [[ sync_selected_instance.details.url ]]
                                        </a>
                                        <div class="small mt-1" style="color:var(--bs-primary);">
                                            <i class="fa-solid fa-rotate fa-xs me-1"></i>
                                            <span v-if="sync_selected_instance.last_sync">Last sync: [[ sync_selected_instance.last_sync ]]</span>
                                            <span v-else class="fst-italic">Never synced</span>
                                        </div>
                                        <div v-if="sync_selected_instance.details.description" class="small text-muted mt-1">
                                            [[ sync_selected_instance.details.description ]]
                                        </div>
                                        <div v-if="can_view_extended_details && sync_selected_instance.admin_details" class="mt-2">
                                            <button type="button"
                                                    class="btn btn-sm btn-outline-secondary py-0 px-2"
                                                    @click="connector_info_expanded = !connector_info_expanded">
                                                <i :class="connector_info_expanded ? 'fa-solid fa-chevron-down fa-xs me-1' : 'fa-solid fa-chevron-right fa-xs me-1'"></i>
                                                Connector info
                                            </button>
                                            <div v-if="connector_info_expanded" class="small mt-2 text-muted">
                                                <div><span class="fw-semibold">Connector:</span> [[ sync_selected_instance.admin_details.connector_name || 'Unknown' ]]</div>
                                                <div><span class="fw-semibold">Case link ID:</span> [[ sync_selected_instance.admin_details.case_connector_id ]]</div>
                                                <div><span class="fw-semibold">Instance ID:</span> [[ sync_selected_instance.admin_details.instance_id ]]</div>
                                                <div><span class="fw-semibold">Connector ID:</span> [[ sync_selected_instance.admin_details.connector_id ]]</div>
                                                <div><span class="fw-semibold">Scope:</span> [[ sync_selected_instance.admin_details.sharing_scope || 'personal' ]]</div>
                                                <div v-if="sync_selected_instance.admin_details.shared_org_id"><span class="fw-semibold">Shared org ID:</span> [[ sync_selected_instance.admin_details.shared_org_id ]]</div>
                                                <div v-if="sync_selected_instance.admin_details.owner_user_name"><span class="fw-semibold">Owner user:</span> [[ sync_selected_instance.admin_details.owner_user_name ]]</div>
                                                <div v-if="sync_selected_instance.admin_details.owner_org_name"><span class="fw-semibold">Owner org:</span> [[ sync_selected_instance.admin_details.owner_org_name ]]<template v-if="sync_selected_instance.admin_details.owner_org_id"> (#[[ sync_selected_instance.admin_details.owner_org_id ]])</template></div>
                                            </div>
                                        </div>
                                    </div>
                                    <div class="small mt-1 ms-4 d-flex gap-1">
                                        <span class="text-muted">Identifier:</span>
                                        <template v-if="identifier_editing">
                                            <input type="text" class="form-control form-control-sm py-0" style="min-width:100%; height:1.6rem;" v-model="identifier_draft"
                                                @keyup.enter="save_edit_identifier()"
                                                @keyup.escape="cancel_edit_identifier()">
                                            <span>
                                                <button class="btn btn-success btn-sm py-0 px-1" @click="save_edit_identifier()" title="Save">
                                                    <i class="fa-solid fa-check fa-xs"></i>
                                                </button>
                                            </span>
                                            <span>
                                                <button class="btn btn-outline-secondary btn-sm py-0 px-1" @click="cancel_edit_identifier()" title="Cancel">
                                                    <i class="fa-solid fa-xmark fa-xs"></i>
                                                </button>
                                            </span>
                                        </template>
                                        <template v-else>
                                            <span :class="sync_selected_instance.identifier ? 'fw-semibold' : 'fst-italic text-muted'" style="color:var(--bs-primary);">
                                                [[ sync_selected_instance.identifier || 'None' ]]
                                            </span>
                                            <a v-if="sync_selected_instance.is_misp_connector && sync_selected_instance.identifier && sync_selected_instance.details?.url"
                                               :href="((sync_selected_instance.details.url.endsWith('/') ? sync_selected_instance.details.url : sync_selected_instance.details.url + '/') + 'events/view/' + sync_selected_instance.identifier)"
                                               target="_blank"
                                               rel="noopener noreferrer"
                                               class="btn btn-link btn-sm p-0 ms-1"
                                               style="color:var(--bs-primary); line-height:1;"
                                               title="Open current MISP event">
                                                <i class="fa-solid fa-arrow-up-right-from-square fa-xs"></i>
                                            </a>
                                            <span>
                                                <button v-if="is_case && sync_selected_instance.can_interact_connector" class="btn btn-link btn-sm p-0 ms-1" style="color:var(--bs-primary); line-height:1;" @click="start_edit_identifier()" title="Edit identifier">
                                                    <i class="fa-solid fa-pen fa-xs"></i>
                                                </button>
                                            </span>
                                        </template>
                                    </div>
                                </div>
                            </div>
                            <div v-if="!sync_selected_instance.can_use_connector && sync_direction !== 'logs'" class="alert alert-info py-2 px-3 mb-3">
                                You can inspect which objects are synced with this connector, but only connectors you can use directly are interactive.
                            </div>
                            <!-- Direction tabs: Send / Receive / Logs -->
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
                                <li class="nav-item">
                                    <button :class="['nav-link', {active: sync_direction === 'logs'}]" @click="set_sync_direction('logs')">
                                        <i class="fa-solid fa-clock-rotate-left fa-sm me-1"></i>Logs
                                    </button>
                                </li>
                            </ul>
                            <!-- MispSyncPanel (Send / Receive) -->
                            <template v-if="sync_direction !== 'logs'">
                                    <misp-sync-panel
                                        :ref="el => sync_panel_ref = el"
                                        :case_id="object_id"
                                        :instance="sync_selected_instance"
                                        :can_use_connector="!!sync_selected_instance.can_use_connector"
                                        :direction="sync_direction"
                                        :modules="modules"
                                        :case_misp_objects_list="case_misp_objects_list"
                                        :cases_info="cases_info"
                                        @sync_done="(e) => on_sync_done(e)">
                                    </misp-sync-panel>
                            </template>
                            <!-- Logs panel -->
                            <template v-else>
                                <div class="d-flex align-items-center justify-content-between mb-2">
                                    <span class="text-muted small fw-semibold">Sync history for [[ sync_selected_instance.details.name ]]</span>
                                    <button class="btn btn-sm btn-outline-secondary" @click="refresh_sync_logs(sync_selected_instance.case_task_instance_id)" title="Refresh logs">
                                        <i class="fa-solid fa-rotate-right fa-xs"></i>
                                    </button>
                                </div>
                                <div v-if="sync_logs_map[sync_selected_instance.case_task_instance_id]?.loading" class="text-muted small">
                                    <span class="spinner-border spinner-border-sm me-2"></span>Loading sync history…
                                </div>
                                <div v-else-if="!sync_logs_map[sync_selected_instance.case_task_instance_id]?.logs?.length" class="text-muted small">
                                    <i class="fa-solid fa-circle-info me-1"></i>No sync history yet for this instance.
                                </div>
                                <div v-else class="table-responsive">
                                    <table class="table table-sm table-borderless mb-0">
                                        <thead>
                                            <tr class="text-muted" style="font-size:0.8em;">
                                                <th>Time</th>
                                                <th>Direction</th>
                                                <th>Status</th>
                                                <th>Synced</th>
                                                <th>Failed</th>
                                                <th>Message</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="log in sync_logs_map[sync_selected_instance.case_task_instance_id].logs" :key="log.id" style="font-size:0.85em;">
                                                <td class="text-muted">[[log.timestamp]]</td>
                                                <td>
                                                    <span v-if="log.direction === 'send'" class="badge bg-secondary"><i class="fa-solid fa-arrow-up me-1"></i>Send</span>
                                                    <span v-else class="badge bg-info text-dark"><i class="fa-solid fa-arrow-down me-1"></i>Receive</span>
                                                </td>
                                                <td>
                                                    <span v-if="log.status === 'success'" class="badge bg-success">success</span>
                                                    <span v-else-if="log.status === 'partial'" class="badge bg-warning text-dark">partial</span>
                                                    <span v-else class="badge bg-danger">error</span>
                                                </td>
                                                <td>[[log.objects_synced]]</td>
                                                <td>[[log.objects_failed]]</td>
                                                <td class="text-muted">
                                                    <span v-if="log.message">[[log.message]]</span>
                                                    <span v-else-if="log.details && log.details.length">
                                                        <span v-for="d in log.details.filter(d=>d.status==='error').slice(0,3)" :key="d.name" class="text-danger me-2" :title="d.error">[[d.name]]</span>
                                                        <span v-if="log.details.filter(d=>d.status==='error').length > 3" class="text-muted">…</span>
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                            </template>
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
                                <div>
                                    <a :href="search_selected_instance.details.url" class="text-primary small fw-semibold" target="_blank">[[ search_selected_instance.details.url ]]</a>
                                    <div v-if="search_selected_instance.details.description" class="small text-muted mt-1">[[ search_selected_instance.details.description ]]</div>
                                    <div v-if="can_view_extended_details && search_selected_instance.admin_details" class="mt-2">
                                        <button type="button"
                                                class="btn btn-sm btn-outline-secondary py-0 px-2"
                                                @click="connector_info_expanded = !connector_info_expanded">
                                            <i :class="connector_info_expanded ? 'fa-solid fa-chevron-down fa-xs me-1' : 'fa-solid fa-chevron-right fa-xs me-1'"></i>
                                            Connector info
                                        </button>
                                        <div v-if="connector_info_expanded" class="small mt-2 text-muted">
                                            <div><span class="fw-semibold">Instance ID:</span> [[ search_selected_instance.admin_details.instance_id ]]</div>
                                            <div><span class="fw-semibold">Scope:</span> [[ search_selected_instance.admin_details.sharing_scope || 'personal' ]]</div>
                                            <div v-if="search_selected_instance.admin_details.shared_org_id"><span class="fw-semibold">Shared org ID:</span> [[ search_selected_instance.admin_details.shared_org_id ]]</div>
                                            <div v-if="search_selected_instance.admin_details.owner_user_name"><span class="fw-semibold">Owner user:</span> [[ search_selected_instance.admin_details.owner_user_name ]]</div>
                                            <div v-if="search_selected_instance.admin_details.owner_org_name"><span class="fw-semibold">Owner org:</span> [[ search_selected_instance.admin_details.owner_org_name ]]</div>
                                        </div>
                                    </div>
                                </div>
                            </div>
                            <div v-if="!search_selected_instance.can_use_connector" class="alert alert-info py-2 px-3 mb-3">
                                This connector is visible on the case for tracking purposes, but search is only available on connectors you can use directly.
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
                                    :disabled="get_misp_search(search_selected_instance.case_task_instance_id).loading || !search_selected_instance.can_use_connector">
                                <button type="submit" class="btn btn-primary"
                                    :disabled="get_misp_search(search_selected_instance.case_task_instance_id).loading || !get_misp_search(search_selected_instance.case_task_instance_id).query.trim() || !search_selected_instance.can_use_connector">
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
