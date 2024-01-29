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
			
			const targetElement = document.getElementById('editor_' + props.template.id)
			editor = new Editor.EditorView({
				doc: "\n\n",
				extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
					if (v.docChanged) {
						note_editor_render.value = editor.state.doc.toString()
					}
				})],
				parent: targetElement
			})

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
        const edit_mode = ref(false)

		const notes = ref(props.template.notes)
		const note_editor_render = ref("")
		let editor
		const md = window.markdownit()
		md.use(mermaidMarkdown.default)

		if(props.template.notes)
			note_editor_render.value = props.template.notes
		

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
        

		async function edit_note(template){
            edit_mode.value = true

			const res = await fetch('/tools/template/get_note/' + template.id)
			let loc = await res.json()
			template.notes = loc["notes"]

			const targetElement = document.getElementById('editor1_' + props.template.id)
			editor = new Editor.EditorView({
				doc: template.notes,
				extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
					if (v.docChanged) {
						note_editor_render.value = editor.state.doc.toString()
					}
				})],
				parent: targetElement
			})
			
		}

		async function modif_note(template){
			let notes_loc = editor.state.doc.toString()
			if(notes_loc.trim().length == 0){
				notes_loc = notes_loc.trim()
			}
			const res_msg = await fetch(
				'/tools/template/modif_note/' + template.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
					method: "POST",
					body: JSON.stringify({"notes": notes_loc})
				}
			)

			if(await res_msg.status == 200){
                edit_mode.value = false
				template.last_modif = Date.now()
				template.notes = notes_loc
				notes.value = notes_loc
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
					}
				}
			}
			await display_toast(res_msg)
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
			notes,
			note_editor_render,
			md,
			getTextColor,
			mapIcon,
            edit_mode,
			delete_task,
			edit_note,
			modif_note,
			formatNow,
			endOf,
			move_task_up,
			move_task_down,
			remove_task
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
					<div v-if="template.notes">
						<template v-if="edit_mode">
							<div>
								<button class="btn btn-primary" @click="modif_note(template)" type="button" :id="'note_'+template.id">
									<div hidden>[[template.title]]</div>
									Save
								</button>
							</div>
							<div style="display: flex;">
								<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor1_'+template.id"></div>
								<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render)"></div>
							</div>
						</template>
						<template v-else>
							<template v-if="!template.current_user_permission.read_only || template.current_user_permission.admin">
								<button class="btn btn-primary" @click="edit_note(template)" type="button" :id="'note_'+template.id">
									<div hidden>[[template.title]]</div>
									Edit
								</button>
							</template> 
							<p style="background-color: white; border: 1px #515151 solid; padding: 5px;" v-html="md.render(notes)"></p>
						</template>
					</div>
					<div v-else>
						<template v-if="!template.current_user_permission.read_only || template.current_user_permission.admin">
							<div>
								<button class="btn btn-primary" @click="modif_note(template)" type="button" :id="'note_'+template.id">
									<div hidden>[[template.title]]</div>
									Create
								</button>
							</div>
							<div style="display: flex;">
								<div style="background-color: white; border-width: 1px; border-style: solid; width: 50%" :id="'editor_'+template.id"></div>
								<div style="background-color: white; border: 1px #515151 solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render)"></div>
							</div>
						</template>
					</div>
				</div>
			</div>
		</div>
	</div>
	`
}