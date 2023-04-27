export default {
	delimiters: ['[[', ']]'],
	props: {
		msg: String,
		cases_info: Object,
		status_info: Object,
		edit_mode: Boolean,
		task: Object
	},
	emits: ['edit_mode'],
	setup(props, {emit}) {
		function change_status(status, task){
			task.last_modif = Date.now()
			task.status_id=status
			fetch(
				'/case/change_status/'+task.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"status": status})
				}
			)
				
			if(props.status_info.status[status-1].name == 'Finished'){
				task.last_modif = Date.now()
				task.completed = true
				fetch('/case/complete_task/'+task.id)
			}else{
				task.completed = false
			}
		}

		function take_task(task, current_user){
			task.last_modif = Date.now()
			task.is_current_user_assigned = true
			task.users.push(current_user)
			
			fetch(
				'/case/take_task',{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"task_id": task.id.toString()})
				}
			)
		}

		function remove_assign_task(task, current_user){
			task.last_modif = Date.now()
			task.is_current_user_assigned = false

			let index = -1

			for(let i=0;i<task.users.length;i++){
				if (task.users[i].id==current_user.id)
					index = i
			}

			if(index > -1)
				task.users.splice(index, 1)
		
			fetch(
				'/case/remove_assign_task',{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"task_id": task.id.toString()})
				}
			)
		}

		function delete_task(task, task_array){
			fetch(
				'/case/delete_task',{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"task_id": task.id.toString()})
				}
			)

			let index = task_array.indexOf(task)
			if(index > -1)
				task_array.splice(index, 1)
		}

		async function edit_note(task){
			task.last_modif = Date.now()
			emit('edit_mode', true)

			const res = await fetch('/case/get_note_text?id='+task.id)
			let loc = await res.json()
			task.notes = loc["note"]
		}

		async function modif_note(task){
			task.last_modif = Date.now()
			emit('edit_mode', false)

			let notes = this.$refs["ref_note_" + task.id].value
			task.notes = notes

			await fetch(
				'/case/modif_note',{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"task_id": task.id.toString(), "notes": notes})
				}
			)

			const res = await fetch('/case/get_note_markdown?id='+task.id)
			let loc = await res.json()
			task.notes = loc["note"]
		}


		async function add_file(task){
			task.last_modif = Date.now()
			let files = document.getElementById('formFileMultiple'+task.id).files

			let formData = new FormData();
			for(let i=0;i<files.length;i++){
				formData.append("files"+i, files[i]);
			}
			formData.append("task_id", task.id.toString());

			const res = await fetch(
				'/case/add_files',{
					headers: { "X-CSRFToken": $("#csrf_token").val() },
					method: "POST",
					files: files,
					body: formData
				}
			)
			
			let loc = await res.json()
			for(let file in loc){
				task.files.push(loc[file])
			}

		}

		function delete_file(file, task){
			task.last_modif = Date.now()
			fetch('/case/task/' + task.id + '/delete_file/' + file.id)

			let index = task.files.indexOf(file)
			if(index > -1)
			task.files.splice(index, 1)
		}

		function complete_task(task){
			task.last_modif = Date.now()
			task.completed = !task.completed
			let status = task.status_id
			fetch('/case/complete_task/'+task.id)

			if(props.status_info.status[task.status_id -1].name == 'Finished'){
				for(let i in props.status_info.status){
					if(props.status_info.status[i].name == 'Revive')
						task.status_id = props.status_info.status[i].id
				}
				if(task.status_id == status)
					task.status_id = 1

				fetch('/case/change_status/'+task.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"status": task.status_id})
				})
			}else{
				for(let i in props.status_info.status){
					if(props.status_info.status[i].name == 'Finished'){
						task.status_id = props.status_info.status[i].id
						fetch('/case/change_status/'+task.id,{
							headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
							method: "POST",
							body: JSON.stringify({"status": task.status_id})
						})
						break
					}
				}
			}
		}

		function formatNow(dt) {
			return moment(dt).fromNow()
		}

		return {
			change_status,
			take_task,
			remove_assign_task,
			delete_task,
			edit_note,
			modif_note,
			add_file,
			delete_file,
			complete_task,
			formatNow
		}
	},
	template: `
	<div style="display: flex;">                          
		<a :href="'#collapse'+task.id" class="list-group-item list-group-item-action" data-bs-toggle="collapse" role="button" aria-expanded="false" :aria-controls="'collapse'+task.id">
			<div class="d-flex w-100 justify-content-between">
				<h5 class="mb-1">[[task.title]]</h5>
				<small><i>Changed [[ formatNow(task.last_modif) ]] </i></small>
			</div>

			<div class="d-flex w-100 justify-content-between">
				<p v-if="task.description" class="card-text">[[ task.description ]]</p>
				<p v-else class="card-text"><i style="font-size: 12px;">No description</i></p>

				<small v-if="status_info">
					<span :class="'badge rounded-pill text-bg-'+status_info.status[task.status_id -1].bootstrap_style">
						[[ status_info.status[task.status_id -1].name ]]
					</span>
				</small>
			</div>

			<div v-if="task.users.length">
				Users: 
				<template v-for="user in task.users">
					[[user.first_name]] [[user.last_name]],
				</template>
			</div>

			<div v-else>
				<i>No user assigned</i>
			</div>
		</a>
		<div v-if="!cases_info.permission.read_only && cases_info.present_in_case" style="display: grid;">
			<button class="btn btn-success btn-sm"  @click="complete_task(task, status_info)"><i class="fa-solid fa-check"></i></button>
			<button v-if="!task.is_current_user_assigned" class="btn btn-secondary btn-sm"  @click="take_task(task, cases_info.current_user)"><i class="fa-solid fa-hand"></i></button>
			<button v-else class="btn btn-secondary btn-sm"  @click="remove_assign_task(task, cases_info.current_user)"><i class="fa-solid fa-handshake-slash"></i></button>
			<a class="btn btn-primary btn-sm" :href="'/case/view/'+cases_info.case.id+'/edit_task/'+task.id" type="button"><i class="fa-solid fa-pen-to-square"></i></a>
			<button class="btn btn-danger btn-sm"  @click="delete_task(task, cases_info.tasks)"><i class="fa-solid fa-trash"></i></button>
		</div>
	</div>

	
	<!-- Collapse Part -->
	<div class="collapse" :id="'collapse'+task.id">
		<div class="card card-body" style="background-color: whitesmoke;">
			<div class="d-flex w-100 justify-content-between">
				<div>
					<div>
						<h3>Notes</h3>
					</div>
					<div v-if="task.notes">
						<template v-if="edit_mode">
							<div>
								<button class="btn btn-primary" @click="modif_note(task)" type="button" :id="'note_'+task.id">
									<div hidden>[[task.title]]</div>
									Save
								</button>
							</div>
							<textarea :ref="'ref_note_'+task.id" :id="'note_area_'+task.id" rows="5" cols="30" maxlength="5000" v-html="task.notes"></textarea>
						</template>
						<template v-else>
							<template v-if="!cases_info.permission.read_only && cases_info.present_in_case">
								<button class="btn btn-primary" @click="edit_note(task)" type="button" :id="'note_'+task.id">
									<div hidden>[[task.title]]</div>
									Edit
								</button>
							</template> 
							<p v-html="task.notes"></p>
						</template>
					</div>
					<div v-else>
						<template v-if="!cases_info.permission.read_only && cases_info.present_in_case">
							<div>
								<button class="btn btn-primary" @click="modif_note(task)" type="button" :id="'note_'+task.id">
									<div hidden>[[task.title]]</div>
									Create
								</button>
							</div>
							<textarea :ref="'ref_note_'+task.id" :id="'note_area_'+task.id" rows="5" cols="30" maxlength="5000"></textarea>
						</template>
					</div>
				</div>

				<div>
					<div>
						<h3>Files</h3>
					</div>
					<div>
						<div>
							<input class="form-control" type="file" :id="'formFileMultiple'+task.id" multiple/>
							<button class="btn btn-primary" @click="add_file(task)">Add</button>
						</div>
						<br/>
						<template v-if="task.files.length">
							<template v-for="file in task.files">
								<div>
									<a class="btn btn-link" :href="'/case/task/'+task.id+'/download_file/'+file.id">
										[[ file.name.split(")")[1] ]]
									</a>
									<button class="btn btn-danger" @click="delete_file(file, task)"><i class="fa-solid fa-trash"></i></button>
								</div>
							</template>
						</template>
					</div>
				</div>
				<div>
					<div>
						<h3>Change Status</h3>
					</div>
					<div>
						<div class="dropdown" :id="'dropdown_status_'+task.id">
							<template v-if="status_info">
								<button class="btn btn-secondary dropdown-toggle" :id="'button_'+task.id" type="button" data-bs-toggle="dropdown" aria-expanded="false">[[ status_info.status[task.status_id -1].name ]]</button>
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
				</div>
			</div>
		</div>
	</div>
	`
}