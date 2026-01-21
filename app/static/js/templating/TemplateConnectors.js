import {display_toast} from '../toaster.js'
const { ref, onMounted } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        template_connectors_list: Object,
        all_connectors_list: Object,
        is_case: Boolean,
        object_id: Number,
        cases_info: Object
    },
    emits: ['case_connectors', 'task_connectors'],
    setup(props, {emit}) {
        const connector_instances_selected = ref([])
        const edit_instance = ref()

        let modal_indentifier = ""
        if(props.is_case){
            modal_indentifier = "case-" + props.object_id
        }else{
            modal_indentifier = "task-" + props.object_id
        }

        async function add_connector(){
            let connector_dict = []
            for(let i in connector_instances_selected.value){
                connector_dict.push({
                    "id": connector_instances_selected.value[i].id,
                    "name": connector_instances_selected.value[i].name,
                    "identifier": $("#identifier_"+connector_instances_selected.value[i].id).val()
                })
            }

            let url
            if(props.is_case){
                url = "/templating/"+ window.location.pathname.split("/").slice(-1) +"/add_connector"
            }else{
                url = "/templating/task/"+props.object_id+"/add_connector"
            }

            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "connector_instances": connector_dict
                })
            })
            if(await res.status==200){
                connector_instances_selected.value = []
                if (props.is_case){
                    emit("case_connectors", true)
                }else{
                    emit("task_connectors", true)
                }
                $("#modal-add-connectors-"+modal_indentifier).modal("hide");
            }
            display_toast(res)
        }

        async function remove_connector(element_instance_id) {
            let url
            if(props.is_case){
                url = "/templating/connectors/"+element_instance_id+"/remove_connector"
            }else{
                url = "/templating/task/"+props.object_id+"/remove_connector/"+element_instance_id
            }

            const res = await fetch(url)
            if(await res.status==200){
                let loc
                for(let i in props.template_connectors_list){
                    if(props.template_connectors_list[i].template_instance_id == element_instance_id){
                        loc = i
                        break
                    }
                }
                props.template_connectors_list.splice(loc, 1)
            }
            display_toast(res)
        }

        function edit_instance_open_modal(instance){
            edit_instance.value = instance
            var myModal = new bootstrap.Modal(document.getElementById("modal-edit-connectors-"+modal_indentifier), {});
            myModal.show();
        }

        async function edit_connector(){
            let url
            if(props.is_case){
                url = "/templating/connectors/"+edit_instance.value.template_instance_id+"/edit_connector"
            }else{
                url = "/templating/task/"+props.object_id+"/edit_connector/"+edit_instance.value.template_instance_id
            }

            let loc_indentifier = $("#input-edit-connector").val()
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "identifier": loc_indentifier
                })
            });
            if(await res.status==200){
                for (let i in props.template_connectors_list){
                    if (props.template_connectors_list[i].template_instance_id == edit_instance.value.template_instance_id){
                        props.template_connectors_list[i].identifier = loc_indentifier
                    }
                }
                edit_instance.value = {}
                $("#modal-edit-connectors-"+modal_indentifier).modal("hide");
            }
            display_toast(res)
        }


        onMounted(() => {
            $('.select2-connect').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-add-connectors-"+modal_indentifier)
            })

            $('#connectors_select_'+modal_indentifier).on('change.select2', function (e) {
                connector_instances_selected.value = []
                let id_connector_instances_selected = $(this).select2('data').map(item => item.id)

                for(let i in id_connector_instances_selected){                    
                    for(let connectors in props.all_connectors_list){
                        for(let connector in props.all_connectors_list[connectors]){
                            if(id_connector_instances_selected[i] == props.all_connectors_list[connectors][connector].id){
                                connector_instances_selected.value.push({
                                    "id": props.all_connectors_list[connectors][connector].id,
                                    "name": props.all_connectors_list[connectors][connector].name,
                                    "identifier": props.all_connectors_list[connectors][connector].identifier
                                })
                            }
                        }
                    }
                }    
            })
        })

        return {
            connector_instances_selected,
            edit_instance,
            modal_indentifier,
            
            add_connector,
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
        <div class="card card-body">
            <div>
                <button class="btn btn-outline-primary" data-bs-toggle="modal" :data-bs-target="'#modal-add-connectors-'+modal_indentifier">
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
                    <tr v-for="instance in template_connectors_list">
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

                        <td>
                            <button class="btn btn-outline-primary" @click="edit_instance_open_modal(instance)"> <i class="fa-solid fa-pen-to-square"></i> </button>
                            <button class="btn btn-outline-danger" @click="remove_connector(instance.template_instance_id)"> <i class="fa-solid fa-trash"></i> </button>
                        </td>
                    </tr>
                </tbody>
            </table>
        </div>

        <!-- Add Connectors -->
        <div class="modal fade" :id="'modal-add-connectors-'+modal_indentifier" tabindex="-1" aria-labelledby="AddConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog modal-xl">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="AddConnectorsLabel">Add Connectors</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="w-50">
                            <select data-placeholder="Connectors" class="select2-connect form-control" multiple name="connectors_select" :id="'connectors_select_'+modal_indentifier" >
                                <template v-if="all_connectors_list">
                                    <template v-for="(instances, connector) in all_connectors_list">
                                        <optgroup :label="[[connector]]">
                                            <option :value="[[instance.id]]" v-for="instance in instances">[[instance.name]]</option>
                                        </optgroup>
                                    </template>
                                </template>
                            </select>
                        </div>
                        <div class="row" v-if="connector_instances_selected">
                            <div class="mb-3 w-25" v-for="c_i_s in connector_instances_selected" >
                                <label :for="'identifier_' + c_i_s.id">[[c_i_s.name]] Complement</label>
                                <input :id="'identifier_' + c_i_s.id" class="form-control" :name="'identifier_' + c_i_s.id" type="text">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" @click="add_connector()">
                            Save
                        </button>
                    </div>
                </div>
            </div>
        </div>


        <!-- Edit Connectors -->
        <div class="modal fade" :id="'modal-edit-connectors-'+modal_indentifier" tabindex="-1" aria-labelledby="EditConnectorsLabel" aria-hidden="true">
            <div class="modal-dialog">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="EditConnectorsLabel">Edit Connectors</h1>
                        <button type="button" class="btn-close" aria-label="Cancel"></button>
                    </div>
                    <div class="modal-body">
                        <b>Identifier</b>
                        <input type="text" v-if="edit_instance" :value="edit_instance.identifier" id="input-edit-connector">
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
    `
}
