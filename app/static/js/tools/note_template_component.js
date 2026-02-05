import { display_toast } from '../toaster.js'
import { renderMarkdownServer } from '/static/js/markdown_render.js'
const { ref, nextTick, onMounted, watch } = Vue
const { EditorView, basicSetup, languages } = window.CodeMirrorBundle;

export default {
	delimiters: ['[[', ']]'],
	props: {
		note_template: Object,
		key_loop: Number,
		notes_list: Array
	},
	setup(props) {
		const is_mounted = ref(false)
		const edit_mode = ref(false)
		const temp_content = ref(props.note_template.content || "")
		const rendered_content = ref("")
		const rendered_preview = ref("")

		let content_editor = null
		let previewTimer = null


		onMounted(async () => {
			rendered_content.value = await renderMarkdownServer(props.note_template.content || "")
			rendered_preview.value = rendered_content.value
			is_mounted.value = true
		})

		watch(temp_content, async (val) => {
			if (previewTimer) {
				clearTimeout(previewTimer)
			}
			previewTimer = setTimeout(async () => {
				rendered_preview.value = await renderMarkdownServer(val || "")
			}, 200)
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

		async function init_editor() {
			if (content_editor) {
				content_editor.destroy()
				content_editor = null
			}
			await nextTick()
			const targetElement = document.getElementById('editor_' + props.note_template.id)
			if (targetElement) {
				content_editor = new EditorView({
					doc: props.note_template.content || "\n\n",
					extensions: [basicSetup, languages.markdown(), EditorView.updateListener.of((v) => {
						if (v.docChanged) {
							temp_content.value = content_editor.state.doc.toString()
						}
					})],
					parent: targetElement
				})
			}
		}

		async function save_content() {
			let content_text = content_editor.state.doc.toString()
			if (content_text.trim().length == 0) {
				content_text = content_text.trim()
			}

			const res = await fetch('/tools/note_template/' + props.note_template.id + '/edit_content', {
				headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
				method: "POST",
				body: JSON.stringify({
					"content": content_text
				})
			})

			if (await res.status == 200) {
				let loc = await res.json()
				props.note_template.content = content_text
				props.note_template.version = loc.version
				rendered_content.value = await renderMarkdownServer(content_text)
				rendered_preview.value = rendered_content.value
				edit_mode.value = false
			}
			display_toast(res)
		}

		function toggleCollapse(id) {
			const collapseEl = document.getElementById('collapse' + id);
			const collapse = bootstrap.Collapse.getOrCreateInstance(collapseEl);
			collapse.toggle();
		}

		return {
			temp_content,
			edit_mode,
			rendered_content,
			rendered_preview,
			delete_note_template,
			init_editor,
			save_content,
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

			<div class="d-flex w-100 justify-content-between mt-2">
				<span class="badge rounded-pill" style="color: black; background-color: aliceblue; font-weight: normal">
					<i>Version: [[note_template.version]]</i>
				</span>
				<span class="badge rounded-pill" style="color: black; background-color: aliceblue; font-weight: normal">
					<i>UUID: [[note_template.uuid]]</i>
				</span>
			</div>
        </a>
		
        <div>
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
	<div class="modal fade" :id="'delete_note_template_modal_'+note_template.id" tabindex="-1" aria-labelledby="delete_note_template_modal" aria-hidden="true">
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
			<!-- Content editing -->
			<div>
				<fieldset class="analyzer-select-case">
					<legend class="analyzer-select-case">
						<i class="fa-solid fa-file-lines fa-sm me-1"></i><span class="section-title">Content</span>
					<button v-if="!edit_mode" class="btn btn-primary btn-sm" @click="edit_mode = true; init_editor()" title="Edit content" style="float: right; margin-left: 10px;">
							<i class="fa-solid fa-pen"></i>
						</button>
					<button v-else class="btn btn-success btn-sm" @click="save_content()" title="Save content" style="float: right; margin-left: 10px;">
						<i class="fa-solid fa-check"></i>
					</button>
					<button v-if="edit_mode" class="btn btn-secondary btn-sm" @click="edit_mode = false" title="Cancel" style="float: right; margin-left: 10px;">
							<i class="fa-solid fa-times"></i>
						</button>
					</legend>
					
					<template v-if="edit_mode">
						<div style="display: flex;">
							<div class="note-editor" :id="'editor_'+note_template.id"></div>
							<div class="markdown-render" v-html="rendered_preview"></div>
						</div>
					</template>
					<template v-else>
						<div v-if="note_template.content" class="markdown-render-result" v-html="rendered_content"></div>
						<div v-else><i style="font-size: 12px;">No content</i></div>
					</template>
				</fieldset>
			</div>
		</div>
	</div>
	`
}
