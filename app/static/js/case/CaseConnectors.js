import {display_toast, create_message} from '../toaster.js'
const { ref, onMounted } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object
	},
	setup(props) {
        const case_connectors_list = ref([])
        const connectors_list = ref([])
        const is_sending = ref(false)
        const connectors_selected = ref()
        const edit_instance = ref()
        const modules = ref()
        const send_to_instance = ref()

		
        async function fetch_case_connectors(){
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/get_case_connectors")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                case_connectors_list.value = loc["case_connectors"]
            }
        }
        async function fetch_connectors(){
            const res = await fetch("/case/get_connectors")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                connectors_list.value = loc["connectors"]
            }
        }
        fetch_connectors()

        async function fetch_modules(){
            // Get modules and instances linked on
            const res = await fetch("/case/get_case_modules")
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                modules.value = loc["modules"]
            }
        }
        fetch_modules()


        async function save_connector_case(){
            let connector_dict = []
            for(let i in connectors_selected.value){
                let loc = $("#identifier_"+connectors_selected.value[i]).val()
                let loc_key = connectors_selected.value[i]
                connector_dict.push({
                    "name": loc_key,
                    "identifier": loc
                })
            }

            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/add_connector", {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "connectors": connector_dict
                })
            });
            if(await res.status==200){
                connectors_selected.value = []
                await fetch_case_connectors()
                $("#modal-case-add-connectors").modal("hide");
            }
            display_toast(res)
            
        }

        async function remove_connector(instance_id) {
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/connectors/"+instance_id+"/remove_connector")
            if(await res.status==200){
                let loc
                for(let i in case_connectors_list.value){
                    if(case_connectors_list.value[i].id == instance_id){
                        loc = i
                        break
                    }
                }
                case_connectors_list.value.splice(loc, 1)
            }
            display_toast(res)
        }

        function edit_instance_open_modal(instance){
            edit_instance.value = instance

            var myModal = new bootstrap.Modal(document.getElementById("modal-case-edit-connectors"), {});
            myModal.show();
        }

        async function edit_connector(){
            let loc_indentifier = $("#input-case-edit-connector").val()
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/connectors/"+edit_instance.value.id+"/edit_connector", {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "identifier": loc_indentifier
                })
            });
            if(await res.status==200){
                for (let i in case_connectors_list.value){
                    if (case_connectors_list.value[i].id == edit_instance.value.id){
                        case_connectors_list.value[i].identifier = loc_indentifier
                    }
                }
                edit_instance.value = {}
                $("#modal-case-edit-connectors").modal("hide");
            }
            display_toast(res)
            
        }

        function case_send_to_modal(instance){
            send_to_instance.value=instance
            var myModal = new bootstrap.Modal(document.getElementById("modal-case-send-to"), {});
            myModal.show();
        }

        async function submit_module(){
            is_sending.value = true
            $("#modules_errors").hide()
            let modules_select = $("#case_modules_select").val()

            if(!modules_select || modules_select == "None"){
                $("#modules_errors").text("Select an item")
                $("#modules_errors").show()
            }

            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/call_module_case", {
                method: "POST",
                body: JSON.stringify({
                    "module": modules_select,
                    "instance_id": send_to_instance.value.id
                }),
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                }
            });
            is_sending.value = false

            if (await res.status==200){
                $("#modal-case-send-to").modal("hide");
            }

            display_toast(res, true)
        }


		onMounted(() => {
            fetch_case_connectors()

            $('.select2-case-connect').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-case-add-connectors")
            })
            $('.select2-case-module').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-case-send-to")
            })
            $('.select2-case-module').css("min-width", "200px")

            $('#case_connectors_select').on('change.select2', function (e) {
                connectors_selected.value = $(this).select2('data').map(item => item.id)
            })
            
        })

		return {
            case_connectors_list,
            connectors_list,
            is_sending,
            connectors_selected,
            edit_instance,
            modules,

            save_connector_case,
            remove_connector,
            edit_instance_open_modal,
            edit_connector,
            case_send_to_modal,
            submit_module
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
        <div class="collapse" id="collapseConnectors">
            <div class="card card-body">
                <div>
                    <button class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#modal-case-add-connectors">
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
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="instance in case_connectors_list">
                            <td>
                                <div :title="instance.description">
                                    <img :src="'/static/icons/'+instance.icon" style="max-width: 30px;">
                                    [[instance.name]]
                                </div>
                            </td>
                            <td>
                                <a style="margin-left: 5px" :href="instance.url">[[instance.url]]</a>
                            </td>

                            <td v-if="instance.type">
                                <span style="margin-left: 3px;" title="type of the module">[[instance.type]]</span>
                            </td>
                            <td v-else><i>None</i></td>

                            <td v-if="instance.identifier">
                                <span style="margin-left: 3px;" title="identifier used by module">[[instance.identifier]]</span>
                            </td>
                            <td v-else><i>None</i></td>

                            <td>
                                <button class="btn btn-outline-primary" @click="edit_instance_open_modal(instance)"> <i class="fa-solid fa-pen-to-square"></i> </button> 
                                <button v-if="!is_sending" class="btn btn-outline-secondary" @click="case_send_to_modal(instance)"> Send to </button>
                                <button v-else class="btn btn-outline-secondary" type="button" disabled>
                                    <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                    <span role="status">Loading...</span>
                                </button>
                                <button class="btn btn-outline-danger" @click="remove_connector(instance.id)"> <i class="fa-solid fa-trash"></i> </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <!-- Add Connectors -->
        <div class="modal fade" id="modal-case-add-connectors" tabindex="-1" aria-labelledby="AddConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="AddConnectorsLabel">Add Connectors</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="w-50">
                            <select data-placeholder="Connectors" class="select2-case-connect form-control" multiple name="connectors_select" id="case_connectors_select" >
                                <template v-if="connectors_list">
                                    <template v-for="(instances, connector) in connectors_list">
                                        <optgroup :label="[[connector]]">
                                            <option :value="[[instance.name]]" v-for="instance in instances">[[instance.name]]</option>
                                        </optgroup>
                                    </template>
                                </template>
                            </select>
                        </div>
                        <div class="row" v-if="connectors_selected">
                            <div class="mb-3 w-25" v-for="instance in connectors_selected" >
                                <label :for="'identifier_' + instance">[[instance]] Complement</label>
                                <input :id="'identifier_' + instance" class="form-control" :name="'identifier_' + instance" type="text">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" @click="save_connector_case()">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>


        <!-- Edit Connectors -->
        <div class="modal fade" id="modal-case-edit-connectors" tabindex="-1" aria-labelledby="EditConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="EditConnectorsLabel">Edit Connectors</h1>
                        <button type="button" class="btn-close" aria-label="Cancel"></button>
                    </div>
                    <div class="modal-body">
                        <b>Identifier</b>
                        <input type="text" v-if="edit_instance" :value="edit_instance.identifier" id="input-case-edit-connector">
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
        <div class="modal fade" id="modal-case-send-to" tabindex="-1" aria-labelledby="modal-case-send-toLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="modal-case-send-toLabel">Send to modules</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex;">
                            <div>
                                <label for="case_modules_select">Modules:</label>
                                <select data-placeholder="Modules" class="select2-case-module form-control" name="case_modules_select" id="case_modules_select" style="min-width: 100px" >
                                    <option value="None">--</option>
                                    <template v-for="module, key in modules">
                                        <option v-if="module.type == 'send_to'" :value="[[key]]">[[key]]</option>
                                    </template>
                                </select>
                                <div id="modules_errors" class="invalid-feedback"></div>
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