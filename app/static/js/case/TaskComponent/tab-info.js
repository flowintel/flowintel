import {display_toast, create_message} from '/static/js/toaster.js'
const { ref } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		task: Object
	},
	setup(props) {

        
		return {
            
		}
    },
	template: `
	<div class="row">
		<div class="col-auto">
			<fieldset class="analyzer-select-case">
				<legend class="analyzer-select-case">Creation date</legend>
				<i>[[task.creation_date]]</i>
			</fieldset>
		</div>
		<div class="col-auto">
			<fieldset class="analyzer-select-case" style="text-align: center;">
				<legend class="analyzer-select-case">Time required</legend>
				<i>[[task.time_required]]</i>
			</fieldset>
		</div>
	</div>
    `
}