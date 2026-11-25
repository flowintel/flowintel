import { display_toast, create_message } from '../toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
import connector_picker from '/static/js/components/connector_picker.js'
const { ref, computed } = Vue
export default {
    delimiters: ['[[', ']]'],
    components: { connector_picker },
    props: {
        case_task_connectors_list: Object,
        all_connectors_list: Object,
        icons: { type: Object, default: () => ({}) },   // connector type → icon file uuid
        modules: Object,
        is_case: Boolean,
        object_id: Number,
        cases_info: Object,
    },
    emits: ['case_connectors', 'note_change', 'task_note_added'],
    setup(props, { emit }) {
        const show_add_page = ref(false)
        const picked = ref([])              // ids of the instances being added
        const identifiers = ref({})         // instance id → identifier typed for it
        const saving = ref(false)
        const editing_id = ref(null)
        const editing_identifier = ref('')

        const can_edit_object = computed(() => {
            if (!props.cases_info) return false
            const permission = props.cases_info.permission || {}
            const present_in_case = props.cases_info.present_in_case
            if (permission.admin) return true
            if (!props.is_case && props.object_id && props.cases_info.tasks) {
                const task = props.cases_info.tasks.find(t => t.id === props.object_id)
                return !!(task && task.can_edit && present_in_case)
            }
            if (permission.read_only) return false
            return !!present_in_case
        })

        const linked = computed(() => Object.values(props.case_task_connectors_list || {}))
        const attached_ids = computed(() => linked.value.map(l => l.details && l.details.id).filter(id => id != null))

        const by_id = computed(() => {
            const m = new Map()
            for (const [type, list] of Object.entries(props.all_connectors_list || {}))
                for (const i of (list || [])) if (i) m.set(String(i.id), { ...i, type })
            return m
        })
        const picked_instances = computed(() => picked.value.map(id => by_id.value.get(String(id))).filter(Boolean))

        function icon_of(l) { return l.details && l.details.icon ? '/static/icons/' + l.details.icon : null }
        function type_icon(type) { return props.icons && props.icons[type] ? '/static/icons/' + props.icons[type] : null }
        function host(url) { try { return new URL(url).host } catch (e) { return url || '' } }
        function misp_link(l) {
            const u = l.details.url || ''
            return (u.endsWith('/') ? u : u + '/') + 'events/view/' + l.identifier
        }

        function open_add() { picked.value = []; identifiers.value = {}; show_add_page.value = true }
        function close_add() { show_add_page.value = false }

        async function save_connector() {
            if (!picked_instances.value.length || saving.value) return
            saving.value = true
            try {
                // the backend expects the instance name (Connector_Instance.name)
                const connectors = picked_instances.value.map(i => ({ name: i.name, identifier: identifiers.value[i.id] || '' }))
                const res = await fetch("/case/" + props.object_id + "/add_connector", {
                    method: 'POST',
                    headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                    body: JSON.stringify({ connectors })
                })
                if (res.status == 200) {
                    show_add_page.value = false
                    touchCaseLastModif(props.cases_info)
                    emit('case_connectors', true)
                }
                display_toast(res)
            } catch (e) {
                create_message('Error while adding connector', 'danger-subtle')
            } finally {
                saving.value = false
            }
        }

        async function remove_connector(element_instance_id) {
            const ok = await confirmDelete({
                title: 'Remove connector?',
                message: 'Are you sure you want to remove this connector? This cannot be undone.'
            })
            if (!ok) return
            const res = await fetch("/case/" + props.object_id + "/connectors/" + element_instance_id + "/remove_connector")
            if (res.status == 200) {
                const list = props.case_task_connectors_list
                const loc = list.findIndex(l => l.case_task_instance_id == element_instance_id)
                if (loc >= 0) list.splice(loc, 1)
                touchCaseLastModif(props.cases_info)
            }
            display_toast(res)
        }

        function start_edit(l) { editing_id.value = l.case_task_instance_id; editing_identifier.value = l.identifier || '' }
        function cancel_edit() { editing_id.value = null; editing_identifier.value = '' }

        async function edit_connector() {
            const res = await fetch("/case/" + props.object_id + "/connectors/" + editing_id.value + "/edit_connector", {
                method: "POST",
                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                body: JSON.stringify({ "identifier": editing_identifier.value })
            })
            if (res.status == 200) {
                for (const l of linked.value) if (l.case_task_instance_id == editing_id.value) l.identifier = editing_identifier.value
                touchCaseLastModif(props.cases_info)
                cancel_edit()
            }
            display_toast(res)
        }

        return {
            show_add_page, picked, identifiers, saving, editing_id, editing_identifier,
            can_edit_object, linked, attached_ids, picked_instances,
            icon_of, type_icon, host, misp_link, open_add, close_add,
            save_connector, remove_connector, start_edit, cancel_edit, edit_connector,
        }
    },
    template: `
    <div class="cconn">
        <!-- list of the linked instances -->
        <template v-if="!show_add_page">
            <div class="cconn-head">
                <span class="cconn-count">[[ linked.length ]] connector[[ linked.length === 1 ? '' : 's' ]] linked</span>
                <button v-if="can_edit_object" type="button" class="btn btn-primary btn-sm" @click="open_add" title="Link connector instances to this case">
                    <i class="fa-solid fa-plus me-1"></i>Add
                </button>
            </div>

            <div v-if="!linked.length" class="cconn-empty">
                <i class="fa-solid fa-plug"></i>
                <p>No connector linked yet.</p>
                <button v-if="can_edit_object" type="button" class="btn btn-outline-primary btn-sm" @click="open_add">Link a connector</button>
            </div>

            <ul v-else class="cconn-list">
                <li v-for="l in linked" :key="l.case_task_instance_id" class="cconn-row">
                    <span class="cconn-icon" :title="l.details.description">
                        <img v-if="icon_of(l)" :src="icon_of(l)" alt=""><i v-else class="fa-solid fa-plug"></i>
                    </span>
                    <span class="cconn-main">
                        <span class="cconn-name">[[ l.details.name ]]</span>
                        <a v-if="l.details.url" class="cconn-url" :href="l.details.url" target="_blank" rel="noopener" :title="l.details.url">[[ host(l.details.url) ]]</a>
                    </span>
                    <span class="cconn-ident">
                        <template v-if="editing_id === l.case_task_instance_id">
                            <input type="text" class="form-control form-control-sm" v-model="editing_identifier" placeholder="Identifier on the instance"
                                   @keyup.enter="edit_connector()" @keyup.escape="cancel_edit()" aria-label="Identifier on the instance">
                        </template>
                        <template v-else>
                            <span v-if="l.identifier" class="cconn-id-chip" title="Identifier used by the module on this instance"><i class="fa-solid fa-fingerprint"></i>[[ l.identifier ]]</span>
                            <span v-else class="cconn-id-none" title="No identifier set">No identifier</span>
                            <a v-if="l.is_misp_connector && l.identifier" class="cconn-ext" :href="misp_link(l)" target="_blank" rel="noopener" title="Open the MISP event on the remote instance">
                                <i class="fa-solid fa-arrow-up-right-from-square"></i>
                            </a>
                        </template>
                    </span>
                    <span v-if="can_edit_object" class="cconn-actions">
                        <template v-if="editing_id === l.case_task_instance_id">
                            <button type="button" class="btn btn-success btn-sm" @click="edit_connector()" title="Save the identifier"><i class="fa-solid fa-check"></i></button>
                            <button type="button" class="btn btn-outline-secondary btn-sm" @click="cancel_edit()" title="Cancel"><i class="fa-solid fa-xmark"></i></button>
                        </template>
                        <template v-else>
                            <button type="button" class="btn btn-outline-secondary btn-sm" @click="start_edit(l)" title="Edit the identifier"><i class="fa-solid fa-pen"></i></button>
                            <button type="button" class="btn btn-outline-danger btn-sm" @click="remove_connector(l.case_task_instance_id)" title="Remove this connector"><i class="fa-solid fa-trash"></i></button>
                        </template>
                    </span>
                </li>
            </ul>
        </template>

        <!-- add form -->
        <template v-else>
            <div class="cconn-head">
                <button type="button" class="btn btn-link btn-sm p-0 text-body text-decoration-none" @click="close_add" title="Back to the linked connectors">
                    <i class="fa-solid fa-arrow-left me-2"></i><span class="fw-semibold">Link connectors</span>
                </button>
            </div>
            <label class="cconn-label">Instances</label>
            <connector_picker v-model="picked" :instances="all_connectors_list || {}" :icons="icons" :exclude="attached_ids"></connector_picker>

            <div v-if="picked_instances.length" class="cconn-idents">
                <label class="cconn-label">Identifier on each instance <small>(optional — e.g. a MISP event UUID)</small></label>
                <div v-for="i in picked_instances" :key="i.id" class="cconn-ident-row">
                    <span class="cchip" :title="i.type">
                        <img v-if="type_icon(i.type)" :src="type_icon(i.type)" alt="" class="cchip-icon"><i v-else class="fa-solid fa-plug cchip-icon"></i>
                        <span class="cchip-name">[[ i.name ]]</span>
                    </span>
                    <input type="text" class="form-control form-control-sm" v-model="identifiers[i.id]" :placeholder="'Identifier on ' + i.name" :aria-label="'Identifier on ' + i.name">
                </div>
            </div>

            <div class="cconn-foot">
                <button type="button" class="btn btn-outline-secondary btn-sm" @click="close_add">Cancel</button>
                <button type="button" class="btn btn-primary btn-sm" :disabled="!picked_instances.length || saving" @click="save_connector()">
                    <span v-if="saving" class="spinner-border spinner-border-sm me-1"></span>
                    Link [[ picked_instances.length || '' ]] connector[[ picked_instances.length === 1 ? '' : 's' ]]
                </button>
            </div>
        </template>
    </div>
    `
}
