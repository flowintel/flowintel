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
	<div class="col" v-if="task.instances.length">
        <fieldset class="analyzer-select-case">
            <legend class="analyzer-select-case"><i class="fa-solid fa-link"></i> Connectors</legend>
            <div v-for="instance in task.instances" :title="instance.description">
                <img :src="'/static/icons/'+instance.icon" style="max-width: 30px;">
                <a style="margin-left: 5px" :href="instance.url">[[instance.url]]</a>
                <span style="margin-left: 3px;" title="identifier used by module">[[instance.identifier]]</span>
            </div>
        </fieldset>
    </div>
    `
}