import {display_toast} from '../toaster.js'
import { renderMarkdownServer } from '/static/js/markdown_render.js'
const { ref } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		status_info: Object
	},
	setup(props) {
		const hedgedoc_notes = ref("")
		const rendered_notes = ref("")
		const is_loading = ref(false)

		async function get_hedgedoc_notes(){
			is_loading.value = true
			const res = await fetch('/case/' + props.cases_info.case.id + '/get_hedgedoc_notes')
			if(await res.status == 200){
				let loc = await res.json()
				headgedoc_notes.value = loc["notes"]
				rendered_notes.value = await renderMarkdownServer({ markdown: hedgedoc_notes.value || '' })
			}else{
				await display_toast(res)
				$("#hedgedoc_input_error").text("Error with the url")
				headgedoc_notes.value = ""
				rendered_notes.value = ""
			}
			is_loading.value = false
		}
		get_hedgedoc_notes()

		async function change_hedgedoc_url(){
			$("#hedgedoc_input_error").text("")
			let loc_hedgedoc_url = $("#hedgedoc_input").val()
			const res = await fetch(
				'/case/' + props.cases_info.case.id + '/change_hedgedoc_url',{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"hedgedoc_url": loc_hedgedoc_url})
				}
			)
			if(await res.status == 200){
				props.cases_info.case.hedgedoc_url = loc_hedgedoc_url
				await get_hedgedoc_notes()
			}else{
				await display_toast(res)
				$("#hedgedoc_input_error").text("Error with the url")
				headgedoc_notes.value = ""
				rendered_notes.value = ""
			}
		}

		return {
			hedgedoc_notes,
			rendered_notes,
			is_loading,
			get_hedgedoc_notes,
			change_hedgedoc_url
		}
    },
	template: `
		<div class="d-flex">
			<button v-if="!is_loading" class="btn btn-primary mb-3" @click="get_hedgedoc_notes()">Refresh</button> 
			<button v-else class="btn btn-primary" type="button" disabled>
				<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
				<span role="status">Loading...</span>
			</button>
			<div style="left: 40%; position: absolute;">
				<input 
					class="form-control rounded" 
					type="text"
					style="margin-right: 5px; min-width: 400px; display: initial; width: 0;" 
					:value="cases_info.case.hedgedoc_url" id="hedgedoc_input" 
					:title="cases_info.case.hedgedoc_url" 
				/>
				<button class="btn btn-primary" @click="change_hedgedoc_url()">Change url</button>
				<div id="hedgedoc_input_error" style="color: brown"></div>
			</div>
		</div>
		<p v-if="hedgedoc_notes" style="background-color: white; border: 1px #515151 solid; padding: 5px;" v-html="rendered_notes"></p>
		<p v-else><i>No notes</i></p>
    `
}