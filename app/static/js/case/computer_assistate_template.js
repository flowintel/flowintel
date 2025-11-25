import {display_toast} from '../toaster.js'
const { ref, onMounted } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object
	},
	setup(props) {
		const computer_assistate_report = ref("")
		const md = window.markdownit()			// Library to Parse and display markdown
		md.use(mermaidMarkdown.default)			// Use mermaid library
		const is_loading = ref(false)
		const is_exporting = ref(false)
		const markdown_view = ref(false)

		async function get_computer_assistate_report(){
			is_loading.value = true
			const res = await fetch('/case/' + props.cases_info.case.id + '/get_computer_assistate_report')
			if(await res.status == 200){
				let loc = await res.json()
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
				if (loc["report_status"] == "done")
					await get_computer_assistate_report()
				else
					computer_assistate_report.value = 'running'
			}else{
				await display_toast(res)
				computer_assistate_report.value = ""
				await get_computer_assistate_report()
			}
			is_loading.value = false
		}



		async function generate_computer_assistate_report(){
			computer_assistate_report.value = ""
			is_loading.value = true
			const res = await fetch('/case/' + props.cases_info.case.id + '/run_computer_assistate_report')
			
			if(res.status == 200){
				computer_assistate_report.value = "running"
			}else{
				computer_assistate_report.value = ""
			}
			await display_toast(res, true)
			is_loading.value = false
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

		onMounted( () => {
			get_status_computer_assistate_report()
		})

		return {
			md,
			computer_assistate_report,
			is_loading,
			is_exporting,
			markdown_view,
			get_computer_assistate_report,
			generate_computer_assistate_report,
			get_status_computer_assistate_report,
			download_report,
			download_markdown
		}
    },
	template: `

		<div class="d-flex">
			<div v-if="computer_assistate_report && computer_assistate_report == 'running'">
				<button v-if="!is_loading" class="btn btn-primary mb-3" @click="get_status_computer_assistate_report()">Refresh</button> 
				<button v-else class="btn btn-primary" type="button" disabled>
					<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
					<span role="status"> Loading...</span>
				</button>
			</div>
			<div v-else-if="!computer_assistate_report">
				<button v-if="!is_loading" class="btn btn-primary mb-3" @click="generate_computer_assistate_report()">Generate</button> 
				<button v-else class="btn btn-primary" type="button" disabled>
					<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
					<span role="status"> Loading...</span>
				</button>
			</div>
			<div v-else>
				<button v-if="!is_loading" class="btn btn-primary mb-3" @click="generate_computer_assistate_report()">Regenerate</button> 
				<button v-else class="btn btn-primary" type="button" disabled>
					<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
					<span role="status"> Loading...</span>
				</button>
			</div>

			<template v-if="computer_assistate_report && computer_assistate_report != 'running'">
				<button class="btn btn-secondary mb-3 ms-2" @click="markdown_view = !markdown_view">
					<i :class="['fas', markdown_view ? 'fa-eye-slash' : 'fa-eye']"></i> Markdown
				</button>
				<div>
					<button class="btn btn-secondary dropdown-toggle ms-2" data-bs-toggle="dropdown" aria-expanded="false">
						<small><i class="fa-solid fa-download fa-fw"></i></small> Export
					</button>
					<ul class="dropdown-menu">
						<li>
							<button v-if="!is_exporting" class="btn btn-link" @click="download_report('pdf')" title="Export markdown as pdf">PDF</button>
							<button v-else class="btn btn-link" disabled>
								<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
								<span role="status">Loading...</span>
							</button>
						</li>
						<li>
							<button v-if="!is_exporting" class="btn btn-link" @click="download_report('docx')" title="Export markdown as docx">DOCX</button>
							<button v-else class="btn btn-link" disabled>
								<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
								<span role="status">Loading...</span>
							</button>
						</li>
						<li>
							<button v-if="!is_exporting" class="btn btn-link" @click="download_markdown()" title="Export markdown">MD</button>
							<button v-else class="btn btn-link" disabled>
								<span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
								<span role="status">Loading...</span>
							</button>
						</li>
					</ul>
				</div>
			</template>
		</div>

		<div class="case-core-style" v-if="computer_assistate_report">
			<template v-if="computer_assistate_report == 'running'">
				[[computer_assistate_report]]
			</template>
			<template v-else>
				<div v-if="markdown_view">
					<pre class="description">[[computer_assistate_report]]</pre>
				</div>
				<div v-else v-html="md.render(computer_assistate_report)"></div>
			</template>	
		</div>
    `
}