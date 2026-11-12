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

		// Sort field ('' = default order of the server) and direction
		const sort_field = ref('')
		const descending = ref(false)

		async function set_sort(field) {
			sort_field.value = field
			current_filter = field
			await asc_desc_filter()
		}

		async function toggle_order() {
			descending.value = !descending.value
			await asc_desc_filter(true)
		}

		async function asc_desc_filter(change = false) {
			emit("current_filter", current_filter)
			if (change)
				asc_desc = !asc_desc
			const res = await fetch(build_url(active_filter.value, 1, current_filter))
			const loc = await res.json()
			if (current_filter && !asc_desc) {
				for (let key in loc.tasks) {
					loc.tasks[key] = loc.tasks[key].reverse()
				}
			}
			emit('tasks_list', loc)
		}

		function activate_overdue() {
			// Programmatically activate the overdue filter (called from the parent badge)
			filter_tasks('overdue')
		}

		expose({ activate_overdue, filter_tasks, active_filter })

		const MODES = [
			{ value: 'ongoing', label: 'Ongoing', icon: 'fa-solid fa-spinner' },
			{ value: 'overdue', label: 'Overdue', icon: 'fa-solid fa-clock-rotate-left' },
			{ value: 'finished', label: 'Finished', icon: 'fa-solid fa-check' },
			{ value: 'inactive', label: 'Rejected / Unavailable', icon: 'fa-solid fa-ban' },
		]

		return {
			active_filter,
			filter_tasks,
			sort_field,
			descending,
			set_sort,
			toggle_order,
			MODES
		}
	},
	// Same controls as the other list pages (page_header macros): segmented status,
	// "Sort" select, and the order button
	template: `
	<div class="ctx-seg" role="group" aria-label="Task status">
		<button v-for="m in MODES" :key="m.value" type="button" :class="{ active: active_filter === m.value }"
				@click="active_filter !== m.value && filter_tasks(m.value)" :title="m.label + ' tasks'">
			<i :class="m.icon + ' fa-sm me-1'"></i>[[ m.label ]]
		</button>
	</div>
	<label class="ctx-select">
		<span>Sort</span>
		<select class="form-select form-select-sm" aria-label="Sort" :value="sort_field" @change="set_sort($event.target.value)">
			<option value="">Default</option>
			<option value="last_modif">Last modification</option>
			<option value="deadline">Deadline</option>
			<option value="title">Title</option>
			<option value="status_id">Status</option>
		</select>
	</label>
	<button type="button" class="ctx-ghost-btn" @click="toggle_order()" :disabled="!sort_field"
			:title="descending ? 'Descending order (click for ascending)' : 'Ascending order (click for descending)'">
		<i :class="['fa-solid fa-sm', descending ? 'fa-arrow-down-wide-short' : 'fa-arrow-up-short-wide']"></i>[[ descending ? 'Desc' : 'Asc' ]]
	</button>
	`
}
