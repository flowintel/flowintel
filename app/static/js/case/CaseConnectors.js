import { display_toast } from '../toaster.js'
const { ref, reactive, onMounted, computed } = Vue
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
    setup(props, { emit }) {
        const is_sending = ref(false)
        const connectors_selected = ref([])
        const edit_instance = ref()
        const send_to_instance = ref()
        const receive_from_instance = ref()
        const module_selected = ref({})
        const is_loading_update = ref(false)
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
            let connector_dict = []
            for (let i in connectors_selected.value) {
                let loc = $("#identifier_" + connectors_selected.value[i].id).val()

                let loc_key = connectors_selected.value[i].name
                connector_dict.push({
                    "name": loc_key,
                    "identifier": loc
                })
            }

            let url
            if (props.is_case) {
                url = "/case/" + props.object_id + "/add_connector"
            } else {
                url = "/case/task/" + props.object_id + "/add_connector"
            }

            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "connectors": connector_dict
                })
            });
            if (await res.status == 200) {
                connectors_selected.value = []
                if (props.is_case) {
                    emit("case_connectors", true)
                } else {
                    emit("task_connectors", true)
                }
                $("#modal-add-connectors-" + modal_identifier).modal("hide");
            }
            display_toast(res)

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
            var myModal = new bootstrap.Modal(document.getElementById("modal-edit-connectors-" + modal_identifier), {});
            myModal.show();
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
                $("#modal-edit-connectors-" + modal_identifier).modal("hide");
                edit_instance.value = null

            }
            display_toast(res)

        }

        function send_to_modal(instance) {
            send_to_instance.value = instance
            var myModal = new bootstrap.Modal(document.getElementById("modal-send-to-" + modal_identifier), {});
            myModal.show();
        }

        function receive_from_modal(instance) {
            receive_from_instance.value = instance
            var myModal = new bootstrap.Modal(document.getElementById("modal-receive-from-" + modal_identifier), {});
            myModal.show();
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

            const res = await fetch(url, {
                method: "POST",
                body: JSON.stringify({
                    "module": modules_select,
                    "case_task_instance_id": send_to_instance.value.case_task_instance_id
                }),
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                }
            });
            is_sending.value = false

            if (await res.status == 200) {
                $("#modal-send-to-" + modal_identifier).modal("hide");
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

            const res = await fetch(url, {
                method: "POST",
                body: JSON.stringify({
                    "module": modules_select,
                    "case_task_instance_id": receive_from_instance.value.case_task_instance_id
                }),
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                }
            });
            is_sending.value = false

            if (await res.status == 200) {
                $("#modal-receive-from-" + modal_identifier).modal("hide");
                if (props.is_case) {
                    emit("case_connectors", true)
                } else {
                    emit("task_connectors", true)
                }
            }

            display_toast(res)
        }

        onMounted(() => {
            $('.select2-connect').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-add-connectors-" + modal_identifier)
            })
            $('.select2-module').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-send-to-" + modal_identifier)
            })
            $('.select2-module-receive').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-receive-from-" + modal_identifier)
            })

            $("#modules_select_" + modal_identifier).on('change.select2', function (e) {
                let loc = $(this).select2('data').map(item => item.id)

                for (let i in props.modules) {
                    if (loc == i) {
                        module_selected.value = props.modules[i].config
                        break
                    }
                }

            })

            $("#modules_select_receive_" + modal_identifier).on('change.select2', function (e) {
                let loc = $(this).select2('data').map(item => item.id)

                for (let i in props.modules) {
                    if (loc == i) {
                        module_selected.value = props.modules[i].config
                        break
                    }
                }

            })

            $('#connectors_select_' + modal_identifier).on('change.select2', function (e) {
                connectors_selected.value = []
                let loc = $(this).select2('data').map(item => item.id)
                for (let element in loc) {
                    for (let connectors in props.all_connectors_list) {
                        for (let connector in props.all_connectors_list[connectors]) {
                            if (loc[element] == props.all_connectors_list[connectors][connector].id) {
                                connectors_selected.value.push({
                                    "id": props.all_connectors_list[connectors][connector].id,
                                    "name": props.all_connectors_list[connectors][connector].name
                                })
                            }
                        }
                    }
                }
            })

        })

        return {
            is_sending,
            connectors_selected,
            edit_instance,
            modal_identifier,
            module_selected,
            is_loading_update,
            can_edit_object,

            save_connector,
            remove_connector,
            edit_instance_open_modal,
            edit_connector,
            send_to_modal,
            receive_from_modal,
            submit_module,
            submit_receive_module,
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
        <div v-if="(!is_case && object_id && cases_info.tasks) ? (cases_info.tasks.find(t => t.id === object_id)?.can_edit && cases_info.present_in_case || cases_info.permission.admin) : (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)">
            <button class="btn btn-outline-primary" data-bs-toggle="modal" :data-bs-target="'#modal-add-connectors-'+modal_identifier">
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
                    <th></th>
                    <th></th>
                </tr>
            </thead>
            <tbody>
                <template v-for="instance in case_task_connectors_list">
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
                                                    <th>Attribute Type</th>
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
                </template>
            </tbody>
        </table>

        <!-- Add Connectors -->
        <div class="modal fade" :id="'modal-add-connectors-'+modal_identifier" tabindex="-1" aria-labelledby="AddConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="AddConnectorsLabel">Add Connectors</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="w-50">
                            <select data-placeholder="Connectors" class="select2-connect form-control" multiple name="connectors_select" :id="'connectors_select_'+modal_identifier" >
                                <template v-if="all_connectors_list">
                                    <template v-for="(instances, connector) in all_connectors_list">
                                        <optgroup :label="[[connector]]">
                                            <option :value="[[instance.id]]" v-for="instance in instances">[[instance.name]]</option>
                                        </optgroup>
                                    </template>
                                </template>
                            </select>
                        </div>
                        <div class="row" v-if="connectors_selected">
                            <div class="mb-3 w-25" v-for="instance in connectors_selected" >
                                <label :for="'identifier_' + instance.id">[[instance.name]] Complement</label>
                                <input :id="'identifier_' + instance.id" class="form-control" :name="'identifier_' + instance.id" type="text">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" @click="save_connector()">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>


        <!-- Edit Connectors -->
        <div class="modal fade" :id="'modal-edit-connectors-'+modal_identifier" tabindex="-1" aria-labelledby="EditConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="EditConnectorsLabel">Edit Connectors</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cancel"></button>
                    </div>
                    <div class="modal-body" v-if="edit_instance">
                        <div class="mb-3">
                            <small class="text-muted">Instance name</small>
                            <div class="fw-semibold">[[ edit_instance.details.name ]]</div>
                        </div>
                        <div class="mb-3">
                            <small class="text-muted">Instance URL</small>
                            <div class="fw-semibold">[[ edit_instance.details.url ]]</div>
                        </div>
                        <div class="form-floating col">
                            <input :id="'input-edit-connector-'+modal_identifier" class="form-control" :value="edit_instance.identifier">
                            <label>Identifier</label>
                        </div>

                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button type="button" class="btn btn-primary" @click="edit_connector()">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal send to -->
        <div class="modal fade" :id="'modal-send-to-'+modal_identifier" tabindex="-1" aria-labelledby="modal-send-toLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="modal-send-toLabel">Send to modules</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex;">
                            <div>
                                <label for="modules_select">Modules:</label>
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
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button v-if="is_sending" class="btn btn-primary" type="button" disabled>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span role="status">Loading...</span>
                        </button>
                        <button v-else type="button" @click="submit_module()" class="btn btn-primary">Submit</button>
                    </div>
                </div>
            </div>
        </div>


        <!-- Modal receive from -->
        <div class="modal fade" :id="'modal-receive-from-'+modal_identifier" tabindex="-1" aria-labelledby="modal-receive-fromLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="modal-receive-fromLabel">Receive from modules</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex;">
                            <div>
                                <label for="modules_select_receive">Modules:</label>
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
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button v-if="is_sending" class="btn btn-primary" type="button" disabled>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span role="status">Loading...</span>
                        </button>
                        <button v-else type="button" @click="submit_receive_module()" class="btn btn-primary">Submit</button>
                    </div>
                </div>
            </div>
        </div>
    `
}