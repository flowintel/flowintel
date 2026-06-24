import { display_toast } from '../toaster.js'
const { ref, onMounted, onUpdated } = Vue

export default {
	delimiters: ['[[', ']]'],
	props: {
		note_template: Object,
		key_loop: Number,
		notes_list: Array,
		can_edit: {
			type: Boolean,
			default: true
		}
	},
	setup(props) {
		const is_mounted = ref(false)

		const md = window.markdownit()
		md.use(mermaidMarkdown.default)

		const dayjs = window.dayjs

		onMounted(async () => {
			const allCollapses = document.getElementById('collapse' + props.note_template.id)
			if (allCollapses) {
				allCollapses.addEventListener('shown.bs.collapse', async event => {
					md.mermaid.init()
				})
			}
			is_mounted.value = true
		})

		onUpdated(async () => {
			if (is_mounted.value) {
				md.mermaid.init()
			}
		})

		async function delete_note_template(note_template, notes_array) {
			const res = await fetch("/tools/delete_note_template/" + note_template.id)
			if (await res.status == 200) {
				let index = notes_array.indexOf(note_template)
				if (index > -1)
					notes_array.splice(index, 1)

				var myModalEl = document.getElementById('delete_note_template_modal_' + note_template.id);
				var modal = bootstrap.Modal.getInstance(myModalEl)
				modal.hide();
			}
			display_toast(res)
		}

		function toggleCollapse(id) {
			const collapseEl = document.getElementById('collapse' + id);
			const collapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
			collapse.toggle();
		}

		return {
			md,
			dayjs,
			delete_note_template,
			toggleCollapse
		}
	},
	template: `
	<div style="display: flex;"> 
        <a href="javascript:void(0)"
			class="list-group-item list-group-item-action case-index-list"
			style="border-top-left-radius: 15px; border-top-right-radius: 15px;"
			@click="toggleCollapse(note_template.id)"
		>        
            <div class="d-flex w-100 justify-content-between">
                <h5 class="mb-1">
					<i class="fa-solid fa-note-sticky fa-sm me-2"></i>
					[[ key_loop+1 ]]-[[ note_template.title ]]
				</h5>
            </div>
			
			<div class="d-flex w-100 justify-content-between" v-if="note_template.description">
				<pre class="description">[[ note_template.description ]]</pre>
			</div>

			<div class="case-meta-grid" style="margin-bottom: 4px;">
				<div class="case-meta-item" v-if="note_template.last_modif" :title="'Modified: ' + note_template.last_modif">
					<i class="fa-solid fa-clock-rotate-left fa-fw"></i>
					<span class="meta-label">Modified</span>
					<span class="meta-value">[[ dayjs.utc(note_template.last_modif).fromNow() ]]</span>
				</div>
				<div class="case-meta-item" v-if="note_template.uuid" :title="note_template.uuid">
					<i class="fa-solid fa-fingerprint fa-fw"></i>
					<span class="meta-label">UUID</span>
					<span class="meta-value" style="font-family: monospace; font-size: 0.8em;">[[note_template.uuid]]</span>
				</div>
				<div class="case-meta-item" v-if="note_template.version">
					<i class="fa-solid fa-code-branch fa-fw"></i>
					<span class="meta-label">Version</span>
					<span class="meta-value">v[[note_template.version]]</span>
				</div>
			</div>
        </a>
		
		<div v-if="can_edit">
			<div>
				<a class="btn btn-primary" :href="'/tools/edit_note_template_view/'+note_template.id" type="button" title="Edit the note template">
					<i class="fa-solid fa-pen-to-square fa-fw"></i>
				</a>
			</div>
			<div>
				<button type="button" class="btn btn-danger" title="Delete the note template" data-bs-toggle="modal" 
					:data-bs-target="'#delete_note_template_modal_'+note_template.id">
					<i class="fa-solid fa-trash fa-fw"></i>
				</button>
			</div>
		</div>
	</div>

	<!-- Modal delete note template -->
	<div v-if="can_edit" class="modal fade" :id="'delete_note_template_modal_'+note_template.id" tabindex="-1" aria-labelledby="delete_note_template_modal" aria-hidden="true">
		<div class="modal-dialog">
			<div class="modal-content">
				<div class="modal-header">
					<h1 class="modal-title fs-5" id="delete_note_template_modal">Delete '[[note_template.title]]' ?</h1>
					<button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
				</div>
				<div class="modal-footer">
					<button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
					<button class="btn btn-danger btn-sm" @click="delete_note_template(note_template, notes_list)">
						<i class="fa-solid fa-trash"></i> Confirm
					</button>
				</div>
			</div>
		</div>
	</div>

	<!-- Collapse Part -->
	<div class="collapse" :id="'collapse'+note_template.id">
		<div class="card card-body" style="background-color: whitesmoke;">
			<!-- Content preview (editing happens on the edit page) -->
			<div>
				<fieldset class="analyzer-select-case">
					<legend class="analyzer-select-case">
						<i class="fa-solid fa-file-lines fa-sm me-1"></i><span class="section-title">Content</span>
					</legend>

					<div v-if="note_template.content" class="markdown-render-result" v-html="md.render(note_template.content)"></div>
					<div v-else><i style="font-size: 12px;">No content</i></div>
				</fieldset>
			</div>
		</div>
	</div>
	`
}
