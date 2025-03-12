import {display_toast, create_message} from '/static/js/toaster.js'
const { ref, nextTick} = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		task: Object,
		cases_info: Object,
	},
	setup(props) {
        async function complete_subtask(task, subtask_id, completed){
			const res = await fetch('/case/' + task.case_id + '/task/' + task.id+"/complete_subtask/"+subtask_id)

			if( await res.status == 200){
				for(let i in task.subtasks){
					if (task.subtasks[i].id == subtask_id){
						task.subtasks[i].completed=!task.subtasks[i].completed
						if(completed){
							task.nb_open_subtasks -= 1
						}else{
							task.nb_open_subtasks += 1
						}
						break
					}
				}
			}
			await display_toast(res)
		}

        async function create_subtask(task){
			$("#textarea-subtask-error-"+task.id).text("")
			let description = $("#textarea-subtask-"+task.id).val()
			if(!description){
				$("#textarea-subtask-error-"+task.id).text("Cannot be empty...").css("color", "brown")
			}
			
			const res = await fetch("/case/"+ task.case_id +"/task/"+task.id+"/create_subtask", {
				method: "POST",
				headers: {
					"X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
				},
				body: JSON.stringify({
					"description": description
				})				
			});
			if( await res.status == 200){
				let loc = await res.json()
				
				task.subtasks.push({"id": loc["id"], "description": description, "task_id": task.id, "completed": false})
				create_message("Subtask created", "success-subtle", false, "fas fa-plus")
				$("#textarea-subtask-"+task.id).val("")
                $("#create_subtask_"+task.id).modal("hide")
			}else{
				await display_toast(res)
			}
		}

		async function edit_subtask(task, subtask_id){
			$("#edit-subtask-error-"+subtask_id).text("")
			let description = $("#edit-subtask-"+subtask_id).val()
			if(!description){
				$("#edit-subtask-error-"+subtask_id).text("Cannot be empty...").css("color", "brown")
			}
			const res = await fetch("/case/"+ task.case_id +"/task/"+task.id+"/edit_subtask/"+subtask_id, {
				method: "POST",
				headers: {
					"X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
				},
				body: JSON.stringify({
					"description": description
				})				
			});
			if( await res.status == 200){
				for(let i in task.subtasks){
					if (task.subtasks[i].id == subtask_id){
						task.subtasks[i].description = description
						break
					}
				}
                $("#edit_subtask_"+subtask_id).modal("hide")
			}
			await display_toast(res)
		}

		async function delete_subtask(task, subtask_id){
			const res = await fetch('/case/' + task.case_id + '/task/' + task.id+"/delete_subtask/"+subtask_id)

			if( await res.status == 200){
				let loc_i
				for(let i in task.subtasks){
					if (task.subtasks[i].id == subtask_id){
						loc_i=i
						break
					}
				}
				task.subtasks.splice(loc_i, 1)
			}
			await display_toast(res)
		}

		return {
            complete_subtask,
            create_subtask,
            edit_subtask,
            delete_subtask
		}
    },
	template: `
	<div>
        <fieldset class="analyzer-select-case">
            <legend class="analyzer-select-case">
                <i class="fa-solid fa-list"></i> 
                Subtasks
				<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
					<button class="btn btn-primary btn-sm" title="Add new subtask" data-bs-toggle="modal" :data-bs-target="'#create_subtask_'+task.id" style="float: right; margin-left:3px;">
						<i class="fa-solid fa-plus"></i>
					</button>
				</template>
            </legend>
            <template v-for="subtask in task.subtasks">
                <div>
                    <div v-if="subtask.completed">
						<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                        	<input type="checkbox" checked @click="complete_subtask(task, subtask.id, false)"/>
						</template>
                        <span style="text-decoration-line: line-through; margin-left: 3px">[[subtask.description]]</span>
                    </div>
                    <div v-else>
						<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                        	<input type="checkbox" @click="complete_subtask(task, subtask.id, true)"/>
						</template>
                        [[subtask.description]]
						<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
							<button @click="delete_subtask(task, subtask.id)" class="btn btn-danger btn-sm" style="float: right;" ><i class="fa-solid fa-trash"></i></button>
							<button class="btn btn-primary btn-sm" title="Edit subtask" data-bs-toggle="modal" :data-bs-target="'#edit_subtask_'+subtask.id" style="float: right;">
								<i class="fa-solid fa-pen-to-square"></i>
							</button>
						</template>
                    </div>
                    
                </div>
                <hr>
                <!-- Modal edit subtask -->
                <div class="modal fade" :id="'edit_subtask_'+subtask.id" tabindex="-1" aria-labelledby="edit_subtask_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h1 class="modal-title fs-5" id="edit_subtask_modal">Edit subtask</h1>
                                <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <textarea class="form-control" :value="subtask.description" :id="'edit-subtask-'+subtask.id"/>
                                <div :id="'edit-subtask-error-'+subtask.id"></div>
                            </div>
                            <div class="modal-footer">
                                <button @click="edit_subtask(task, subtask.id)" class="btn btn-primary">Submit</button>
                            </div>
                        </div>
                    </div>
                </div>
            </template>
        </fieldset>
    </div>

    <!-- Modal create subtask -->
    <div class="modal fade" :id="'create_subtask_'+task.id" tabindex="-1" aria-labelledby="create_subtask_modal" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="create_subtask_modal">Create subtask</h1>
                    <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
					<div class="form-floating">
						<textarea class="form-control" :id="'textarea-subtask-'+task.id"/>
						<label>New Subtask</label>
						<div :id="'textarea-subtask-error-'+task.id"></div>
					</div>
                </div>
                <div class="modal-footer">
                    <button @click="create_subtask(task)" class="btn btn-primary">Submit</button>
                </div>
            </div>
        </div>
    </div>
    `
}