const { ref, onMounted, onUpdated } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		template: Object,
        only_attr: Boolean,
        key_obj: String
	},
    emits:[
        "object-attribute-added",
        "object-attribute-deleted"
    ],
	setup(props, {emit}) {
        const list_attr = ref([])
        let attribueCount = 0

        function add_attribute(){            
            attribueCount += 1

            let loc_type = $("#select-type-"+props.key_obj).val()
            
            let loc = {
                "id": attribueCount, "value": $("#input-value-"+props.key_obj).val(), 
                "type": loc_type.split("::")[1], "object_relation": loc_type.split("::")[0],
                "first_seen": $("#input-first-seen-"+props.key_obj).val(), "last_seen": $("#input-last-seen-"+props.key_obj).val(),
                "comment": $("#textarea-comment-"+props.key_obj).val(), "ids_flag": $("#input-ids-"+props.key_obj).is(":checked"),
                "disable_correlation": $("#input-disable-correlation-"+props.key_obj).is(":checked")
            }
            
            list_attr.value.push(loc)
            $("#input-value-"+props.key_obj).val("")
            $("#textarea-comment-"+props.key_obj).val("")
            $("#input-first-seen-"+props.key_obj).val("")
            $("#input-last-seen-"+props.key_obj).val("")
            $("#input-ids-"+props.key_obj).prop("checked", false);
            $("#input-disable-correlation-"+props.key_obj).prop("checked", true);

            emit('object-attribute-added', loc)
            
        }

        function deleteObjectAttribute(attribute_id){
            let loc 
            for (let i in list_attr.value){
                if(list_attr.value[i].id == attribute_id){
                    loc = i
                    break
                }
            }
            list_attr.value.splice(loc, 1)
            emit('object-attribute-deleted', loc);
        }

		onMounted(() => {
            if(props.only_attr){
                $('.select2-type').select2({
                    theme: 'bootstrap-5',
                    dropdownParent: $("#modal-add-attribute-"+props.key_obj)
                })
            }else{
                $('.select2-type').select2({
                    theme: 'bootstrap-5',
                    dropdownParent: $("#modal-add-object")
                })
            }
        })
        onUpdated(() => {
            if(props.only_attr){
                $('.select2-type').select2({
                    theme: 'bootstrap-5',
                    dropdownParent: $("#modal-add-attribute-"+props.key_obj)
                })
            }else{
                $('.select2-type').select2({
                    theme: 'bootstrap-5',
                    dropdownParent: $("#modal-add-object")
                })
            }
            
        })

		return {
            list_attr,
            add_attribute,
            deleteObjectAttribute
		}
    },
	template: `
        <div>
            <div class="mt-3 mb-3">
                <div class="card card-body">
                    <div>
                        <span class="fw-bold">[[ template.name ]] </span>
                        <span class="badge bg-info flex ms-1">v[[ template.version ]]</span>
                    </div>
                    <div><span class="badge bg-secondary flex">[[ template.meta_category ]]</span>
                    </div>
                    <div>
                        <span>[[ template.description ]]</span>
                    </div>
                    <span class="fw-bold">requires one of:</span>
                    <ul>
                        <li v-for="attribute in template.requiredOneOf">[[ attribute ]]</li>
                    </ul>
                </div>
            </div>

            <div class="form-floating input-group mb-3" v-for="attribute in list_attr">
                <div class="row">
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_value'" class="form-control" :value="attribute.value" disabled>
                        <label>value</label>
                    </div>
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_object_relation'" :value="attribute.object_relation" class="form-control" disabled>
                        <label>Object relation</label>
                    </div>
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_type'" :value="attribute.type" class="form-control" disabled>
                        <label>type</label>
                    </div>
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_first_seen'" :value="attribute.first_seen" class="form-control" disabled>
                        <label>first_seen</label>
                    </div>
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_last_seen'" :value="attribute.last_seen" class="form-control" disabled>
                        <label>last_seen</label>
                    </div>
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_ids'" :value="attribute.ids_flag" class="form-control" type="checkbox" disabled>
                        <label>IDS</label>
                    </div>
                    <div class="form-floating col">
                        <input :name="'attribute_'+attribute.id+'_disable_correlation'" :value="attribute.disable_correlation" class="form-control" type="checkbox" disabled>
                        <label>Disable Correlation</label>
                    </div>
                    <div class="form-floating col">
                        <textarea :name="'attribute_'+attribute.id+'_comment'" :value="attribute.comment" class="form-control" disabled></textarea>
                        <label>Comment</label>
                    </div>
                </div>

                <button class="btn btn-outline-danger" type="button" @click="deleteObjectAttribute(attribute.id)">
                    <i class="fa-solid fa-trash" />
                </button>
            </div>

            <div class="input-group has-validation mb-3">
                <label class="input-group-text" for="input-value">value</label>
                <input class="form-control" :id="'input-value-'+key_obj">
                <label class="input-group-text" for="select-type">type</label>
                <select class="select2-type form-control" :id="'select-type-'+key_obj" v-if="template">
                    <template v-for="attr in template.attributes">
                                                 // object_relation::type
                        <option :value="attr.name+'::'+attr.misp_attribute">[[attr.name]]::[[attr.misp_attribute]]</option>
                    </template>
                </select>
            </div>
            <div class="input-group has-validation mb-3">
                <label class="input-group-text">first seen</label>
                <input class="form-control" :id="'input-first-seen-'+key_obj" type="datetime-local">

                <label class="input-group-text" for="input-last-seen">last seen</label>
                <input class="form-control" :id="'input-last-seen-'+key_obj" name="input-last-seen" type="datetime-local">
            </div>
            <div class="input-group has-validation mb-3">
                <label class="input-group-text">Comment</label>
                <textarea class="form-control" :id="'textarea-comment-'+key_obj"></textarea>
            </div>
            <div class="d-flex mb-3">
                <label class="input-group-text me-1" for="input-ids">
                    IDS flag
                </label>
                <input :id="'input-ids-'+key_obj" name="input-ids" type="checkbox" value="y">

                <label class="input-group-text me-1" for="input-disable-correlation">
                    Disable Correlation
                </label>
                <input :id="'input-disable-correlation-'+key_obj" name="input-disable-correlation" type="checkbox" checked value="y">
            </div>

            <button @click="add_attribute()" class="btn btn-outline-primary">
                Add Attribute
            </button>
        </div>
    `
}