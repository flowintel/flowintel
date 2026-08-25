export default {
	delimiters: ['[[', ']]'],
	props: {
		task: Object
	},
	template: `
	<div class="row">
		<div class="col-auto">
			<div class="task-section">
				<div class="task-section-header">
					<i class="fa-solid fa-calendar-plus fa-sm me-1"></i>
					<span class="section-title">Creation date</span>
				</div>
				<div class="task-section-body">
					<i>[[task.creation_date]]</i>
				</div>
			</div>
		</div>
		<div class="col-auto">
			<div class="task-section">
				<div class="task-section-header">
					<i class="fa-solid fa-calendar-check fa-sm me-1"></i>
					<span class="section-title">Deadline</span>
				</div>
				<div class="task-section-body">
					<i>[[task.deadline]]</i>
				</div>
			</div>
		</div>
		<div class="col-auto">
			<div class="task-section" style="text-align: center;">
				<div class="task-section-header">
					<i class="fa-solid fa-clock fa-sm me-1"></i>
					<span class="section-title">Time required</span>
				</div>
				<div class="task-section-body">
					<i>[[task.time_required]]</i>
				</div>
			</div>
		</div>
		<div class="col-auto">
			<div class="task-section" style="text-align: center;">
				<div class="task-section-header">
					<i class="fa-solid fa-fingerprint fa-sm me-1"></i>
					<span class="section-title">UUID</span>
				</div>
				<div class="task-section-body">
					<i>[[task.uuid]]</i>
				</div>
			</div>
		</div>
	</div>
    `
}
