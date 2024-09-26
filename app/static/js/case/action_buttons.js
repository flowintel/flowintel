import {display_toast} from '../toaster.js'
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		status_info: Object
	},
	setup(props) {

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

		return {
            delete_case,
			complete_case,
            fork_case,
            create_template,
		}
    },
	template: `
		<div v-if="cases_info && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)" style="float:right; display: grid;">
            <a class="btn btn-primary btn-sm"  :href="'/case/'+cases_info.case.id+'/download'" type="button" title="Download the case in json"><i class="fa-solid fa-download"></i></a>
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
    `
}