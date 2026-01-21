import { display_toast } from '/static/js/toaster.js'

export default {
	delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		task: Object,
		open_closed: Object
	},
	setup(props) {

		async function delete_task(task, task_array) {
			// delete the task
			const res = await fetch('/case/' + task.case_id + '/delete_task/' + task.id)

			if (await res.status == 200) {
				if (task.completed) {
					props.open_closed["closed"] -= 1
				} else {
					props.open_closed["open"] -= 1
				}

				// remove the task from the list of task
				let index = task_array.indexOf(task)
				if (index > -1)
					task_array.splice(index, 1)

				$("#modal-delete-task-" + task.id).modal("hide")
			}
			await display_toast(res)
		}


		return {
			delete_task
		}
	},
	template: `
	<div class="row">
		<div class="col-auto">
			<fieldset class="analyzer-select-case">
				<legend class="analyzer-select-case"><i class="fa-solid fa-calendar-plus fa-sm me-1"></i><span class="section-title">Creation date</span></legend>
				<i>[[task.creation_date]]</i>
			</fieldset>
		</div>
		<div class="col-auto">
			<fieldset class="analyzer-select-case">
				<legend class="analyzer-select-case"><i class="fa-solid fa-calendar-check fa-sm me-1"></i><span class="section-title">Deadline</span></legend>
				<i>[[task.deadline]]</i>
			</fieldset>
		</div>
		<div class="col-auto">
			<fieldset class="analyzer-select-case" style="text-align: center;">
				<legend class="analyzer-select-case"><i class="fa-solid fa-clock fa-sm me-1"></i><span class="section-title">Time required</span></legend>
				<i>[[task.time_required]]</i>
			</fieldset>
		</div>
	</div>
	<div class="row">
		<div class="col">
			<button class="btn btn-danger btn-sm" title="Delete the task" data-bs-toggle="modal" :data-bs-target="'#modal-delete-task-'+task.id">
				<i class="fa-solid fa-trash fa-fw"></i> Delete The task
			</button>
		</div>
	</div>

	<!-- Modal delete task -->
	<div class="modal fade" :id="'modal-delete-task-'+task.id" tabindex="-1" aria-labelledby="delete_task_modal" aria-hidden="true">
		<div class="modal-dialog modal-sm">
			<div class="modal-content">
				<div class="modal-header">
					<h1 class="modal-title fs-5" id="delete_task_modal">Delete '[[task.title]]' ?</h1>
					<button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
					<button class="btn btn-danger btn-sm" @click="delete_task(task, cases_info.tasks)"><i class="fa-solid fa-trash"></i> Confirm</button>
				</div>
			</div>
		</div>
	</div>
    `
}