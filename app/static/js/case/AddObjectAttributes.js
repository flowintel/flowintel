const { ref, onMounted } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		template: Object,
        only_attr: Boolean,
        key: Number
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
            list_attr.value.push({"id": attribueCount, "value": $("#input-value").val(), "type": $("#select-type").val()})
            emit('object-attribute-added', {"id": attribueCount, "value": $("#input-value").val(), "type": $("#select-type").val()})
            $("#input-value").val("")
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
                    dropdownParent: $("#modal-add-attribute-"+props.key)
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
                        <span class="badge bg-info flex">v[[ template.version ]]</span>
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
                <div class="form-floating">
                    <input :name="'attribute_'+attribute.id+'.value'" class="form-control" :value="attribute.value" disabled>
                    <label>value</label>
                </div>
                <div class="form-floating">
                    <input :name="'attribute_'+attribute.id+'.type'" :value="attribute.type" class="form-control" disabled>
                    <label>type</label>
                </div>
                <button class="btn btn-outline-danger" type="button" @click="deleteObjectAttribute(attribute.id)">
                    <i class="fa-solid fa-trash" />
                </button>
            </div>

            <div class="input-group has-validation mb-3">
                <label class="input-group-text" for="attribute.value">value</label>
                <input class="form-control" id="input-value">
                <label class="input-group-text" for="attribute.type">type</label>
                <select class="select2-type form-control" id="select-type" v-if="template">
                    <template v-for="attr in template.attributes">
                        <option :value="attr.name">[[attr.name]]</option>
                    </template>
                </select>
                
                <button @click="add_attribute()" class="btn btn-outline-primary">
                    Add Attribute
                </button>
            </div>

        </div>
    `
}