import {display_toast, create_message} from '../toaster.js'
import AddObjectAttributes from './AddObjectAttributes.js'
const { ref, onMounted, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		case_id: Number
	},
    emits: ['modif_misp_objects'],
    components: {
        AddObjectAttributes,
    },
	setup(props, {emit}) {
        const case_misp_objects = ref([])
        const misp_objects = ref([])
        const activeTemplate = ref({requiredOneOf: [],})
        const activeTemplateAttr = ref({requiredOneOf: [],})
        const selectedQuickTemplate = ref('');
        const list_attr = ref([])
        const editingAttrId = ref(null)
        const editState = ref({})
        const addingAttrToObject = ref(null)
        const newAttrState = ref({})
        const compactView = ref(false)

        const defaultObjectTemplates = {
            'domain/ip': '43b3b146-77eb-4931-b4cc-b66c60f28734',
            'url/domain': '60efb77b-40b5-4c46-871b-ed1ed999fce5',
            'file/hash': '688c46fb-5edb-40a3-8273-1af7923e2215',
            'vulnerability': '81650945-f186-437b-8945-9f31715d32da',
            'financial': 'c51ed099-a628-46ee-ad8f-ffed866b6b8d',
            'personal': 'a15b0477-e9d1-4b9c-9546-abe78a4f4248'
        };
		
        async function fetch_case_misp_object(){
            const res = await fetch("/case/"+props.case_id+"/get_case_misp_object")
            // const res = await fetch("/case/"+ window.location.pathname.split("/").slice(-1) +"/get_case_misp_object")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                case_misp_objects.value = loc["misp-object"]
            }
        }
        async function fetch_misp_object(){
            const res = await fetch("/case/get_misp_object")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                misp_objects.value = loc["misp-object"]
            }
        }

        async function save_changes(object_id=null, key=null) {
            if(list_attr.value.length){
                let url = ""
                if (object_id){
                    url = "/case/"+props.case_id+"/add_attributes/"+object_id
                }else{
                    url = "/case/"+props.case_id+"/create_misp_object"
                }
                const res = await fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        "object-template": activeTemplate.value,
                        "attributes": list_attr.value
                    })
                });
                if(await res.status==200){
                    list_attr.value = []
                    activeTemplate.value = {}
                    await fetch_case_misp_object()
                    if(key){
                        $("#modal-add-attribute-"+key).modal("hide")

                        var myModal = new bootstrap.Modal(document.getElementById("modal-add-attribute-"+key), {});
                        myModal.hide();
                    }
                    emit("modif_misp_objects", true)
                }
                display_toast(res)
            }else{
                create_message("Need to add an attribute", "warning-subtle")
            }
        }

        function add_attribute_list(object){
            list_attr.value.push(object)            
        }
        function delete_attribute_list(object){
            list_attr.value.splice(object, 1)
        }

        function toggleCompactView() {
            compactView.value = !compactView.value
        }

        function copyUuidToClipboard() {
            navigator.clipboard.writeText(activeTemplate.value.uuid);
        }

        async function delete_object(object_id){
            const res = await fetch("/case/"+props.case_id+"/delete_object/"+object_id)
            if(await res.status==200 ){
                let loc
                for(let i in case_misp_objects.value){
                    if(case_misp_objects.value[i].object_id == object_id){
                        loc = i
                        break
                    }
                }
                case_misp_objects.value.splice(loc, 1)

                emit("modif_misp_objects", true)
            }
            display_toast(res)
        }

        async function open_modal_add_attribute(template_uuid, modal_id, key){
            activeTemplateAttr.value = misp_objects.value.find((objectTemplate) => objectTemplate.uuid === template_uuid);
            var myModal = new bootstrap.Modal(document.getElementById(modal_id + key), {});
            myModal.show();
            
        }

        async function delete_attribute(attribute_id, misp_object_id) {
            // Find the MISP object and attribute
            let misp_object = null
            let attribute_to_delete = null
            let loc = null

            for(let i in case_misp_objects.value){
                if(misp_object_id == case_misp_objects.value[i].object_id){
                    misp_object = case_misp_objects.value[i]
                    for(let j in case_misp_objects.value[i].attributes){
                        if(attribute_id == case_misp_objects.value[i].attributes[j].id){
                            attribute_to_delete = case_misp_objects.value[i].attributes[j]
                            loc = [i,j]
                            break
                        }
                    }
                    break
                }
            }

            if (!misp_object || !attribute_to_delete) {
                display_toast({status: 400, json: async () => ({message: "Attribute not found", toast_class: "danger-subtle"})})
                return
            }

            const template = misp_objects.value.find((t) => t.uuid === misp_object.object_uuid)
            
            if (template && template.requiredOneOf && template.requiredOneOf.length > 0) {
                const attr_relation = attribute_to_delete.object_relation
                
                if (template.requiredOneOf.includes(attr_relation)) {
                    // Count how many attributes matching ANY of the requiredOneOf types will remain after deletion
                    const remainingRequiredAttrs = misp_object.attributes.filter(attr => 
                        attr.id !== attribute_id && template.requiredOneOf.includes(attr.object_relation)
                    ).length
                    
                    // If no required attributes will remain, prevent deletion
                    if (remainingRequiredAttrs === 0) {
                        display_toast({
                            status: 400, 
                            json: async () => ({
                                message: `Cannot delete attribute: At least one attribute of type [${template.requiredOneOf.join(', ')}] is required for this object`, 
                                toast_class: "danger-subtle"
                            })
                        })
                        return
                    }
                }
            }

            const res = await fetch("/case/"+props.case_id+"/misp_object/"+misp_object_id+"/delete_attribute/"+attribute_id)
            if(await res.status==200 ){
                case_misp_objects.value[loc[0]].attributes.splice(loc[1], 1)
            }
            display_toast(res)
        }

        function enterEditMode(attribute, template_uuid) {
            editingAttrId.value = attribute.id
            editState.value = {
                value: attribute.value,
                type: attribute.type,
                object_relation: attribute.object_relation,
                relation_type_combo: attribute.object_relation + '::' + attribute.type,
                first_seen: attribute.first_seen ? attribute.first_seen.replace(' ', 'T') : '',
                last_seen: attribute.last_seen ? attribute.last_seen.replace(' ', 'T') : '',
                ids_flag: attribute.ids_flag,
                disable_correlation: attribute.disable_correlation,
                comment: attribute.comment || ''
            }
            activeTemplateAttr.value = misp_objects.value.find((objectTemplate) => objectTemplate.uuid === template_uuid)
        }

        function cancelEdit() {
            editingAttrId.value = null
            editState.value = {}
        }

        function startAddingAttribute(object_id, template_uuid) {
            addingAttrToObject.value = object_id
            activeTemplateAttr.value = misp_objects.value.find((objectTemplate) => objectTemplate.uuid === template_uuid)
            newAttrState.value = {
                value: '',
                relation_type_combo: activeTemplateAttr.value.attributes[0] ? 
                    activeTemplateAttr.value.attributes[0].name + '::' + activeTemplateAttr.value.attributes[0].misp_attribute : '',
                first_seen: '',
                last_seen: '',
                ids_flag: false,
                disable_correlation: false,
                comment: ''
            }
        }

        function cancelAddAttribute() {
            addingAttrToObject.value = null
            newAttrState.value = {}
        }

        async function saveNewAttribute(misp_object_id) {
            if(!newAttrState.value.value) {
                create_message("Need to add a value", "warning-subtle")
                return
            }

            // Parse relation_type_combo to get object_relation and type
            const parts = newAttrState.value.relation_type_combo.split('::')
            const object_relation = parts[0]
            const type = parts[1]

            let url = "/case/"+props.case_id+"/add_attributes/"+misp_object_id
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "object-template": activeTemplateAttr.value,
                    "attributes": [{
                        "value": newAttrState.value.value,
                        "type": type,
                        "object_relation": object_relation,
                        "first_seen": newAttrState.value.first_seen,
                        "last_seen": newAttrState.value.last_seen,
                        "comment": newAttrState.value.comment,
                        "ids_flag": newAttrState.value.ids_flag,
                        "disable_correlation": newAttrState.value.disable_correlation
                    }]
                })
            });
            
            if(await res.status==200){
                await fetch_case_misp_object()
                cancelAddAttribute()
                emit("modif_misp_objects", true)
            }
            display_toast(res)
        }

        async function saveInlineEdit(misp_object_id, attr_id) {
            if(!editState.value.value) {
                create_message("Need to add a value", "warning-subtle")
                return
            }

            const parts = editState.value.relation_type_combo.split('::')
            const object_relation = parts[0]
            const type = parts[1]

            let misp_object = null
            let original_attribute = null
            for(let i in case_misp_objects.value){
                if(misp_object_id == case_misp_objects.value[i].object_id){
                    misp_object = case_misp_objects.value[i]
                    for(let j in case_misp_objects.value[i].attributes){
                        if(attr_id == case_misp_objects.value[i].attributes[j].id){
                            original_attribute = case_misp_objects.value[i].attributes[j]
                            break
                        }
                    }
                    break
                }
            }

            if(misp_object && original_attribute && original_attribute.object_relation !== object_relation) {
                const template = misp_objects.value.find((t) => t.uuid === misp_object.object_uuid)
                
                if (template && template.requiredOneOf && template.requiredOneOf.length > 0) {
                    if (template.requiredOneOf.includes(original_attribute.object_relation)) {
                        const remainingRequiredAttrs = misp_object.attributes.filter(attr => 
                            attr.id !== attr_id && template.requiredOneOf.includes(attr.object_relation)
                        ).length
                        
                        const newIsRequired = template.requiredOneOf.includes(object_relation)
                        
                        if (remainingRequiredAttrs === 0 && !newIsRequired) {
                            display_toast({
                                status: 400,
                                json: async () => ({
                                    message: `Cannot change type: At least one attribute of type [${template.requiredOneOf.join(', ')}] is required for this object`,
                                    toast_class: "danger-subtle"
                                })
                            })
                            return
                        }
                    }
                }
            }

            let url = "/case/"+props.case_id+"/misp_object/"+misp_object_id+"/edit_attr/"+attr_id
            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "value": editState.value.value,
                    "type": type,
                    "object_relation": object_relation,
                    "first_seen": editState.value.first_seen,
                    "last_seen": editState.value.last_seen,
                    "comment": editState.value.comment,
                    "ids_flag": editState.value.ids_flag,
                    "disable_correlation": editState.value.disable_correlation
                })
            });
            
            if(await res.status==200){
                for(let i in case_misp_objects.value){
                    if(misp_object_id == case_misp_objects.value[i].object_id){
                        for(let j in case_misp_objects.value[i].attributes){
                            if(attr_id == case_misp_objects.value[i].attributes[j].id){
                                case_misp_objects.value[i].attributes[j].value = editState.value.value
                                case_misp_objects.value[i].attributes[j].type = type
                                case_misp_objects.value[i].attributes[j].object_relation = object_relation
                                case_misp_objects.value[i].attributes[j].first_seen = editState.value.first_seen ? editState.value.first_seen.replace("T", " ") : null
                                case_misp_objects.value[i].attributes[j].last_seen = editState.value.last_seen ? editState.value.last_seen.replace("T", " ") : null
                                case_misp_objects.value[i].attributes[j].ids_flag = editState.value.ids_flag
                                case_misp_objects.value[i].attributes[j].disable_correlation = editState.value.disable_correlation
                                case_misp_objects.value[i].attributes[j].comment = editState.value.comment
                                if(editState.value.disable_correlation){
                                    case_misp_objects.value[i].attributes[j].correlation_list = []
                                }else{
                                    const res_correlation = await fetch("/case/"+props.case_id+"/get_correlation_attr/"+case_misp_objects.value[i].attributes[j].id)
                                    let loc_cor = await res_correlation.json()
                                    case_misp_objects.value[i].attributes[j].correlation_list = loc_cor["correlation_list"]
                                }
                            }
                        }
                    }
                }
                cancelEdit()
            }
            display_toast(res)
        }

        watch(selectedQuickTemplate, (newValue, oldValue) => {
            if (defaultObjectTemplates[newValue]) {                
                activeTemplate.value = misp_objects.value.find((objectTemplate) => objectTemplate.uuid === defaultObjectTemplates[newValue]);
            }
        });
        

		onMounted(() => {
            fetch_case_misp_object()
            fetch_misp_object()

            $('.select2-misp-object').select2({
                theme: 'bootstrap-5',
                dropdownParent: $("#modal-add-object")
            })
            $('.select2-misp-object').on('change.select2', function (e) {
                activeTemplate.value = misp_objects.value.find(
                    (objectTemplate) => objectTemplate.uuid === $(this).select2('data').map(item => item.id)[0]
                );
            })
            
        })

		return {
            case_misp_objects,
            misp_objects,
            activeTemplate,
            activeTemplateAttr,
            selectedQuickTemplate,
            list_attr,
            save_changes,
            add_attribute_list,
            delete_attribute_list,
            copyUuidToClipboard,
            delete_object,
            open_modal_add_attribute,
            delete_attribute,
            editingAttrId,
            editState,
            enterEditMode,
            cancelEdit,
            saveInlineEdit,
            addingAttrToObject,
            newAttrState,
            startAddingAttribute,
            cancelAddAttribute,
            saveNewAttribute,
            compactView,
            toggleCompactView
		}
    },
    css: `
        .tab-content {
            border-left: 1px solid #ddd;
            border-right: 1px solid #ddd;
            border-bottom: 1px solid #ddd;
            padding: 10px;
        }

        .nav-tabs {
            margin-bottom: 0;
        }

        .figure {
            width: 100px;
            text-align: center;
            vertical-align: middle;
        }
    `,
	template: `
    <div class="mb-1">
        <button class="btn btn-primary" title="Add a new object" data-bs-toggle="modal" data-bs-target="#modal-add-object">
            <i class="fa-solid fa-plus"></i> <i class="fa-solid fa-cubes"></i>
        </button>
        <a type="button" class="btn btn-secondary ms-3" title="Analyze misp-objects"
        :href="'/analyzer/misp-modules?case_id='+case_id+'&misp_object=True'">
            <i class="fa-solid fa-magnifying-glass"></i>
        </a>
        <button type="button" class="btn btn-outline-secondary ms-3" @click="toggleCompactView()" :title="compactView ? 'Show all columns' : 'Show compact view'">
            <i :class="compactView ? 'fa-solid fa-expand' : 'fa-solid fa-compress'"></i>
            <span class="d-none d-sm-inline ms-1">[[ compactView ? 'Detailed' : 'Compact' ]]</span>
        </button>
    </div>
    <div class="row">
        <div v-for="misp_object, key_obj in case_misp_objects" class="accordion col-6 p-1" :id="'accordion-'+key_obj">
            <div class="accordion-item">
                <h2 class="accordion-header">
                <button class="accordion-button" type="button" data-bs-toggle="collapse" :data-bs-target="'#collapse-'+key_obj" aria-expanded="true" :aria-controls="'collapse-'+key_obj">
                    [[ misp_object.object_name ]]
                </button>
                </h2>
                <div :id="'collapse-'+key_obj" class="accordion-collapse collapse show" :data-bs-parent="'#accordion-'+key_obj">
                    <div class="accordion-body">
                        <button type="button" class="btn btn-primary btn-sm" title="Add new attributes" 
                            @click="startAddingAttribute(misp_object.object_id, misp_object.object_uuid)" >
                            <i class="fa-solid fa-plus"></i>
                        </button>
                        <button type="button" class="btn btn-danger btn-sm" @click="delete_object(misp_object.object_id)" title="Delete object">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                        <div class="table-responsive">
                            <table class="table">
                                <thead>
                                    <tr>
                                        <th>Value</th>
                                        <th>Object Relation</th>
                                        <th>Type</th>
                                        <th v-show="!compactView">First seen</th>
                                        <th v-show="!compactView">Last seen</th>
                                        <th v-show="!compactView">IDS</th>
                                        <th v-show="!compactView" title="Correlation"><i class="fa-solid fa-diagram-project"></i></th>
                                        <th v-show="!compactView">Comment</th>
                                        <th></th>
                                    </tr>
                                </thead>
                                <tbody>
                                    <tr v-for="attribute, key_attr in misp_object.attributes ">
                                        <!-- Display mode -->
                                        <template v-if="editingAttrId !== attribute.id">
                                            <td>[[attribute.value]]</td>
                                            <td>[[attribute.object_relation]]</td>
                                            <td>[[attribute.type]]</td>
                                            <td v-show="!compactView">
                                                <template v-if="attribute.first_seen">[[attribute.first_seen]]</template>
                                                <i v-else>none</i>
                                            </td>
                                            <td v-show="!compactView">
                                                <template v-if="attribute.last_seen">[[attribute.last_seen]]</template>
                                                <i v-else>none</i>
                                            </td>
                                            <td v-show="!compactView">[[attribute.ids_flag]]</td>
                                            <td v-show="!compactView">
                                                <template v-if="attribute.disable_correlation">
                                                    <i class="fa-solid fa-link-slash text-muted" title="Correlation disabled"></i>
                                                </template>
                                                <template v-else>
                                                    <template v-for="cid, key in attribute.correlation_list">
                                                        <a :href="'/case/'+cid">[[cid]]</a>
                                                        <template v-if="key != attribute.correlation_list.length-1">,</template>
                                                    </template>
                                                </template>
                                            </td>
                                            <td v-show="!compactView">
                                                <template v-if="attribute.comment">[[attribute.comment]]</template>
                                                <i v-else>none</i>
                                            </td>
                                            <td style="white-space: nowrap;">
                                                <button type="button" class="btn btn-primary btn-sm" title="Edit attribute"
                                                @click="enterEditMode(attribute, misp_object.object_uuid)">
                                                    <i class="fa-solid fa-fw fa-pen-to-square"></i>
                                                </button>
                                                <button type="button" class="btn btn-danger btn-sm" title="Delete attribute"
                                                @click="delete_attribute(attribute.id, misp_object.object_id)">
                                                    <i class="fa-solid fa-fw fa-trash"></i>
                                                </button>
                                            </td>
                                        </template>
                                        
                                        <!-- Edit mode -->
                                        <template v-else>
                                            <td :colspan="compactView ? 4 : 9" style="padding: 1rem;">
                                                <div class="mb-3">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value</label>
                                                    <input v-model="editState.value" class="form-control form-control-sm" type="text" style="font-size: 0.875rem;">
                                                </div>
                                                <div class="row g-2 mb-3">
                                                    <div class="col-md-4">
                                                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type</label>
                                                        <select v-model="editState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                            <template v-for="attr in activeTemplateAttr.attributes">
                                                                <option :value="attr.name + '::' + attr.misp_attribute">[[attr.name]]::[[attr.misp_attribute]]</option>
                                                            </template>
                                                        </select>
                                                    </div>
                                                    <div class="col-md-3">
                                                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">First Seen</label>
                                                        <input v-model="editState.first_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                                                    </div>
                                                    <div class="col-md-3">
                                                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Last Seen</label>
                                                        <input v-model="editState.last_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                                                    </div>
                                                    <div class="col-md-1">
                                                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">IDS</label>
                                                        <div class="form-check mt-1">
                                                            <input v-model="editState.ids_flag" type="checkbox" class="form-check-input">
                                                        </div>
                                                    </div>
                                                    <div class="col-md-1">
                                                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;" title="Disable correlation">Corr.</label>
                                                        <div class="form-check mt-1">
                                                            <input v-model="editState.disable_correlation" type="checkbox" class="form-check-input" title="Disable correlation">
                                                        </div>
                                                    </div>
                                                </div>
                                                <div class="mb-3">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Comment</label>
                                                    <textarea v-model="editState.comment" class="form-control form-control-sm" placeholder="Comment" rows="2" style="font-size: 0.875rem;"></textarea>
                                                </div>
                                                <div class="d-flex gap-2">
                                                    <button type="button" class="btn btn-success btn-sm" title="Save changes"
                                                    @click="saveInlineEdit(misp_object.object_id, attribute.id)">
                                                        <i class="fa-solid fa-fw fa-check me-1"></i>Save
                                                    </button>
                                                    <button type="button" class="btn btn-secondary btn-sm" title="Cancel"
                                                    @click="cancelEdit()">
                                                        <i class="fa-solid fa-fw fa-times me-1"></i>Cancel
                                                    </button>
                                                </div>
                                            </td>
                                        </template>
                                    </tr>
                                    
                                    <!-- Add new attribute row -->
                                    <tr v-if="addingAttrToObject === misp_object.object_id">
                                        <td :colspan="compactView ? 4 : 9" style="padding: 1rem; background-color: #f8f9fa;">
                                            <div class="mb-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value</label>
                                                <input v-model="newAttrState.value" class="form-control form-control-sm" type="text" placeholder="Value" style="font-size: 0.875rem;">
                                            </div>
                                            <div class="row g-2 mb-3">
                                                <div class="col-md-4">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type</label>
                                                    <select v-model="newAttrState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                        <template v-for="attr in activeTemplateAttr.attributes">
                                                            <option :value="attr.name + '::' + attr.misp_attribute">[[attr.name]]::[[attr.misp_attribute]]</option>
                                                        </template>
                                                    </select>
                                                </div>
                                                <div class="col-md-3">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">First Seen</label>
                                                    <input v-model="newAttrState.first_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                                                </div>
                                                <div class="col-md-3">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Last Seen</label>
                                                    <input v-model="newAttrState.last_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                                                </div>
                                                <div class="col-md-1">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">IDS</label>
                                                    <div class="form-check mt-1">
                                                        <input v-model="newAttrState.ids_flag" type="checkbox" class="form-check-input">
                                                    </div>
                                                </div>
                                                <div class="col-md-1">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;" title="Disable correlation">Corr.</label>
                                                    <div class="form-check mt-1">
                                                        <input v-model="newAttrState.disable_correlation" type="checkbox" class="form-check-input" title="Disable correlation">
                                                    </div>
                                                </div>
                                            </div>
                                            <div class="mb-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Comment</label>
                                                <textarea v-model="newAttrState.comment" class="form-control form-control-sm" placeholder="Comment" rows="2" style="font-size: 0.875rem;"></textarea>
                                            </div>
                                            <div class="d-flex gap-2">
                                                <button type="button" class="btn btn-success btn-sm" title="Add attribute"
                                                @click="saveNewAttribute(misp_object.object_id)">
                                                    <i class="fa-solid fa-fw fa-check me-1"></i>Add
                                                </button>
                                                <button type="button" class="btn btn-secondary btn-sm" title="Cancel"
                                                @click="cancelAddAttribute()">
                                                    <i class="fa-solid fa-fw fa-times me-1"></i>Cancel
                                                </button>
                                            </div>
                                        </td>
                                    </tr>
                                </tbody>
                            </table>
                        </div>
                    </div>
                </div>
            </div>

        </div>
    </div>

    <!-- Modal Add object -->
    <div class="modal fade" id="modal-add-object" tabindex="-1" aria-labelledby="EditObjectLabel" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="EditObjectLabel">Add Object</h1>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>

                <div class="modal-body">
                    <ul class="nav nav-tabs" id="addObjectTabs" role="tablist">
                        <li class="nav-item" role="presentation">
                            <button class="nav-link active" id="category-tab" data-bs-toggle="tab"
                                data-bs-target="#category" type="button" role="tab" aria-controls="category"
                                aria-selected="true">Category</button>
                        </li>
                        <li class="nav-item" role="presentation">
                            <button class="nav-link" id="attributes-tab" data-bs-toggle="tab"
                                :disabled="!activeTemplate.uuid" data-bs-target="#attributes" type="button"
                                role="tab" aria-controls="attributes" aria-selected="false">Attributes</button>
                        </li>
                    </ul>

                    <div class="tab-content" id="add-object-tab-content">
                        <div class="tab-pane show active" id="category" role="tabpanel"
                            aria-labelledby="category-tab">
                            <div class="btn-group" role="group">
                                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                                    v-bind:value="'domain/ip'" name="btnradio" id="btn-domain-ip"
                                    autocomplete="off">
                                <label class="btn btn-outline-primary" for="btn-domain-ip">
                                    <i class="fa-solid fa-network-wired fa-2xl mt-3" />
                                    <p>Domain/IP</p>
                                </label>
                                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                                    v-bind:value="'url/domain'" name="btnradio" id="btn-url-domain"
                                    autocomplete="off">
                                <label class="btn btn-outline-primary" for="btn-url-domain">
                                    <i class="fa-solid fa-link fa-2xl mt-3" />
                                    <p>URL/Domain</p>
                                </label>
                                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                                    v-bind:value="'file/hash'" name="btnradio" id="btn-file-hash"
                                    autocomplete="off">
                                <label class="btn btn-outline-primary" for="btn-file-hash">
                                    <i class="fa-solid fa-file-lines fa-2xl mt-3" />
                                    <p>File/Hash</p>
                                </label>
                                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                                    v-bind:value="'vulnerability'" name="btnradio" id="btn-vulnerability"
                                    autocomplete="off">
                                <label class="btn btn-outline-primary" for="btn-vulnerability">
                                    <i class="fa-solid fa-skull-crossbones fa-2xl mt-3" />
                                    <p>Vulnerability</p>
                                </label>
                                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                                    v-bind:value="'financial'" name="btnradio" id="btn-financial"
                                    autocomplete="off">
                                <label class="btn btn-outline-primary" for="btn-financial">
                                    <i class="fa-solid fa-money-check-dollar fa-2xl mt-3" />
                                    <p>Financial</p>
                                </label>
                                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                                    v-bind:value="'personal'" name="btnradio" id="btn-person" autocomplete="off">
                                <label class="btn btn-outline-primary" for="btn-person">
                                    <i class="fa-solid fa-person fa-2xl mt-3" />
                                    <p>Personal</p>
                                </label>
                            </div>
                            <div class="col text-start mt-3">
                                <label for="activeTemplate" class="form-label">Or select a template from the
                                    list:</label>
                                <select class="select2-misp-object">
                                    <option value="">--</option>
                                    <template v-for="object in misp_objects">
                                        <option :value="object.uuid">[[object.name]]</option>
                                    </template>
                                </select>
                            </div>
                            <div v-if="activeTemplate.uuid">
                                <div class="mt-3">
                                    <span class="fw-bold">[[ activeTemplate.name ]] </span>
                                    <span class="badge bg-light text-dark">[[activeTemplate.uuid]] </span>
                                    <button type="button" class="btn"><i class="text-primary fa-solid fa-copy"
                                            @click="copyUuidToClipboard" /></button>
                                    <span class="badge bg-secondary">[[ activeTemplate.meta_category ]]</span>
                                    <div>[[ activeTemplate.description ]]</div>
                                </div>
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th style="width: 30%" scope="col">type</th>
                                            <th style="width: 30%" scope="col">MISP type</th>
                                            <th style="width: 30%" scope="col">correlate</th>
                                            <th style="width: 30%" scope="col">multiple</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <template :key="attribute.id" v-for="attribute in activeTemplate.attributes">
                                            <tr>
                                                <td>[[ attribute.name ]] </td>
                                                <td>[[ attribute.misp_attribute ]]</td>
                                                <td>[[ attribute.disable_correlation ]]</td>
                                                <td>[[ attribute.multiple ]]</td>
                                            </tr>
                                            <tr>
                                                <td></td>
                                                <td colspan="3" class="text-secondary">[[ attribute.description ]]</td>
                                            </tr>
                                        </template>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                        <div class="tab-pane" id="attributes" role="tabpanel" aria-labelledby="attributes-tab">
                            <AddObjectAttributes v-if="activeTemplate.uuid"
                                :key_obj="activeTemplate.uuid"
                                :template="activeTemplate"
                                :only_attr="false"
                                @object-attribute-added="(object) => add_attribute_list(object)"
                                @object-attribute-deleted="delete_attribute_list"/>
                        </div>
                    </div>
                </div>

                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" @click="save_changes()">Save changes</button>
                </div>
            </div>
        </div>
    </div>
    `
}