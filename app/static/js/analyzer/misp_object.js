import {display_toast, create_message} from '../toaster.js'
import AddObjectAttributes from '/static/js/case/AddObjectAttributes.js'
const { ref, onMounted, watch, nextTick } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		case_id: Number
	},
    components: {
        AddObjectAttributes
    },
    emits:[
        "list_misp_objects"
    ],
	setup(props, {emit}) {
        const loc_misp_objects = ref([])
        const misp_objects = ref([])
        const activeTemplate = ref({requiredOneOf: [],})
        const activeTemplateAttr = ref({requiredOneOf: [],})
        const selectedQuickTemplate = ref('');
        const list_attr = ref([])
        let cp = 0
        let cp_attr = 0

        const defaultObjectTemplates = {
            'domain/ip': '43b3b146-77eb-4931-b4cc-b66c60f28734',
            'url/domain': '60efb77b-40b5-4c46-871b-ed1ed999fce5',
            'file/hash': '688c46fb-5edb-40a3-8273-1af7923e2215',
            'vulnerability': '81650945-f186-437b-8945-9f31715d32da',
            'financial': 'c51ed099-a628-46ee-ad8f-ffed866b6b8d',
            'personal': 'a15b0477-e9d1-4b9c-9546-abe78a4f4248'
        };

        async function fetch_misp_object(){
            const res = await fetch("/case/get_misp_object")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                misp_objects.value = loc["misp-object"]
            }
        }

        function save_changes(key=null) {
            if(list_attr.value.length){
                cp += 1
                
                loc_misp_objects.value.push({
                    "id": cp,
                    "object-template": activeTemplate.value,
                    "attributes": list_attr.value
                })
                list_attr.value = []
                activeTemplate.value = {}

                if(key){
                    $("#modal-add-attribute-"+key).modal("hide")

                    var myModal = new bootstrap.Modal(document.getElementById("modal-add-attribute-"+key), {});
                    myModal.hide();
                }else{
                    $("#modal-add-object").modal("hide")
                }
                emit('list_misp_objects', loc_misp_objects.value);
                create_message("Object added", "success-subtle")
            }else{
                create_message("Need to add an attribute", "warning-subtle")
            }
        }

        function add_attribute_list(object){
            cp_attr += 1
            object["id"] = cp_attr
            list_attr.value.push(object)            
        }
        function delete_attribute_list(object){
            cp_attr -= 1
            list_attr.value.splice(object, 1)
        }

        function copyUuidToClipboard() {
            navigator.clipboard.writeText(activeTemplate.value.uuid);
        }

        function delete_object(object_id){
            let loc
            for(let i in loc_misp_objects.value){
                if(loc_misp_objects.value[i].id == object_id){
                    loc = i
                    break
                }
            }
            loc_misp_objects.value.splice(loc, 1)
            emit('list_misp_objects', loc_misp_objects.value);
            create_message("Object deleted", "success-subtle")
        }

        async function open_modal_add_attribute(template_uuid, modal_id, key){
            activeTemplateAttr.value = misp_objects.value.find((objectTemplate) => objectTemplate.uuid === template_uuid);
            await nextTick()
            var myModal = new bootstrap.Modal(document.getElementById(modal_id + key), {});
            myModal.show();
            
        }

        function edit_attr(misp_object_id, attr_id){
            let value = $("#attribute_value_"+attr_id).val()
            let type = $("#select-type-attr-"+attr_id).val()
            let first_seen = $("#attribute_"+attr_id+"_first_seen").val()
            let last_seen = $("#attribute_"+attr_id+"_last_seen").val()
            let ids = $("#attribute_"+attr_id+"_ids").is(":checked")
            let comment = $("#attribute_"+attr_id+"_comment").val()

            if(value){
                for(let i in loc_misp_objects.value){
                    if(misp_object_id == loc_misp_objects.value[i].id){
                        for(let j in loc_misp_objects.value[i].attributes){
                            if(attr_id == loc_misp_objects.value[i].attributes[j].id){
                                loc_misp_objects.value[i].attributes[j].value = value
                                loc_misp_objects.value[i].attributes[j].type = type.split("::")[1]
                                loc_misp_objects.value[i].attributes[j].object_relation = type.split("::")[0]
                                loc_misp_objects.value[i].attributes[j].first_seen = first_seen.replace("T", " ");
                                loc_misp_objects.value[i].attributes[j].last_seen = last_seen.replace("T", " ");
                                loc_misp_objects.value[i].attributes[j].ids_flag = ids
                                loc_misp_objects.value[i].attributes[j].comment = comment
                            }
                        }
                    }
                }
                create_message("Attribute edited", "success-subtle")
                var myModal = new bootstrap.Modal(document.getElementById("modal-edit-attr-"+attr_id), {});
                myModal.hide();
                emit('list_misp_objects', loc_misp_objects.value);
            }else{
                create_message("Need to add a value", "warning-subtle")
            }
        }

         function delete_attribute(attribute_id, misp_object_id) {
            let loc

            for(let i in loc_misp_objects.value){
                if(misp_object_id == loc_misp_objects.value[i].id){
                    for(let j in loc_misp_objects.value[i].attributes){
                        if(attribute_id == loc_misp_objects.value[i].attributes[j].id){
                            loc = [i,j]
                            break
                        }
                    }
                }
            }
            loc_misp_objects.value[loc[0]].attributes.splice(loc[1], 1)
            
            create_message("Attribute deleted", "success-subtle")
            emit('list_misp_objects', loc_misp_objects.value);
        }

        async function fetch_misp_object_selected(){
            const res = await fetch("/analyzer/misp-modules/get_misp_object_selected")
            let loc = await res.json()
            
            loc_misp_objects.value=loc_misp_objects.value.concat(loc)
            emit('list_misp_objects', loc_misp_objects.value);
        }
        

        watch(selectedQuickTemplate, (newValue, oldValue) => {
            if (defaultObjectTemplates[newValue]) {                
                activeTemplate.value = misp_objects.value.find((objectTemplate) => objectTemplate.uuid === defaultObjectTemplates[newValue]);
            }
        });
        

		onMounted(() => {
            fetch_misp_object()
            fetch_misp_object_selected()

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
            loc_misp_objects,
            misp_objects,
            activeTemplate,
            activeTemplateAttr,
            selectedQuickTemplate,
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
        <div class="card card-body">
            <div class="mb-1">
                <button class="btn btn-primary" title="Add a new object" data-bs-toggle="modal" data-bs-target="#modal-add-object">
                    <i class="fa-solid fa-plus"></i> <i class="fa-solid fa-cubes"></i>
                </button>
            </div>
            <div class="row" v-if="loc_misp_objects.length">
                <div v-for="misp_object, key_obj in loc_misp_objects" class="accordion p-1" :id="'accordion-'+key_obj">
                    <div class="accordion-item">
                        <h2 class="accordion-header">
                        <button class="accordion-button" type="button" data-bs-toggle="collapse" :data-bs-target="'#collapse-'+key_obj" aria-expanded="true" :aria-controls="'collapse-'+key_obj">
                            [[ misp_object['object-template'].name ]]
                        </button>
                        </h2>
                        <div :id="'collapse-'+key_obj" class="accordion-collapse collapse show" :data-bs-parent="'#accordion-'+key_obj">
                            <div class="accordion-body">
                                <button type="button" class="btn btn-primary btn-sm" title="Add new attributes" @click="open_modal_add_attribute(misp_object['object-template'].uuid, 'modal-add-attribute-', key_obj)" >
                                    <i class="fa-solid fa-plus"></i>
                                </button>
                                <button type="button" class="btn btn-danger btn-sm" @click="delete_object(misp_object.id)" title="Delete object">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                                <div class="table-responsive">
                                    <table class="table">
                                        <thead>
                                            <tr>
                                                <th>Value</th>
                                                <th>Object Relation</th>
                                                <th>Type</th>
                                                <th>First seen</th>
                                                <th>Last seen</th>
                                                <th>IDS</th>
                                                <th>Comment</th>
                                                <th></th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr v-for="attribute, key_attr in misp_object.attributes ">
                                                <td>[[attribute.value]]</td>
                                                <td>[[attribute.object_relation]]</td>
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
                                                    @click="open_modal_add_attribute(misp_object['object-template'].uuid, 'modal-edit-attr-', attribute.id)">
                                                        <i class="fa-solid fa-pen-to-square"></i>
                                                    </button>
                                                    <button type="button" class="btn btn-danger btn-sm" title="Delete attribute"
                                                    @click="delete_attribute(attribute.id, misp_object['object-template'].id)">
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
                                                                                <option :value="attr.name+'::'+attr.misp_attribute">
                                                                                    [[attr.name]]::[[attr.misp_attribute]]
                                                                                </option>
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
                                                                </div>
                                                                <div class="row mt-3">
                                                                    <div class="col">
                                                                        <input :id="'attribute_'+attribute.id+'_ids'" 
                                                                                :checked="attribute.ids_flag"
                                                                                type="checkbox">
                                                                        <label>IDS</label>
                                                                    </div>
                                                                </div>
                                                                <div class="row mt-3">
                                                                    <div class="form-floating col">
                                                                        <textarea :id="'attribute_'+attribute.id+'_comment'" 
                                                                                    :value="attribute.comment" 
                                                                                    class="form-control" row="4" cols="70">
                                                                        </textarea>
                                                                        <label>Comment</label>
                                                                    </div>
                                                                </div>
                                                            </div>
                                                        </div>
                                                        <div class="modal-footer">
                                                            <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                                                            <button type="button" class="btn btn-primary" 
                                                                @click="edit_attr(misp_object.id, attribute.id)">
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
                                <button type="button" class="btn btn-primary" @click="save_changes(key_obj)">Save changes</button>
                            </div>
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