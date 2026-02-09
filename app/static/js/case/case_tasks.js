import { display_toast } from '/static/js/toaster.js'
import tabMain from './TaskComponent/tab-main.js'
import tabNote from './TaskComponent/tab-note.js'
import tabFile from './TaskComponent/tab-file.js'
import tabExternalRef from './TaskComponent/tab-external-ref.js'
import tabInfo from './TaskComponent/tab-info.js'
import caseconnectors from './CaseConnectors.js'
import { truncateText, getTextColor, mapIcon } from '/static/js/utils.js'
const { ref, nextTick } = Vue
export default {
	delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		status_info: Object,
		users_in_case: Object,
		task: Object,
		key_loop: Number,
		open_closed: Object,
		md: Object,
		all_connectors_list: Object,
		task_modules: Object,
	},
	components: {
		tabMain,
		tabNote,
		tabFile,
		tabExternalRef,
		tabInfo,
		caseconnectors
	},
	setup(props) {
		// Variables part
		let is_mounted = false			// Boolean use to know if the app is mount to initialize mermaid
		const selected_tab = ref("main")

		const module_loader = ref(false)
		const task_instances_selected = ref([])
		const task_module_selected = ref()
		const task_connectors_list = ref()

		const expandedTasks = ref({});



		async function complete_task(task) {
			// Complete a task
			const res = await fetch('/case/complete_task/' + task.id)
			if (await res.status == 200) {
				if (task.completed) {
					props.open_closed["open"] += 1
					props.open_closed["closed"] -= 1
				} else {
					props.open_closed["closed"] += 1
					props.open_closed["open"] -= 1
				}
				task.last_modif = Date.now()
				task.completed = !task.completed
				let status = task.status_id
				if (props.status_info.status[task.status_id - 1].name == 'Finished') {
					for (let i in props.status_info.status) {
						if (props.status_info.status[i].name == 'Created')
							task.status_id = props.status_info.status[i].id
					}
					if (task.status_id == status)
						task.status_id = 1

				} else {
					for (let i in props.status_info.status) {
						if (props.status_info.status[i].name == 'Finished') {
							task.status_id = props.status_info.status[i].id
							break
						}
					}
				}
				let index = props.cases_info.tasks.indexOf(task)
				if (index > -1)
					props.cases_info.tasks.splice(index, 1)
			}
			await display_toast(res)
		}

		async function fetch_task_connectors() {
			const res = await fetch("/case/get_task_connectors/" + props.task.id)
			if (await res.status == 404) {
				display_toast(res)
			} else {
				let loc = await res.json()
				task_connectors_list.value = loc["task_connectors"]
			}
		}

		async function fetch_module_selected(module) {
			// Get modules and instances linked on
			const res = await fetch("/case/" + window.location.pathname.split("/").slice(-1) + "/task/" + props.task.id + "/get_instance_module?type=send_to&module=" + module)
			if (await res.status == 400) {
				display_toast(res)
			} else {
				let loc = await res.json()
				task_module_selected.value = loc["instances"]
				await nextTick()
				$('#task_instances_select_' + props.task.id).select2({
					theme: 'bootstrap-5',
					width: '50%',
					closeOnSelect: false
				})
				$('#task_instances_select_' + props.task.id).on('change.select2', function (e) {
					let name_instance = $(this).select2('data').map(item => item.id)
					task_instances_selected.value = []
					for (let index in task_module_selected.value) {
						if (name_instance.includes(task_module_selected.value[index].name)) {
							if (!task_instances_selected.value.includes(task_module_selected.value[index]))
								task_instances_selected.value.push(task_module_selected.value[index])
						}
					}
				})
			}
		}

		function present_user_in_task(task_user_list, user) {
			// Check if user is already assign
			let index = -1

			for (let i = 0; i < task_user_list.length; i++) {
				if (task_user_list[i].id == user.id)
					index = i
			}
			return index
		}

		async function remove_assign_task(task, current_user) {
			// Remove current user from assignment to the task
			const res = await fetch('/case/' + task.case_id + '/remove_assignment/' + task.id)

			if (await res.status == 200) {
				task.last_modif = Date.now()
				task.is_current_user_assigned = false

				let index = -1

				for (let i = 0; i < task.users.length; i++) {
					if (task.users[i].id == current_user.id)
						index = i
				}

				if (index > -1)
					task.users.splice(index, 1)
			}
			await display_toast(res)
		}

		async function take_task(task, current_user) {
			// Assign the task to the current user
			const res = await fetch('/case/' + task.case_id + '/take_task/' + task.id)

			if (await res.status == 200) {
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

		function endOf(dt) {
			return dayjs.utc(dt).endOf().from(dayjs.utc())
		}

		function select2_change(tid) {
			$('.select2-selectUser' + tid).select2({ width: 'element' })
			$('.select2-container').css("min-width", "200px")
		}


		async function select_tab_task(tab_name) {
			if (tab_name == 'main') {
				selected_tab.value = 'main'
				if (!document.getElementById("tab-task-main-" + props.task.id).classList.contains("active")) {
					document.getElementById("tab-task-main-" + props.task.id).classList.add("active")
					document.getElementById("tab-task-notes-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-files-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-external-ref-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-connectors-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-info-" + props.task.id).classList.remove("active")
				}
			} else if (tab_name == 'notes') {
				selected_tab.value = 'notes'
				if (!document.getElementById("tab-task-notes-" + props.task.id).classList.contains("active")) {
					document.getElementById("tab-task-notes-" + props.task.id).classList.add("active")
					document.getElementById("tab-task-main-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-files-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-external-ref-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-connectors-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-info-" + props.task.id).classList.remove("active")
				}
				await nextTick()
				props.md.mermaid.run({
					querySelector: `#collapse${props.task.id} .mermaid`
				})
			} else if (tab_name == 'files') {
				selected_tab.value = 'files'
				if (!document.getElementById("tab-task-files-" + props.task.id).classList.contains("active")) {
					document.getElementById("tab-task-files-" + props.task.id).classList.add("active")
					document.getElementById("tab-task-main-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-notes-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-external-ref-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-connectors-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-info-" + props.task.id).classList.remove("active")
				}
			} else if (tab_name == 'external-ref') {
				selected_tab.value = 'external-ref'
				if (!document.getElementById("tab-task-external-ref-" + props.task.id).classList.contains("active")) {
					document.getElementById("tab-task-external-ref-" + props.task.id).classList.add("active")
					document.getElementById("tab-task-main-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-notes-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-files-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-connectors-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-info-" + props.task.id).classList.remove("active")
				}
			} else if (tab_name == 'connectors') {
				// await fetch_task_connectors()
				await nextTick()
				selected_tab.value = 'connectors'
				if (!document.getElementById("tab-task-connectors-" + props.task.id).classList.contains("active")) {
					document.getElementById("tab-task-connectors-" + props.task.id).classList.add("active")
					document.getElementById("tab-task-main-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-notes-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-files-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-external-ref-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-info-" + props.task.id).classList.remove("active")
				}
			}
			else if (tab_name == 'info') {
				selected_tab.value = 'info'
				if (!document.getElementById("tab-task-info-" + props.task.id).classList.contains("active")) {
					document.getElementById("tab-task-info-" + props.task.id).classList.add("active")
					document.getElementById("tab-task-main-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-notes-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-files-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-external-ref-" + props.task.id).classList.remove("active")
					document.getElementById("tab-task-connectors-" + props.task.id).classList.remove("active")

				}
			}

		}

		function toggleCollapse(id) {
			const collapseEl = document.getElementById('collapse' + id);
			const collapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
			collapse.toggle();
		}


		// Vue function
		Vue.onMounted(() => {
			fetch_task_connectors()
			select2_change(props.task.id)
			// $('.select2-select').select2({
			// 	theme: 'bootstrap-5',
			// 	width: '50%',
			// 	closeOnSelect: false
			// })

			// When openning a task, initialize mermaid library
			// const allCollapses = document.getElementById('collapse' + props.task.id)
			// allCollapses.addEventListener('shown.bs.collapse', event => {
			// 	props.md.mermaid.run({
			// 		querySelector: `#${event.target.id} .mermaid`
			// 	})
			// })
			is_mounted = true

		})
		Vue.onUpdated(() => {
			select2_change(props.task.id)
			// do not initialize mermaid before the page is mounted
			if (is_mounted) {
				$('#task_modules_select_' + props.task.id).on('change.select2', function (e) {
					if ($(this).select2('data').map(item => item.id)[0] == "None") {
						task_module_selected.value = []
					} else {
						fetch_module_selected($(this).select2('data').map(item => item.id))
					}
				})
			}
		})

		return {
			getTextColor,
			mapIcon,
			module_loader,
			task_instances_selected,
			task_module_selected,
			selected_tab,
			task_connectors_list,
			expandedTasks,

			take_task,
			remove_assign_task,
			complete_task,
			formatNow,
			endOf,
			present_user_in_task,

			select_tab_task,
			fetch_task_connectors,
			truncateText,
			toggleCollapse
		}
	},
	template: `
	<div style="display: flex;">                          
		<a href="javascript:void(0)" 
			class="list-group-item list-group-item-action case-index-list"
			style="border-top-left-radius: 15px; border-top-right-radius: 15px;"
			@click="toggleCollapse(task.id)"
		>
			<div class="d-flex w-100 justify-content-between">
				<h5 class="mb-1"><i class="fa-solid fa-angle-right fa-sm me-2" style="color: #6c757d;"></i>[[ key_loop+1 ]]- [[task.title]]</h5>
				<small :title="'Changed: ' + task.last_modif"><i><i class="fa-solid fa-arrows-rotate"></i> [[ formatNow(task.last_modif) ]] </i></small>
			</div>

			<div class="d-flex w-100 justify-content-between mt-1">
				<template v-if="task.description">
					<template v-if="task.description.length > 300">
						<div class="position-relative">
							<button
								type="button"
								class="btn btn-outline-primary btn-sm float-end me-2"
								@click.stop.prevent="expandedTasks[task.id] = !expandedTasks[task.id];"
								title="See the full description"
							>
								<i :class="['fa-solid', expandedTasks[task.id] ? 'fa-chevron-up' : 'fa-chevron-down']"></i>
							</button>

							<!-- Show either truncated or full text -->
							<pre class="description" v-html="md.render(expandedTasks[task.id] ? task.description : truncateText(task.description))"></pre>
						</div>
					</template>
					<template v-else>
						<pre v-html="md.render(task.description)" class="description"></pre>
					</template>
				</template>
				<template v-else>
					<p class="card-text"><i style="font-size: 12px;">No description</i></p>
				</template>

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
						<span v-if="user.nickname" class="btn btn-primary btn-sm person" :title="user.first_name+' ' +user.last_name">
							<i class="fa-solid fa-user"></i> [[user.nickname]]
						</span>
						<span v-else class="btn btn-primary btn-sm person" :title="user.first_name+' ' +user.last_name">
							<i class="fa-solid fa-user"></i> [[user.last_name]]
						</span>
					</template>
                </div>

                <div v-else>
                    <i>No user assigned</i>
                </div>
                <small v-if="task.deadline" :title="'Deadline: ' + task.deadline"><i><i class="fa-solid fa-hourglass-start"></i> [[endOf(task.deadline)]]</i></small>
                <small v-else><i>No deadline</i></small>
            </div>
			<div class="d-flex w-100 justify-content-between">
				<div style="display: flex;" v-if="task.galaxies">
					<template v-for="galaxy in task.galaxies">
						<div :title="'Description:\\n' + galaxy.description">
							<span class="cluster">
								<span v-html="mapIcon(galaxy.icon)"></span>
								[[galaxy.name]]
							</span>
						</div>
					</template>
				</div>
				<div v-else></div>
			</div>
			<div class="d-flex w-100 justify-content-between">
				<div style="display: flex;" v-if="task.clusters">
					<template v-for="cluster in task.clusters">
						<div :title="'Description:\\n' + cluster.description + '\\n\\nMetadata:\\n' + cluster.meta">
							<span v-html="mapIcon(cluster.icon)"></span>
							[[cluster.tag]]
						</div>
					</template>
				</div>
				<div v-else></div>
			</div>
			<div class="d-flex w-100 mt-2 justify-content-between">
				<span class="badge rounded-pill" style="color: black; background-color: aliceblue; font-weight: normal">
					<i>[[task.files.length]] Files</i>
				</span>
				<span class="badge rounded-pill" style="color: black; background-color: aliceblue; font-weight: normal">
					<i>[[task.notes.length]] Notes</i>
				</span>
				<span class="badge rounded-pill" style="color: black; background-color: aliceblue; font-weight: normal">
					<i>[[task.urls_tools.length]] Urls/Tools</i>
				</span>
			</div>
			<div class="mt-2 card card-body" v-if="task.subtasks.length && task.nb_open_subtasks > 0" style="filter:drop-shadow(1px 1px 2px rgba(181, 181, 181, 0.5))">
				<div style="margin-bottom: 3px"><b><u>Subtasks: </u></b></div>
				<template v-for="subtask in task.subtasks">
					<div v-if="!subtask.completed" style="display: flex;">
						<div class="subtask-tree"></div>
						[[subtask.description]]
					</div>
				</template>
			</div>
		</a>
		<div v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
			<div>
				<button v-if="task.completed" class="btn btn-secondary"  @click="complete_task(task)" title="Revive the task">
					<i class="fa-solid fa-backward fa-fw"></i>
				</button>
				<button v-else class="btn btn-success" @click="complete_task(task)" title="Complete the task">
					<i class="fa-solid fa-check fa-fw"></i>
				</button>
			</div>
			<div>
				<button v-if="!task.is_current_user_assigned" class="btn btn-secondary" @click="take_task(task, cases_info.current_user)" title="Be assigned to the task">
					<i class="fa-solid fa-hand fa-fw"></i>
				</button>
				<button v-else class="btn btn-secondary" @click="remove_assign_task(task, cases_info.current_user)" title="Remove the assignment">
					<i class="fa-solid fa-handshake-slash fa-fw"></i>
				</button>
			</div>
			<div>
				<a class="btn btn-primary" :href="'/case/'+cases_info.case.id+'/edit_task/'+task.id" type="button" title="Edit the task">
					<i class="fa-solid fa-pen-to-square fa-fw"></i>
				</a>
			</div>
		</div>
	</div>
	
	<!-- Collapse Part -->
	<div class="collapse" :id="'collapse'+task.id">
		<div class="card card-body" style="background-color: whitesmoke;">
			
			<ul class="nav nav-tabs" style="margin-bottom: 10px;">
				<li class="nav-item">
					<button class="nav-link active" :id="'tab-task-main-'+task.id" aria-current="page" @click="select_tab_task('main')">
						<i class="fa-solid fa-house fa-sm me-1"></i><span class="section-title">Main</span>
					</button>
				</li>
				<li class="nav-item">
					<button class="nav-link" :id="'tab-task-notes-'+task.id" @click="select_tab_task('notes')">
					<i class="fa-solid fa-note-sticky fa-sm me-1"></i><span class="section-title">Notes<template v-if="task.notes.length"> ([[ task.notes.length ]])</template></span>
					</button>
				</li>
				<li class="nav-item">
					<button class="nav-link" :id="'tab-task-connectors-'+task.id" @click="select_tab_task('connectors')">
					<i class="fa-solid fa-plug fa-sm me-1"></i><span class="section-title">Connectors<template v-if="task_connectors_list && task_connectors_list.length"> ([[ task_connectors_list.length ]])</template></span>
					</button>
				</li>
				<li class="nav-item">
					<button class="nav-link" :id="'tab-task-files-'+task.id" @click="select_tab_task('files')">
					<i class="fa-solid fa-file fa-sm me-1"></i><span class="section-title">Files<template v-if="task.files.length"> ([[ task.files.length ]])</template></span>
					</button>
				</li>
				<li class="nav-item">
					<button class="nav-link" :id="'tab-task-external-ref-'+task.id" @click="select_tab_task('external-ref')">
					<i class="fa-solid fa-link fa-sm me-1"></i><span class="section-title">External references<template v-if="task.external_references && task.external_references.length"> ([[ task.external_references.length ]])</template></span>
					</button>
				</li>
				<li class="nav-item">
					<button class="nav-link" :id="'tab-task-info-'+task.id" @click="select_tab_task('info')">
						<i class="fa-solid fa-circle-info fa-sm me-1"></i><span class="section-title">Info</span>
					</button>
				</li>
			</ul>

			<template v-if="selected_tab == 'main'">
				<tabMain :cases_info="cases_info" 
						 :users_in_case="users_in_case" 
						 :status_info="status_info" 
						 :task="task"
						 :task_modules="task_modules"
						 :open_closed="open_closed">
                </tabMain>
			</template>

			<template v-else-if="selected_tab == 'notes'">
				<tabNote :cases_info="cases_info"
						 :task="task"
						 :md="md">
                </tabNote>
			</template>

			<template v-else-if="selected_tab == 'connectors'">
				<div class="card card-body">
					<caseconnectors 
						:case_task_connectors_list="task_connectors_list"
						:all_connectors_list="all_connectors_list"
						:modules="task_modules"
						:is_case="false"
						:object_id="task.id"
						:cases_info="cases_info"
						@case_connectors=""
						@task_connectors="(msg) => fetch_task_connectors()">
					</caseconnectors>
				</div>
			</template>

			<template v-else-if="selected_tab == 'files'">
				<tabFile :cases_info="cases_info" :task="task"></tabFile>
			</template>

			<template v-else-if="selected_tab == 'external-ref'">
				<tabExternalRef :cases_info="cases_info" :task="task"></tabExternalRef>
			</template>

			<template v-else-if="selected_tab == 'info'">
				<tabInfo :task="task" :cases_info="cases_info" :open_closed="open_closed"></tabInfo>
			</template>
		</div>
	</div>
	`
}