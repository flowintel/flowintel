import {display_toast} from '/static/js/toaster.js'
const { ref } = Vue
import subtask from './subtask.js'
export default {
    delimiters: ['[[', ']]'],
    components: {
        subtask
    },
	props: {
		cases_info: Object,
		status_info: Object,
		users_in_case: Object,
		task: Object,
		task_modules: Object,
        open_closed: Object
	},
	setup(props) {
        const is_module_loading = ref(false)

        async function assign_user_task(){
			// Assign users present in the case to the task
			let users_select = $('#selectUser'+props.task.id).val()
			if(users_select.length){
				const res_msg = await fetch(
					'/case/' + props.task.case_id + '/assign_users/' + props.task.id,{
						headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
						method: "POST",
						body: JSON.stringify({"users_id": users_select})
					}
				)
				if( await res_msg.status == 200){
					// Check if current user is assign
					if(users_select.includes(props.cases_info.current_user.id.toString())){
						props.task.is_current_user_assigned = true
					}
					const res = await fetch('/case/' + props.task.case_id + '/get_assigned_users/' +props.task.id)
					if(await res.status == 404){
						display_toast(res)
					}else{
						let loc = await res.json()
						props.task.users = loc
						props.task.last_modif = Date.now()
					}
				}
				await display_toast(res_msg)
			}
		}

        async function change_status(status, task){
			// Change the status of the task
			const res = await fetch(
				'/case/' + task.case_id + '/change_task_status/'+task.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"status": status})
				}
			)
			if(await res.status==200){
				task.last_modif = Date.now()
				task.status_id=status
					
				// If 'Finished' is selected, the task is completed
				if(props.status_info.status[status-1].name == 'Finished'){
					props.open_closed["closed"] += 1
					props.open_closed["open"] -= 1
					task.last_modif = Date.now()
					task.completed = true
					fetch('/case/complete_task/'+task.id)
				}else{
					props.open_closed["closed"] -= 1
					props.open_closed["open"] += 1
					task.completed = false
				}
			}
			await display_toast(res)
		}

        function present_user_in_task(task_user_list, user){
			// Check if user is already assign
			let index = -1

			for(let i=0;i<task_user_list.length;i++){
				if (task_user_list[i].id==user.id)
					index = i
			}
			return index
		}

        async function notify_user(user_id){
			// Send a notification to the user
			const res = await fetch(
				'/case/' + props.task.case_id + '/task/' + props.task.id + '/notify_user',{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"task_id": props.task.id, "user_id": user_id})
				}
			)
			await display_toast(res)
		}

        async function remove_assigned_user(user_id){
			// Remove a user from assignment to the task
			const res = await fetch(
				'/case/' + props.task.case_id + '/remove_assigned_user/' + props.task.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"user_id": user_id})
				}
			)

			if( await res.status == 200){
				props.task.last_modif = Date.now()

				let index = -1
				for(let i=0;i<props.task.users.length;i++){
					if (props.task.users[i].id==user_id){
						// Check if the user is the current one
						if(user_id == props.cases_info.current_user.id.toString()){
							props.task.is_current_user_assigned = true
						}
						props.task.is_current_user_assigned = false
						index = i
					}
				}

				if(index > -1)
					props.task.users.splice(index, 1)
			}
			await display_toast(res)
		}

        async function submit_module_task(user_id){
			is_module_loading.value = true
			$("#modules_errors").hide()
			const loc_val = $("#modules_select_"+props.task.id+"_"+user_id).val()
			if(!loc_val || loc_val == "None"){
				$("#modules_errors").text("Select an item")
				$("#modules_errors").show()
			}else{
				if(loc_val == "flowintel"){
					notify_user(user_id)
				}else{
					const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/task/"+props.task.id+"/call_module_task_no_instance?module=" + loc_val + "&user_id="+user_id);
					display_toast(res, true)
				}
                is_module_loading.value = false
			}
		}

		return {
            is_module_loading,

            assign_user_task,
            change_status,
            notify_user,
            present_user_in_task,
            remove_assigned_user,
            submit_module_task
		}
    },
	template: `
	<div class="row">
        <div class="col" v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
            <fieldset class="analyzer-select-case">
                <legend class="analyzer-select-case"><i class="fa-solid fa-user"></i> Assign</legend>
                <div v-if="users_in_case">
                    <select data-placeholder="Users" multiple :class="'select2-selectUser'+task.id" :name="'selectUser'+task.id" :id="'selectUser'+task.id" style="min-width:200px">
                        <template v-for="user in users_in_case.users_list">
                            <option :value="user.id" v-if="present_user_in_task(task.users, user) == -1">[[user.first_name]] [[user.last_name]]</option>
                        </template>
                    </select>
                    <button class="btn btn-primary" @click="assign_user_task()">Assign</button>
                </div>
                <hr>
                <div v-if="task.users.length">
                    <div v-for="user in task.users">
                        <span style="margin-right: 5px"><i class="fa-solid fa-user"></i> [[user.first_name]] [[user.last_name]]</span>
                        <button v-if="cases_info.current_user.id != user.id" class="btn btn-primary btn-sm" data-bs-toggle="modal" :data-bs-target="'#notify_modal_'+task.id+'_'+user.id" title="Use a module to notify user"><i class="fa-solid fa-bell"></i></button>
                        <button class="btn btn-danger btn-sm" @click="remove_assigned_user(user.id)"><i class="fa-solid fa-trash"></i></button>
                    
                        <div class="modal fade" :id="'notify_modal_'+task.id+'_'+user.id" tabindex="-1" aria-labelledby="notify_modalLabel" aria-hidden="true">
                            <div class="modal-dialog modal-lg">
                                <div class="modal-content">
                                    <div class="modal-header">
                                        <h1 class="modal-title fs-5" id="notify_modalLabel">Notify user</h1>
                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                    </div>
                                    <div class="modal-body">
                                        <div class="d-flex w-100 justify-content-center">
                                            <label :for="'modules_select_'+task.id+'_'+user.id">Modules:</label>
                                        </div>
                                        <div class="d-flex w-100 justify-content-center">
                                            
                                            <select data-placeholder="Modules" class="select2-select form-control" style="min-width: 100px; max-width: 300px;" :name="'modules_select_'+task.id+'_'+user.id" :id="'modules_select_'+task.id+'_'+user.id" >
                                                <option value="None">--</option>
                                                <option value="flowintel">flowintel</option>
                                                <template v-for="module, key in task_modules">
                                                    <option v-if="module.type == 'notify_user' && module.config.case_task == 'task'" :value="[[key]]">[[key]]</option>
                                                </template>
                                            </select>
                                            <div id="modules_errors" class="invalid-feedback"></div>
                                        </div>
                                    </div>
                                    <div class="modal-footer">
                                        <button v-if="is_module_loading" class="btn btn-primary" type="button" disabled>
                                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                            <span role="status">Loading...</span>
                                        </button>
                                        <button v-else type="button" @click="submit_module_task(user.id)" class="btn btn-primary">Submit</button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </fieldset>
        </div>

        <div class="col" v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
            <fieldset class="analyzer-select-case">
                <legend class="analyzer-select-case"><i class="fa-solid fa-temperature-three-quarters"></i> Status</legend>
                <div>
                    <div class="dropdown" :id="'dropdown_status_'+task.id">
                        <template v-if="status_info">
                            <button class="btn btn-secondary dropdown-toggle" :id="'button_'+task.id" type="button" data-bs-toggle="dropdown" aria-expanded="false">
                                [[ status_info.status[task.status_id -1].name ]]
                            </button>
                            <ul class="dropdown-menu" :id="'dropdown_ul_status_'+task.id">
                                <template v-for="status_list in status_info.status">
                                    <li v-if="status_list.id != task.status_id">
                                        <button class="dropdown-item" @click="change_status(status_list.id, task)">[[ status_list.name ]]</button>
                                    </li>
                                </template>
                            </ul>
                        </template>
                    </div>
                </div>
            </fieldset>
        </div>
        
    </div>
    <hr>

    <subtask :task="task" :cases_info="cases_info"></subtask>
    `
}