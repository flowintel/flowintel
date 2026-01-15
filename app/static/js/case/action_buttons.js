import {display_toast} from '../toaster.js'
const { ref } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		status_info: Object
	},
	setup(props) {
        const selected_merge = ref({})

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

        async function merge_case() {
            const res = await fetch('/case/' + props.cases_info.case.id + '/merge/' + selected_merge.value.id)
            if(await res.status == 200)
                return window.location.href = "/case/" + selected_merge.value.id
            display_toast(res)
        }

        function merge_case_modal() {
            var myModal = new bootstrap.Modal(document.getElementById("merge_case_modal"), {});
            myModal.show();
            $('.merge-case-ajax').select2({
                ajax: {
                    url: '/case/search',
                    data: function (params) {
                        var query = {
                            text: params.term
                        }
                        // Query parameters will be ?text=[term]
                        return query;
                    },
                    processResults: function (data) {
                        let case_for_merge = []
                        for(let i in data.cases){
                            case_for_merge.push({id: data.cases[i].id, text: data.cases[i].title, description: data.cases[i].description})
                        }
                        
                        return {
                            results: case_for_merge
                        };
                    }
                },
                minimumInputLength: 1,
                width: "50%",
                dropdownParent: $('#merge_case_modal')
            });

            $('.merge-case-ajax').on('change.select2', function (e) {
                // selected_taxo.value = $(this).select2('data').map(item => item.id);
                selected_merge.value = $(this).select2('data')[0]
            })

            $('.merge-case-ajax').on('select2:open', function () {
                // Timeout is needed to ensure the input is rendered
                setTimeout(() => {
                    document.querySelector('.select2-container--open .select2-search__field').focus();
                }, 0);
            });
        }

        async function fetch_case_title(case_title_fork){
            const res = await fetch("/case/check_case_title_exist?title="+case_title_fork)
            let loc = await res.json()
            if(loc["title_already_exist"]){
                return true
            }
            return false
        }

        async function create_template(case_id){
            if(await fetch_case_template_title($("#case_title_template").val())){
                $("#collapseTemplateBody").append(
                    $("<span>").text("Already exist").css("color", 'red')
                )
            }else{
                const res = await fetch("/case/" + case_id + "/create_template",{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({"case_title_template": $("#case_title_template").val()})
                })
                let loc = await res.json()
                window.location.href="/templating/case/" + loc["template_id"]
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
            selected_merge,
            delete_case,
			complete_case,
            fork_case,
            create_template,
            merge_case_modal,
            merge_case
		}
    },
	template: `
        <div v-if="cases_info && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)" style="margin-right:10px;">
            <button v-if="cases_info.case.completed" class="btn btn-secondary" @click="complete_case(cases_info.case)" title="Revive the case" style="margin-right:10px">
                <i class="fa-solid fa-backward"></i>
            </button>
            <button v-else class="btn btn-success" @click="complete_case(cases_info.case)" title="Complete the case" style="margin-right:10px">
                <i class="fa-solid fa-check"></i>
            </button>

            <a class="btn btn-primary" :href="'/case/edit/'+cases_info.case.id" type="button" title="Edit the case">
                <i class="fa-solid fa-pen-to-square"></i>
            </a>
        </div>
        <div class="dropdown">
            <button class="btn btn-outline-primary dropdown-toggle" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                Actions
            </button>
            <ul class="dropdown-menu">
                <template v-if="cases_info && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)">
                    <li>
                        <a class="dropdown-item" :href="'/case/'+cases_info.case.id+'/download'" type="button" title="Download the case in json">
                            <span class="btn btn-primary btn-sm"><i class="fa-solid fa-download"></i></span> Download
                        </a>
                    </li>
                    <li>
                        <a class="dropdown-item" :href="'/case/'+cases_info.case.id+'/recurring'" type="button" title="Recurring Case">
                            <span class="btn btn-secondary btn-sm"><i class="fa-solid fa-clock"></i></span> Recurring
                        </a>
                    </li>
                    <li>
                        <button type="button" class="dropdown-item" title="Merge this case into an other one" @click="merge_case_modal()">
                            <span class="btn btn-secondary btn-sm"><i class="fa-solid fa-code-merge"></i></span> Merge
                        </button>
                    </li>
                    <li>
                        <button type="button" class="dropdown-item" title="Fork this case" data-bs-toggle="modal" data-bs-target="#fork_case_modal">
                            <span class="btn btn-secondary btn-sm"><i class="fa-solid fa-code-fork"></i></span> Fork
                        </button>
                    </li>
                    <li>
                        <button type="button" class="dropdown-item" title="Create a template from the case" data-bs-toggle="modal" data-bs-target="#template_case_modal">
                            <span class="btn btn-secondary btn-sm"><i class="fa-solid fa-book-bookmark"></i></span> Template
                        </button>
                    </li>
                    <li>
                        <button type="button" class="dropdown-item" title="Delete the case" data-bs-toggle="modal" data-bs-target="#delete_case_modal">
                            <span class="btn btn-danger btn-sm"><i class="fa-solid fa-trash"></i></span> Delete
                        </button>
                    </li>
                </template>
            </ul>
        </div>
        
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
                        <button class="btn btn-danger" @click="delete_case(cases_info.case.id)"><i class="fa-solid fa-trash"></i> Confirm</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal fork case -->
        <div class="modal fade" id="fork_case_modal" tabindex="-1" aria-labelledby="fork_case_modal" aria-hidden="true">
            <div class="modal-dialog modal-sm">
                <div class="modal-content" v-if="cases_info">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="fork_case_modal">Fork '[[cases_info.case.title]]'</h1>
                        <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <input id="case_title_fork" placeholder="Case title"/>
                        <div id="collapseForkBody"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button class="btn btn-primary" @click="fork_case(cases_info.case.id)"><i class="fa-solid fa-check"></i> Confirm</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal merge case -->
        <div class="modal fade" id="merge_case_modal" tabindex="-1" aria-labelledby="merge_case_modal" aria-hidden="true">
            <div class="modal-dialog modal-md">
                <div class="modal-content" v-if="cases_info">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" >Merge '[[cases_info.case.title]]'</h1>
                        <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <div class="alert alert-danger" role="alert">
                            <i class="fa-solid fa-triangle-exclamation"></i> This will delete this Case !
                        </div>
                        <select class="merge-case-ajax" name="merge_into" data-placeholder="Merge into"></select>
                        <div class="case-core-style mt-3" v-if="Object.keys(selected_merge).length">
                            <b>Case Description:</b><br>
                            <p style="white-space: pre-wrap; word-wrap: break-word; margin-top: 5px">[[selected_merge.description]]</p>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button class="btn btn-primary" @click="merge_case()"><i class="fa-solid fa-check"></i> Confirm</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Modal template case -->
        <div class="modal fade" id="template_case_modal" tabindex="-1" aria-labelledby="template_case_modal" aria-hidden="true">
            <div class="modal-dialog modal-md">
                <div class="modal-content" v-if="cases_info">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="template_case_modal">Template for '[[cases_info.case.title]]'</h1>
                        <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <input id="case_title_template" placeholder="Case title"/>
                        <div id="collapseTemplateBody"></div>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button class="btn btn-primary" @click="create_template(cases_info.case.id)"><i class="fa-solid fa-check"></i> Confirm</button>
                    </div>
                </div>
            </div>
        </div>
    `
}