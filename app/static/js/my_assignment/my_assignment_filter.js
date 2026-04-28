export default {
	delimiters: ['[[', ']]'],
	props: {
		tasks_list: Object
	},
	emits: ['tasks_list', 'current_filter', 'active_mode'],
	setup(props, { emit, expose }) {
		const { ref } = Vue
		const active_filter = ref('ongoing')
		let current_filter = ""
		let asc_desc = true

		const FILTER_LABELS = {
			ongoing: 'Ongoing tasks',
			finished: 'Finished tasks',
			inactive: 'Rejected / Unavailable',
			overdue: 'Overdue tasks'
		}

		function build_url(mode, page = 1, sort_field = "") {
			let url = `/my_assignment/sort_tasks?page=${page}`
			if (mode === 'finished') {
				url += '&status=false'
			} else {
				url += '&status=true'
			}
			if (mode === 'inactive') {
				url += '&inactive=true'
			}
			if (mode === 'overdue') {
				url += '&overdue=true'
			}
			if (sort_field) {
				url += `&filter=${sort_field}`
			}
			return url
		}

		async function filter_tasks(mode) {
			active_filter.value = mode
			emit('active_mode', { mode, label: FILTER_LABELS[mode] || '' })
			const res = await fetch(build_url(mode, 1, current_filter))
			const loc = await res.json()
			if (current_filter && !asc_desc) {
				for (let key in loc.tasks) {
					loc.tasks[key] = loc.tasks[key].reverse()
				}
			}
			emit('tasks_list', loc)
		}

		function sort_by_title() {
			current_filter = "title"
			asc_desc_filter()
		}

		function sort_by_last_modif() {
			current_filter = "last_modif"
			asc_desc_filter()
		}

		function sort_by_deadline() {
			current_filter = "deadline"
			asc_desc_filter()
		}

		function sort_by_status() {
			current_filter = "status_id"
			asc_desc_filter()
		}

		async function asc_desc_filter(change = false) {
			emit("current_filter", current_filter)
			if (change)
				asc_desc = !asc_desc

			if (current_filter) {
				const res = await fetch(build_url(active_filter.value, 1, current_filter))
				const loc = await res.json()
				if (!asc_desc) {
					for (let key in loc.tasks) {
						loc.tasks[key] = loc.tasks[key].reverse()
					}
				}
				emit('tasks_list', loc)
			}
		}

		function activate_overdue() {
			// Programmatically activate the overdue filter (called from the parent badge)
			filter_tasks('overdue')
			const collapse = document.getElementById('collapsefiltertask')
			if (collapse && !collapse.classList.contains('show')) {
				collapse.classList.add('show')
			}
		}

		expose({ activate_overdue, filter_tasks, active_filter })

		return {
			active_filter,
			filter_tasks,
			sort_by_last_modif,
			sort_by_title,
			sort_by_deadline,
			sort_by_status,
			asc_desc_filter
		}
	},
	template: `
	<button class="btn position-relative"
			:class="active_filter === 'ongoing' ? 'btn-outline-primary' : 'btn-primary'"
			type="button" data-bs-toggle="collapse" data-bs-target="#collapsefiltertask"
			aria-expanded="false" aria-controls="collapsefiltertask"
			:title="active_filter === 'ongoing' ? 'Filter tasks' : 'Filter active'">
		<i class="fa-solid fa-filter"></i>
		<span v-if="active_filter !== 'ongoing'"
			  class="position-absolute top-0 start-100 translate-middle p-1 bg-warning border border-light rounded-circle"
			  style="width: 12px; height: 12px;">
			<span class="visually-hidden">Filter active</span>
		</span>
	</button>
	<div class="collapse" id="collapsefiltertask">
		<div class="card card-body">
			<div class="d-flex w-100 justify-content-between">
				<div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioStatus" id="radioStatusOngoing" :checked="active_filter === 'ongoing'" @click="filter_tasks('ongoing')">
						<label class="form-check-label" for="radioStatusOngoing"><i class="fa-solid fa-spinner fa-sm me-1"></i>Ongoing tasks</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioStatus" id="radioStatusOverdue" :checked="active_filter === 'overdue'" @click="filter_tasks('overdue')">
						<label class="form-check-label" for="radioStatusOverdue"><i class="fa-solid fa-clock-rotate-left fa-sm me-1 text-danger"></i>Overdue tasks</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioStatus" id="radioStatusFinished" :checked="active_filter === 'finished'" @click="filter_tasks('finished')">
						<label class="form-check-label" for="radioStatusFinished"><i class="fa-solid fa-check-circle fa-sm me-1"></i>Finished tasks</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioStatus" id="radioStatusInactive" :checked="active_filter === 'inactive'" @click="filter_tasks('inactive')">
						<label class="form-check-label" for="radioStatusInactive"><i class="fa-solid fa-ban fa-sm me-1"></i>Rejected / Unavailable</label>
					</div>
				</div>

				<div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOtherTitle" @click="sort_by_title()">
						<label class="form-check-label" for="radioOtherTitle"><i class="fa-solid fa-heading fa-sm me-1"></i>Title</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOrderAsc" @click="sort_by_last_modif()">
						<label class="form-check-label" for="radioOrderAsc"><i class="fa-solid fa-clock-rotate-left fa-sm me-1"></i>Last modification</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOtherDeadLine" @click="sort_by_deadline()">
						<label class="form-check-label" for="radioOtherDeadLine"><i class="fa-solid fa-calendar-check fa-sm me-1"></i>Deadline</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOtherStatus" @click="sort_by_status()">
						<label class="form-check-label" for="radioOtherStatus"><i class="fa-solid fa-signal fa-sm me-1"></i>Status</label>
					</div>
				</div>

				<div style="display:flex">
				<span style="margin-right: 10px">Asc</span>
					<div class="form-check form-switch">
						<input class="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault" @click="asc_desc_filter(true)">
						<label class="form-check-label" for="flexSwitchCheckDefault">Desc</label>
					</div>
			  
				</div>
			</div>
		</div>
	</div>
	`
}
