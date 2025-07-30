import {display_toast} from '../toaster.js'
const { ref, onMounted } = Vue
export default {
    delimiters: ['[[', ']]'],
	setup() {
        const connectors_list = ref();
        const objects_connectors_list = ref();
        const connectors_selected = ref([])
        const edit_instance = ref()
        const is_sending = ref(false)

        async function fetch_misp_connectors(){
            const res = await fetch("/case/misp_connectors")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                connectors_list.value = loc["misp_connectors"]
            }
        }
        fetch_misp_connectors()

        async function fetch_objects_misp_connectors(){
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/misp_object_connectors")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                objects_connectors_list.value = loc
            }
        }
        fetch_objects_misp_connectors()

        async function save_connector_object(){
            let connector_dict = []
            for(let i in connectors_selected.value){
                let loc = $("#identifier_"+connectors_selected.value[i].id).val()
                let loc_key = connectors_selected.value[i].name
                connector_dict.push({
                    "name": loc_key,
                    "identifier": loc
                })
            }

            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/add_misp_object_connector", {
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
                await fetch_objects_misp_connectors()
            }
            display_toast(res)
            
        }

        async function remove_connector(instance_id) {
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/misp_object_connectors/"+instance_id+"/remove_connector")
            if(await res.status==200){
                let loc
                for(let i in objects_connectors_list.value){
                    if(objects_connectors_list.value[i].object_instance_id == instance_id){
                        loc = i
                        break
                    }
                }
                objects_connectors_list.value.splice(loc, 1)
            }
            display_toast(res)
        }

        async function edit_connector_object(){
            let loc_indentifier = $("#input-edit-connector").val()
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/misp_object_connectors/"+edit_instance.value.object_instance_id+"/edit_connector", {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "identifier": loc_indentifier
                })
            });
            if(await res.status==200){
                for (let i in objects_connectors_list.value){
                    if (objects_connectors_list.value[i].object_instance_id == edit_instance.value.object_instance_id){
                        objects_connectors_list.value[i].identifier = loc_indentifier
                    }
                }
                edit_instance.value = {}
                $("#modal-edit-connectors").modal("hide");
            }
            display_toast(res)
            
        }

        function edit_instance_open_modal(instance){
            edit_instance.value = instance

            $("#modal-send-to").modal("hide");

            var myModal = new bootstrap.Modal(document.getElementById("modal-edit-connectors"), {});
            myModal.show();
        }

        async function send_to_action(instance_id) {
            is_sending.value = true
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/misp_object_connectors/"+instance_id+"/call_module_misp")

            display_toast(res, true)
            is_sending.value = false
        }

		onMounted(() => {
            $('.select2-select-connect').select2({
                theme: 'bootstrap-5'
            })

            $('#object_connectors_select').on('change.select2', function (e) {
                connectors_selected.value = []
                let loc = $(this).select2('data').map(item => item.id)
                
                for(let element in loc){
                    for(let connectors in connectors_list.value){
                            if(loc[element] == connectors_list.value[connectors].id){
                                connectors_selected.value.push({
                                    "id": connectors_list.value[connectors].id,
                                    "name": connectors_list.value[connectors].name
                                })
                            }
                        // }
                    }
                }
            })
        })

		return {
            connectors_list,
            objects_connectors_list,
            connectors_selected,
            edit_instance,
            is_sending,
            save_connector_object,
            remove_connector,
            edit_connector_object,
            edit_instance_open_modal,
            send_to_action
		}
    },
	template: `
        <div class="modal fade" id="modal-send-to" tabindex="-1" aria-labelledby="SendToLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="SendToLabel">Send to MISP</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <button class="btn btn-outline-primary" data-bs-toggle="modal" data-bs-target="#modal-add-misp-connectors">
                            <i class="fa-solid fa-plus"></i>
                        </button>
                        <table class="table" v-if="objects_connectors_list && objects_connectors_list.length">
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
                                <template v-for="instance in objects_connectors_list">
                                    <tr >
                                        <td>
                                            <div :title="instance.details.description">
                                                <img :src="'/static/icons/'+instance.details.icon" style="max-width: 30px;">
                                                [[instance.details.name]]
                                            </div>
                                        </td>
                                        <td>
                                            <a style="margin-left: 5px" :href="instance.details.url">[[instance.details.url]]</a>
                                        </td>
                                        <td v-if="instance.details.type"><span style="margin-left: 3px;" title="type of the module">[[instance.details.type]]</span></td>
                                        <td v-else><i>None</i></td>

                                        <td v-if="instance.identifier"><span style="margin-left: 3px;" title="identifier used by module">[[instance.identifier]]</span></td>
                                        <td v-else><i>None</i></td>

                                        <td>
                                            <button class="btn btn-outline-primary" @click="edit_instance_open_modal(instance)"> <i class="fa-solid fa-pen-to-square"></i> </button> 
                                            <button v-if="!is_sending" class="btn btn-outline-secondary" @click="send_to_action(instance.object_instance_id)"> Send to </button>
                                            <button v-else class="btn btn-outline-secondary" type="button" disabled>
                                                <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                                <span role="status">Loading...</span>
                                            </button>
                                            <button class="btn btn-outline-danger" @click="remove_connector(instance.object_instance_id)"> <i class="fa-solid fa-trash"></i> </button>
                                        </td>
                                    </tr>
                                    
                                </template>
                            </tbody>
                        </table>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Edit Connectors -->
        <div class="modal fade" id="modal-edit-connectors" tabindex="-1" aria-labelledby="EditConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="EditConnectorsLabel">Edit MISP Connectors</h1>
                        <button type="button" class="btn-close" data-bs-toggle="modal" data-bs-target="#modal-send-to" aria-label="Cancel"></button>
                    </div>
                    <div class="modal-body">
                        <b>Identifier</b>
                        <input type="text" v-if="edit_instance" :value="edit_instance.identifier" id="input-edit-connector">
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-toggle="modal" data-bs-target="#modal-send-to">Cancel</button>
                        <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modal-send-to"
                            @click="edit_connector_object()">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>


        <!-- Add Connectors -->
        <div class="modal fade" id="modal-add-misp-connectors" tabindex="-1" aria-labelledby="AddConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="AddConnectorsLabel">Add MISP Connectors</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="w-50">
                            <select data-placeholder="Connectors" class="select2-select-connect form-control" multiple name="connectors_select" id="object_connectors_select" >
                                <template v-if="connectors_list">
                                    <template v-for="instance in connectors_list">
                                        <option v-if="instance.type == 'send_to'" :value="[[instance.id]]">[[instance.name]]</option>
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
                        <button type="button" class="btn btn-secondary" data-bs-toggle="modal" data-bs-target="#modal-send-to">Close</button>
                        <button type="button" class="btn btn-primary" data-bs-toggle="modal" data-bs-target="#modal-send-to"
                            @click="save_connector_object()">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `
}