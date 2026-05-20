import { display_toast, create_message } from '../toaster.js'
const { ref, onMounted, computed, nextTick, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: {
        case_task_connectors_list: Object,
        all_connectors_list: Object,
        modules: Object,
        is_case: Boolean,
        object_id: Number,
        cases_info: Object,
    },
    emits: ['case_connectors', 'task_connectors', 'note_change', 'task_note_added'],
    setup(props, { emit }) {
        const show_add_page = ref(false)
        const show_edit_page = ref(false)
        const connectors_selected = ref([])
        const edit_instance = ref()
        const is_loading_update = ref(false)

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

        onMounted(async () => {
            await nextTick()
            hasJQuery = (typeof $ !== 'undefined')
            hasSelect2 = hasJQuery && $.fn && $.fn.select2
            if (!hasSelect2) {}

            try {
                if (hasSelect2) {
                    // .select2-connect is now inline (no separate modal), so use body as parent
                    $('.select2-connect').select2({ theme: 'bootstrap-5', dropdownParent: $('body') })
                }
            } catch (e) {}

            const connectorsSelectEl = document.getElementById('connectors_select_' + modal_identifier)

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

        return {
            show_add_page,
            show_edit_page,
            connectors_selected,
            edit_instance,
            modal_identifier,
            is_loading_update,
            can_edit_object,

            save_connector,
            remove_connector,
            edit_instance_open_modal,
            edit_connector,
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
        <template v-if="!show_add_page && !show_edit_page">
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
                    <th>Identifier on the instance</th>
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

                    <td v-if="instance.identifier">
                        <span style="margin-left: 3px;" title="identifier used by module">[[instance.identifier]]</span>
                        <template v-if="instance.is_misp_connector">
                            <a style="margin-left: 8px;" :href="(instance.details.url.endsWith('/') ? instance.details.url : instance.details.url + '/') + 'events/view/' + instance.identifier" target="_blank" title="Open MISP event on remote instance">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                        </template>
                    </td>
                    <td v-else><i>None</i></td>

                    <td v-if="can_edit_object">
                        <button class="btn btn-outline-primary" @click="edit_instance_open_modal(instance)">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button> 
                        <button class="btn btn-outline-danger" @click="remove_connector(instance.case_task_instance_id)">
                            <i class="fa-solid fa-trash"></i>
                        </button>
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


    `
}