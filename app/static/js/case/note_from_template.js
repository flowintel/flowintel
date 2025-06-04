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
		const is_loading = ref(false)
        const mustache_render = ref("")

		const md = window.markdownit()			// Library to Parse and display markdown
		md.use(mermaidMarkdown.default)			// Use mermaid library

		async function fetch_note_template(){
            const res = await fetch('/tools/note_template')
            let loc = await res.json()
            note_template_list.value = loc
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
        

        function reload(current_note_template_content){            
            let loc = {}
            for(let i in selected_note_template.value.params.list){
                loc[selected_note_template.value.params.list[i]] = $("#"+selected_note_template.value.params.list[i]).val()
                case_note_template.value.values.list[i] = $("#"+selected_note_template.value.params.list[i]).val()
            }

            const matches = [...current_note_template_content.matchAll(/{{\s*(\w+)\s*}}/g)];
            matches.forEach(m => {
                const varName = m[1];
                if(!loc[varName]){
                    loc[varName] = `{{${varName}}}`;
                }
            });

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
                        "template_id": selected_note_template.value.id, 
                        "content": selected_note_template.value.content
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

        onMounted(() => {
            fetch_case_note_template()
            md.mermaid.init()

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

        })

		return {
			md,
			is_loading,
			note_template_list,
			selected_note_template,
            mustache_render,
            case_note_template,

            reload,
            create,
            save,
		}
    },
	template: `
    <div v-if="!Object.keys(case_note_template).length">
        <select data-placeholder="Note Template" class="select2-select form-control" multiple name="note_template_select" id="note_template_select" >
            <template v-for="note in note_template_list">
                <option :value="[[note.id]]">[[note.title]]</option>
            </template>
        </select>

        <template v-if="Object.keys(selected_note_template).length">
            <hr style="margin-top: 50px;" class="fading-line">
            <h2>[[selected_note_template.title]]</h2>
            
            <button class="btn btn-primary mt-2 mb-2" @click="reload(selected_note_template.content)">reload</button>
            <div class="row" v-if="Object.keys(selected_note_template).length">
                <div class="col-6">
                    <div v-for="elem in selected_note_template.params.list">
                        <label class="form-label" :for="elem">[[elem]]</label>
                        <input class="form-control" type="text" :name="elem" :id="elem"/>
                    </div>
                </div>

                <div class="col-6" style="background-color: white;">
                    <span v-html="md.render(mustache_render)"></span>
                </div>
            </div>

            <button class="btn btn-primary mt-5" @click="create()">Create</button>
        </template>
    </div>

    <div v-else>
        <button class="btn btn-primary mt-2 mb-2" @click="reload(case_note_template.content)">reload</button>
        <div class="row">
            <div class="col-6">
                <div v-for="elem, key in selected_note_template.params.list">
                    <label class="form-label" :for="elem">[[elem]]</label>
                    <input class="form-control" type="text" :name="elem" :id="elem"/>
                </div>
            </div>

            <div class="col-6" style="background-color: white;">
                <span v-html="md.render(mustache_render)"></span>
            </div>
        </div>

        <button class="btn btn-primary mt-5" @click="save()">Save</button>
    </div>
    `
}