import {display_toast, create_message} from '../toaster.js'
const { ref, onMounted, onUnmounted } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object
	},
	setup(props) {
		const computer_assistate_report = ref("")
		const model_input = ref("")
		const models = ref([])
		const prompt_input = ref("")
		const md = window.markdownit()			// Library to Parse and display markdown
		md.use(mermaidMarkdown.default)			// Use mermaid library
		const latest_model = ref("")
		const latest_prompt = ref("")
		const is_loading = ref(false)
		const is_exporting = ref(false)
		const markdown_view = ref(false)
		const status_timer = ref(null)

		function clear_status_timer(){
			if(status_timer.value){
				clearTimeout(status_timer.value)
				status_timer.value = null
			}
		}

		async function get_computer_assistate_report(){
			is_loading.value = true
			const res = await fetch('/case/' + props.cases_info.case.id + '/get_computer_assistate_report')
			if(await res.status == 200){
				let loc = await res.json()
				// Always store persisted model/prompt for on-demand viewing
				latest_model.value = loc["model"] || ""
				latest_prompt.value = loc["prompt"] || ""

				computer_assistate_report.value = loc["report"]
				
			}else{
				await display_toast(res, true)
				computer_assistate_report.value = ""
			}
			is_loading.value = false
		}

		async function get_status_computer_assistate_report(){
			is_loading.value = true
			const res = await fetch('/case/' + props.cases_info.case.id + '/status_computer_assistate_report')
			if(await res.status == 200){
				let loc = await res.json()
				if (loc["report_status"] == "done"){
					await create_message(loc["message"], "success-subtle", true)
					clear_status_timer()
					await get_computer_assistate_report()
				}
				else{
					computer_assistate_report.value = 'running'
					clear_status_timer()
					status_timer.value = setTimeout(() => {get_status_computer_assistate_report()}, 10000)
				}
			}else{
				await display_toast(res)
				computer_assistate_report.value = ""
				clear_status_timer()
				await get_computer_assistate_report()
			}
			is_loading.value = false
		}



		async function generate_computer_assistate_report(){
			computer_assistate_report.value = ""
			is_loading.value = true
			let url = '/case/' + props.cases_info.case.id + '/run_computer_assistate_report'
			const params = []
			if(model_input.value) params.push('model=' + encodeURIComponent(model_input.value))
			if(prompt_input.value) params.push('prompt=' + encodeURIComponent(prompt_input.value))
			if(params.length) url += '?' + params.join('&')
			const res = await fetch(url)
			
			if(res.status == 200){
				computer_assistate_report.value = "running"
				clear_status_timer()
				status_timer.value = setTimeout(() => {get_status_computer_assistate_report()}, 10000)
			}else{
				computer_assistate_report.value = ""
				clear_status_timer()
			}
			await display_toast(res, true)
			is_loading.value = false
		}

		async function fetch_ollama_models(){
			try{
				const res = await fetch('/case/list_ollama_models')
				if(res.status == 200){
					const loc = await res.json()
					models.value = loc.models || []
				}else{
					await display_toast(res)
				}
			}catch(e){
				console.error('Error fetching ollama models', e)
			}
		}

		async function download_report(type){
			// Export notes in different format and download it
			is_exporting.value = true
			let filename = ""
			await fetch('/case/'+props.cases_info.case.id+'/export_computer_assistate_report?type=' + type)
			.then(res => {
				if(res.status != 200){
					display_toast(res, true)
					is_exporting.value = false
					return null
				}
			})
			.then(res =>{
				if(!res) return
				filename = res.headers.get("content-disposition").split("=")
				filename = filename[filename.length - 1]
				return res.blob() 
			})
			.then(data =>{
				if(!data) return
				var a = document.createElement("a")
				a.href = window.URL.createObjectURL(data);
				a.download = filename;
				a.click();
			})
			is_exporting.value = false
		}

		function download_markdown(){
			// Download markdown file
			var blob = new Blob([computer_assistate_report.value], {type: "text/markdown;charset=utf-8"});
			var a = document.createElement("a")
			a.href = window.URL.createObjectURL(blob);
			a.download = "computer_assistate_report.md";
			a.click();
		}

		function show_full_prompt(){
			try{
				const modalEl = document.getElementById('aiPromptModal')
				if(!modalEl) return
				const modal = bootstrap.Modal.getOrCreateInstance(modalEl)
				modal.show()
			}catch(e){
				console.error('Error showing prompt modal', e)
			}
		}

		onMounted( () => {
			fetch_ollama_models()
			get_status_computer_assistate_report()
		})

		onUnmounted(() => {
			clear_status_timer()
		})

		return {
			md,
			computer_assistate_report,
			model_input,
			models,
			latest_model,
			latest_prompt,
			prompt_input,
			is_loading,
			is_exporting,
			markdown_view,
			status_timer,
			get_computer_assistate_report,
			generate_computer_assistate_report,
			get_status_computer_assistate_report,
			download_report,
			download_markdown,
			show_full_prompt
		}
    },
	template: `

		<div class="row g-3">
			<div class="col-md-4">
				<div class="case-core-style">
					<label class="form-label">Model</label>
					<select class="form-select form-select-sm mb-2" v-model="model_input">
						<option value="">Use default</option>
						<option v-for="m in models" :key="m" :value="m">[[m]]</option>
					</select>
					<label class="form-label">Prompt (optional)</label>
					<textarea class="form-control form-control-sm mb-2" v-model="prompt_input" rows="5" placeholder="Custom prompt to send to the model"></textarea>
					<div class="d-grid gap-2">
						<button v-if="!computer_assistate_report || computer_assistate_report == ''" :disabled="is_loading" class="btn btn-primary btn-sm" @click="generate_computer_assistate_report()">
							<i class="fas fa-robot me-1"></i> Generate
						</button>
						<button v-else-if="computer_assistate_report == 'running'" :disabled="is_loading" class="btn btn-warning btn-sm" @click="get_status_computer_assistate_report()">
							<i class="fas fa-spinner fa-spin me-1"></i> Check Status
						</button>
						<button v-else :disabled="is_loading" class="btn btn-primary btn-sm" @click="generate_computer_assistate_report()">
							<i class="fas fa-redo me-1"></i> Regenerate
						</button>
					</div>
				</div>
			</div>
			<div class="col-md-8" v-if="computer_assistate_report">
				<div class="d-flex justify-content-between mb-2">
					<div>
						<button class="btn btn-outline-secondary btn-sm me-2" @click="markdown_view = !markdown_view">
							<i :class="['fas', markdown_view ? 'fa-eye-slash' : 'fa-eye']"></i> View
						</button>
						<button v-if="latest_prompt" class="btn btn-outline-primary btn-sm me-2" @click="show_full_prompt()">Show full prompt</button>
					</div>
					<div>
						<div class="btn-group">
							<button class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown">Export</button>
							<ul class="dropdown-menu dropdown-menu-end">
								<li><button class="dropdown-item" @click="download_report('pdf')">Export PDF</button></li>
								<li><button class="dropdown-item" @click="download_report('docx')">Export DOCX</button></li>
								<li><button class="dropdown-item" @click="download_markdown()">Download MD</button></li>
							</ul>
						</div>
					</div>
				</div>
				<div class="case-core-style border p-3" v-if="computer_assistate_report && computer_assistate_report != 'running'">
					<div v-if="markdown_view">
						<pre class="description">[[computer_assistate_report]]</pre>
					</div>
					<div v-else v-html="md.render(computer_assistate_report)"></div>
				</div>
			</div>
		</div>

		<!-- Prompt modal -->
		<div class="modal fade" id="aiPromptModal" tabindex="-1" aria-hidden="true">
			<div class="modal-dialog modal-lg modal-dialog-scrollable">
				<div class="modal-content">
					<div class="modal-header">
						<h5 class="modal-title">Full AI Prompt</h5>
						<button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
					</div>
					<div class="modal-body">
						<pre style="white-space:pre-wrap;">[[ latest_prompt ]]</pre>
					</div>
					<div class="modal-footer">
						<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
					</div>
				</div>
			</div>
		</div>
	` 
	}