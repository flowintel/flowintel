import { display_toast, create_message } from '../toaster.js'
import MispSyncPanel from './MispSyncPanel.js'
const { ref, reactive, onMounted, computed, nextTick, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: {
        case_task_connectors_list: Object,
        all_connectors_list: Object,
        modules: Object,
        is_case: Boolean,
        object_id: Number,
        cases_info: Object
    },
    emits: ['case_connectors', 'task_connectors', 'note_change', 'task_note_added'],
    components: { 'misp-sync-panel': MispSyncPanel },
    setup(props, { emit }) {
        const is_sending = ref(false)
        const show_add_page = ref(false)
        const show_edit_page = ref(false)
        const show_send_page = ref(false)
        const show_receive_page = ref(false)
        const connectors_selected = ref([])
        const edit_instance = ref()
        const send_to_instance = ref()
        const receive_from_instance = ref()
        const module_selected = ref({})
        const is_loading_update = ref(false)
        const case_misp_objects = ref([])
        const remote_misp_objects = ref([])
        const selected_send_ids = ref([])
        const selected_receive_uuids = ref([])
        const is_loading_objects = ref(false)
        const selected_send_module_name = ref('')
        const selected_receive_module_name = ref('')

        // MispSyncPanel state
        const sync_panel_instance = ref(null)
        const sync_panel_direction = ref('send')
        const sync_panel_ref = ref(null)

        // Sync log expansion
        const expanded_log_row = ref(null)
        const sync_logs_map = ref({})   // keyed by case_task_instance_id
        const misp_search_state = reactive({})

        const can_edit_object = computed(() => {
            if (!props.cases_info) return false
            const permission = props.cases_info.permission || {}
            const present_in_case = props.cases_info.present_in_case
            if (permission.admin) return true
            if (!props.is_case && props.object_id && props.cases_info.tasks) {
                const task = props.cases_info.tasks.find(t => t.id === props.object_id)
                return !!(task && task.can_edit && present_in_case)
            }
            if (permission.read_only) return false
            return !!present_in_case
        })

        function get_misp_search(instance_id) {
            if (!misp_search_state[instance_id]) {
                misp_search_state[instance_id] = {
                    open: false,
                    query: '',
                    loading: false,
                    has_searched: false,
                    results: [],
                    appending: false
                }
            }
            return misp_search_state[instance_id]
        }

        function toggle_misp_search(instance) {
            const state = get_misp_search(instance.case_task_instance_id)
            state.open = !state.open
        }

        // Feature-detection flags for Select2/jQuery availability
        let hasJQuery = false
        let hasSelect2 = false

        // Initialize the connectors select2 when options are available
        async function initConnectorsSelect2() {
            await nextTick()
            try {
                hasJQuery = (typeof $ !== 'undefined')
                hasSelect2 = hasJQuery && $.fn && $.fn.select2
                const sel = document.getElementById('connectors_select_' + modal_identifier)
                if (!sel) return
                if (hasSelect2) {
                    try { if ($(sel).data('select2')) $(sel).select2('destroy') } catch (e) {}
                    $(sel).select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                }
            } catch (e) {}
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
            // Reuse the existing 'create or modify task note' endpoint with note_id=-1 to create a new note.
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

        let modal_identifier = ""
        if (props.is_case) {
            modal_identifier = "case-" + props.object_id
        } else {
            modal_identifier = "task-" + props.object_id
        }

        async function save_connector() {
            try {
                // Build selected connectors from the select element (more robust than relying on connectors_selected)
                const sel = document.getElementById('connectors_select_' + modal_identifier)
                const selectedIds = sel ? Array.from(sel.selectedOptions).map(o => String(o.value)) : []

                const connector_dict = []
                if (props.all_connectors_list && selectedIds.length) {
                    // props.all_connectors_list is keyed by connector type/name and contains arrays of instances
                    for (const [_groupName, instances] of Object.entries(props.all_connectors_list)) {
                        for (const instance of instances) {
                            if (selectedIds.includes(String(instance.id))) {
                                const identEl = document.getElementById('identifier_' + instance.id)
                                const identifier = identEl ? identEl.value : ''
                                // IMPORTANT: backend expects the instance name (Connector_Instance.name), not the group key
                                connector_dict.push({ name: instance.name, identifier: identifier })
                            }
                        }
                    }
                }

                let url = props.is_case ? ("/case/" + props.object_id + "/add_connector") : ("/case/task/" + props.object_id + "/add_connector")

                const res = await fetch(url, {
                    method: 'POST',
                    headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ connectors: connector_dict })
                })

                if (res.status == 200) {
                    // clear UI selections
                    try { $(sel).val(null).trigger('change') } catch(e) {}
                    connectors_selected.value = []
                    show_add_page.value = false
                    if (props.is_case) emit('case_connectors', true)
                    else emit('task_connectors', true)
                }
                display_toast(res)
            } catch (e) {
                create_message('Error while adding connector', 'danger-subtle')
            }
        }

        async function remove_connector(element_instance_id) {
            let url
            if (props.is_case) {
                url = "/case/" + props.object_id + "/connectors/" + element_instance_id + "/remove_connector"
            } else {
                url = "/case/task/" + props.object_id + "/remove_connector/" + element_instance_id
            }

            const res = await fetch(url)
            if (await res.status == 200) {
                let loc
                for (let i in props.case_task_connectors_list) {
                    if (props.case_task_connectors_list[i].case_task_instance_id == element_instance_id) {
                        loc = i
                        break
                    }
                }
                props.case_task_connectors_list.splice(loc, 1)
            }
            display_toast(res)
        }

        function edit_instance_open_modal(instance) {
            edit_instance.value = instance
            show_edit_page.value = true
        }

        async function edit_connector() {
            let url
            if (props.is_case) {
                url = "/case/" + props.object_id + "/connectors/" + edit_instance.value.case_task_instance_id + "/edit_connector"
            } else {
                url = "/case/task/" + props.object_id + "/edit_connector/" + edit_instance.value.case_task_instance_id
            }

            let loc_identifier = $("#input-edit-connector-" + modal_identifier).val()
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "identifier": loc_identifier
                })
            });
            if (await res.status == 200) {
                for (let i in props.case_task_connectors_list) {
                    if (props.case_task_connectors_list[i].case_task_instance_id == edit_instance.value.case_task_instance_id) {
                        props.case_task_connectors_list[i].identifier = loc_identifier
                    }
                }
                show_edit_page.value = false
                edit_instance.value = null

            }
            display_toast(res)

        }

        async function send_to_modal(instance) {
            if (props.is_case && instance.is_misp_connector) {
                sync_panel_instance.value = instance
                sync_panel_direction.value = 'send'
                send_to_instance.value = instance
                show_send_page.value = true
                await nextTick()
                await sync_panel_ref.value?.on_show()
                return
            }
            send_to_instance.value = instance
            case_misp_objects.value = []
            selected_send_ids.value = []
            selected_send_module_name.value = ''
            module_selected.value = {}
            if (props.is_case) {
                const res = await fetch("/case/" + props.object_id + "/get_case_misp_object")
                if (res.status == 200) {
                    const loc = await res.json()
                    case_misp_objects.value = loc["misp-object"] || []
                    selected_send_ids.value = case_misp_objects.value.map(o => o.object_id)
                }
            }
            show_send_page.value = true
        }

        async function receive_from_modal(instance) {
            if (props.is_case && instance.is_misp_connector) {
                sync_panel_instance.value = instance
                sync_panel_direction.value = 'receive'
                receive_from_instance.value = instance
                show_receive_page.value = true
                await nextTick()
                await sync_panel_ref.value?.on_show()
                return
            }
            receive_from_instance.value = instance
            remote_misp_objects.value = []
            selected_receive_uuids.value = []
            selected_receive_module_name.value = ''
            module_selected.value = {}
            show_receive_page.value = true
        }

        async function fetch_remote_objects() {
            if (!receive_from_instance.value || !props.is_case) return
            is_loading_objects.value = true
            remote_misp_objects.value = []
            selected_receive_uuids.value = []
            const res = await fetch("/case/" + props.object_id + "/connectors/" + receive_from_instance.value.case_task_instance_id + "/misp_objects_preview")
            is_loading_objects.value = false
            if (res.status == 200) {
                const loc = await res.json()
                remote_misp_objects.value = loc["objects"] || []
                selected_receive_uuids.value = remote_misp_objects.value.map(o => o.uuid)
            } else {
                display_toast(res)
            }
        }

        async function toggle_sync_logs(instance_id) {
            if (expanded_log_row.value === instance_id) {
                expanded_log_row.value = null
                return
            }
            expanded_log_row.value = instance_id
            if (sync_logs_map.value[instance_id]) return  // already loaded
            sync_logs_map.value[instance_id] = { loading: true, logs: [] }
            try {
                const res = await fetch("/case/" + props.object_id + "/connectors/" + instance_id + "/sync_logs")
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

        function on_sync_done({ direction, instance }) {
            // Refresh connector list to pick up updated last_sync
            if (props.is_case) {
                emit("case_connectors", true)
            } else {
                emit("task_connectors", true)
            }
            // Clear cached logs for this connector so they reload on next expand
            if (instance) {
                delete sync_logs_map.value[instance.case_task_instance_id]
            }
        }

        async function submit_module() {
            is_sending.value = true
            $("#modules_errors").hide()
            let modules_select = $("#modules_select_" + modal_identifier).val()


            if (!modules_select || modules_select == "None") {
                $("#modules_errors").text("Select an item")
                $("#modules_errors").show()
                return
            }

            let url
            if (props.is_case) {
                url = "/case/" + props.object_id + "/call_module_case"
            } else {
                url = "/case/" + props.cases_info.case.id + "/task/" + props.object_id + "/call_module_task"
            }

            const body = {
                "module": modules_select,
                "case_task_instance_id": send_to_instance.value.case_task_instance_id
            }
            if (modules_select === "misp_object_event" && case_misp_objects.value.length > 0) {
                body["selected_objects"] = selected_send_ids.value
            }
            const res = await fetch(url, {
                method: "POST",
                body: JSON.stringify(body),
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                }
            });
            is_sending.value = false

            if (await res.status == 200) {
                show_send_page.value = false
                if (props.is_case) {
                    emit("case_connectors", true)
                } else {
                    emit("task_connectors", true)
                }
            }

            display_toast(res)
        }

        async function submit_receive_module() {
            is_sending.value = true
            $("#modules_errors_receive").hide()
            let modules_select = $("#modules_select_receive_" + modal_identifier).val()


            if (!modules_select || modules_select == "None") {
                $("#modules_errors_receive").text("Select an item")
                $("#modules_errors_receive").show()
                is_sending.value = false
                return
            }

            let url
            if (props.is_case) {
                url = "/case/" + props.object_id + "/call_module_case"
            } else {
                url = "/case/" + props.cases_info.case.id + "/task/" + props.object_id + "/call_module_task"
            }

            const body = {
                "module": modules_select,
                "case_task_instance_id": receive_from_instance.value.case_task_instance_id
            }
            if (modules_select === "receive_misp_object" && remote_misp_objects.value.length > 0) {
                body["selected_objects"] = selected_receive_uuids.value
            }
            const res = await fetch(url, {
                method: "POST",
                body: JSON.stringify(body),
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                }
            });
            is_sending.value = false

            if (await res.status == 200) {
                show_receive_page.value = false
                if (props.is_case) {
                    emit("case_connectors", true)
                } else {
                    emit("task_connectors", true)
                }
            }

            display_toast(res)
        }

        onMounted(async () => {
            await nextTick()
            hasJQuery = (typeof $ !== 'undefined')
            hasSelect2 = hasJQuery && $.fn && $.fn.select2
            if (!hasSelect2) {}

            try {
                if (hasSelect2) {
                    // .select2-connect is now inline (no separate modal), so use body as parent
                    $('.select2-connect').select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                    $('.select2-module').select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                    $('.select2-module-receive').select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                }
            } catch (e) {}

            const modulesSelectEl = document.getElementById('modules_select_' + modal_identifier)
            const modulesSelectReceiveEl = document.getElementById('modules_select_receive_' + modal_identifier)
            const connectorsSelectEl = document.getElementById('connectors_select_' + modal_identifier)

            const handleModulesChange = function (e) {
                const el = e.target || this
                let loc = []
                try {
                    if (hasSelect2 && $(el).data('select2')) loc = $(el).select2('data').map(item => item.id)
                    else loc = Array.from(el.selectedOptions || []).map(o => o.value)
                } catch (err) {
                    loc = Array.from(el.selectedOptions || []).map(o => o.value)
                }

                for (let i in props.modules) {
                    if (loc == i) {
                        module_selected.value = props.modules[i].config
                        break
                    }
                }
            }

            const handleModulesReceiveChange = function (e) {
                const el = e.target || this
                let loc = []
                try {
                    if (hasSelect2 && $(el).data('select2')) loc = $(el).select2('data').map(item => item.id)
                    else loc = Array.from(el.selectedOptions || []).map(o => o.value)
                } catch (err) {
                    loc = Array.from(el.selectedOptions || []).map(o => o.value)
                }

                for (let i in props.modules) {
                    if (loc == i) {
                        module_selected.value = props.modules[i].config
                        break
                    }
                }

                selected_receive_module_name.value = loc[0] || ''
                if (loc[0] !== 'receive_misp_object') {
                    remote_misp_objects.value = []
                    selected_receive_uuids.value = []
                }
            }

            const handleModulesObjSel = function (e) {
                const el = e.target || this
                let loc = []
                try {
                    if (hasSelect2 && $(el).data('select2')) loc = $(el).select2('data').map(item => item.id)
                    else loc = Array.from(el.selectedOptions || []).map(o => o.value)
                } catch (err) {
                    loc = Array.from(el.selectedOptions || []).map(o => o.value)
                }
                selected_send_module_name.value = loc[0] || ''
            }

            const handleConnectorsChange = function (e) {
                const el = e.target || this
                connectors_selected.value = []
                let loc = []
                try {
                    if (hasSelect2 && $(el).data('select2')) loc = $(el).select2('data').map(item => item.id)
                    else loc = Array.from(el.selectedOptions || []).map(o => o.value)
                } catch (err) {
                    loc = Array.from(el.selectedOptions || []).map(o => o.value)
                }
                for (let element in loc) {
                    for (let connectors in props.all_connectors_list) {
                        for (let connector in props.all_connectors_list[connectors]) {
                            if (String(loc[element]) == String(props.all_connectors_list[connectors][connector].id)) {
                                connectors_selected.value.push({
                                    "id": props.all_connectors_list[connectors][connector].id,
                                    "name": props.all_connectors_list[connectors][connector].name
                                })
                            }
                        }
                    }
                }
            }

            try {
                if (modulesSelectEl) {
                    modulesSelectEl.addEventListener('change', handleModulesChange)
                    if (hasJQuery) $(modulesSelectEl).on('change.select2', handleModulesChange)
                    if (hasJQuery) $(modulesSelectEl).on('change.select2.objsel', handleModulesObjSel)
                }
                if (modulesSelectReceiveEl) {
                    modulesSelectReceiveEl.addEventListener('change', handleModulesReceiveChange)
                    if (hasJQuery) $(modulesSelectReceiveEl).on('change.select2', handleModulesReceiveChange)
                }
                if (connectorsSelectEl) {
                    connectorsSelectEl.addEventListener('change', handleConnectorsChange)
                    if (hasJQuery) $(connectorsSelectEl).on('change.select2', handleConnectorsChange)
                }
            } catch (err) {}


        })

        // Re-initialize connectors select when the available connectors list is populated/updated
        watch(() => props.all_connectors_list, async (nv) => {
            if (!nv || Object.keys(nv).length === 0) return
            await nextTick()
            await initConnectorsSelect2()
        }, { immediate: true, deep: true })

        // Re-initialize connectors select2 when the add-connector page opens
        watch(show_add_page, async (nv) => {
            if (!nv) return
            await nextTick()
            await initConnectorsSelect2()
        })

        async function initModuleSelect2() {
            await nextTick()
            try {
                if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
                    const el = document.getElementById('modules_select_' + modal_identifier)
                    if (el) {
                        try { if ($(el).data('select2')) $(el).select2('destroy') } catch(e) {}
                        $(el).select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                        $(el).on('change.select2', function() {
                            const val = $(el).val()
                            selected_send_module_name.value = val || ''
                            for (let i in props.modules) {
                                if (val == i) { module_selected.value = props.modules[i].config; break }
                            }
                        })
                    }
                }
            } catch(e) {}
        }

        async function initModuleReceiveSelect2() {
            await nextTick()
            try {
                if (typeof $ !== 'undefined' && $.fn && $.fn.select2) {
                    const el = document.getElementById('modules_select_receive_' + modal_identifier)
                    if (el) {
                        try { if ($(el).data('select2')) $(el).select2('destroy') } catch(e) {}
                        $(el).select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                        $(el).on('change.select2', function() {
                            const val = $(el).val()
                            selected_receive_module_name.value = val || ''
                            for (let i in props.modules) {
                                if (val == i) { module_selected.value = props.modules[i].config; break }
                            }
                            if (val !== 'receive_misp_object') {
                                remote_misp_objects.value = []
                                selected_receive_uuids.value = []
                            }
                        })
                    }
                }
            } catch(e) {}
        }

        watch(show_send_page, async (nv) => {
            if (!nv) return
            await nextTick()
            await initModuleSelect2()
        })

        watch(show_receive_page, async (nv) => {
            if (!nv) return
            await nextTick()
            await initModuleReceiveSelect2()
        })

        return {
            is_sending,
            show_add_page,
            show_edit_page,
            show_send_page,
            show_receive_page,
            connectors_selected,
            edit_instance,
            send_to_instance,
            receive_from_instance,
            modal_identifier,
            module_selected,
            is_loading_update,
            case_misp_objects,
            remote_misp_objects,
            selected_send_ids,
            selected_receive_uuids,
            is_loading_objects,
            selected_send_module_name,
            selected_receive_module_name,
            sync_panel_instance,
            sync_panel_direction,
            sync_panel_ref,
            expanded_log_row,
            sync_logs_map,
            can_edit_object,

            save_connector,
            remove_connector,
            edit_instance_open_modal,
            edit_connector,
            send_to_modal,
            receive_from_modal,
            fetch_remote_objects,
            submit_module,
            submit_receive_module,
            toggle_sync_logs,
            on_sync_done,
            get_misp_search,
            toggle_misp_search,
            submit_misp_search,
            add_results_to_note
        }
    },
    css: `
        .tab-content {
            border-left: 1px solid #ddd;
            border-right: 1px solid #ddd;
            border-bottom: 1px solid #ddd;
            padding: 10px;
        }
    `,
    template: `
        <!-- PAGE 1: connector list -->
        <template v-if="!show_add_page && !show_edit_page && !show_send_page && !show_receive_page">
        <div v-if="can_edit_object">
            <button class="btn btn-outline-primary" @click="show_add_page = true" title="Add connector">
                <i class="fa-solid fa-plus"></i>
            </button>
        </div>
        <table class="table">
            <thead>
                <tr>
                    <th>Instance name</th>
                    <th>Instance url</th>
                    <th>Type</th>
                    <th>Identifier on the instance</th>
                    <th>Last sync</th>
                    <th></th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                <template v-for="instance in case_task_connectors_list" :key="instance.case_task_instance_id">
                <tr>
                    <td>
                        <div :title="instance.details.description">
                            <img :src="'/static/icons/'+instance.details.icon" style="max-width: 30px;">
                            [[instance.details.name]]
                        </div>
                    </td>
                    <td>
                        <a style="margin-left: 5px" :href="instance.details.url">[[instance.details.url]]</a>
                    </td>

                    <td v-if="instance.details.type">
                        <span style="margin-left: 3px;" title="type of the module">[[instance.details.type]]</span>
                    </td>
                    <td v-else><i>None</i></td>

                    <td v-if="instance.identifier">
                        <span style="margin-left: 3px;" title="identifier used by module">[[instance.identifier]]</span>
                        <template v-if="instance.is_misp_connector">
                            <a style="margin-left: 8px;" :href="(instance.details.url.endsWith('/') ? instance.details.url : instance.details.url + '/') + 'events/view/' + instance.identifier" target="_blank" title="Open MISP event on remote instance">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                        </template>
                    </td>
                    <td v-else><i>None</i></td>
                    <td>
                        <span v-if="instance.last_sync" :title="'Last synced: ' + instance.last_sync" class="text-muted small"><i class="fa-solid fa-rotate me-1"></i>[[instance.last_sync]]</span>
                        <span v-else class="text-muted small"><i>Never</i></span>
                    </td>

                    <td v-if="can_edit_object">
                        <button class="btn btn-outline-primary" @click="edit_instance_open_modal(instance)">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button> 
                        <template v-if="instance.details.type == 'send_to'">
                            <button v-if="!is_sending" class="btn btn-outline-secondary mx-1" @click="send_to_modal(instance)"> Send to </button>
                            <button v-else class="btn btn-outline-secondary" type="button" disabled>
                                <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                <span role="status">Loading...</span>
                            </button>
                        </template>
                        <template v-else-if="instance.details.type == 'receive_from'">
                            <button v-if="!is_sending" class="btn btn-outline-secondary mx-1" @click="receive_from_modal(instance)"> Receive </button>
                            <button v-else class="btn btn-outline-secondary" type="button" disabled>
                                <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                <span role="status">Loading...</span>
                            </button>
                            <button v-if="instance.is_misp_connector" class="btn btn-outline-info mx-1" @click="toggle_misp_search(instance)" title="Search attributes in MISP">
                                <i class="fa-solid fa-magnifying-glass"></i> Search in MISP
                            </button>
                        </template>
                        <button class="btn btn-outline-danger" @click="remove_connector(instance.case_task_instance_id)">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                        <button v-if="is_case" type="button" class="btn btn-outline-secondary ms-1"
                                :title="expanded_log_row === instance.case_task_instance_id ? 'Hide sync history' : 'Show sync history'"
                                @click="toggle_sync_logs(instance.case_task_instance_id)">
                            <i :class="expanded_log_row === instance.case_task_instance_id ? 'fa-solid fa-chevron-up' : 'fa-solid fa-clock-rotate-left'"></i>
                        </button>
                    </td>
                </tr>
                
                <tr v-if="can_edit_object && instance.is_misp_connector && instance.details.type == 'receive_from' && get_misp_search(instance.case_task_instance_id).open">
                    <td colspan="6" style="background-color: #f8f9fa;">
                        <div class="p-2">
                            <div class="alert alert-info border-0 py-2 px-3 mb-2 d-flex align-items-start" style="background-color: #eaf4fb;">
                                <i class="fa-solid fa-circle-info mt-1 me-2 text-primary"></i>
                                <small class="mb-0">
                                    Searches <strong>attributes</strong> on this MISP instance using a <strong>partial match</strong> (e.g. <code>example.com</code> matches <code>https://example.com/foo</code>).
                                    Use <code>%</code> for explicit wildcard patterns.
                                    Results include attributes from both published and unpublished events &mdash; you can then append the table to your notes in one click.
                                </small>
                            </div>
                            <form @submit.prevent="submit_misp_search(instance)" class="d-flex align-items-center mb-2">
                                <input type="text" class="form-control me-2" placeholder="Search attributes in MISP..." v-model="get_misp_search(instance.case_task_instance_id).query" :disabled="get_misp_search(instance.case_task_instance_id).loading">
                                <button type="submit" class="btn btn-primary" :disabled="get_misp_search(instance.case_task_instance_id).loading || !get_misp_search(instance.case_task_instance_id).query.trim()">
                                    <template v-if="get_misp_search(instance.case_task_instance_id).loading">
                                        <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                        <span role="status">Searching...</span>
                                    </template>
                                    <template v-else>Submit</template>
                                </button>
                            </form>

                            <template v-if="get_misp_search(instance.case_task_instance_id).has_searched && !get_misp_search(instance.case_task_instance_id).loading">
                                <template v-if="get_misp_search(instance.case_task_instance_id).results.length">
                                    <div class="table-responsive">
                                        <table class="table table-sm table-bordered">
                                            <thead>
                                                <tr>
                                                    <th>Event ID</th>
                                                    <th title="Whether the event has been published in MISP">Published</th>
                                                    <th>Organisation</th>
                                                    <th>Event title</th>
                                                    <th>Date</th>
                                                    <th>Attribute type</th>
                                                    <th>Attribute category</th>
                                                    <th>Value</th>
                                                    <th title="to_ids flag in MISP">IDS</th>
                                                    <th>Comment</th>
                                                    <th>Tags</th>
                                                </tr>
                                            </thead>
                                            <tbody>
                                                <tr v-for="r in get_misp_search(instance.case_task_instance_id).results">
                                                    <td>
                                                        <a :href="(instance.details.url.endsWith('/') ? instance.details.url : instance.details.url + '/') + 'events/view/' + r.event_id" target="_blank">[[r.event_id]]</a>
                                                    </td>
                                                    <td>
                                                        <span v-if="r.event_published" class="badge bg-success">yes</span>
                                                        <span v-else class="badge bg-warning text-dark">no</span>
                                                    </td>
                                                    <td>[[r.organisation]]</td>
                                                    <td>[[r.event_info]]</td>
                                                    <td>[[r.date]]</td>
                                                    <td>[[r.attribute_type]]</td>
                                                    <td>[[r.attribute_category]]</td>
                                                    <td>[[r.attribute_value]]</td>
                                                    <td>
                                                        <span v-if="r.to_ids" class="badge bg-success" title="to_ids = true">yes</span>
                                                        <span v-else class="badge bg-secondary" title="to_ids = false">no</span>
                                                    </td>
                                                    <td>[[r.comment]]</td>
                                                    <td>
                                                        <span v-for="t in r.tags" class="badge bg-secondary me-1">[[t]]</span>
                                                    </td>
                                                </tr>
                                            </tbody>
                                        </table>
                                    </div>
                                    <div class="d-flex justify-content-end">
                                        <button class="btn btn-outline-success btn-sm" @click="add_results_to_note(instance)" :disabled="get_misp_search(instance.case_task_instance_id).appending">
                                            <template v-if="get_misp_search(instance.case_task_instance_id).appending">
                                                <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                                Adding...
                                            </template>
                                            <template v-else>
                                                <i class="fa-solid fa-plus"></i> Add as a [[ is_case ? 'case' : 'task' ]] note
                                            </template>
                                        </button>
                                    </div>
                                </template>
                                <div v-else class="text-muted"><i>No results found.</i></div>
                            </template>
                        </div>
                    </td>
                </tr>
                <!-- Inline sync log row -->
                <tr v-if="is_case && expanded_log_row === instance.case_task_instance_id">
                    <td colspan="7" class="p-0">
                        <div class="p-3 bg-body-secondary border-top border-bottom">
                            <div v-if="sync_logs_map[instance.case_task_instance_id]?.loading" class="text-muted small">
                                <span class="spinner-border spinner-border-sm me-2"></span>Loading sync history…
                            </div>
                            <div v-else-if="!sync_logs_map[instance.case_task_instance_id]?.logs?.length" class="text-muted small">
                                No sync history yet for this connector.
                            </div>
                            <div v-else>
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
                                        <tr v-for="log in sync_logs_map[instance.case_task_instance_id].logs" :key="log.id" style="font-size:0.85em;">
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
                        </div>
                    </td>
                </tr>
                </template>
            </tbody>
        </table>
        </template><!-- end page 1 -->

        <!-- PAGE 2: Add connector form (inline, no separate modal) -->
        <template v-else-if="show_add_page">
            <div class="d-flex align-items-center mb-3 pb-2 border-bottom">
                <button type="button" class="btn btn-link p-0 me-3 text-decoration-none text-body" @click="show_add_page = false" title="Back to connectors list">
                    <i class="fa-solid fa-arrow-left fa-lg"></i>
                </button>
                <span class="fw-semibold">Add Connectors</span>
            </div>
            <div class="w-50">
                <select data-placeholder="Connectors" class="select2-connect form-control" multiple name="connectors_select" :id="'connectors_select_'+modal_identifier">
                    <template v-if="all_connectors_list">
                        <template v-for="(instances, connector) in all_connectors_list">
                            <optgroup :label="[[connector]]">
                                <option :value="[[instance.id]]" v-for="instance in instances">[[instance.name]]</option>
                            </optgroup>
                        </template>
                    </template>
                </select>
            </div>
            <div class="row mt-3" v-if="connectors_selected && connectors_selected.length">
                <div class="mb-3 col-md-3" v-for="instance in connectors_selected">
                    <label :for="'identifier_' + instance.id">[[instance.name]] Complement</label>
                    <input :id="'identifier_' + instance.id" class="form-control" :name="'identifier_' + instance.id" type="text">
                </div>
            </div>
            <div class="d-flex justify-content-end gap-2 mt-3">
                <button type="button" class="btn btn-secondary" @click="show_add_page = false">
                    <i class="fa-solid fa-arrow-left me-1"></i>Cancel
                </button>
                <button type="button" class="btn btn-primary" @click="save_connector()">
                    Save
                </button>
            </div>
        </template><!-- end page 2 -->

        <!-- PAGE 3: Edit connector form (inline) -->
        <template v-else-if="show_edit_page && edit_instance">
            <div class="d-flex align-items-center mb-3 pb-2 border-bottom">
                <button type="button" class="btn btn-link p-0 me-3 text-decoration-none text-body" @click="show_edit_page = false; edit_instance = null" title="Back to connectors list">
                    <i class="fa-solid fa-arrow-left fa-lg"></i>
                </button>
                <span class="fw-semibold">Edit Connector</span>
            </div>
            <div class="mb-3">
                <small class="text-muted">Instance name</small>
                <div class="fw-semibold">[[ edit_instance.details.name ]]</div>
            </div>
            <div class="mb-3">
                <small class="text-muted">Instance URL</small>
                <div class="fw-semibold">[[ edit_instance.details.url ]]</div>
            </div>
            <div class="form-floating col-md-6">
                <input :id="'input-edit-connector-'+modal_identifier" class="form-control" :value="edit_instance.identifier">
                <label>Identifier</label>
            </div>
            <div class="d-flex justify-content-end gap-2 mt-3">
                <button type="button" class="btn btn-secondary" @click="show_edit_page = false; edit_instance = null">
                    <i class="fa-solid fa-arrow-left me-1"></i>Cancel
                </button>
                <button type="button" class="btn btn-primary" @click="edit_connector()">
                    Save
                </button>
            </div>
        </template><!-- end page 3 -->

        <!-- PAGE 4: Send to modules (inline) -->
        <template v-else-if="show_send_page && send_to_instance">
            <div class="d-flex align-items-center mb-3 pb-2 border-bottom">
                <button type="button" class="btn btn-link p-0 me-3 text-decoration-none text-body" @click="show_send_page = false" title="Back to connectors list">
                    <i class="fa-solid fa-arrow-left fa-lg"></i>
                </button>
                <span class="fw-semibold">Send to</span>
            </div>
            <div class="d-flex align-items-center gap-2 mb-3 p-2 border rounded bg-body-secondary">
                <img :src="'/static/icons/'+send_to_instance.details.icon" style="max-width:32px;">
                <div>
                    <div class="fw-semibold">[[ send_to_instance.details.name ]]</div>
                    <a :href="send_to_instance.details.url" class="text-muted small" target="_blank">[[ send_to_instance.details.url ]]</a>
                </div>
            </div>
            <!-- MISP connector: use full MispSyncPanel -->
            <template v-if="send_to_instance.is_misp_connector">
                <misp-sync-panel
                    :ref="el => sync_panel_ref = el"
                    :case_id="object_id"
                    :instance="sync_panel_instance"
                    :direction="sync_panel_direction"
                    :modules="modules"
                    @sync_done="(e) => { on_sync_done(e); show_send_page = false }"
                    @close="show_send_page = false">
                </misp-sync-panel>
            </template>
            <!-- Non-MISP connector: simple module select -->
            <template v-else>
            <div>
                <label :for="'modules_select_'+modal_identifier">Modules:</label>
                <select data-placeholder="Modules" class="select2-module form-control" name="modules_select" :id="'modules_select_'+modal_identifier">
                    <option value="None">--</option>
                    <template v-for="module, key in modules">
                        <option v-if="module.type == 'send_to'" :value="[[key]]">[[key]]</option>
                    </template>
                </select>
                <div id="modules_errors" class="invalid-feedback"></div>
                <div class="case-core-style mt-3" v-if="Object.keys(module_selected).length">
                    <b>Module Description:</b><br>
                    <p style="white-space: pre-wrap; word-wrap: break-word; margin-top: 5px">[[module_selected.description]]</p>
                </div>
            </div>
            <template v-if="selected_send_module_name === 'misp_object_event' && case_misp_objects.length > 0">
                <hr>
                <div>
                    <b>Select objects to send:</b>
                    <div class="mt-1">
                        <div v-for="obj in case_misp_objects" :key="obj.object_id" class="form-check">
                            <input class="form-check-input" type="checkbox" :value="obj.object_id" v-model="selected_send_ids" :id="'send-obj-'+modal_identifier+'-'+obj.object_id">
                            <label class="form-check-label" :for="'send-obj-'+modal_identifier+'-'+obj.object_id">
                                <span class="fw-semibold">[[obj.object_name]]</span>
                                <span class="text-muted ms-2 small">([[obj.attributes.length]] attribute<template v-if="obj.attributes.length !== 1">s</template>)</span>
                            </label>
                        </div>
                    </div>
                </div>
            </template>
            <div class="d-flex justify-content-end gap-2 mt-3">
                <button type="button" class="btn btn-secondary" @click="show_send_page = false">
                    <i class="fa-solid fa-arrow-left me-1"></i>Cancel
                </button>
                <button v-if="is_sending" class="btn btn-primary" type="button" disabled>
                    <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                    <span role="status">Loading...</span>
                </button>
                <button v-else type="button" @click="submit_module()" class="btn btn-primary">Submit</button>
            </div>
            </template><!-- end non-MISP -->
        </template><!-- end page 4 -->

        <!-- PAGE 5: Receive from modules (inline) -->
        <template v-else-if="show_receive_page && receive_from_instance">
            <div class="d-flex align-items-center mb-3 pb-2 border-bottom">
                <button type="button" class="btn btn-link p-0 me-3 text-decoration-none text-body" @click="show_receive_page = false" title="Back to connectors list">
                    <i class="fa-solid fa-arrow-left fa-lg"></i>
                </button>
                <span class="fw-semibold">Receive from</span>
            </div>
            <div class="d-flex align-items-center gap-2 mb-3 p-2 border rounded bg-body-secondary">
                <img :src="'/static/icons/'+receive_from_instance.details.icon" style="max-width:32px;">
                <div>
                    <div class="fw-semibold">[[ receive_from_instance.details.name ]]</div>
                    <a :href="receive_from_instance.details.url" class="text-muted small" target="_blank">[[ receive_from_instance.details.url ]]</a>
                </div>
            </div>
            <!-- MISP connector: use full MispSyncPanel -->
            <template v-if="receive_from_instance.is_misp_connector">
                <misp-sync-panel
                    :ref="el => sync_panel_ref = el"
                    :case_id="object_id"
                    :instance="sync_panel_instance"
                    :direction="sync_panel_direction"
                    :modules="modules"
                    @sync_done="(e) => { on_sync_done(e); show_receive_page = false }"
                    @close="show_receive_page = false">
                </misp-sync-panel>
            </template>
            <!-- Non-MISP connector: simple module select -->
            <template v-else>
            <div>
                <label :for="'modules_select_receive_'+modal_identifier">Modules:</label>
                <select data-placeholder="Modules" class="select2-module-receive form-control" name="modules_select_receive" :id="'modules_select_receive_'+modal_identifier">
                    <option value="None">--</option>
                    <template v-for="module, key in modules">
                        <option v-if="module.type == 'receive_from'" :value="[[key]]">[[key]]</option>
                    </template>
                </select>
                <div id="modules_errors_receive" class="invalid-feedback"></div>
                <div class="case-core-style mt-3" v-if="Object.keys(module_selected).length">
                    <b>Module Description:</b><br>
                    <p style="white-space: pre-wrap; word-wrap: break-word; margin-top: 5px">[[module_selected.description]]</p>
                </div>
            </div>
            <template v-if="selected_receive_module_name === 'receive_misp_object'">
                <hr>
                <div class="mb-2">
                    <button v-if="!is_loading_objects" type="button" class="btn btn-sm btn-outline-secondary" @click="fetch_remote_objects()">
                        <i class="fa-solid fa-rotate me-1"></i>Load objects from MISP
                    </button>
                    <button v-else type="button" class="btn btn-sm btn-outline-secondary" disabled>
                        <span class="spinner-border spinner-border-sm me-1" aria-hidden="true"></span>Loading...
                    </button>
                </div>
                <div v-if="is_loading_objects" class="text-muted"><span class="spinner-border spinner-border-sm me-1"></span>Loading objects from MISP...</div>
                <div v-else-if="remote_misp_objects.length > 0">
                    <b>Select objects to receive:</b>
                    <div class="mt-1">
                        <div v-for="obj in remote_misp_objects" :key="obj.uuid" class="form-check">
                            <input class="form-check-input" type="checkbox" :value="obj.uuid" v-model="selected_receive_uuids" :id="'recv-obj-'+modal_identifier+'-'+obj.uuid">
                            <label class="form-check-label" :for="'recv-obj-'+modal_identifier+'-'+obj.uuid">
                                <span class="fw-semibold">[[obj.name]]</span>
                                <span class="text-muted ms-2 small">([[obj.attribute_count]] attribute<template v-if="obj.attribute_count !== 1">s</template>)</span>
                                <span v-if="obj.attributes_preview.length" class="text-muted ms-2 small">&mdash; <template v-for="(a, i) in obj.attributes_preview"><template v-if="i > 0">, </template>[[a.relation]]: [[a.value]]</template></span>
                            </label>
                        </div>
                    </div>
                </div>
                <div v-else-if="!is_loading_objects" class="text-muted small">No objects found in the remote event, or no identifier configured.</div>
            </template>
            <div class="d-flex justify-content-end gap-2 mt-3">
                <button type="button" class="btn btn-secondary" @click="show_receive_page = false">
                    <i class="fa-solid fa-arrow-left me-1"></i>Cancel
                </button>
                <button v-if="is_sending" class="btn btn-primary" type="button" disabled>
                    <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                    <span role="status">Loading...</span>
                </button>
                <button v-else type="button" @click="submit_receive_module()" class="btn btn-primary">Submit</button>
            </div>
            </template><!-- end non-MISP -->
        </template><!-- end page 5 -->


    `
}