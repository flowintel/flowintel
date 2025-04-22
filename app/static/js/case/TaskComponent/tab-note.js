import {display_toast} from '/static/js/toaster.js'
const { ref, nextTick, onMounted, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object,
		task: Object,
        md: Object
	},
	setup(props) {
        const is_exporting = ref(false)		 	// Boolean to display a spinner when exporting
        const note_editor_render = ref([])		// Notes display in mermaid
		let editor_list = []								// Variable for the editor
		const edit_mode = ref(-1)			// Boolean use when the note is in edit mode

        if(props.task.notes.length){
			for(let i in props.task.notes){
				note_editor_render.value[i] = props.task.notes[i].note		// If this task has notes
			}
		}else{
			note_editor_render.value[0] = ""
		}


        async function add_notes_task(){
			// Create a new empty note in the task
			const res = await fetch('/case/' + props.task.case_id + '/create_note/'+props.task.id)

			if(await res.status == 200){
				let loc = await res.json()
				props.task.notes.push(loc["note"])
				let key = props.task.notes.length-1
				note_editor_render.value[key] = ""
				await nextTick()
				const targetElement = document.getElementById('editor_' + key + "_" + props.task.id)
				
				if(targetElement.innerHTML === ""){
					let editor = new Editor.EditorView({
						doc: "\n\n",
						extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
							if (v.docChanged) {
								note_editor_render.value[key] = editor.state.doc.toString()
							}
						})],
						parent: targetElement
					})
					editor_list.push(editor)
				}
				props.md.mermaid.run()
			}
		}

        async function delete_note(task, note_id, key){
			// Delete a note of the task
			const res = await fetch('/case/' + task.case_id + '/delete_note/' + task.id + '?note_id='+note_id)

			if( await res.status == 200){
				props.task.notes.splice(key, 1);
			}
			display_toast(res)
		}

        async function edit_note(task, note_id, key){
			// Edit the note of the task
			edit_mode.value = note_id

			const res = await fetch('/case/' + task.case_id + '/get_note/' + task.id + '?note_id=' + note_id)
			let loc = await res.json()
			task.notes[key].note = loc["note"]

			// Initialize the editor
			const targetElement = document.getElementById('editor1_'+ key + "_" + props.task.id)
			let editor = new Editor.EditorView({
				doc: task.notes[key].note,
				extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
					if (v.docChanged) {
						note_editor_render.value[key] = editor.state.doc.toString()
					}
				})],
				parent: targetElement
			})
			editor_list[key] = editor
			props.md.mermaid.run()
		}

		async function export_notes(task, type, note_id){
			// Export notes in different format and download it
			is_exporting.value = true
			let filename = ""
			await fetch('/case/'+task.case_id+'/task/'+task.id+'/export_notes?type=' + type+"&note_id="+note_id)
			.then(res =>{
				filename = res.headers.get("content-disposition").split("=")
				filename = filename[filename.length - 1]
				return res.blob() 
			})
			.then(data =>{
				var a = document.createElement("a")
				a.href = window.URL.createObjectURL(data);
				a.download = filename;
				a.click();
			})
			is_exporting.value = false
		}

        async function modif_note(task, note_id, key){
			// Modify notes of the task
			let notes_loc = editor_list[key].state.doc.toString()
			if(notes_loc.trim().length == 0){
				notes_loc = notes_loc.trim()
			}
			const res_msg = await fetch(
				'/case/' + task.case_id + '/modif_note/' + task.id + '?note_id=' + note_id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"notes": notes_loc})
				}
			)

			if(await res_msg.status == 200){
				let loc = await res_msg.json()
				edit_mode.value = -1
				task.last_modif = Date.now()
				if(note_id == -1){
					note_id = loc["note"]["id"]
					task.notes.push(loc["note"])
				}else{
					task.notes[key].note = notes_loc
				}

				await nextTick()
				
				if(!notes_loc){
					const targetElement = document.getElementById('editor_' +key + "_" + props.task.id)
					if(targetElement.innerHTML === ""){
						let editor = new Editor.EditorView({
							doc: "\n\n",
							extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
								if (v.docChanged) {
									note_editor_render.value[key] = editor.state.doc.toString()
								}
							})],
							parent: targetElement
						})
						editor_list[key] = editor
					}
				}
				props.md.mermaid.run()
			}else{
				display_toast(res_msg)
			}
		}

        onMounted( () => {
			if(props.task.notes.length){
				for(let i in props.task.notes){
					const targetElement = document.getElementById('editor_' +i +'_' + props.task.id)
					let editor=new Editor.EditorView({
						doc: "\n\n",
						extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
							if (v.docChanged) {
								note_editor_render.value[i] = editor.state.doc.toString()
							}
						})],
						parent: targetElement
					})
					editor_list[i] = editor
				}
			}else{
				const targetElement = document.getElementById('editor_0_' + props.task.id)
				let editor=new Editor.EditorView({
					doc: "\n\n",
					extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
						if (v.docChanged) {
							note_editor_render.value[0] = editor.state.doc.toString()
						}
					})],
					parent: targetElement
				})
				editor_list[0] = editor
				// md.mermaid.run()
			}

		})

        watch(note_editor_render, async (newAllContent, oldAllContent) => {
            await nextTick()
            props.md.mermaid.run()
        }, {deep: true})

		return {
            // md,
            note_editor_render,
			is_exporting,
			edit_mode,

            add_notes_task,
            delete_note,
            edit_note,
            export_notes,
            modif_note,
		}
    },
	template: `
	<div>
        <fieldset class="analyzer-select-case">
            <legend class="analyzer-select-case">
                <i class="fa-solid fa-note-sticky"></i> 
                Notes 
				<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                	<button class="btn btn-outline-primary btn-sm me-1" title="Add notes" @click="add_notes_task()" style="margin-bottom: 1px; border-radius: 10px">
						<i class="fa-solid fa-plus fa-fw"></i>
					</button>
				</template>
                <a class="btn btn-outline-primary btn-sm" :href="'/analyzer/misp-modules?case_id='+task.case_id+'&task_id='+task.id" 
					style="margin-bottom: 1px;border-radius: 10px" title="Analyze notes">
                    <i class="fa-solid fa-magnifying-glass fa-fw"></i>
                </a>
            </legend>
            <!-- Task contains notes -->
            <div v-if="task.notes.length">
                <template v-for="task_note, key in task.notes">
                    <h5>#[[key+1]]</h5>
                    <!-- Note is not empty -->
                    <template v-if="task_note.note">
                        <!-- Edit existing note -->
                        <template v-if="edit_mode == task_note.id">
                            <div>
                                <button class="btn btn-primary" @click="modif_note(task, task_note.id, key)" type="button" :id="'note_'+task.id">
                                    <div hidden>[[task.title]]</div>
                                    Save
                                </button>
                            </div>
                            <div style="display: flex;">
                                <div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor1_'+key+'_'+task.id"></div>
                                <div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[key])"></div>
                            </div>
                        </template>
                        <!-- Render an existing note -->
                        <template v-else>
                            <template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                                <button class="btn btn-primary btn-sm" @click="edit_note(task, task_note.id, key)" :id="'note_'+task.id" style="margin-bottom: 3px;">
                                    <div hidden>[[task.title]]</div>
                                    <small><i class="fa-solid fa-pen"></i></small> Edit
                                </button>
                                <div class="btn-group">
                                    <button class="btn btn-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false" style="margin-bottom: 3px;margin-left:3px">
                                        <small><i class="fa-solid fa-download"></i></small> Export
                                    </button>
                                    <ul class="dropdown-menu">
                                        <li>
                                            <button v-if="!is_exporting" class="btn btn-link" @click="export_notes(task, 'pdf', task_note.id)" title="Export markdown as pdf">PDF</button>
                                            <button v-else class="btn btn-link" disabled>
                                                <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                                <span role="status">Loading...</span>
                                            </button>
                                        </li>
                                        <li>
                                            <button v-if="!is_exporting" class="btn btn-link" @click="export_notes(task, 'docx', task_note.id)" title="Export markdown as docx">DOCX</button>
                                            <button v-else class="btn btn-link" disabled>
                                                <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                                                <span role="status">Loading...</span>
                                            </button>
                                        </li>
                                    </ul>
                                </div>
                                <button class="btn btn-danger btn-sm" @click="delete_note(task, task_note.id, key)" style="margin-bottom: 3px;margin-left:3px">
                                    <small><i class="fa-solid fa-trash"></i></small> Delete
                                </button>

                            </template> 
                            <p style="background-color: white; border: 1px #515151 solid; padding: 5px;" v-html="md.render(task_note.note)"></p>
                        </template>
                    </template>
                    <!-- Note is empty -->
                    <template v-else>
                        <template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                            <div>
                                <button class="btn btn-primary btn-sm" @click="modif_note(task, task_note.id, key)" type="button" :id="'note_'+task.id" style="margin-bottom: 3px;">
                                    <div hidden>[[task.title]]</div>
									<small><i class="fa-solid fa-plus fa-fw"></i></small>
                                    Create
                                </button>
                                <button class="btn btn-danger btn-sm" @click="delete_note(task, task_note.id, key)" style="margin-bottom: 3px; margin-left:3px">
                                    <small><i class="fa-solid fa-trash fa-fw"></i></small> Delete
                                </button>
                            </div>
                            <div style="display: flex;">
                                <div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_'+key+'_'+task.id"></div>
                                <div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[key])"></div>
                            </div>
                        </template>
                    </template>
                </template>
				
            </div>
            <!-- Task doesn't contains notes -->
            <div v-else>
                <template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                    <div>
                        <button class="btn btn-primary btn-sm" @click="modif_note(task, -1, 0)" type="button" :id="'note_'+task.id" style="margin-bottom: 3px;">
                            <div hidden>[[task.title]]</div>
                            Create
                        </button>
                    </div>
                    <div style="display: flex;">
                        <div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_0_'+task.id"></div>
                        <div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[0])"></div>
                    </div>
                </template>
            </div>
        </fieldset>
    </div>
    `
}