import {display_toast, create_message} from '../toaster.js'
import AddObjectAttributes from './AddObjectAttributes.js'
import ObjectConnectors from './ObjectConnectors.js'
const { ref, onMounted, watch } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		case_id: Number
	},
    emits: ['modif_misp_objects'],
    components: {
        AddObjectAttributes,
        ObjectConnectors
    },
	setup(props, {emit}) {
        const case_misp_objects = ref([])
        const misp_objects = ref([])
        const activeTemplate = ref({requiredOneOf: [],})
        const activeTemplateAttr = ref({requiredOneOf: [],})
        const selectedQuickTemplate = ref('');
        const list_attr = ref([])

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

        async function edit_attr(misp_object_id, attr_id){
            let value = $("#attribute_value_"+attr_id).val()
            let type = $("#select-type-attr-"+attr_id).val()
            let first_seen = $("#attribute_"+attr_id+"_first_seen").val()
            let last_seen = $("#attribute_"+attr_id+"_last_seen").val()
            let ids = $("#attribute_"+attr_id+"_ids").is(":checked")
            let comment = $("#attribute_"+attr_id+"_comment").val()            

            if(value){
                let url = "/case/"+props.case_id+"/misp_object/"+misp_object_id+"/edit_attr/"+attr_id
                const res = await fetch(url, {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        "value": value,
                        "type": type,
                        "first_seen": first_seen,
                        "last_seen": last_seen,
                        "comment": comment,
                        "ids_flag": ids
                    })
                });
                if(await res.status==200){
                    for(let i in case_misp_objects.value){
                        if(misp_object_id == case_misp_objects.value[i].object_id){
                            for(let j in case_misp_objects.value[i].attributes){
                                if(attr_id == case_misp_objects.value[i].attributes[j].id){
                                    case_misp_objects.value[i].attributes[j].value = value
                                    case_misp_objects.value[i].attributes[j].type = type
                                    case_misp_objects.value[i].attributes[j].first_seen = first_seen.replace("T", " ");
                                    case_misp_objects.value[i].attributes[j].last_seen = last_seen.replace("T", " ");
                                    case_misp_objects.value[i].attributes[j].ids_flag = ids
                                    case_misp_objects.value[i].attributes[j].comment = comment
                                }
                            }
                        }
                    }
                    var myModal = new bootstrap.Modal(document.getElementById("modal-edit-attr-"+attr_id), {});
                    myModal.hide();
                }
                display_toast(res)
            }else{
                create_message("Need to add a value", "warning-subtle")
            }
        }

        async function delete_attribute(attribute_id, misp_object_id) {
            const res = await fetch("/case/"+props.case_id+"/misp_object/"+misp_object_id+"/delete_attribute/"+attribute_id)
            if(await res.status==200 ){
                let loc

                for(let i in case_misp_objects.value){
                    if(misp_object_id == case_misp_objects.value[i].object_id){
                        for(let j in case_misp_objects.value[i].attributes){
                            if(attribute_id == case_misp_objects.value[i].attributes[j].id){
                                loc = [i,j]
                                break
                            }
                        }
                    }
                }
                case_misp_objects.value[loc[0]].attributes.splice(loc[1], 1)
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
            edit_attr,
            delete_attribute
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
        <div class="collapse" id="collapseMispObject">
            <div class="card card-body">
                <div class="mb-1">
                    <button class="btn btn-primary" title="Add a new object" data-bs-toggle="modal" data-bs-target="#modal-add-object">
                        <i class="fa-solid fa-plus"></i> <i class="fa-solid fa-cubes"></i>
                    </button>
                    <button class="btn btn-outline-primary" style="float: right;" data-bs-toggle="modal" data-bs-target="#modal-send-to">
                        <i class="fa-solid fa-link"></i> MISP Connectors
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
                                <button type="button" class="btn btn-primary btn-sm" title="Add new attributes" @click="open_modal_add_attribute(misp_object.object_uuid, 'modal-add-attribute-', key_obj)" >
                                    <i class="fa-solid fa-plus"></i>
                                </button>
                                <button type="button" class="btn btn-danger btn-sm" @click="delete_object(misp_object.object_id)" title="Delete object">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                                <table class="table">
                                    <thead>
                                        <tr>
                                            <th>value</th>
                                            <th>type</th>
                                            <th>first seen</th>
                                            <th>last seen</th>
                                            <th>IDS</th>
                                            <th>comment</th>
                                            <th></th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        <tr v-for="attribute, key_attr in misp_object.attributes ">
                                            <td>[[attribute.value]]</td>
                                            <td>[[attribute.type]]</td>

                                            <td v-if="attribute.first_seen">[[attribute.first_seen]]</td>
                                            <td v-else><i>none</i></td>

                                            <td v-if="attribute.last_seen">[[attribute.last_seen]]</td>
                                            <td v-else><i>none</i></td>

                                            <td>[[attribute.ids_flag]]</td>

                                            <td v-if="attribute.comment">[[attribute.comment]]</td>
                                            <td v-else><i>none</i></td>
                                            <td>
                                                <button type="button" class="btn btn-primary btn-sm" title="Edit attribute"
                                                @click="open_modal_add_attribute(misp_object.object_uuid, 'modal-edit-attr-', attribute.id)">
                                                    <i class="fa-solid fa-pen-to-square"></i>
                                                </button>
                                                <button type="button" class="btn btn-danger btn-sm" title="Delete attribute"
                                                @click="delete_attribute(attribute.id, misp_object.object_id)">
                                                    <i class="fa-solid fa-trash"></i>
                                                </button>
                                            </td>


                                            <!-- Modal Edit attribute -->
                                            <div class="modal fade" :id="'modal-edit-attr-'+attribute.id" tabindex="-1" aria-labelledby="EditObjectLabel" aria-hidden="true">
                                                <div class="modal-dialog modal-xl">
                                                    <div class="modal-content">
                                                    <div class="modal-header">
                                                        <h1 class="modal-title fs-5" id="EditObjectLabel">Edit Attribute</h1>
                                                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                                                    </div>
                                                    <div class="modal-body">
                                                        <div class="form-floating input-group mb-3">
                                                            <div class="row">
                                                                <div class="form-floating col">
                                                                    <input :id="'attribute_value_'+attribute.id" class="form-control" :value="attribute.value">
                                                                    <label>value</label>
                                                                </div>
                                                                <div class="form-floating col">
                                                                    <select class="form-select" :id='"select-type-attr-"+attribute.id'>
                                                                        <template v-for="attr in activeTemplateAttr.attributes">
                                                                            <option :value="attr.name">[[attr.name]]</option>
                                                                        </template>
                                                                    </select>
                                                                    <label>type</label>
                                                                </div>
                                                                <div class="form-floating col">
                                                                    <input :id="'attribute_'+attribute.id+'_first_seen'" 
                                                                            :value="attribute.first_seen" 
                                                                            class="form-control"
                                                                            type="datetime-local">
                                                                    <label>first_seen</label>
                                                                </div>
                                                                <div class="form-floating col">
                                                                    <input :id="'attribute_'+attribute.id+'_last_seen'" 
                                                                            :value="attribute.last_seen" 
                                                                            class="form-control"
                                                                            type="datetime-local">
                                                                    <label>last_seen</label>
                                                                </div>
                                                                <div class="col">
                                                                    <input :id="'attribute_'+attribute.id+'_ids'" 
                                                                            :checked="attribute.ids_flag"
                                                                            type="checkbox">
                                                                    <label>IDS</label>
                                                                </div>
                                                                <div class="form-floating col">
                                                                    <textarea :id="'attribute_'+attribute.id+'_comment'" 
                                                                                :value="attribute.comment" 
                                                                                class="form-control">
                                                                    </textarea>
                                                                    <label>Comment</label>
                                                                </div>
                                                            </div>
                                                        </div>
                                                    </div>
                                                    <div class="modal-footer">
                                                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                                        <button type="button" class="btn btn-primary" 
                                                            @click="edit_attr(misp_object.object_id, attribute.id)">
                                                            Save changes
                                                        </button>
                                                    </div>
                                                    </div>
                                                </div>
                                            </div>


                                        </tr>
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>

                    <!-- Modal add attributes -->
                    <div class="modal fade" :id="'modal-add-attribute-'+key_obj" tabindex="-1" aria-labelledby="EditObjectLabel" aria-hidden="true">
                        <div class="modal-dialog modal-xl">
                            <div class="modal-content">
                            <div class="modal-header">
                                <h1 class="modal-title fs-5" id="EditObjectLabel">Add Attributes</h1>
                                <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <AddObjectAttributes v-if="activeTemplateAttr.uuid"
                                    :template="activeTemplateAttr"
                                    :only_attr="true"
                                    :key_obj="key_obj"
                                    @object-attribute-added="(object) => add_attribute_list(object)"
                                    @object-attribute-deleted="delete_attribute_list"/>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                <button type="button" class="btn btn-primary" @click="save_changes(misp_object.object_id, key_obj)">Save changes</button>
                            </div>
                            </div>
                        </div>
                    </div>

                </div>
                </div>
            </div>
        </div>

        <ObjectConnectors/>

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