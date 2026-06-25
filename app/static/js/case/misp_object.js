import {display_toast, create_message} from '../toaster.js'
import MispObjectLink from './MispObjectLink.js'
import { confirmDelete } from '/static/js/confirm.js'
const { ref, computed, onMounted, onUnmounted, watch, nextTick } = Vue
export default {
    delimiters: ['[[', ']]'],
    components: { 'misp-object-link': MispObjectLink },
	props: {
		case_id: Number,
		cases_info: Object,
		spotlight_id: { type: Number, default: null },
		case_misp_objects_list: { type: Array, default: null }
	},
    emits: ['modif_misp_objects', 'clear_spotlight'],
	setup(props, {emit}) {
        function empty_template(overrides = {}) {
            return { requiredOneOf: [], attributes: [], ...overrides }
        }

        const case_misp_objects = ref([])
        const misp_objects = ref([])
        const activeTemplate = ref(empty_template())
        const activeTemplateAttr = ref(empty_template())
        const selectedQuickTemplate = ref('');
        const showAddObject = ref(false)
        const newObjectAttrState = ref({ relation_type_combo: '', value: '', first_seen: '', last_seen: '', comment: '', ids_flag: false, disable_correlation: true })
        const editingObjectAttrId = ref(null)
        const editObjectAttrState = ref({})
        const objectAttrCount = ref(0)
        const list_attr = ref([])
        const editingAttrId = ref(null)
        const editState = ref({})
        const addingAttrToObject = ref(null)
        const newAttrState = ref({})
        const compactView = ref(true)
        const tabView = ref(false)
        const activeTabIdx = ref(0)

        // Task assignment state
        const assigningTasks = ref(null) // object_id currently editing assignments
        const assign_task_state = ref({}) // map object_id -> [task_ids]
        const new_object_task_ids = ref([]) // for creation form

        // Object linking
        const link_modal_object = ref(null)   // the object currently open in the link modal
        const link_modal_ref = ref(null)
        // Search / filter / pagination
        const search_query = ref('')
        const type_filter = ref('')
        const show_unsynced_only = ref(false)
        const current_page = ref(1)
        const per_page = 10

        const filtered_objects = computed(() => {
            // Spotlight mode: show only the highlighted object
            if (props.spotlight_id != null) {
                return case_misp_objects.value.filter(o => o.object_id === props.spotlight_id)
            }
            let objs = case_misp_objects.value
            const q = search_query.value.trim().toLowerCase()
            const t = type_filter.value
            if (q) {
                objs = objs.filter(o => {
                    if (o.object_name.toLowerCase().includes(q)) return true
                    return o.attributes.some(a => String(a.value).toLowerCase().includes(q) || a.object_relation.toLowerCase().includes(q))
                })
            }
            if (t) {
                objs = objs.filter(o => o.object_name === t)
            }
            if (show_unsynced_only.value) {
                objs = objs.filter(o => !o.synced_instances || !o.synced_instances.length)
            }
            return objs
        })

        const total_pages = computed(() => Math.max(1, Math.ceil(filtered_objects.value.length / per_page)))

        const paged_objects = computed(() => {
            const start = (current_page.value - 1) * per_page
            return filtered_objects.value.slice(start, start + per_page)
        })

        const object_type_options = computed(() => {
            const names = [...new Set(case_misp_objects.value.map(o => o.object_name))]
            return names.sort()
        })

        watch([search_query, type_filter, show_unsynced_only], () => { current_page.value = 1; activeTabIdx.value = 0 })
        watch(() => props.spotlight_id, () => { current_page.value = 1; activeTabIdx.value = 0 })

        // Select2 for task assignment in new object form
        let hasJQuery = false
        let hasSelect2 = false
        try {
            hasJQuery = (typeof $ !== 'undefined')
            hasSelect2 = hasJQuery && $.fn && $.fn.select2
        } catch(e) {}

        watch(() => activeTemplate.value.uuid, async (newUuid) => {
            if (!newUuid) return
            await nextTick()
            try {
                const sel = document.getElementById('new-object-task-select')
                if (!sel) return

                const updateTaskSelection = function(el) {
                    try {
                        if (hasSelect2 && $(el).data('select2')) {
                            new_object_task_ids.value = $(el).select2('data').map(item => parseInt(item.id))
                        } else {
                            new_object_task_ids.value = Array.from(el.selectedOptions || []).map(o => parseInt(o.value))
                        }
                    } catch (e) {}
                }

                // Always attach native change listener as a fallback
                try { sel.removeEventListener && sel.removeEventListener('change', sel._fi_updateTaskSelection) } catch(e) {}
                sel._fi_updateTaskSelection = function() { updateTaskSelection(this) }
                sel.addEventListener('change', sel._fi_updateTaskSelection)

                if (hasSelect2) {
                    try { if ($(sel).data('select2')) $(sel).select2('destroy') } catch(e) {}
                    $(sel).select2({ theme: 'bootstrap-5', dropdownParent: $('body'), placeholder: 'Select tasks...', allowClear: true })
                    $(sel).on('change.select2', function() { updateTaskSelection(this) })
                }
            } catch(e) {}
        })

        const can_edit = computed(() => {
            if (!props.cases_info) return false
            const permission = props.cases_info.permission
            if (permission && permission.read_only) return false
            if (permission && permission.admin) return true
            if (permission && permission.misp_editor) return true
            return false
        })

        // Disable Save/Add buttons until required fields are filled in.
        const can_add_new_object_attr = computed(() =>
            !!(newObjectAttrState.value.value && newObjectAttrState.value.relation_type_combo))
        const can_save_edit_object_attr = computed(() =>
            !!(editObjectAttrState.value.value && editObjectAttrState.value.relation_type_combo))
        const can_save_object = computed(() => list_attr.value.length > 0)
        const can_save_new_attr = computed(() =>
            !!(newAttrState.value.value && newAttrState.value.relation_type_combo))
        const can_save_edit_attr = computed(() => !!editState.value.value)

        function template_attributes(template) {
            return Array.isArray(template?.attributes) ? template.attributes : []
        }

        function relation_type_option(attribute) {
            if (!attribute || !attribute.object_relation || !attribute.type) return null
            return {
                name: attribute.object_relation,
                misp_attribute: attribute.type
            }
        }

        function fallback_template(template_uuid, attribute = null) {
            const currentOption = relation_type_option(attribute)
            return empty_template({
                uuid: template_uuid || '',
                name: 'Unknown template',
                attributes: currentOption ? [currentOption] : []
            })
        }

        function find_object_template(template_uuid, attribute = null) {
            return misp_objects.value.find((objectTemplate) => objectTemplate.uuid === template_uuid) ||
                fallback_template(template_uuid, attribute)
        }

        const defaultObjectTemplates = {
            'domain/ip': '43b3b146-77eb-4931-b4cc-b66c60f28734',
            'url/domain': '60efb77b-40b5-4c46-871b-ed1ed999fce5',
            'file/hash': '688c46fb-5edb-40a3-8273-1af7923e2215',
            'vulnerability': '81650945-f186-437b-8945-9f31715d32da',
            'financial': 'c51ed099-a628-46ee-ad8f-ffed866b6b8d',
            'personal': 'a15b0477-e9d1-4b9c-9546-abe78a4f4248'
        };
		
        async function fetch_case_misp_object(){
            if (props.case_misp_objects_list !== null) {
                // Data is managed by the parent; signal it to refresh
                emit('modif_misp_objects', true)
                return
            }
            const res = await fetch("/case/"+props.case_id+"/get_case_misp_object")
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

        function scroll_to_task(task_id){
            const el = document.getElementById('task-' + task_id)
            if (el) {
                el.scrollIntoView({ behavior: 'smooth', block: 'start' })
            } else {
                // fallback: navigate to task collapse
                window.location.hash = 'task-' + task_id
            }
        }

        function toggleAssignTasks(misp_object){
            if(assigningTasks.value === misp_object.object_id){
                assigningTasks.value = null
                return
            }
            // initialize selected ids from object.tasks if present
            assign_task_state.value[misp_object.object_id] = (misp_object.tasks || []).map(t => t.id)
            assigningTasks.value = misp_object.object_id
        }

        async function saveAssignTasks(misp_object_id){
            const sel = assign_task_state.value[misp_object_id] || []
            if (!sel.length) {
                create_message("Select at least one task", "warning-subtle")
                return
            }
            const res = await fetch(`/case/${props.case_id}/misp_object/${misp_object_id}/set_tasks`, {
                method: 'POST',
                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                body: JSON.stringify({ task_ids: sel })
            })
            if (await res.status == 200) {
                // Refresh the case objects list so the per-object task badges update.
                await fetch_case_misp_object()

                // Also refresh `misp_object_links` on every affected task so the
                // task header badge ("MISP Objects (N)") and the task's MISP-objects
                // tab reflect the new assignment immediately, without a page reload.
                if (props.cases_info && Array.isArray(props.cases_info.tasks)) {
                    const new_ids = new Set(sel.map(Number))
                    const affected = new Set(new_ids)
                    for (const t of props.cases_info.tasks) {
                        const links = t.misp_object_links || []
                        if (links.some(l => l.misp_object_id === misp_object_id)) {
                            affected.add(t.id)
                        }
                    }
                    await Promise.all([...affected].map(async tid => {
                        const r = await fetch(`/case/${props.case_id}/task/${tid}/get_misp_object_links`)
                        if (r.status === 200) {
                            const data = await r.json()
                            const task = props.cases_info.tasks.find(t => t.id === tid)
                            if (task) task.misp_object_links = data.misp_object_links || []
                        }
                    }))
                }

                assigningTasks.value = null
                emit('modif_misp_objects', true)
            }
            display_toast(res)
        }

        function toggleAddObject() {
            showAddObject.value = !showAddObject.value
            if (!showAddObject.value) {
                resetAddObjectForm()
            }
        }

        function resetAddObjectForm() {
            try {
                if (hasSelect2) {
                    const sel = document.getElementById('new-object-task-select')
                    if (sel && $(sel).data('select2')) $(sel).select2('destroy')
                }
            } catch(e) {}
            new_object_task_ids.value = []
            activeTemplate.value = empty_template()
            selectedQuickTemplate.value = ''
            newObjectAttrState.value = { relation_type_combo: '', value: '', first_seen: '', last_seen: '', comment: '', ids_flag: false, disable_correlation: true }
            list_attr.value = []
            objectAttrCount.value = 0
            editingObjectAttrId.value = null
        }

        function cancelAddObject() {
            showAddObject.value = false
            resetAddObjectForm()
        }

        function addObjectAttribute() {
            let s = newObjectAttrState.value
            if (!s.value) {
                create_message("Need to add a value", "warning-subtle")
                return
            }
            if (!s.relation_type_combo) {
                create_message("Need to select a type", "warning-subtle")
                return
            }
            let parts = s.relation_type_combo.split('::')
            objectAttrCount.value += 1
            list_attr.value.push({
                id: objectAttrCount.value, value: s.value,
                object_relation: parts[0], type: parts[1],
                first_seen: s.first_seen, last_seen: s.last_seen,
                comment: s.comment, ids_flag: s.ids_flag,
                disable_correlation: s.disable_correlation
            })
            s.value = ''
            s.comment = ''
            s.first_seen = ''
            s.last_seen = ''
            s.ids_flag = false
            s.disable_correlation = true
        }

        function removeObjectAttribute(attr_id) {
            let idx = list_attr.value.findIndex(a => a.id === attr_id)
            if (idx !== -1) {
                list_attr.value.splice(idx, 1)
            }
        }

        function startEditObjectAttr(attr) {
            editingObjectAttrId.value = attr.id
            editObjectAttrState.value = {
                value: attr.value,
                relation_type_combo: attr.object_relation + '::' + attr.type,
                first_seen: attr.first_seen,
                last_seen: attr.last_seen,
                comment: attr.comment,
                ids_flag: attr.ids_flag,
                disable_correlation: attr.disable_correlation
            }
        }

        function cancelEditObjectAttr() {
            editingObjectAttrId.value = null
            editObjectAttrState.value = {}
        }

        function saveEditObjectAttr(attr_id) {
            let s = editObjectAttrState.value
            if (!s.value) { create_message("Need to add a value", "warning-subtle"); return }
            if (!s.relation_type_combo) { create_message("Need to select a type", "warning-subtle"); return }
            let parts = s.relation_type_combo.split('::')
            let idx = list_attr.value.findIndex(a => a.id === attr_id)
            if (idx !== -1) {
                list_attr.value.splice(idx, 1, {
                    id: attr_id, value: s.value,
                    object_relation: parts[0], type: parts[1],
                    first_seen: s.first_seen, last_seen: s.last_seen,
                    comment: s.comment, ids_flag: s.ids_flag,
                    disable_correlation: s.disable_correlation
                })
            }
            cancelEditObjectAttr()
        }

        async function save_changes() {
            if(list_attr.value.length){
                const res = await fetch("/case/"+props.case_id+"/create_misp_object", {
                    method: "POST",
                    headers: {
                        "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                    },
                    body: JSON.stringify({
                        "object-template": activeTemplate.value,
                        "attributes": list_attr.value,
                        "task_ids": new_object_task_ids.value
                    })
                });
                if(await res.status==200){
                    await fetch_case_misp_object()
                    cancelAddObject()
                    emit("modif_misp_objects", true)
                }
                display_toast(res)
            }else{
                create_message("Need to add an attribute", "warning-subtle")
            }
        }

        function toggleCompactView() {
            compactView.value = !compactView.value
        }

        function toggleTabView() {
            tabView.value = !tabView.value
            activeTabIdx.value = 0
        }

        function copyUuidToClipboard() {
            const text = activeTemplate.value && activeTemplate.value.uuid
            if (!text) return
            if (navigator.clipboard && navigator.clipboard.writeText) {
                navigator.clipboard.writeText(text).catch(() => fallback_copy(text))
            } else {
                fallback_copy(text)
            }
        }

        function fallback_copy(text) {
            const ta = document.createElement('textarea')
            ta.value = text
            ta.style.position = 'fixed'
            ta.style.opacity = '0'
            document.body.appendChild(ta)
            ta.select()
            try { document.execCommand('copy') } catch (e) {}
            document.body.removeChild(ta)
        }

        async function delete_object(object_id){
            const ok = await confirmDelete({
                title: 'Delete MISP object?',
                message: 'Are you sure you want to delete this MISP object? This cannot be undone.'
            })
            if (!ok) return
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
                display_toast({message: "Attribute not found", toast_class: "danger-subtle"})
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

            const ok = await confirmDelete({
                title: 'Delete attribute?',
                message: 'Are you sure you want to delete this attribute? This cannot be undone.'
            })
            if (!ok) return

            const res = await fetch("/case/"+props.case_id+"/misp_object/"+misp_object_id+"/delete_attribute/"+attribute_id)
            if(await res.status==200 ){
                case_misp_objects.value[loc[0]].attributes.splice(loc[1], 1)
            }
            display_toast(res)
        }

        function enterEditMode(attribute, template_uuid) {
            activeTemplateAttr.value = find_object_template(template_uuid, attribute)
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
        }

        function cancelEdit() {
            editingAttrId.value = null
            editState.value = {}
        }

        function startAddingAttribute(object_id, template_uuid) {
            addingAttrToObject.value = object_id
            activeTemplateAttr.value = find_object_template(template_uuid)
            const firstTemplateAttr = template_attributes(activeTemplateAttr.value)[0]
            newAttrState.value = {
                value: '',
                relation_type_combo: firstTemplateAttr ?
                    firstTemplateAttr.name + '::' + firstTemplateAttr.misp_attribute : '',
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
                activeTemplate.value = find_object_template(defaultObjectTemplates[newValue])
            }
        });

        async function open_link_modal(misp_object) {
            link_modal_object.value = misp_object
            await nextTick()
            await link_modal_ref.value?.on_show()
            const el = document.getElementById('modal-link-object')
            if (el) new bootstrap.Modal(el).show()
        }

        async function on_link_updated() {
            // Refresh objects so synced_instances badges update
            await fetch_case_misp_object()
            // Keep the modal open with the refreshed object — will also be handled by the prop watch
            if (link_modal_object.value && props.case_misp_objects_list === null) {
                const refreshed = case_misp_objects.value.find(o => o.object_id === link_modal_object.value.object_id)
                if (refreshed) link_modal_object.value = refreshed
            }
        }

        // When parent provides case_misp_objects_list, sync it into local ref
        watch(() => props.case_misp_objects_list, (val) => {
            if (val !== null) {
                case_misp_objects.value = val
                // Refresh link modal object reference if open
                if (link_modal_object.value) {
                    const refreshed = val.find(o => o.object_id === link_modal_object.value.object_id)
                    if (refreshed) link_modal_object.value = refreshed
                }
            }
        }, { immediate: true })

        // Refresh case-side data (task badges per MISP object) when a task
        // independently links/unlinks one of its MISP objects via the task UI.
        const onTaskMispLinkChanged = () => { fetch_case_misp_object() }

		onMounted(() => {
            if (props.case_misp_objects_list === null) fetch_case_misp_object()
            fetch_misp_object()
            window.addEventListener('task-misp-link-changed', onTaskMispLinkChanged)
        })

        onUnmounted(() => {
            window.removeEventListener('task-misp-link-changed', onTaskMispLinkChanged)
        })

		return {
            case_misp_objects,
            misp_objects,
            activeTemplate,
            activeTemplateAttr,
            template_attributes,
            selectedQuickTemplate,
            list_attr,
            showAddObject,
            newObjectAttrState,
            editingObjectAttrId,
            editObjectAttrState,
            toggleAddObject,
            cancelAddObject,
            addObjectAttribute,
            can_add_new_object_attr,
            can_save_edit_object_attr,
            can_save_object,
            can_save_new_attr,
            can_save_edit_attr,
            removeObjectAttribute,
            startEditObjectAttr,
            cancelEditObjectAttr,
            saveEditObjectAttr,
            save_changes,
            copyUuidToClipboard,
            delete_object,
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
            toggleCompactView,
            tabView,
            activeTabIdx,
            toggleTabView,
            search_query,
            type_filter,
            show_unsynced_only,
            current_page,
            per_page,
            filtered_objects,
            paged_objects,
            total_pages,
            object_type_options,
            link_modal_object,
            link_modal_ref,
            open_link_modal,
            on_link_updated,
            on_link_updated,
            can_edit,
            assigningTasks,
            assign_task_state,
            new_object_task_ids,
            toggleAssignTasks,
            saveAssignTasks,
            scroll_to_task
		}
    },

	template: `
    <div class="mb-1">
        <button v-if="can_edit" class="btn btn-primary" title="Add a new object" @click="toggleAddObject()">
            <i class="fa-solid fa-plus"></i> <i class="fa-solid fa-cubes"></i>
        </button>
        <a v-if="cases_info && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)" 
           type="button" class="btn btn-secondary ms-3" title="Analyze misp-objects"
           :href="'/analyzer/misp-modules?case_id='+case_id+'&misp_object=True'">
            <i class="fa-solid fa-magnifying-glass"></i>
        </a>
        <button type="button" class="btn btn-outline-secondary ms-3" @click="toggleCompactView()" :title="compactView ? 'Show all columns' : 'Show compact view'">
            <i :class="compactView ? 'fa-solid fa-expand' : 'fa-solid fa-compress'"></i>
            <span class="d-none d-sm-inline ms-1">[[ compactView ? 'Detailed' : 'Compact' ]]</span>
        </button>
        <button type="button" class="btn btn-outline-secondary ms-2" @click="toggleTabView()" :title="tabView ? 'Switch to card view' : 'Switch to tab view'">
            <i :class="tabView ? 'fa-solid fa-table-cells-large' : 'fa-solid fa-folder'"></i>
            <span class="d-none d-sm-inline ms-1">[[ tabView ? 'Cards' : 'Tabs' ]]</span>
        </button>
    </div>

    <!-- Spotlight banner -->
    <div v-if="spotlight_id != null" class="alert alert-info d-flex align-items-center mb-2 mt-2 py-2" role="alert">
        <i class="fa-solid fa-magnifying-glass me-2"></i>
        <span>Showing only the selected object.</span>
        <button type="button" class="btn btn-sm btn-outline-info ms-auto" @click="$emit('clear_spotlight')">
            <i class="fa-solid fa-xmark me-1"></i>Show all objects
        </button>
    </div>

    <!-- Inline panel -->
    <div v-if="showAddObject" class="card mb-3 mt-2">
        <div class="card-header d-flex justify-content-between align-items-center">
            <span class="fw-bold">Add object</span>
            <button type="button" class="btn-close" @click="cancelAddObject()" aria-label="Close"></button>
        </div>
        <div class="card-body">
            <div class="btn-group mb-3" role="group">
                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                    v-bind:value="'domain/ip'" name="btnradio-inline" id="btn-domain-ip-inline" autocomplete="off">
                <label class="btn btn-outline-primary" for="btn-domain-ip-inline">
                    <i class="fa-solid fa-network-wired fa-lg mt-2" />
                    <p class="mb-0 mt-1" style="font-size: 0.8rem;">Domain/IP</p>
                </label>
                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                    v-bind:value="'url/domain'" name="btnradio-inline" id="btn-url-domain-inline" autocomplete="off">
                <label class="btn btn-outline-primary" for="btn-url-domain-inline">
                    <i class="fa-solid fa-link fa-lg mt-2" />
                    <p class="mb-0 mt-1" style="font-size: 0.8rem;">URL/Domain</p>
                </label>
                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                    v-bind:value="'file/hash'" name="btnradio-inline" id="btn-file-hash-inline" autocomplete="off">
                <label class="btn btn-outline-primary" for="btn-file-hash-inline">
                    <i class="fa-solid fa-file-lines fa-lg mt-2" />
                    <p class="mb-0 mt-1" style="font-size: 0.8rem;">File/Hash</p>
                </label>
                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                    v-bind:value="'vulnerability'" name="btnradio-inline" id="btn-vulnerability-inline" autocomplete="off">
                <label class="btn btn-outline-primary" for="btn-vulnerability-inline">
                    <i class="fa-solid fa-skull-crossbones fa-lg mt-2" />
                    <p class="mb-0 mt-1" style="font-size: 0.8rem;">Vulnerability</p>
                </label>
                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                    v-bind:value="'financial'" name="btnradio-inline" id="btn-financial-inline" autocomplete="off">
                <label class="btn btn-outline-primary" for="btn-financial-inline">
                    <i class="fa-solid fa-money-check-dollar fa-lg mt-2" />
                    <p class="mb-0 mt-1" style="font-size: 0.8rem;">Financial</p>
                </label>
                <input type="radio" class="btn-check" v-model="selectedQuickTemplate"
                    v-bind:value="'personal'" name="btnradio-inline" id="btn-person-inline" autocomplete="off">
                <label class="btn btn-outline-primary" for="btn-person-inline">
                    <i class="fa-solid fa-person fa-lg mt-2" />
                    <p class="mb-0 mt-1" style="font-size: 0.8rem;">Personal</p>
                </label>
            </div>

            <div class="mb-3">
                <label class="form-label">Or select a template from the list:</label>
                <select class="form-select" @change="activeTemplate = misp_objects.find(o => o.uuid === $event.target.value) || { requiredOneOf: [] }">
                    <option value="">--</option>
                    <template v-for="object in misp_objects">
                        <option :value="object.uuid" :selected="activeTemplate.uuid === object.uuid">[[object.name]]</option>
                    </template>
                </select>
            </div>

            <div v-if="activeTemplate.uuid">
                <div class="mb-3">
                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Assign to tasks (optional)</label>
                    <select id="new-object-task-select" class="form-select form-select-sm" multiple data-placeholder="Select tasks...">
                        <option v-for="t in (cases_info && cases_info.tasks ? cases_info.tasks : [])" :value="t.id">[[ t.title ]]</option>
                    </select>
                </div>
                <div class="mb-2">
                    <span class="fw-bold">[[ activeTemplate.name ]] </span>
                    <span class="badge bg-light text-dark">[[activeTemplate.uuid]] </span>
                    <button type="button" class="btn btn-sm"><i class="text-primary fa-solid fa-copy"
                            @click="copyUuidToClipboard" /></button>
                    <span class="badge bg-secondary">[[ activeTemplate.meta_category ]]</span>
                    <div class="text-muted" style="font-size: 0.85rem;">[[ activeTemplate.description ]]</div>
                    <div v-if="activeTemplate.requiredOneOf && activeTemplate.requiredOneOf.length" class="text-muted" style="font-size: 0.8rem;">
                        <i class="fa-solid fa-circle-info me-1"></i>Required (at least one): [[ activeTemplate.requiredOneOf.join(', ') ]]
                    </div>
                </div>

                <hr>

                <h6 class="fw-bold">Add attributes</h6>
                <div class="row g-2 mb-2">
                    <div class="col-md-3">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type <span class="text-danger">*</span></label>
                        <select v-model="newObjectAttrState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                            <option value="">-- select --</option>
                            <template v-for="attr in template_attributes(activeTemplate)">
                                <option :value="attr.name + '::' + attr.misp_attribute">[[attr.name]]::[[attr.misp_attribute]]</option>
                            </template>
                        </select>
                    </div>
                    <div class="col-md-3">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value <span class="text-danger">*</span></label>
                        <input v-model="newObjectAttrState.value" class="form-control form-control-sm" type="text" placeholder="Value" style="font-size: 0.875rem;">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">First Seen</label>
                        <input v-model="newObjectAttrState.first_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                    </div>
                    <div class="col-md-2">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Last Seen</label>
                        <input v-model="newObjectAttrState.last_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                    </div>
                    <div class="col-md-1">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">IDS</label>
                        <div class="form-check mt-1">
                            <input v-model="newObjectAttrState.ids_flag" type="checkbox" class="form-check-input">
                        </div>
                    </div>
                    <div class="col-md-1">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;" title="Disable correlation">Corr.</label>
                        <div class="form-check mt-1">
                            <input v-model="newObjectAttrState.disable_correlation" type="checkbox" class="form-check-input" title="Disable correlation">
                        </div>
                    </div>
                </div>
                <div class="row g-2 mb-3">
                    <div class="col-md-6">
                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Comment</label>
                        <input v-model="newObjectAttrState.comment" class="form-control form-control-sm" type="text" placeholder="Comment" style="font-size: 0.875rem;">
                    </div>
                    <div class="col-md-6 d-flex align-items-end">
                        <button type="button" class="btn btn-primary btn-sm" :disabled="!can_add_new_object_attr"
                                :title="can_add_new_object_attr ? 'Add attribute' : 'Enter a value and select an object relation & type first'"
                                @click="addObjectAttribute()">
                            <i class="fa-solid fa-plus me-1"></i>Add attribute
                        </button>
                    </div>
                </div>

                <!-- Added attributes table -->
                <div v-if="list_attr.length" class="table-responsive mb-3">
                    <table class="table table-sm">
                        <thead>
                            <tr>
                                <th>Object Relation</th>
                                <th>Type</th>
                                <th>Value</th>
                                <th>First Seen</th>
                                <th>Last Seen</th>
                                <th>IDS</th>
                                <th>Comment</th>
                                <th></th>
                            </tr>
                        </thead>
                        <tbody>
                            <tr v-for="attr in list_attr" :key="attr.id">
                                <template v-if="editingObjectAttrId !== attr.id">
                                    <td>[[attr.object_relation]]</td>
                                    <td>[[attr.type]]</td>
                                    <td :title="attr.value">[[ attr.value && attr.value.length > 256 ? attr.value.slice(0, 256) + '…' : attr.value ]]</td>
                                    <td>[[attr.first_seen || '-']]</td>
                                    <td>[[attr.last_seen || '-']]</td>
                                    <td>[[attr.ids_flag]]</td>
                                    <td>[[attr.comment || '-']]</td>
                                    <td style="white-space: nowrap;">
                                        <button type="button" class="btn btn-primary btn-sm" @click="startEditObjectAttr(attr)" title="Edit">
                                            <i class="fa-solid fa-fw fa-pen-to-square"></i>
                                        </button>
                                        <button type="button" class="btn btn-danger btn-sm" @click="removeObjectAttribute(attr.id)" title="Remove">
                                            <i class="fa-solid fa-fw fa-trash"></i>
                                        </button>
                                    </td>
                                </template>
                                <template v-else>
                                    <td colspan="8" style="padding: 1rem;">
                                        <div class="row g-2 mb-2">
                                            <div class="col-md-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type <span class="text-danger">*</span></label>
                                                <select v-model="editObjectAttrState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                    <template v-for="a in template_attributes(activeTemplate)">
                                                        <option :value="a.name + '::' + a.misp_attribute">[[a.name]]::[[a.misp_attribute]]</option>
                                                    </template>
                                                </select>
                                            </div>
                                            <div class="col-md-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value <span class="text-danger">*</span></label>
                                                <textarea v-model="editObjectAttrState.value" class="form-control form-control-sm" rows="2" style="font-size: 0.875rem; resize: vertical;"></textarea>
                                            </div>
                                            <div class="col-md-2">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">First Seen</label>
                                                <input v-model="editObjectAttrState.first_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                                            </div>
                                            <div class="col-md-2">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Last Seen</label>
                                                <input v-model="editObjectAttrState.last_seen" class="form-control form-control-sm" type="datetime-local" style="font-size: 0.875rem;">
                                            </div>
                                            <div class="col-md-1">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">IDS</label>
                                                <div class="form-check mt-1">
                                                    <input v-model="editObjectAttrState.ids_flag" type="checkbox" class="form-check-input">
                                                </div>
                                            </div>
                                            <div class="col-md-1">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;" title="Disable correlation">Corr.</label>
                                                <div class="form-check mt-1">
                                                    <input v-model="editObjectAttrState.disable_correlation" type="checkbox" class="form-check-input" title="Disable correlation">
                                                </div>
                                            </div>
                                        </div>
                                        <div class="row g-2 mb-2">
                                            <div class="col-md-6">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Comment</label>
                                                <input v-model="editObjectAttrState.comment" class="form-control form-control-sm" type="text" placeholder="Comment" style="font-size: 0.875rem;">
                                            </div>
                                        </div>
                                        <div class="d-flex gap-2">
                                            <button type="button" class="btn btn-secondary btn-sm" @click="cancelEditObjectAttr()">
                                                Cancel
                                            </button>
                                            <button type="button" class="btn btn-primary btn-sm" :disabled="!can_save_edit_object_attr"
                                                    :title="can_save_edit_object_attr ? 'Save' : 'A value and object relation & type are required'"
                                                    @click="saveEditObjectAttr(attr.id)">
                                                Save
                                            </button>
                                        </div>
                                    </td>
                                </template>
                            </tr>
                        </tbody>
                    </table>
                </div>

                <div v-if="!can_save_object" class="text-muted mb-2" style="font-size: 0.85rem;">
                    <i class="fa-solid fa-circle-info me-1"></i>Add at least one attribute before saving the object.
                </div>
                <div class="d-flex gap-2">
                    <button type="button" class="btn btn-secondary" @click="cancelAddObject()">
                        Cancel
                    </button>
                    <button type="button" class="btn btn-primary" :disabled="!can_save_object"
                            :title="can_save_object ? 'Save object' : 'Add at least one attribute first'"
                            @click="save_changes()">
                        Save
                    </button>
                </div>
            </div>
        </div>
    </div>

    <div class="row g-2 align-items-end mb-2 mt-2">
        <div class="col-md-5">
            <div class="input-group input-group-sm">
                <span class="input-group-text"><i class="fa-solid fa-search"></i></span>
                <input v-model="search_query" class="form-control" type="text" placeholder="Search objects by name or attribute value…">
                <button v-if="search_query" class="btn btn-outline-secondary" type="button" @click="search_query=''"><i class="fa-solid fa-xmark"></i></button>
            </div>
        </div>
        <div class="col-md-3">
            <select v-model="type_filter" class="form-select form-select-sm">
                <option value="">All types</option>
                <option v-for="t in object_type_options" :key="t" :value="t">[[ t ]]</option>
            </select>
        </div>
        <div class="col-auto">
            <button type="button"
                    :class="['btn btn-sm', show_unsynced_only ? 'btn-warning' : 'btn-outline-secondary']"
                    @click="show_unsynced_only = !show_unsynced_only"
                    title="Show only objects not yet synced to any MISP instance">
                <i class="fa-solid fa-filter me-1"></i>Unsynced only
            </button>
        </div>
        <div class="col text-muted small">
            [[ filtered_objects.length ]] object(s)
            <span v-if="search_query || type_filter || show_unsynced_only"> matching filter</span>
        </div>
    </div>

    <template v-if="!tabView">
        <div v-for="misp_object, key_obj in paged_objects" :key="misp_object.object_id" class="card mb-2">
            <!-- Card header: name + badges + action buttons -->
            <div class="card-header d-flex align-items-center justify-content-between py-2 px-3">
                <div class="d-flex align-items-center gap-2 flex-wrap">
                    <button class="btn btn-link p-0 fw-semibold text-dark text-decoration-none"
                            type="button" data-bs-toggle="collapse"
                            :data-bs-target="'#collapse-'+key_obj" aria-expanded="true">
                        <i class="fa-solid fa-cube me-1 text-secondary fa-sm"></i>[[ misp_object.object_name ]]
                    </button>
                    <template v-if="misp_object.synced_instances && misp_object.synced_instances.length">
                        <span v-for="si in misp_object.synced_instances" :key="si.instance_id"
                            class="badge bg-info text-dark"
                            :title="'Synced with ' + si.instance_name + ' — remote UUID: ' + si.object_uuid">
                            <i class="fa-solid fa-cloud me-1 fa-sm"></i>[[ si.instance_name ]]
                        </span>
                    </template>
                    <template v-if="misp_object.tasks && misp_object.tasks.length">
                        <span v-for="t in misp_object.tasks" :key="t.id"
                            class="badge bg-secondary"
                            style="cursor:pointer;"
                            :title="'Go to task: ' + t.title"
                            @click.stop="scroll_to_task(t.id)">
                            <i class="fa-solid fa-list-check me-1 fa-sm"></i>[[ t.title ]]
                        </span>
                    </template>
                </div>
                <div class="d-flex gap-1">
                    <button v-if="can_edit" type="button" class="btn btn-sm btn-outline-primary" title="Add attribute"
                            @click="startAddingAttribute(misp_object.object_id, misp_object.object_uuid)">
                        <i class="fa-solid fa-plus fa-sm"></i>
                    </button>
                    <button type="button" class="btn btn-sm btn-outline-secondary" title="Link to remote MISP object"
                            @click="open_link_modal(misp_object)">
                        <i class="fa-solid fa-link fa-sm"></i>
                    </button>
                    <button v-if="can_edit" type="button" class="btn btn-sm btn-outline-secondary"
                            @click="toggleAssignTasks(misp_object)" title="Assign tasks">
                        <i class="fa-solid fa-tasks fa-sm"></i>
                    </button>
                    <button v-if="can_edit" type="button" class="btn btn-sm btn-outline-danger"
                            @click="delete_object(misp_object.object_id)" title="Delete object">
                        <i class="fa-solid fa-trash fa-sm"></i>
                    </button>
                </div>
            </div>

            <div :id="'collapse-'+key_obj" class="collapse show">
                <!-- Task assign panel -->
                <div v-if="assigningTasks === misp_object.object_id" class="px-3 pt-2 pb-2 border-bottom bg-light">
                    <div v-if="cases_info && cases_info.tasks && cases_info.tasks.length">
                        <div class="d-flex flex-wrap gap-3 mb-2">
                            <div v-for="task in cases_info.tasks" :key="task.id" class="form-check form-check-inline m-0">
                                <input class="form-check-input" type="checkbox"
                                    :id="'assign-'+misp_object.object_id+'-'+task.id"
                                    :value="task.id" v-model="assign_task_state[misp_object.object_id]">
                                <label class="form-check-label small" :for="'assign-'+misp_object.object_id+'-'+task.id">[[ task.title ]]</label>
                            </div>
                        </div>
                        <button class="btn btn-primary btn-sm" @click="saveAssignTasks(misp_object.object_id)">Save</button>
                        <button class="btn btn-secondary btn-sm ms-1" @click="assigningTasks = null">Cancel</button>
                    </div>
                    <div v-else class="text-muted small">No tasks available in this case.</div>
                </div>

                <!-- Attributes table -->
                <div class="table-responsive">
                    <table class="table table-sm table-hover mb-0">
                        <thead class="table-light">
                            <tr>
                                <th class="ps-3">Value</th>
                                <th>Relation</th>
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
                            <tr v-for="attribute, key_attr in misp_object.attributes">
                                <!-- Display mode -->
                                <template v-if="editingAttrId !== attribute.id">
                                    <td class="ps-3">[[attribute.value]]</td>
                                    <td><span class="badge bg-light text-dark border">[[attribute.object_relation]]</span></td>
                                    <td class="text-muted small align-middle">[[attribute.type]]</td>
                                    <td v-show="!compactView" class="small">
                                        <template v-if="attribute.first_seen">[[attribute.first_seen]]</template>
                                        <span v-else class="text-muted">—</span>
                                    </td>
                                    <td v-show="!compactView" class="small">
                                        <template v-if="attribute.last_seen">[[attribute.last_seen]]</template>
                                        <span v-else class="text-muted">—</span>
                                    </td>
                                    <td v-show="!compactView">
                                        <i v-if="attribute.ids_flag" class="fa-solid fa-check text-success fa-sm"></i>
                                        <span v-else class="text-muted">—</span>
                                    </td>
                                    <td v-show="!compactView">
                                        <template v-if="attribute.disable_correlation">
                                            <i class="fa-solid fa-link-slash text-muted fa-sm" title="Correlation disabled"></i>
                                        </template>
                                        <template v-else>
                                            <template v-for="(cid, idx) in attribute.correlation_list">
                                                <template v-if="idx < 4">
                                                    <a :href="'/case/'+cid" class="badge bg-light text-dark me-1" title="Open case [[cid]]">Case [[cid]]</a>
                                                </template>
                                            </template>
                                            <button v-if="attribute.correlation_list.length > 4" class="btn btn-link p-0 ms-1 small" type="button"
                                                    data-bs-toggle="collapse"
                                                    :data-bs-target="'#corr-'+misp_object.object_id+'-'+attribute.id"
                                                    aria-expanded="false">
                                                [[ attribute.correlation_list.length - 4 ]] more
                                            </button>
                                            <div class="collapse mt-1" :id="'corr-'+misp_object.object_id+'-'+attribute.id">
                                                <template v-for="(cid, idx) in attribute.correlation_list">
                                                    <template v-if="idx >= 4">
                                                        <a :href="'/case/'+cid" class="badge bg-light text-dark me-1">Case [[cid]]</a>
                                                    </template>
                                                </template>
                                            </div>
                                        </template>
                                    </td>
                                    <td v-show="!compactView" class="small text-muted">
                                        <template v-if="attribute.comment">[[attribute.comment]]</template>
                                        <span v-else>—</span>
                                    </td>
                                    <td class="text-end pe-2" style="white-space:nowrap;">
                                        <button v-if="can_edit" type="button" class="btn btn-link btn-sm p-0 me-2 text-primary" title="Edit attribute"
                                                @click="enterEditMode(attribute, misp_object.object_uuid)">
                                            <i class="fa-solid fa-pen-to-square fa-sm"></i>
                                        </button>
                                        <button v-if="can_edit" type="button" class="btn btn-link btn-sm p-0 text-danger" title="Delete attribute"
                                                @click="delete_attribute(attribute.id, misp_object.object_id)">
                                            <i class="fa-solid fa-trash fa-sm"></i>
                                        </button>
                                    </td>
                                </template>

                                <!-- Edit mode -->
                                <template v-else>
                                    <td :colspan="compactView ? 4 : 9" class="p-3 bg-light">
                                        <div class="mb-3">
                                            <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value</label>
                                            <input v-model="editState.value" class="form-control form-control-sm" type="text" style="font-size: 0.875rem;">
                                        </div>
                                        <div class="row g-2 mb-3">
                                            <div class="col-md-4">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type</label>
                                                <select v-model="editState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                    <template v-for="attr in template_attributes(activeTemplateAttr)">
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
                                            <button type="button" class="btn btn-secondary btn-sm" @click="cancelEdit()">Cancel</button>
                                            <button type="button" class="btn btn-primary btn-sm" @click="saveInlineEdit(misp_object.object_id, attribute.id)">Save</button>
                                        </div>
                                    </td>
                                </template>
                            </tr>

                            <!-- Add new attribute row -->
                            <tr v-if="addingAttrToObject === misp_object.object_id">
                                <td :colspan="compactView ? 4 : 9" class="p-3 bg-light">
                                    <div class="mb-3">
                                        <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value</label>
                                        <input v-model="newAttrState.value" class="form-control form-control-sm" type="text" placeholder="Value" style="font-size: 0.875rem;">
                                    </div>
                                    <div class="row g-2 mb-3">
                                        <div class="col-md-4">
                                            <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type</label>
                                            <select v-model="newAttrState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                <template v-for="attr in template_attributes(activeTemplateAttr)">
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
                                        <button type="button" class="btn btn-secondary btn-sm" @click="cancelAddAttribute()">Cancel</button>
                                        <button type="button" class="btn btn-primary btn-sm" @click="saveNewAttribute(misp_object.object_id)">Add</button>
                                    </div>
                                </td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        </div>

        <nav v-if="total_pages > 1" class="mt-2" aria-label="Objects pagination">
            <ul class="pagination pagination-sm justify-content-center">
                <li class="page-item" :class="{disabled: current_page === 1}">
                    <button class="page-link" @click="current_page--">&laquo;</button>
                </li>
                <li v-for="p in total_pages" :key="p" class="page-item" :class="{active: p === current_page}">
                    <button class="page-link" @click="current_page = p">[[ p ]]</button>
                </li>
                <li class="page-item" :class="{disabled: current_page === total_pages}">
                    <button class="page-link" @click="current_page++">&raquo;</button>
                </li>
            </ul>
        </nav>
    </template>

    <!-- Tab view -->
    <template v-else>
        <div v-if="filtered_objects.length === 0" class="text-muted p-2"><i>No objects match the current filter.</i></div>
        <template v-else>
            <ul class="nav nav-tabs mb-0" style="flex-wrap: wrap;">
                <li v-for="(misp_object, idx) in filtered_objects" :key="misp_object.object_id" class="nav-item flex-shrink-0">
                    <button class="nav-link py-1 px-3" :class="{active: activeTabIdx === idx}" @click="activeTabIdx = idx" type="button">
                        <i class="fa-solid fa-cube me-1 text-secondary fa-sm"></i>[[ misp_object.object_name ]]
                        <template v-if="misp_object.synced_instances && misp_object.synced_instances.length">
                            <i class="fa-solid fa-cloud ms-1 text-info" style="font-size:0.7rem;"></i>
                        </template>
                    </button>
                </li>
            </ul>
            <div class="tab-content border border-top-0 rounded-bottom">
                <div v-for="(misp_object, idx) in filtered_objects" :key="misp_object.object_id"
                     v-show="activeTabIdx === idx" class="tab-pane active show">
                    <!-- Tab pane header: badges + action buttons -->
                    <div class="d-flex align-items-center justify-content-between py-2 px-3 border-bottom">
                        <div class="d-flex align-items-center gap-2 flex-wrap">
                            <template v-if="misp_object.synced_instances && misp_object.synced_instances.length">
                                <span v-for="si in misp_object.synced_instances" :key="si.instance_id"
                                      class="badge bg-info text-dark"
                                      :title="'Synced with ' + si.instance_name + ' — remote UUID: ' + si.object_uuid">
                                    <i class="fa-solid fa-cloud me-1 fa-sm"></i>[[ si.instance_name ]]
                                </span>
                            </template>
                            <template v-if="misp_object.tasks && misp_object.tasks.length">
                                <span v-for="t in misp_object.tasks" :key="t.id"
                                      class="badge bg-secondary"
                                      style="cursor:pointer;"
                                      :title="'Go to task: ' + t.title"
                                      @click.stop="scroll_to_task(t.id)">
                                    <i class="fa-solid fa-list-check me-1 fa-sm"></i>[[ t.title ]]
                                </span>
                            </template>
                        </div>
                        <div class="d-flex gap-1">
                            <button v-if="can_edit" type="button" class="btn btn-sm btn-outline-primary" title="Add attribute"
                                    @click="startAddingAttribute(misp_object.object_id, misp_object.object_uuid)">
                                <i class="fa-solid fa-plus fa-sm"></i>
                            </button>
                            <button type="button" class="btn btn-sm btn-outline-secondary" title="Link to remote MISP object"
                                    @click="open_link_modal(misp_object)">
                                <i class="fa-solid fa-link fa-sm"></i>
                            </button>
                            <button v-if="can_edit" type="button" class="btn btn-sm btn-outline-secondary"
                                    @click="toggleAssignTasks(misp_object)" title="Assign tasks">
                                <i class="fa-solid fa-tasks fa-sm"></i>
                            </button>
                            <button v-if="can_edit" type="button" class="btn btn-sm btn-outline-danger"
                                    @click="delete_object(misp_object.object_id)" title="Delete object">
                                <i class="fa-solid fa-trash fa-sm"></i>
                            </button>
                        </div>
                    </div>
                    <!-- Task assign panel -->
                    <div v-if="assigningTasks === misp_object.object_id" class="px-3 pt-2 pb-2 border-bottom bg-light">
                        <div v-if="cases_info && cases_info.tasks && cases_info.tasks.length">
                            <div class="d-flex flex-wrap gap-3 mb-2">
                                <div v-for="task in cases_info.tasks" :key="task.id" class="form-check form-check-inline m-0">
                                    <input class="form-check-input" type="checkbox"
                                           :id="'tab-assign-'+misp_object.object_id+'-'+task.id"
                                           :value="task.id" v-model="assign_task_state[misp_object.object_id]">
                                    <label class="form-check-label small" :for="'tab-assign-'+misp_object.object_id+'-'+task.id">[[ task.title ]]</label>
                                </div>
                            </div>
                            <button class="btn btn-primary btn-sm"
                                            :disabled="!(assign_task_state[misp_object.object_id] && assign_task_state[misp_object.object_id].length)"
                                            :title="!(assign_task_state[misp_object.object_id] && assign_task_state[misp_object.object_id].length) ? 'Select at least one task' : ''"
                                            @click="saveAssignTasks(misp_object.object_id)">Save</button>
                            <button class="btn btn-secondary btn-sm ms-1" @click="assigningTasks = null">Cancel</button>
                        </div>
                        <div v-else class="text-muted small">No tasks available in this case.</div>
                    </div>
                    <!-- Attributes table -->
                    <div class="table-responsive">
                        <table class="table table-sm table-hover mb-0">
                            <thead class="table-light">
                                <tr>
                                    <th class="ps-3">Value</th>
                                    <th>Relation</th>
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
                                <tr v-for="attribute in misp_object.attributes" :key="attribute.id">
                                    <!-- Display mode -->
                                    <template v-if="editingAttrId !== attribute.id">
                                        <td :title="attribute.value">[[ attribute.value && attribute.value.length > 256 ? attribute.value.slice(0, 256) + '…' : attribute.value ]]</td>
                                        <td><span class="badge bg-light text-dark border">[[attribute.object_relation]]</span></td>
                                        <td class="text-muted small align-middle">[[attribute.type]]</td>
                                        <td v-show="!compactView" class="small">
                                            <template v-if="attribute.first_seen">[[attribute.first_seen]]</template>
                                            <span v-else class="text-muted">—</span>
                                        </td>
                                        <td v-show="!compactView" class="small">
                                            <template v-if="attribute.last_seen">[[attribute.last_seen]]</template>
                                            <span v-else class="text-muted">—</span>
                                        </td>
                                        <td v-show="!compactView">
                                            <i v-if="attribute.ids_flag" class="fa-solid fa-check text-success fa-sm"></i>
                                            <span v-else class="text-muted">—</span>
                                        </td>
                                        <td v-show="!compactView">
                                            <template v-if="attribute.disable_correlation">
                                                <i class="fa-solid fa-link-slash text-muted fa-sm" title="Correlation disabled"></i>
                                            </template>
                                            <template v-else>
                                                <template v-for="(c_cid, c_idx) in attribute.correlation_list">
                                                    <template v-if="c_idx < 4">
                                                        <a :href="'/case/'+c_cid" class="badge bg-light text-dark me-1" :title="'Open case '+c_cid">Case [[c_cid]]</a>
                                                    </template>
                                                </template>
                                                <button v-if="attribute.correlation_list.length > 4" class="btn btn-link p-0 ms-1 small" type="button"
                                                        data-bs-toggle="collapse"
                                                        :data-bs-target="'#tab-corr-'+misp_object.object_id+'-'+attribute.id"
                                                        aria-expanded="false">
                                                    [[ attribute.correlation_list.length - 4 ]] more
                                                </button>
                                                <div class="collapse mt-1" :id="'tab-corr-'+misp_object.object_id+'-'+attribute.id">
                                                    <template v-for="(c_cid, c_idx) in attribute.correlation_list">
                                                        <template v-if="c_idx >= 4">
                                                            <a :href="'/case/'+c_cid" class="badge bg-light text-dark me-1">Case [[c_cid]]</a>
                                                        </template>
                                                    </template>
                                                </div>
                                            </template>
                                        </td>
                                        <td v-show="!compactView" class="small text-muted">
                                            <template v-if="attribute.comment">[[attribute.comment]]</template>
                                            <span v-else>—</span>
                                        </td>
                                        <td class="text-end pe-2" style="white-space:nowrap;">
                                            <button v-if="can_edit" type="button" class="btn btn-link btn-sm p-0 me-2 text-primary" title="Edit attribute"
                                                    @click="enterEditMode(attribute, misp_object.object_uuid)">
                                                <i class="fa-solid fa-pen-to-square fa-sm"></i>
                                            </button>
                                            <button v-if="can_edit" type="button" class="btn btn-link btn-sm p-0 text-danger" title="Delete attribute"
                                                    @click="delete_attribute(attribute.id, misp_object.object_id)">
                                                <i class="fa-solid fa-trash fa-sm"></i>
                                            </button>
                                        </td>
                                    </template>
                                    <!-- Edit mode -->
                                    <template v-else>
                                        <td :colspan="compactView ? 4 : 9" class="p-3 bg-light">
                                            <div class="mb-3">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value</label>
                                                <textarea v-model="editState.value" class="form-control form-control-sm" rows="2" style="font-size: 0.875rem; resize: vertical;"></textarea>
                                            </div>
                                            <div class="row g-2 mb-3">
                                                <div class="col-md-4">
                                                    <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type</label>
                                                    <select v-model="editState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                        <template v-for="attr in template_attributes(activeTemplateAttr)">
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
                                                <button type="button" class="btn btn-secondary btn-sm" @click="cancelEdit()">Cancel</button>
                                                <button type="button" class="btn btn-primary btn-sm" @click="saveInlineEdit(misp_object.object_id, attribute.id)">Save</button>
                                            </div>
                                        </td>
                                    </template>
                                </tr>
                                <!-- Add new attribute row -->
                                <tr v-if="addingAttrToObject === misp_object.object_id">
                                    <td :colspan="compactView ? 4 : 9" class="p-3 bg-light">
                                        <div class="mb-3">
                                            <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Value</label>
                                            <input v-model="newAttrState.value" class="form-control form-control-sm" type="text" placeholder="Value" style="font-size: 0.875rem;">
                                        </div>
                                        <div class="row g-2 mb-3">
                                            <div class="col-md-4">
                                                <label class="form-label fw-semibold mb-1" style="font-size: 0.875rem;">Object Relation & Type</label>
                                                <select v-model="newAttrState.relation_type_combo" class="form-select form-select-sm" style="font-size: 0.875rem;">
                                                    <template v-for="attr in template_attributes(activeTemplateAttr)">
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
                                            <button type="button" class="btn btn-secondary btn-sm" title="Cancel"
                                            @click="cancelAddAttribute()">
                                                Cancel
                                            </button>
                                            <button type="button" class="btn btn-primary btn-sm" :disabled="!can_save_new_attr"
                                            :title="can_save_new_attr ? 'Add attribute' : 'A value and object relation & type are required'"
                                            @click="saveNewAttribute(misp_object.object_id)">
                                                Add
                                            </button>
                                        </div>
                                    </td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </template>
    </template>

    <!-- MispObjectLink modal (single shared instance) -->
    <misp-object-link
        v-if="link_modal_object"
        :ref="el => link_modal_ref = el"
        :case_id="case_id"
        :local_object="link_modal_object"
        modal_id="modal-link-object"
        @link_updated="on_link_updated">
    </misp-object-link>

    `
}
