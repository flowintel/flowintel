import {display_toast} from '../toaster.js'
const { ref, nextTick } = Vue
export default {
	delimiters: ['[[', ']]'],
	props: {
        templates_list: Object,
		template: Object,
        key_loop: Number,
        task_in_case: Boolean,
		case_id: Number
	},
	setup(props) {
		Vue.onMounted(async () => {
			if(props.template.notes.length){
				for(let i in props.template.notes){
					const targetElement = document.getElementById('editor_' +i +'_' + props.template.id)
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
				const targetElement = document.getElementById('editor_0_' + props.template.id)
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
			}

			const allCollapses = document.getElementById('collapse' + props.template.id)
			allCollapses.addEventListener('shown.bs.collapse', event => {
				md.mermaid.init()
			})
			is_mounted.value = true
		})
		Vue.onUpdated(async () => {
			// do not initialize mermaid before the page is mounted
			if(is_mounted)
				md.mermaid.init()
		})

		const is_mounted = ref(false)
        const edit_mode = ref(-1)

		const note_editor_render = ref([])
		let editor_list = []
		const md = window.markdownit()
		md.use(mermaidMarkdown.default)

		if(props.template.notes.length){
			for(let i in props.template.notes){
				note_editor_render.value[i] = props.template.notes[i].note		// If this template has notes
			}
		}else{
			note_editor_render.value[0] = ""
		}


		async function add_notes_task(){
			// Create a new empty note in the task
			const res = await fetch('/tools/template/create_note/' + props.template.id)

			if(await res.status == 200){
				let loc = await res.json()
				props.template.notes.push(loc["note"])
				let key = props.template.notes.length-1
				note_editor_render.value[key] = ""
				await nextTick()
				const targetElement = document.getElementById('editor_' + key + "_" + props.template.id)
				
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
			}
		}
		
		async function delete_note(template, note_id, key){
			// Delete a note of the task
			const res = await fetch('/tools/template/delete_note/' + template.id + '?note_id='+note_id)

			if( await res.status == 200){
				props.template.notes.splice(key, 1);
			}
			display_toast(res)
		}

        async function delete_task(template, template_array){
            const res = await fetch("/tools/template/delete_task/" + template.id)
            if( await res.status == 200){
				let index = template_array.indexOf(template)
				if(index > -1)
					template_array.splice(index, 1)
			}
            display_toast(res)
        }

        async function remove_task(template, template_array){
            const res = await fetch("/tools/template/" + props.case_id + "/remove_task/" + template.id)
            if(await res.status == 200){
                let index = template_array.indexOf(template)
                if(index > -1)
                    template_array.splice(index, 1)
            }
            display_toast(res)
        }
        

		async function edit_note(template, note_id, key){
            edit_mode.value = note_id

			const res = await fetch('/tools/template/get_note/' + template.id + "?note_id=" + note_id)
			let loc = await res.json()
			template.notes[key].note = loc["notes"]

			const targetElement = document.getElementById('editor1_'+key+"_" + props.template.id)
			let editor = new Editor.EditorView({
				doc: template.notes[key].note,
				extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
					if (v.docChanged) {
						note_editor_render.value[key] = editor.state.doc.toString()
					}
				})],
				parent: targetElement
			})
			editor_list[key] = editor
		}

		async function modif_note(template, note_id, key){
			let notes_loc = editor_list[key].state.doc.toString()
			if(notes_loc.trim().length == 0){
				notes_loc = notes_loc.trim()
			}
			const res_msg = await fetch(
				'/tools/template/modif_note/' + template.id + "?note_id=" + note_id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"notes": notes_loc})
				}
			)

			if(await res_msg.status == 200){
				let loc = await res_msg.json()
                edit_mode.value = -1
				template.last_modif = Date.now()
				if(note_id == -1){
					note_id = loc["note"]["id"]
					template.notes.push(loc["note"])
				}else{
					template.notes[key].note = notes_loc
				}
				await nextTick()
				
				if(!notes_loc){
					const targetElement = document.getElementById('editor_' + props.template.id)
					if(targetElement.innerHTML === ""){
						editor = new Editor.EditorView({
							doc: "\n\n",
							extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
								if (v.docChanged) {
									note_editor_render.value = editor.state.doc.toString()
								}
							})],
							parent: targetElement
						})
						editor_list[key] = editor
					}
				}
			}else{
				display_toast(res_msg)
			}
		}


		function formatNow(dt) {
			return dayjs.utc(dt).from(dayjs.utc())
		}

		function endOf(dt){
			return dayjs.utc(dt).endOf().from(dayjs.utc())
		}

		async function move_task_up(task, up_down){
			const res = await fetch('/tools/template/' + props.case_id + '/change_order/' + task.id + "?up_down=" + up_down)
			await display_toast(res)
			for( let i in props.templates_list){
				if(props.templates_list[i]["case_order_id"] == task.case_order_id-1){
					props.templates_list[i]["case_order_id"] = task.case_order_id
					task.case_order_id -= 1
					break
				}
			}
			props.templates_list.sort(order_task)
		}
		async function move_task_down(task, up_down){
			const res = await fetch('/tools/template/' + props.case_id + '/change_order/' + task.id + "?up_down=" + up_down)
			await display_toast(res)
			for( let i in props.templates_list){
				if(props.templates_list[i]["case_order_id"] == task.case_order_id+1){
					props.templates_list[i]["case_order_id"] = task.case_order_id
					task.case_order_id += 1
					break
				}
			}
			props.templates_list.sort(order_task)
		}

		function order_task(a, b){
			if(a.case_order_id > b.case_order_id){
				return 1
			}
			if(a.case_order_id < b.case_order_id){
				return -1
			}
			return 0
		}

		return {
			note_editor_render,
			md,
			getTextColor,
			mapIcon,
            edit_mode,
			delete_note,
			delete_task,
			edit_note,
			modif_note,
			formatNow,
			endOf,
			move_task_up,
			move_task_down,
			remove_task,
			add_notes_task
		}
	},
	template: `
	<div style="display: flex;"> 
        <a :href="'#collapse'+template.id" class="list-group-item list-group-item-action" data-bs-toggle="collapse" role="button" aria-expanded="false" :aria-controls="'collapse'+template.id">        
            <div class="d-flex w-100 justify-content-between">
                <h4 class="mb-1">[[ key_loop+1 ]]- [[ template.title ]]</h4>
            </div>
            <div class="d-flex w-100 justify-content-between">
                <p v-if="template.description" class="card-text">[[ template.description ]]</p>
                <p v-else class="card-text"><i style="font-size: 12px;">No description</i></p>
            </div>
            <div class="d-flex w-100 justify-content-between">
                <p v-if="template.url" class="card-text">[[ template.url ]]</p>
                <p v-else class="card-text"><i style="font-size: 12px;">No url</i></p>
            </div>
            <div v-for="instance in template.instances" :title="instance.description">
                <img :src="'/static/icons/'+instance.icon" style="max-width: 30px;">
                <i>[[instance.url]]</i>
            </div>
			<div class="d-flex w-100 justify-content-between" style="margin-top: 5px;">
				<div style="display: flex;" v-if="template.custom_tags">
					<template v-for="custom_tag in template.custom_tags">
						<div class="tag" :style="{'background-color': custom_tag.color, 'color': getTextColor(custom_tag.color)}">
							<i v-if="custom_tag.icon" :class="custom_tag.icon"></i>
							[[custom_tag.name]]
						</div>
					</template>
				</div>
			</div>
            <div class="d-flex w-100 justify-content-between">
                <div style="display: flex;" v-if="template.tags">
                    <template v-for="tag in template.tags">
                        <div class="tag" :title="tag.description" :style="{'background-color': tag.color, 'color': getTextColor(tag.color)}">
                            <i class="fa-solid fa-tag" style="margin-right: 3px; margin-left: 3px;"></i>
                            [[tag.name]]
                        </div>
                    </template>
                </div>
                <div v-else></div>
            </div>
            <div class="d-flex w-100 justify-content-between">
                <div v-if="template.clusters">
                    <template v-for="cluster in template.clusters">
                        <div :title="'Description:' + cluster.description + 'Metadata:' + JSON.stringify(JSON.parse(cluster.meta), null, 4)">
                            <span v-html="mapIcon(cluster.icon)"></span>
                            [[cluster.tag]]
                        </div>
                    </template>
                </div>
            </div>
        </a>
        <div v-if="!template.current_user_permission.read_only" style="display: grid;">
            <a class="btn btn-primary btn-sm" :href="'/tools/template/edit_task/'+template.id" type="button" title="Edit the task template">
                <i class="fa-solid fa-pen-to-square"></i>
            </a>
            <button v-if="task_in_case" class="btn btn-warning btn-sm" @click="remove_task(template, templates_list)" title="Remove the task template from the case"><i class="fa-solid fa-trash"></i></button>
            <button class="btn btn-danger btn-sm" @click="delete_task(template, templates_list)" title="Delete the task template"><i class="fa-solid fa-trash"></i></button>
        </div>
		<div v-if="!template.current_user_permission.read_only" style="display: grid;">
			<button class="btn btn-light btn-sm" title="Move the task up" @click="move_task_up(template, true)">
				<i class="fa-solid fa-chevron-up"></i>
			</button>
			<button class="btn btn-light btn-sm" title="Move the task down" @click="move_task_down(template, false)">
				<i class="fa-solid fa-chevron-down"></i>
			</button>
		</div>
	</div>

	
	<!-- Collapse Part -->
	<div class="collapse" :id="'collapse'+template.id">
		<div class="card card-body" style="background-color: whitesmoke;">
			<div class="d-flex w-100 justify-content-between">
				<div class="w-100">
					<div>
						<h5>Notes</h5>
					</div>
					<div v-if="template.notes.length">
						<template v-for="template_note, key in template.notes">
							<h5>#[[key+1]]</h5>
							<div v-if="template_note.note">
								<template v-if="edit_mode == template_note.id">
									<div>
										<button class="btn btn-primary" @click="modif_note(template, template_note.id, key)" type="button" :id="'note_'+template.id">
											<div hidden>[[template.title]]</div>
											Save
										</button>
									</div>
									<div style="display: flex;">
										<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor1_'+key+'_'+template.id"></div>
										<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[key])"></div>
									</div>
								</template>
								<template v-else>
									<template v-if="!template.current_user_permission.read_only || template.current_user_permission.admin">
										<button class="btn btn-primary btn-sm" @click="edit_note(template, template_note.id, key)" type="button" :id="'note_'+template.id">
											<div hidden>[[template.title]]</div>
											<small><i class="fa-solid fa-pen"></i></small> Edit
										</button>
										<button class="btn btn-danger btn-sm" @click="delete_note(template, template_note.id, key)" style="margin-bottom: 1px;">
											<small><i class="fa-solid fa-trash"></i></small> Delete
										</button>
									</template>
									<p style="background-color: white; border: 1px #515151 solid; padding: 5px;" v-html="md.render(template_note.note)"></p>
								</template>
							</div>
							<div v-else>
								<template v-if="!template.current_user_permission.read_only || template.current_user_permission.admin">
									<div>
										<button class="btn btn-primary btn-sm" @click="modif_note(template, template_note.id, key)" type="button" :id="'note_'+template.id">
											<div hidden>[[template.title]]</div>
											Create
										</button>
										<button class="btn btn-danger btn-sm" @click="delete_note(template, template_note.id, key)" style="margin-bottom: 1px;">
											<small><i class="fa-solid fa-trash"></i></small> Delete
										</button>
									</div>
									<div style="display: flex;">
										<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_'+key+'_'+template.id"></div>
										<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[key])"></div>
									</div>
								</template>
							</div>
							<button class="btn btn-primary btn-sm" @click="add_notes_task()">Add notes</button>
						</template>
					</div>
					<div v-else>
						<template v-if="!template.current_user_permission.read_only || template.current_user_permission.admin">
							<div>
								<button class="btn btn-primary btn-sm" @click="modif_note(template, -1, 0)" type="button" :id="'note_'+template.id" style="margin-bottom: 3px;">
									<div hidden>[[template.title]]</div>
									Create
								</button>
							</div>
							<div style="display: flex;">
								<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_0_'+template.id"></div>
								<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render[0])"></div>
							</div>
						</template>
					</div>
				</div>
			</div>
		</div>
	</div>
	`
}