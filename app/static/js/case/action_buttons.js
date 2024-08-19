import {display_toast} from '../toaster.js'
const { ref, nextTick, onMounted} = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		status_info: Object
	},
	setup(props) {
        const modules = ref()
        const module_selected = ref()
        const instances_selected = ref([])
        const module_loader = ref(false)

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

        async function fetch_module_selected(module){
            // Get modules and instances linked on
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/get_instance_module?type=send_to&module="+module)
            if(await res.status==400 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                module_selected.value = loc["instances"]
                await nextTick()
                $('#instances_select').select2({
                    theme: 'bootstrap-5',
                    width: '50%',
                    closeOnSelect: false
                })
                $('#instances_select').on('change.select2', function (e) {
                    let name_instance = $(this).select2('data').map(item => item.id)
                    instances_selected.value = []
                    for( let index in module_selected.value){
                        if (name_instance.includes(module_selected.value[index].name)){
                            if(!instances_selected.value.includes(module_selected.value[index]))
                                instances_selected.value.push(module_selected.value[index])
                        }
                    }
                })
            }
        }

        async function delete_case(case_id){
            const res = await fetch('/case/' + case_id.toString() + '/delete')
            if (await res.status == 200)
                return window.location.href="/case"
            display_toast(res)
        }

        async function complete_case(case_loc){
            const res = await fetch('/case/' + case_loc.id + '/complete_case')
            if (await res.status == 200){
                if(props.status_info.status[case_loc.status_id -1].name == 'Finished'){
                    for(let i in props.status_info.status){
                        if(props.status_info.status[i].name == 'Created')
                        case_loc.status_id = props.status_info.status[i].id
                    }
                    if(case_loc.status_id == status)
                        case_loc.status_id = 1

                        await fetch('/case/' + case_loc.id + '/change_status',{
                            headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                            method: "POST",
                            body: JSON.stringify({"status": case_loc.status_id})
                        })
                }else{
                    for(let i in props.status_info.status){
                        if(props.status_info.status[i].name == 'Finished'){
                            case_loc.status_id = props.status_info.status[i].id
                            await fetch('/case/' + case_loc.id + '/change_status',{
                                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                                method: "POST",
                                body: JSON.stringify({"status": case_loc.status_id})
                            })
                            break
                        }
                    }
                }
                return window.location.href="/case"
            }
            display_toast(res)
        }

        async function fork_case(case_id){
            if(await fetch_case_title($("#case_title_fork").val())){
                $("#collapseForkBody").append(
                    $("<span>").text("Already exist").css("color", 'red')
                )
            }else{
                const res = await fetch("/case/" + case_id + "/fork",{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({"case_title_fork": $("#case_title_fork").val()})
                })
                let loc = await res.json()
                window.location.href="/case/" + loc["new_case_id"]
            }
        }

        async function fetch_case_title(case_title_fork){
            const res = await fetch("/case/check_case_title_exist?title="+case_title_fork)
            let loc = await res.json()
            if(loc["title_already_exist"]){
                return true
            }
            return false
        }

        async function create_template(case_loc){
            if(await fetch_case_template_title($("#case_title_template").val())){
                $("#collapseTemplateBody").append(
                    $("<span>").text("Already exist").css("color", 'red')
                )
            }else{
                const res = await fetch("/case/" + case_loc.id + "/create_template",{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({"case_title_template": $("#case_title_template").val()})
                })
                let loc = await res.json()
                window.location.href="/tools/template/case/" + loc["template_id"]
            }
        }
        async function fetch_case_template_title(case_title_template){
            const res = await fetch("/case/check_case_template_title_exist?title="+case_title_template)
            let loc = await res.json()
            if(loc["title_already_exist"]){
                return true
            }
            return false
        }

        async function submit_module(){
            module_loader.value = true
            $("#modules_errors").hide()
            $("#instances_errors").hide()
            if(!$("#modules_select").val() || $("#modules_select").val() == "None"){
                $("#modules_errors").text("Select an item")
                $("#modules_errors").show()
            }
            if(!$("#instances_select").val() || $("#instances_select").val().length<1){
                $("#instances_errors").text("Select an item")
                $("#instances_errors").show()
            }

            let i_s = $("#instances_select").val()
            let int_sel = {}
            for(let index in i_s){
                for( let j in module_selected.value){
                    if (module_selected.value[j].name == i_s[index]){
                        let loc_val = $("#identifier_"+module_selected.value[j].id).val()
                        int_sel[module_selected.value[j].name] = loc_val
                        for(let k in instances_selected.value){
                            if(instances_selected.value[k].name == module_selected.value[j].name){
                                instances_selected.value[k].identifier = loc_val
                            }
                        }
                    }
                }
            }
            const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/call_module_case?module=" + $("#modules_select").val() , {
                method: "POST",
                body: JSON.stringify({
                    int_sel
                }),
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                }
            });
            module_loader.value = false

            display_toast(res, true)
        }

        onMounted(() => {
            $('#modules_select').on('select2:select', function (e) {
                if($(this).select2('data').map(item => item.id)[0] == "None"){
                    module_selected.value = []
                }else{
                    fetch_module_selected($(this).select2('data').map(item => item.id))
                }
            })
        })


		return {
            modules,
            module_selected,
            instances_selected,
            module_loader,
            delete_case,
			complete_case,
            fork_case,
            create_template,
            submit_module
		}
    },
	template: `
		<div v-if="cases_info && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)" style="float:right; display: grid;">
            <a class="btn btn-primary btn-sm"  :href="'/case/'+cases_info.case.id+'/download'" type="button" title="Download the case in json"><i class="fa-solid fa-download"></i></a>
            <button type="button" class="btn btn-secondary btn-sm" title="Send to connectors" data-bs-toggle="modal" data-bs-target="#Send_to_modal">
                <i class="fa-solid fa-share-from-square"></i>
            </button>
            <button type="button" class="btn btn-danger btn-sm" title="Delete the case" data-bs-toggle="modal" data-bs-target="#delete_case_modal">
                <i class="fa-solid fa-trash"></i>
            </button>
        </div>
        <div v-if="cases_info && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)" style="float:right">
            <button v-if="cases_info.case.completed" class="btn btn-secondary btn-sm"  @click="complete_case(cases_info.case)" title="Complete the case"><i class="fa-solid fa-backward"></i></button>
            <button v-else class="btn btn-success btn-sm"  @click="complete_case(cases_info.case)" title="Complete the case"><i class="fa-solid fa-check"></i></button>
            <a class="btn btn-primary btn-sm" :href="'/case/edit/'+cases_info.case.id" type="button" title="Edit the case"><i class="fa-solid fa-pen-to-square"></i></a>
            <a class="btn btn-secondary btn-sm"  :href="'/case/'+cases_info.case.id+'/recurring'" type="button" title="Recurring Case"><i class="fa-solid fa-clock"></i></a>

            <button type="button" class="btn btn-secondary btn-sm" data-bs-toggle="dropdown" aria-expanded="false" title="Fork the case">
                <i class="fa-solid fa-code-fork"></i>
            </button>
            <ul class="dropdown-menu">
                <li>
                    <input id="case_title_fork" placeholder="Case title"/>
                    <button class="btn btn-primary btn-sm" @click="fork_case(cases_info.case.id)">Fork</button>
                    <div id="collapseForkBody"></div>
                </li>
            </ul>

            <button type="button" class="btn btn-secondary btn-sm" data-bs-toggle="dropdown" aria-expanded="false" title="Create a template from the case">
                <i class="fa-solid fa-bookmark"></i>
            </button>
            <ul class="dropdown-menu">
                <li>
                    <input id="case_title_template" placeholder="Case title"/>
                    <button class="btn btn-primary btn-sm" @click="create_template(cases_info.case)">Template</button>
                </li>
            </ul>
        </div>
        <br>

        <!-- Modal delete case -->
        <div class="modal fade" id="delete_case_modal" tabindex="-1" aria-labelledby="delete_case_modal" aria-hidden="true">
            <div class="modal-dialog modal-sm">
                <div class="modal-content" v-if="cases_info">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="delete_case_modal">Delete '[[cases_info.case.title]]' ?</h1>
                        <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button class="btn btn-danger btn-sm"  @click="delete_case(cases_info.case.id)"><i class="fa-solid fa-trash"></i> Confirm</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal send to -->
        <div class="modal fade" id="Send_to_modal" tabindex="-1" aria-labelledby="Send_to_modalLabel" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="Send_to_modalLabel">Send to modules</h1>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div style="display: flex;">
                            <div>
                                <label for="modules_select">Modules:</label>
                                <select data-placeholder="Modules" class="select2-select form-control" name="modules_select" id="modules_select" >
                                    <option value="None">--</option>
                                    <template v-for="module, key in modules">
                                        <option v-if="module.type == 'send_to'" :value="[[key]]">[[key]]</option>
                                    </template>
                                </select>
                                <div id="modules_errors" class="invalid-feedback"></div>
                            </div>
                            <div style="min-width: 100%;">
                                <label for="instances_select">Instances:</label>
                                <select data-placeholder="Instances" class="select2-select form-control" multiple name="instances_select" id="instances_select" >
                                    <template v-if="module_selected">
                                        <template v-for="instance, key in module_selected">
                                            <option :value="[[instance.name]]">[[instance.name]]</option>
                                        </template>
                                    </template>
                                </select>
                                <div id="instances_errors" class="invalid-feedback"></div>
                            </div>
                        </div>
                        <div class="row" v-if="instances_selected">
                            <div class="mb-3 w-50" v-for="instance, key in instances_selected" >
                                <label :for="'identifier_' + instance.id">Identifier for <u><i>[[instance.name]]</i></u></label>
                                <input :id="'identifier_' + instance.id" class="form-control" :value="instance.identifier" :name="'identifier_' + instance.id" type="text">
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button v-if="module_loader" class="btn btn-primary" type="button" disabled>
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