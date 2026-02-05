import { display_toast } from '../toaster.js'
const { ref, onMounted } = Vue
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
    emits: ['case_connectors', 'task_connectors'],
    setup(props, { emit }) {
        const is_sending = ref(false)
        const connectors_selected = ref([])
        const edit_instance = ref()
        const send_to_instance = ref()
        const module_selected = ref({})
        const is_loading_update = ref(false)

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
                url = "/case/" + window.location.pathname.split("/").slice(-1) + "/add_connector"
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
                url = "/case/" + window.location.pathname.split("/").slice(-1) + "/connectors/" + element_instance_id + "/remove_connector"
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
            let loc_update_from_misp = false
            if (props.is_case) {
                url = "/case/" + window.location.pathname.split("/").slice(-1) + "/connectors/" + edit_instance.value.case_task_instance_id + "/edit_connector"
                loc_update_from_misp = $("#checkbox-update-misp-" + modal_identifier).is(":checked")
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
                    "identifier": loc_identifier,
                    "update_from_misp": loc_update_from_misp
                })
            });
            if (await res.status == 200) {
                for (let i in props.case_task_connectors_list) {
                    if (props.case_task_connectors_list[i].case_task_instance_id == edit_instance.value.case_task_instance_id) {
                        props.case_task_connectors_list[i].identifier = loc_identifier
                        if (loc_update_from_misp) {
                            props.case_task_connectors_list[i].is_updating_case = true
                        } else {
                            props.case_task_connectors_list[i].is_updating_case = false
                        }
                    }
                }
                if (props.is_case) {
                    if (loc_update_from_misp) {
                        props.cases_info.case.is_updated_from_misp = true
                    } else {
                        props.cases_info.case.is_updated_from_misp = false
                    }
                }
                edit_instance.value = {}
                $("#modal-edit-connectors-" + modal_identifier).modal("hide");

            }
            display_toast(res)

        }

        function send_to_modal(instance) {
            send_to_instance.value = instance
            var myModal = new bootstrap.Modal(document.getElementById("modal-send-to-" + modal_identifier), {});
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
                url = "/case/" + window.location.pathname.split("/").slice(-1) + "/call_module_case"
            } else {
                url = "/case/" + window.location.pathname.split("/").slice(-1) + "/task/" + props.object_id + "/call_module_task"
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
            }

            display_toast(res, true)
        }

        async function update_case(instance_id) {
            is_loading_update.value = true
            let url = '/case/' + props.cases_info.case.id + '/update_case/' + instance_id
            const res = await fetch(url)
            if (await res.status == 200) {
                window.location.href = '/case/' + props.cases_info.case.id
            }
            display_toast(res)
            is_loading_update.value = false
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

            $("#modules_select_" + modal_identifier).on('change.select2', function (e) {
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

            save_connector,
            remove_connector,
            edit_instance_open_modal,
            edit_connector,
            send_to_modal,
            submit_module,
            update_case
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
                <tr v-for="instance in case_task_connectors_list">
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
                    </td>
                    <td v-else><i>None</i></td>

                    <td v-if="(!is_case && object_id && cases_info.tasks) ? (cases_info.tasks.find(t => t.id === object_id)?.can_edit && cases_info.present_in_case || cases_info.permission.admin) : (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)">
                        <button class="btn btn-outline-primary" @click="edit_instance_open_modal(instance)"> <i class="fa-solid fa-pen-to-square"></i> </button> 
                        <button v-if="!is_sending" class="btn btn-outline-secondary" @click="send_to_modal(instance)"> Send to </button>
                        <button v-else class="btn btn-outline-secondary" type="button" disabled>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span role="status">Loading...</span>
                        </button>
                        <button class="btn btn-outline-danger" @click="remove_connector(instance.case_task_instance_id)"> <i class="fa-solid fa-trash"></i> </button>
                    </td>

                    <td>
                        <template v-if="instance.is_updating_case">
                            <template v-if="is_loading_update">
                                <button class="btn btn-outline-secondary" type="button" disabled>
                                    <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                    <span class="visually-hidden" role="status">Loading...</span>
                                </button>
                            </template>
                            <template v-else>
                                <button class="btn btn-outline-secondary" @click="update_case(instance.case_task_instance_id)" title="Update case with the event misp">
                                    <i class="fa-solid fa-recycle"></i>
                                </button>
                            </template>
                        </template>
                    </td>
                </tr>
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
                        <button type="button" class="btn-close" aria-label="Cancel"></button>
                    </div>
                    <div class="modal-body" v-if="edit_instance">
                        <div class="form-floating col">
                            <input :id="'input-edit-connector-'+modal_identifier" class="form-control" :value="edit_instance.identifier">
                            <label>Identifier</label>
                        </div>

                         <div v-if="is_case" class="form-check mt-4">
                            <template v-if="!cases_info.case.is_updated_from_misp || edit_instance.is_updating_case">
                                <input class="form-check-input" :checked="edit_instance.is_updating_case" type="checkbox" :id="'checkbox-update-misp-'+modal_identifier" name="option1" value="">
                                <label class="form-check-label">Use to update the case ?</label>
                            </template>
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
    `
}