import {display_toast} from '../toaster.js'
const { ref, onMounted, nextTick } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		cases_info: Object
	},
	setup(props) {
		const note_template_list = ref([])
        const selected_note_template = ref({})
        const case_note_template = ref({})
		const is_exporting = ref(false)
        const mustache_render = ref("")

        const rendering_tab = ref("mixed")
        const main_tab = ref("template")

        let editor
        const note_editor_render = ref("")
		const md = window.markdownit()			// Library to Parse and display markdown
		md.use(mermaidMarkdown.default)			// Use mermaid library

		async function fetch_note_template(){
            const res = await fetch('/tools/note_template')
            let loc = await res.json()
            note_template_list.value = loc
            await nextTick()
            $('.select2-select').select2({
                theme: 'bootstrap-5'
            })

            $('#note_template_select').on('select2:select', function (e) {
                let loc_id = $(this).select2('data').map(item => item.id)

                for(let i in note_template_list.value){
                    if(note_template_list.value[i].id == loc_id){
                        selected_note_template.value = note_template_list.value[i]
                        mustache_render.value = selected_note_template.value.content
                        break
                    }
                }
            })
        }

        async function fetch_case_note_template() {
            const res = await fetch('/case/'+props.cases_info.case.id+'/get_note_template')
            if(await res.status == 200){
                let loc = await res.json()
                
                case_note_template.value = loc["case_note_template"]
                selected_note_template.value = loc["current_template"]
                await nextTick()
                for(let i in selected_note_template.value.params.list){
                    $("#"+selected_note_template.value.params.list[i]).val(case_note_template.value.values.list[selected_note_template.value.params.list[i]])
                }
                
                reload(case_note_template.value.content)
            }else{
                fetch_note_template()
            }
        }

        function active_rendering_tab(tab_name) {
            if(tab_name == 'mixed'){
                rendering_tab.value = "mixed"
                if ( !document.getElementById("tab-rendering-mixed").classList.contains("active") ){
                    document.getElementById("tab-rendering-mixed").classList.add("active")
                    document.getElementById("tab-rendering-template").classList.remove("active")
                    document.getElementById("tab-rendering-final").classList.remove("active")

                    if(!Object.keys(case_note_template.value).length)
                        reload(selected_note_template.value.content)
                    else
                        reload(case_note_template.value.content)
                }
            }else if(tab_name == 'template'){
                rendering_tab.value = "template"
                if ( !document.getElementById("tab-rendering-template").classList.contains("active") ){
                    document.getElementById("tab-rendering-template").classList.add("active")
                    document.getElementById("tab-rendering-mixed").classList.remove("active")
                    document.getElementById("tab-rendering-final").classList.remove("active")
                }
            }else if(tab_name == 'final'){
                rendering_tab.value = "final"
                if ( !document.getElementById("tab-rendering-final").classList.contains("active") ){
                    document.getElementById("tab-rendering-final").classList.add("active")
                    document.getElementById("tab-rendering-template").classList.remove("active")
                    document.getElementById("tab-rendering-mixed").classList.remove("active")

                    if(!Object.keys(case_note_template.value).length)
                        reload(selected_note_template.value.content, true)
                    else
                        reload(case_note_template.value.content, true)
                }
            }
        }

        async function active_tab(tab_name){
            if(tab_name == 'content'){
                main_tab.value = "content"
                if ( !document.getElementById("tab-content").classList.contains("active") ){
                    document.getElementById("tab-content").classList.add("active")
                    document.getElementById("tab-template").classList.remove("active")
                    await nextTick()

                    note_editor_render.value = case_note_template.value.content

                    const targetElement = document.getElementById('editor')
                    if(targetElement && targetElement.innerHTML === ""){
                        editor = new Editor.EditorView({
                            doc: case_note_template.value.content,
                            extensions: [Editor.basicSetup, Editor.markdown(),Editor.EditorView.updateListener.of((v) => {
                                if (v.docChanged) {
                                    note_editor_render.value = editor.state.doc.toString()
                                }
                            })],
                            parent: targetElement
                        })
                    }
                    md.mermaid.init()
                }
            }else if(tab_name == 'template'){
                main_tab.value = "template"
                if ( !document.getElementById("tab-template").classList.contains("active") ){
                    document.getElementById("tab-template").classList.add("active")
                    document.getElementById("tab-content").classList.remove("active")

                    await nextTick()
                    for(let i in selected_note_template.value.params.list){
                        $("#"+selected_note_template.value.params.list[i]).val(case_note_template.value.values.list[selected_note_template.value.params.list[i]])
                    }
                    
                    reload(case_note_template.value.content)
                }
            }
        }
        

        function reload(current_note_template_content, no_keep=false){            
            let loc = {}
            for(let i in selected_note_template.value.params.list){
                loc[selected_note_template.value.params.list[i]] = $("#"+selected_note_template.value.params.list[i]).val()

                if(Object.keys(case_note_template.value).length)
                    case_note_template.value.values.list[i] = $("#"+selected_note_template.value.params.list[i]).val()
            }

            if(!no_keep && rendering_tab.value != 'final'){
                const matches = [...current_note_template_content.matchAll(/{{\s*(\w+)\s*}}/g)];
                matches.forEach(m => {
                    const varName = m[1];
                    if(!loc[varName]){
                        loc[varName] = `{{${varName}}}`;
                    }
                });
            }

            let compiled = Handlebars.compile(current_note_template_content)
            mustache_render.value = compiled(loc)
        }  
        
        async function create(){
            let loc = {}
            for(let i in selected_note_template.value.params.list){
                loc[selected_note_template.value.params.list[i]] = $("#"+selected_note_template.value.params.list[i]).val()
            }
            const res_msg = await fetch(
                '/case/' + props.cases_info.case.id + '/create_note_template_case',{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({
                        "values": loc, 
                        "template_id": selected_note_template.value.id
                    })
                }
            )
            if(await res_msg.status == 200){
                fetch_case_note_template()
            }
            display_toast(res_msg)
        }

        async function save() {
            let loc = {}
            for(let i in selected_note_template.value.params.list){
                loc[selected_note_template.value.params.list[i]] = $("#"+selected_note_template.value.params.list[i]).val()
                case_note_template.value.values.list[i] = $("#"+selected_note_template.value.params.list[i]).val()
            }
            const res_msg = await fetch(
                '/case/' + props.cases_info.case.id + '/modif_note_template_case',{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({"values": {"list": loc}})
                }
            )
            display_toast(res_msg)
        }

        async function save_content() {
            const res = await fetch(
                '/case/' + props.cases_info.case.id + '/modif_note_template_content',{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({"content": note_editor_render.value})
                }
            )
            if(await res.status == 200){
                case_note_template.value.content = note_editor_render.value
            }
            
            display_toast(res)
        }

        async function export_notes(type){
            is_exporting.value = true
            let filename = ""
            let loc = {}
            for(let i in selected_note_template.value.params.list){
                loc[selected_note_template.value.params.list[i]] = $("#"+selected_note_template.value.params.list[i]).val()
            }
            let compiled = Handlebars.compile(case_note_template.value.content)

            await fetch(
                '/case/'+props.cases_info.case.id+'/export_notes_template?type=' + type,{
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({"content": compiled(loc)})
                }
            ).then(res =>{
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

        async function remove_note_template() {
            const res = await fetch("/case/"+props.cases_info.case.id+"/remove_note_template")
            if(res.status == 200){
                case_note_template.value = {}
                selected_note_template.value = {}
                fetch_note_template()
                var myModalEl = document.getElementById("remove_note_template_modal");
                var modal = bootstrap.Modal.getInstance(myModalEl)
                modal.hide();
            }
            display_toast(res)
        }

        onMounted(() => {
            fetch_case_note_template()
            md.mermaid.init()

        })

		return {
			md,
			is_exporting,
			note_template_list,
			selected_note_template,
            mustache_render,
            case_note_template,
            rendering_tab,
            main_tab,
            note_editor_render,

            active_tab,
            active_rendering_tab,
            reload,
            create,
            save,
            save_content,
            export_notes,
            remove_note_template,
		}
    },
	template: `
    <div>
        <template v-if="!Object.keys(case_note_template).length && Object.keys(note_template_list).length">
            <select data-placeholder="Note Template" class="select2-select form-control" multiple name="note_template_select" id="note_template_select" >
                <template v-for="note in note_template_list">
                    <option :value="[[note.id]]">[[note.title]]</option>
                </template>
            </select>
        </template>
        
        <hr style="margin-top: 50px;" class="fading-line">

        <template v-if="Object.keys(case_note_template).length">
            <div class="btn-group">
                <button class="btn btn-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false" style="margin-bottom: 1px;">
                    <small><i class="fa-solid fa-download"></i></small> Export
                </button>
                <ul class="dropdown-menu">
                    <li>
                        <button v-if="!is_exporting" class="btn btn-link" @click="export_notes('pdf')" title="Export markdown as pdf">PDF</button>
                        <button v-else class="btn btn-link" disabled>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span role="status">Loading...</span>
                        </button>
                    </li>
                    <li>
                        <button v-if="!is_exporting" class="btn btn-link" @click="export_notes('docx')" title="Export markdown as docx">DOCX</button>
                        <button v-else class="btn btn-link" disabled>
                            <span class="spinner-border spinner-border-sm" aria-hidden="true"></span>
                            <span role="status">Loading...</span>
                        </button>
                    </li>
                </ul>
            </div>
            <button class="btn btn-danger btn-sm" data-bs-toggle="modal" data-bs-target="#remove_note_template_modal">
                <i class="fa-solid fa-minus"></i> Remove
            </button>

            <div class="modal fade" id="remove_note_template_modal" tabindex="-1" aria-labelledby="remove_note_template_modal" aria-hidden="true">
                <div class="modal-dialog modal-sm">
                    <div class="modal-content">
                        <div class="modal-header">
                            <h1 class="modal-title fs-5" id="remove_note_template_modal">Remove note template ?</h1>
                            <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                            <button class="btn btn-danger" @click="remove_note_template()"><i class="fa-solid fa-minus"></i> Confirm</button>
                        </div>
                    </div>
                </div>
            </div>
        </template>

        <template v-if="Object.keys(selected_note_template).length">

            <ul class="nav nav-tabs" style="margin-bottom: 10px;">
                <li class="nav-item">
                    <button class="nav-link active" id="tab-template" @click="active_tab('template')">Template</button>
                </li>
                <li class="nav-item">
                    <button v-if="Object.keys(case_note_template).length" class="nav-link" id="tab-content" aria-current="page" @click="active_tab('content')">
                        Content
                    </button>
                    <button v-else class="nav-link disabled" id="tab-content" aria-current="page">Content</button>
                </li>
            </ul>
        </template>

        <template v-if="main_tab == 'template'">
            <template v-if="Object.keys(selected_note_template).length">
                <button v-if="!Object.keys(case_note_template).length" class="btn btn-primary mt-2 mb-2" @click="reload(selected_note_template.content)">
                    reload
                </button>
                <button v-else class="btn btn-primary mt-2 mb-2" @click="reload(case_note_template.content)">reload</button>

                <div class="row">
                    <div class="col-6">
                        <div v-for="elem in selected_note_template.params.list">
                            <label class="form-label" :for="elem">[[elem]]</label>
                            <input class="form-control" type="text" :name="elem" :id="elem"/>
                        </div>
                    </div>

                    <div class="col-6">
                        <ul class="nav nav-tabs" style="margin-bottom: 10px;">
                            <li class="nav-item">
                                <button class="nav-link active" id="tab-rendering-mixed" aria-current="page" @click="active_rendering_tab('mixed')">Mixed</button>
                            </li>
                            <li class="nav-item">
                                <button class="nav-link" id="tab-rendering-template" @click="active_rendering_tab('template')">Template</button>
                            </li>
                            <li class="nav-item">
                                <button class="nav-link" id="tab-rendering-final" @click="active_rendering_tab('final')">Final result</button>
                            </li>
                        </ul>

                        <template v-if="rendering_tab == 'mixed'">
                            <div style="background-color: white; border: 1px rgb(176, 171, 171) solid; padding: 5px; border-radius: 5px; margin-top: 3px; width:99%">
                                <span v-html="md.render(mustache_render)"></span>
                            </div>
                        </template>
                        <template v-else-if="rendering_tab == 'template'">
                            <div style="background-color: white; border: 1px rgb(176, 171, 171) solid; padding: 5px; border-radius: 5px; margin-top: 3px; width:99%">
                                <span v-if="Object.keys(case_note_template).length" v-html="md.render(case_note_template.content)"></span>
                                <span v-else v-html="md.render(selected_note_template.content)"></span>
                            </div>
                        </template>
                        <template v-else-if="rendering_tab == 'final'">
                            <div style="background-color: white; border: 1px rgb(176, 171, 171) solid; padding: 5px; border-radius: 5px; margin-top: 3px; width:99%">
                                <span v-html="md.render(mustache_render)"></span>
                            </div>
                        </template>
                    </div>
                </div>

                <button v-if="!Object.keys(case_note_template).length" class="btn btn-primary mt-5" @click="create()">Create</button>
                <button v-else class="btn btn-primary mt-5" @click="save()">Save</button>
            </template>
        </template>


        <template v-else-if="main_tab == 'content'">
            <i>New handlebarsjs varaibles will not be usable</i>
            <br>
            <button class="btn btn-primary" @click="save_content()">Save</button>
            <div style="display: flex;">
                <div style="background-color: white; border: 1px rgb(159, 159, 159) solid; width: 50%" id="editor"></div>
                <div style="background-color: white; border: 1px rgb(159, 159, 159) solid; padding: 5px; width: 50%" v-html="md.render(note_editor_render)"></div>
            </div>
            <button class="btn btn-primary" @click="save_content()">Save</button>
        </template>

    </div>
    `
}