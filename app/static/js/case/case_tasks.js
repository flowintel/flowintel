import {display_toast} from '../toaster.js'
const { ref, nextTick, watch } = Vue
export default {
	delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		status_info: Object,
		users_in_case: Object,
		task: Object,
		key_loop: Number,
		open_closed: Object,
		modules: Object
	},
	setup(props) {
		// Variables part
		const users_list = ref([])				// List to display in proper way users assign to this task
		let is_mounted = false			// Boolean use to know if the app is mount to initialize mermaid
		const is_exporting = ref(false)		 	// Boolean to display a spinner when exporting

		const note_editor_render = ref([])		// Notes display in mermaid
		let editor_list = []								// Variable for the editor
		const md = window.markdownit()			// Library to Parse and display markdown
		md.use(mermaidMarkdown.default)			// Use mermaid library
		const edit_mode = ref(-1)			// Boolean use when the note is in edit mode
		const module_loader = ref(false)
		const task_modules = ref()
		const task_instances_selected = ref([])
		const task_module_selected = ref()

		if(props.task.notes.length){
			for(let i in props.task.notes){
				note_editor_render.value[i] = props.task.notes[i].note		// If this task has notes
			}
		}else{
			note_editor_render.value[0] = ""
		}

		
		// Function part
		async function add_file(task){
			// Add file to the task
			let files = document.getElementById('formFileMultiple'+task.id).files

			// Create a form with all files upload
			let formData = new FormData();
			for(let i=0;i<files.length;i++){
				formData.append("files"+i, files[i]);
			}

			const res = await fetch(
				'/case/' + task.case_id + '/add_files/' + task.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val() },
					method: "POST",
					files: files,
					body: formData
				}
			)
			if(await res.status == 200){
				// Get the new list of files of the task
				const res_files = await fetch('/case/' + task.case_id + '/get_files/'+task.id)

				if(await res_files.status == 200){
					task.last_modif = Date.now()
					let loc = await res_files.json()
					task.files = []
					for(let file in loc['files']){
						task.files.push(loc['files'][file])
					}
				}else{
					await display_toast(res_files)
				}
			}

			await display_toast(res)
		}

		async function add_notes_task(){
			// Create a new empty note in the task
			const res = await fetch('/case/' + props.task.case_id + '/create_note/'+props.task.id)

			if(await res.status == 200){
				let loc = await res.json()
				props.task.notes.push(loc["note"])
				let key = props.task.notes.length-1
				note_editor_render.value[key] = ""
				await nextTick()
				const targetElement = document.getElementById('editor_' + key + "_" + props.task.id)
				
				if(targetElement.innerHTML === ""){
					let editor = new Editor.EditorView({
						doc: "\n\n",
						extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
							if (v.docChanged) {
								note_editor_render.value[key] = editor.state.doc.toString()
							}
						})],
						parent: targetElement
					})
					editor_list.push(editor)
				}
				md.mermaid.run()
			}
		}

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

		async function complete_task(task){
			// Complete a task
			const res = await fetch('/case/complete_task/'+task.id)
			if (await res.status == 200){
				if(task.completed){
					props.open_closed["open"] += 1
					props.open_closed["closed"] -= 1
				}else{
					props.open_closed["closed"] += 1
					props.open_closed["open"] -= 1
				}
				task.last_modif = Date.now()
				task.completed = !task.completed
				let status = task.status_id
				if(props.status_info.status[task.status_id -1].name == 'Finished'){
					for(let i in props.status_info.status){
						if(props.status_info.status[i].name == 'Created')
							task.status_id = props.status_info.status[i].id
					}
					if(task.status_id == status)
						task.status_id = 1

				}else{
					for(let i in props.status_info.status){
						if(props.status_info.status[i].name == 'Finished'){
							task.status_id = props.status_info.status[i].id
							break
						}
					}
				}
				let index = props.cases_info.tasks.indexOf(task)
				if(index > -1)
					props.cases_info.tasks.splice(index, 1)
			}
			await display_toast(res)
		}

		async function delete_file(file, task){
			// Delete a file in the task
			const res = await fetch('/case/task/' + task.id + '/delete_file/' + file.id)
			if(await res.status == 200){
				task.last_modif = Date.now()

				// Remove the file from list
				let index = task.files.indexOf(file)
				if(index > -1)
					task.files.splice(index, 1)
			}
			await display_toast(res)
		}

		async function delete_note(task, note_id, key){
			// Delete a note of the task
			const res = await fetch('/case/' + task.case_id + '/delete_note/' + task.id + '?note_id='+note_id)

			if( await res.status == 200){
				props.task.notes.splice(key, 1);
			}
			display_toast(res)
		}

		async function delete_task(task, task_array){
			// delete the task
			const res = await fetch('/case/' + task.case_id + '/delete_task/' + task.id)

			if( await res.status == 200){
				if(task.completed){
					props.open_closed["closed"] -= 1
				}else{
					props.open_closed["open"] -= 1
				}

				// remove the task from the list of task
				let index = task_array.indexOf(task)
				if(index > -1)
					task_array.splice(index, 1)
			}
			await display_toast(res)
		}

		async function edit_note(task, note_id, key){
			// Edit the note of the task
			edit_mode.value = note_id

			const res = await fetch('/case/' + task.case_id + '/get_note/' + task.id + '?note_id=' + note_id)
			let loc = await res.json()
			task.notes[key].note = loc["note"]

			// Initialize the editor
			const targetElement = document.getElementById('editor1_'+ key + "_" + props.task.id)
			let editor = new Editor.EditorView({
				doc: task.notes[key].note,
				extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
					if (v.docChanged) {
						note_editor_render.value[key] = editor.state.doc.toString()
					}
				})],
				parent: targetElement
			})
			editor_list[key] = editor
			md.mermaid.run()
		}

		async function export_notes(task, type, note_id){
			// Export notes in different format and download it
			is_exporting.value = true
			let filename = ""
			await fetch('/case/'+task.case_id+'/task/'+task.id+'/export_notes?type=' + type+"&note_id="+note_id)
			.then(res =>{
				filename = res.headers.get("content-disposition").split("=")
				filename = filename[filename.length - 1]
				return res.blob() 
			})
			.then(data =>{
				var a = document.createElement("a")
				a.href = window.URL.createObjectURL(data);
				a.download = filename;
				a.click();
			})
			is_exporting.value = false
		}

		async function fetch_modules(){
			// Get modules and instances linked on
			const res = await fetch("/case/get_task_modules")
			if(await res.status==400 ){
				display_toast(res)
			}else{
				let loc = await res.json()
				task_modules.value = loc["modules"]
			}
		}
		fetch_modules()

		async function fetch_module_selected(module){
			// Get modules and instances linked on
			const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/task/"+props.task.id+"/get_instance_module?type=send_to&module="+module)
			if(await res.status==400 ){
				display_toast(res)
			}else{
				let loc = await res.json()
				task_module_selected.value = loc["instances"]
				await nextTick()
				$('#task_instances_select_'+props.task.id).select2({
					theme: 'bootstrap-5',
					width: '50%',
					closeOnSelect: false
				})
				$('#task_instances_select_'+props.task.id).on('change.select2', function (e) {
					let name_instance = $(this).select2('data').map(item => item.id)
					task_instances_selected.value = []
					for( let index in task_module_selected.value){
						if (name_instance.includes(task_module_selected.value[index].name)){
							if(!task_instances_selected.value.includes(task_module_selected.value[index]))
								task_instances_selected.value.push(task_module_selected.value[index])
						}
					}
				})
			}
		}

		async function move_task(task, up_down){
			// Move the task up and down
			let cp = 0
			up_down ? cp = -1 : cp = 1

			const res = await fetch('/case/' + task.case_id + '/change_order/' + task.id + "?up_down=" + up_down)
			await display_toast(res)
			for( let i in props.cases_info.tasks){
				if(props.cases_info.tasks[i]["case_order_id"] == task.case_order_id+cp){
					props.cases_info.tasks[i]["case_order_id"] = task.case_order_id
					task.case_order_id += cp
					break
				}
			}
			props.cases_info.tasks.sort(order_task)
		}

		async function modif_note(task, note_id, key){
			// Modify notes of the task
			let notes_loc = editor_list[key].state.doc.toString()
			if(notes_loc.trim().length == 0){
				notes_loc = notes_loc.trim()
			}
			const res_msg = await fetch(
				'/case/' + task.case_id + '/modif_note/' + task.id + '?note_id=' + note_id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"notes": notes_loc})
				}
			)

			if(await res_msg.status == 200){
				let loc = await res_msg.json()
				edit_mode.value = -1
				task.last_modif = Date.now()
				if(note_id == -1){
					note_id = loc["note"]["id"]
					task.notes.push(loc["note"])
				}else{
					task.notes[key].note = notes_loc
				}

				await nextTick()
				
				if(!notes_loc){
					const targetElement = document.getElementById('editor_' +key + "_" + props.task.id)
					if(targetElement.innerHTML === ""){
						let editor = new Editor.EditorView({
							doc: "\n\n",
							extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
								if (v.docChanged) {
									note_editor_render.value[key] = editor.state.doc.toString()
								}
							})],
							parent: targetElement
						})
						editor_list[key] = editor
					}
				}
				md.mermaid.run()
			}else{
				display_toast(res_msg)
			}
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


		function order_task(a, b){
			// Helper for move_task function
			if(a.case_order_id > b.case_order_id){
				return 1
			}
			if(a.case_order_id < b.case_order_id){
				return -1
			}
			return 0
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

		async function remove_assign_task(task, current_user){
			// Remove current user from assignment to the task
			const res = await fetch('/case/' + task.case_id + '/remove_assignment/' + task.id)

			if( await res.status == 200){
				task.last_modif = Date.now()
				task.is_current_user_assigned = false
	
				let index = -1
	
				for(let i=0;i<task.users.length;i++){
					if (task.users[i].id==current_user.id)
						index = i
				}
	
				if(index > -1)
					task.users.splice(index, 1)
			}
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

		async function submit_module(){
			module_loader.value = true
			$("#task_modules_errors_"+props.task.id).hide()
			$("#task_instances_errors_"+props.task.id).hide()
			if(!$("#task_modules_select_"+props.task.id).val() || $("#task_modules_select_"+props.task.id).val() == "None"){
				$("#task_modules_errors_"+props.task.id).text("Select an item")
				$("#task_modules_errors_"+props.task.id).show()
			}
			if(!$("#task_instances_select_"+props.task.id).val() || $("#task_instances_select_"+props.task.id).val().length<1){
				$("#task_instances_error_"+props.task.id).text("Select an item")
				$("#task_instances_error_"+props.task.id).show()
			}

			let i_s = $("#task_instances_select_"+props.task.id).val()
			let int_sel = {}
			for(let index in i_s){
				for( let j in task_module_selected.value){
					if (task_module_selected.value[j].name == i_s[index]){
						let loc_val = $("#identifier_"+task_module_selected.value[j].id).val()
						int_sel[task_module_selected.value[j].name] = loc_val
						for(let k in task_instances_selected.value){
							if(task_instances_selected.value[k].name == task_module_selected.value[j].name){
								task_instances_selected.value[k].identifier = loc_val
							}
						}
					}
				}
			}
			const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/task/"+props.task.id+"/call_module_task?module=" + $("#task_modules_select_"+props.task.id).val() , {
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

		async function submit_module_task(user_id){
			module_loader.value = true
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
					module_loader.value = false

					display_toast(res, true)
				}
			}
		}

		async function take_task(task, current_user){
			// Assign the task to the current user
			const res = await fetch('/case/' + task.case_id + '/take_task/' + task.id)

			if( await res.status == 200){
				task.last_modif = Date.now()
				task.is_current_user_assigned = true
				task.users.push(current_user)
			}
			await display_toast(res)
		}



		// Utils function
		function formatNow(dt) {
			return dayjs.utc(dt).from(dayjs.utc())
		}

		function endOf(dt){
			return dayjs.utc(dt).endOf().from(dayjs.utc())
		}

		function select2_change(tid){
			$('.select2-selectUser'+tid).select2({width: 'element'})
			$('.select2-container').css("min-width", "200px")
		}		


		// Vue function
		Vue.onMounted( () => {
			select2_change(props.task.id)
			$('.select2-select').select2({
				theme: 'bootstrap-5',
				width: '50%',
				closeOnSelect: false
			})
			
			if(props.task.notes.length){
				for(let i in props.task.notes){
					const targetElement = document.getElementById('editor_' +i +'_' + props.task.id)
					let editor=new Editor.EditorView({
						doc: "\n\n",
						extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
							if (v.docChanged) {
								note_editor_render.value[i] = editor.state.doc.toString()
							}
						})],
						parent: targetElement
					})
					editor_list[i] = editor
				}
			}else{
				const targetElement = document.getElementById('editor_0_' + props.task.id)
				let editor=new Editor.EditorView({
					doc: "\n\n",
					extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
						if (v.docChanged) {
							note_editor_render.value[0] = editor.state.doc.toString()
						}
					})],
					parent: targetElement
				})
				editor_list[0] = editor
				md.mermaid.run()
			}

			// When openning a task, initialize mermaid library
			const allCollapses = document.getElementById('collapse' + props.task.id)
			allCollapses.addEventListener('shown.bs.collapse', event => {
				md.mermaid.run()
			})
			is_mounted = true

			for(let index in props.task.users){
				users_list.value.push(props.task.users[index].first_name + " " + props.task.users[index].last_name)
			}
		})
		Vue.onUpdated(async () => {
			select2_change(props.task.id)
			// do not initialize mermaid before the page is mounted
			if(is_mounted){
				$('#task_modules_select_'+props.task.id).on('change.select2', function (e) {
					if($(this).select2('data').map(item => item.id)[0] == "None"){
						task_module_selected.value = []
					}else{
						fetch_module_selected($(this).select2('data').map(item => item.id))
					}
				})
			}
		})

		watch(note_editor_render, async (newAllContent, oldAllContent) => {
			await nextTick()
			md.mermaid.run()
		}, {deep: true})

		return {
			note_editor_render,
			md,
			is_exporting,
			getTextColor,
			mapIcon,
			edit_mode,
			users_list,
			module_loader,
			task_modules,
			task_instances_selected,
			task_module_selected,
			change_status,
			take_task,
			remove_assign_task,
			assign_user_task,
			remove_assigned_user,
			delete_task,
			delete_note,
			edit_note,
			modif_note,
			add_file,
			delete_file,
			complete_task,
			notify_user,
			formatNow,
			endOf,
			export_notes,
			present_user_in_task,
			move_task,
			add_notes_task,
			submit_module_task,
			submit_module
		}
	},
	template: `
	<div style="display: flex;">                          
		<a :href="'#collapse'+task.id" class="list-group-item list-group-item-action" data-bs-toggle="collapse" role="button" aria-expanded="false" :aria-controls="'collapse'+task.id">
			<div class="d-flex w-100 justify-content-between">
				<h5 class="mb-1">[[ key_loop ]]- [[task.title]]</h5>
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

			<div class="d-flex w-100 justify-content-between" style="margin-top: 5px;">
				<div style="display: flex;" v-if="task.custom_tags">
					<template v-for="custom_tag in task.custom_tags">
						<div class="tag" :style="{'background-color': custom_tag.color, 'color': getTextColor(custom_tag.color)}">
							<i v-if="custom_tag.icon" :class="custom_tag.icon"></i>
							[[custom_tag.name]]
						</div>
					</template>
				</div>
			</div>
			<div class="d-flex w-100 justify-content-between">
				<div style="display: flex; margin-bottom: 7px" v-if="task.tags">
					<template v-for="tag in task.tags">
						<div class="tag" :title="tag.description" :style="{'background-color': tag.color, 'color': getTextColor(tag.color)}">
							<i class="fa-solid fa-tag" style="margin-right: 3px; margin-left: 3px;"></i>
							[[tag.name]]
						</div>
					</template>
				</div>
				<div v-else></div>
			</div>

			<div class="d-flex w-100 justify-content-between">
                <div v-if="task.users.length">
					<template v-for="user in task.users">
						<span v-if="user.nickname" class="btn btn-primary btn-sm person" :title="user.first_name+' ' +user.last_name"><i class="fa-solid fa-user"></i> [[user.nickname]]</span>
						<span v-else class="btn btn-primary btn-sm person" :title="user.first_name+' ' +user.last_name"><i class="fa-solid fa-user"></i> [[user.last_name]]</span>
					</template>
                </div>

                <div v-else>
                    <i>No user assigned</i>
                </div>
                <small v-if="task.deadline" :title="task.deadline"><i>Deadline [[endOf(task.deadline)]]</i></small>
                <small v-else><i>No deadline</i></small>
            </div>
			<div class="d-flex w-100 justify-content-between">
				<div style="display: flex;" v-if="task.clusters">
					<template v-for="cluster in task.clusters">
						<div :title="'Description:\\n' + cluster.description + '\\n\\nMetadata:\\n' + JSON.stringify(JSON.parse(cluster.meta), null, 4)">
							<span v-html="mapIcon(cluster.icon)"></span>
							[[cluster.tag]]
						</div>
					</template>
				</div>
				<div v-else></div>
			</div>
			<div class="d-flex w-100 justify-content-between">
				<div></div>
				<span class="badge rounded-pill" style="color: black; background-color: aliceblue; font-weight: normal">
					<i>[[task.notes.length]] Notes</i>
				</span>
			</div>
		</a>
		<div v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin" style="display: grid;">
			<button v-if="task.completed" class="btn btn-secondary btn-sm"  @click="complete_task(task)" title="Revive the task">
				<i class="fa-solid fa-backward"></i>
			</button>
			<button v-else class="btn btn-success btn-sm" @click="complete_task(task)" title="Complete the task">
				<i class="fa-solid fa-check"></i>
			</button>
			<button v-if="!task.is_current_user_assigned" class="btn btn-secondary btn-sm" @click="take_task(task, cases_info.current_user)" title="Be assigned to the task">
				<i class="fa-solid fa-hand"></i>
			</button>
			<button v-else class="btn btn-secondary btn-sm" @click="remove_assign_task(task, cases_info.current_user)" title="Remove the assignment">
				<i class="fa-solid fa-handshake-slash"></i>
			</button>
			<button type="button" class="btn btn-secondary btn-sm" data-bs-toggle="modal" :data-bs-target="'#Send_to_modal_task_'+task.id">
				<i class="fa-solid fa-share-from-square"></i>
			</button>
			<a class="btn btn-primary btn-sm" :href="'/case/'+cases_info.case.id+'/edit_task/'+task.id" type="button" title="Edit the task">
				<i class="fa-solid fa-pen-to-square"></i>
			</a>
			<button class="btn btn-danger btn-sm" @click="delete_task(task, cases_info.tasks)" title="Delete the task">
				<i class="fa-solid fa-trash"></i>
			</button>
		</div>
		<div v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin" style="display: grid;">
			<button class="btn btn-light btn-sm" title="Move the task up" @click="move_task(task, true)">
				<i class="fa-solid fa-chevron-up"></i>
			</button>
			<button class="btn btn-light btn-sm" title="Move the task down" @click="move_task(task, false)">
				<i class="fa-solid fa-chevron-down"></i>
			</button>
		</div>
	</div>

	<!-- Modal send to -->
	<div class="modal fade" :id="'Send_to_modal_task_'+task.id" tabindex="-1" aria-labelledby="Send_to_modalLabel" aria-hidden="true">
		<div class="modal-dialog modal-lg">
			<div class="modal-content">
				<div class="modal-header">
					<h1 class="modal-title fs-5" id="Send_to_modalLabel">Send to modules</h1>
					<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
				</div>
				<div class="modal-body">
					<div style="display: flex;">
						<div>
							<label :for="'task_modules_select_'+task.id">Modules:</label>
							<select data-placeholder="Modules" class="select2-select form-control" :name="'task_modules_select_'+task.id" :id="'task_modules_select_'+task.id" >
								<option value="None">--</option>
								<template v-for="module, key in task_modules">
									<option v-if="module.type == 'send_to'" :value="[[key]]">[[key]]</option>
								</template>
							</select>
							<div :id="'task_modules_errors_'+task.id" class="invalid-feedback"></div>
						</div>
						<div style="min-width: 100%;">
							<label :for="'task_instances_select'+task.id">Instances:</label>
							<select data-placeholder="Instances" class="select2-select form-control" multiple :name="'task_instances_select_'+task.id" :id="'task_instances_select_'+task.id" >
								<template v-if="task_module_selected">
									<template v-for="instance, key in task_module_selected">
										<option :value="[[instance.name]]">[[instance.name]]</option>
									</template>
								</template>
							</select>
							<div :id="'task_instances_errors_'+task.id" class="invalid-feedback"></div>
						</div>
					</div>
					<div class="row" v-if="task_instances_selected">
						<div class="mb-3 w-50" v-for="instance, key in task_instances_selected" >
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

	
	<!-- Collapse Part -->
	<div class="collapse" :id="'collapse'+task.id">
		<div class="card card-body" style="background-color: whitesmoke;">
			<div v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
				<div class="d-flex w-100 justify-content-between">
					<div v-if="users_in_case">
						<h5>Assign</h5>
						<select data-placeholder="Users" multiple :class="'select2-selectUser'+task.id" :name="'selectUser'+task.id" :id="'selectUser'+task.id" style="min-width:200px">
							<template v-for="user in users_in_case.users_list">
								<option :value="user.id" v-if="present_user_in_task(task.users, user) == -1">[[user.first_name]] [[user.last_name]]</option>
							</template>
						</select>
						<button class="btn btn-primary" @click="assign_user_task()">Assign</button>
					</div>
					<div style="margin-right: 5px">
						<h5>Change Status</h5>
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
					</div>
				</div>
				<div class="d-flex w-100 justify-content-between">
					<div v-if="task.users.length">
						<h5>Remove assign</h5>
						<div v-for="user in task.users">
							<span style="margin-right: 5px">[[user.first_name]] [[user.last_name]]</span>
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
													<template v-for="module, key in modules">
														<option v-if="module.type == 'notify_user' && module.config.case_task == 'task'" :value="[[key]]">[[key]]</option>
													</template>
												</select>
												<div id="modules_errors" class="invalid-feedback"></div>
											</div>
										</div>
										<div class="modal-footer">
											<button v-if="module_loader" class="btn btn-primary" type="button" disabled>
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
				</div>
			</div>
			<hr>
			<div class="d-flex w-100 justify-content-between">
				<div v-if="task.url">
					<div>
						<h5>Tool/Url</h5>
					</div>
					<div>
						[[task.url]]
					</div>
				</div>
				<div v-if="task.instances.length">
					<div>
						<h5>Connectors</h5>
					</div>
					<div v-for="instance in task.instances" :title="instance.description">
						<img :src="'/static/icons/'+instance.icon" style="max-width: 30px;">
						<a style="margin-left: 5px" :href="instance.url">[[instance.url]]</a>
						<span style="margin-left: 3px;" title="identifier used by module">[[instance.identifier]]</span>
					</div>
				</div>
			</div>
			<hr v-if="task.url || task.instances.length">
			<div class="d-flex w-100 justify-content-between">
				<div>
					<div>
						<h5>Files</h5>
					</div>
					<div style="display: flex;">
						<input class="form-control" type="file" :id="'formFileMultiple'+task.id" multiple/>
						<button class="btn btn-primary btn-sm" @click="add_file(task)" style="margin-left: 2px;">Submit</button>
					</div>
					<br/>
					<template v-if="task.files.length">
						<template v-for="file in task.files">
							<div>
								<a class="btn btn-link" :href="'/case/task/'+task.id+'/download_file/'+file.id">
									[[ file.name ]]
								</a>
								<button class="btn btn-danger" @click="delete_file(file, task)"><i class="fa-solid fa-trash"></i></button>
							</div>
						</template>
					</template>
				</div>
			</div>
			<hr>
			<div class="d-flex w-100 justify-content-between">
				<div class="w-100">
					<div>
						<h5>Notes <a class="btn btn-primary btn-sm" :href="'/analyzer/?case_id='+task.case_id+'&task_id='+task.id" style="margin-bottom: 1px;"><i class="fa-solid fa-magnifying-glass"></i> Analyze</a></h5> 
					</div>
					<div v-if="task.notes.length">
						<template v-for="task_note, key in task.notes">
							<h5>#[[key+1]]</h5>
							<template v-if="task_note.note">
								<template v-if="edit_mode == task_note.id">
									<div>
										<button class="btn btn-primary" @click="modif_note(task, task_note.id, key)" type="button" :id="'note_'+task.id">
											<div hidden>[[task.title]]</div>
											Save
										</button>
									</div>
									<div style="display: flex;">
										<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor1_'+key+'_'+task.id"></div>
										<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[key])"></div>
									</div>
								</template>
								<template v-else>
									<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
										<button class="btn btn-primary btn-sm" @click="edit_note(task, task_note.id, key)" :id="'note_'+task.id" style="margin-bottom: 1px;">
											<div hidden>[[task.title]]</div>
											<small><i class="fa-solid fa-pen"></i></small> Edit
										</button>
										<div class="btn-group">
											<button class="btn btn-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false" style="margin-bottom: 1px;">
												<small><i class="fa-solid fa-download"></i></small> Export
											</button>
											<ul class="dropdown-menu">
												<li>
													<button v-if="!is_exporting" class="btn btn-link" @click="export_notes(task, 'pdf', task_note.id)" title="Export markdown as pdf">PDF</button>
													<button v-else class="btn btn-link" disabled>
														<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
														<span role="status">Loading...</span>
													</button>
												</li>
												<li>
													<button v-if="!is_exporting" class="btn btn-link" @click="export_notes(task, 'docx', task_note.id)" title="Export markdown as docx">DOCX</button>
													<button v-else class="btn btn-link" disabled>
														<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
														<span role="status">Loading...</span>
													</button>
												</li>
											</ul>
										</div>
										<button class="btn btn-danger btn-sm" @click="delete_note(task, task_note.id, key)" style="margin-bottom: 1px;">
											<small><i class="fa-solid fa-trash"></i></small> Delete
										</button>

									</template> 
									<p style="background-color: white; border: 1px #515151 solid; padding: 5px;" v-html="md.render(task_note.note)"></p>
								</template>
							</template>
							<template v-else>
								<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
									<div>
										<button class="btn btn-primary btn-sm" @click="modif_note(task, task_note.id, key)" type="button" :id="'note_'+task.id" style="margin-bottom: 3px;">
											<div hidden>[[task.title]]</div>
											Create
										</button>
										<button class="btn btn-danger btn-sm" @click="delete_note(task, task_note.id, key)" style="margin-bottom: 1px;">
											<small><i class="fa-solid fa-trash"></i></small> Delete
										</button>
									</div>
									<div style="display: flex;">
										<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_'+key+'_'+task.id"></div>
										<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[key])"></div>
									</div>
								</template>
							</template>
						</template>
						<button class="btn btn-primary" @click="add_notes_task()">Add notes</button>
					</div>
					<div v-else>
						<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
							<div>
								<button class="btn btn-primary btn-sm" @click="modif_note(task, -1, 0)" type="button" :id="'note_'+task.id" style="margin-bottom: 3px;">
									<div hidden>[[task.title]]</div>
									Create
								</button>
							</div>
							<div style="display: flex;">
								<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_0_'+task.id"></div>
								<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[0])"></div>
							</div>
						</template>
					</div>
				</div>
			</div>
		</div>
	</div>
	`
}