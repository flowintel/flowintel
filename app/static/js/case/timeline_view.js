import {display_toast, create_message} from '../toaster.js'
import { open_timeline_date_picker } from './timeline_date_picker.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
import { Flowtime } from '../vendor/vitrine/flowtime.js'
import { fromFlowintel } from './flowtime_adapter.js'
import { createFlowtimeGraphView } from './flowtime_graph_view.js'
import { savedFlowtimeTextScale, rememberFlowtimeTextScale } from './flowtime_preferences.js'
const { ref, onMounted, onUnmounted, nextTick, computed, watch } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        cases_info: Object,
        initial_view: { type: String, default: '' }
    },
    emits: ['view-change'],
    setup(props, { emit }) {
        const timeline_events = ref([])
        const timeline_current_view = ref('timeline')
        const show_add_form = ref(false)
        const new_date_text = ref('')
        const new_description = ref('')
        const new_additional_note = ref('')
        const editing_event_id = ref(null)
        const edit_date_text = ref('')
        const edit_description = ref('')
        const edit_additional_note = ref('')
        const inspector_edit_dialog = ref(null)
        const inspector_edit_open = ref(false)
        const edit_saving = ref(false)
        const edit_error = ref('')
        const can_manage_events = computed(() => {
            const permission = props.cases_info?.permission
            return Boolean(permission && !permission.read_only && (permission.admin || props.cases_info.present_in_case))
        })
        const sort_asc = ref(true)
        const timeline_embed = ref(null)
        const timeline_rejected_count = ref(0)
        const timeline_load_error = ref('')
        const timeline_view_key = 'flowintel:case:' + props.case_id + ':timeline-view'
        let timeline = null
        let timeline_filter = null
        let timeline_request = null
        let unmounted = false
        const timeline_listeners = new AbortController()

        // Import modal state
        const show_import_modal = ref(false)
        const misp_objects = ref([])
        const misp_attributes = ref([])
        const files = ref([])
        const selected_ids = ref([])
        const selected_attribute_ids = ref([])
        const selected_file_ids = ref([])
        const select_all = ref(false)
        const select_all_attributes = ref(false)
        const select_all_files = ref(false)

        const sorted_events = computed(() => {
            const list = [...timeline_events.value]
            list.sort((a, b) => {
                const da = a.date_parsed ? new Date(a.date_parsed.replace(' ', 'T')) : new Date(a.date_text)
                const db = b.date_parsed ? new Date(b.date_parsed.replace(' ', 'T')) : new Date(b.date_text)
                const ta = isNaN(da) ? 0 : da.getTime()
                const tb = isNaN(db) ? 0 : db.getTime()
                return sort_asc.value ? ta - tb : tb - ta
            })
            return list
        })

        function toggle_sort() {
            sort_asc.value = !sort_asc.value
        }

        const timeline_views = ['timeline', 'combined', 'feed', 'graph']
        function saved_timeline_view() {
            if (timeline_views.includes(props.initial_view)) return props.initial_view
            try {
                const view = sessionStorage.getItem(timeline_view_key)
                return timeline_views.includes(view) ? view : 'timeline'
            } catch {
                return 'timeline'
            }
        }

        function remember_timeline_view(event) {
            timeline_current_view.value = event.detail.view
            emit('view-change', event.detail.view)
            try {
                sessionStorage.setItem(timeline_view_key, event.detail.view)
            } catch {
                // The switch still works when browser storage is unavailable.
            }
        }

        function remember_timeline_filter(event) {
            timeline_filter = {
                query: event.detail.query,
                groups: [...event.detail.groups],
                dateRange: { ...event.detail.dateRange }
            }
        }

        async function fetch_timeline_events() {
            if (unmounted) return
            timeline_request?.abort()
            const request = new AbortController()
            timeline_request = request
            try {
                const res = await fetch('/case/' + props.case_id + '/get_timeline_events', { signal: request.signal })
                if (unmounted || request.signal.aborted) return
                if (!res.ok) {
                    timeline_load_error.value = 'Unable to load timeline events. Please try again.'
                    display_toast(res)
                    return
                }
                const data = await res.json()
                if (unmounted || request.signal.aborted) return
                timeline_events.value = data.events
                await nextTick()
                if (unmounted || request.signal.aborted) return
                render_timeline()
                timeline_load_error.value = ''
            } catch (error) {
                if (unmounted || request.signal.aborted) return
                timeline_load_error.value = 'Unable to load timeline events. Please try again.'
                console.error('Flowtime render or load error:', error)
            } finally {
                if (timeline_request === request) timeline_request = null
            }
        }

        function render_timeline() {
            const container = timeline_embed.value
            if (!container) return
            const { events, rejected } = fromFlowintel(timeline_events.value)
            timeline_rejected_count.value = rejected.length
            if (timeline) {
                timeline.setEvents(events)
                if (timeline_filter) timeline.setFilter(timeline_filter)
            } else {
                timeline = new Flowtime(container, {
                    events,
                    groups: [
                        { id: 'analysis', label: 'Analyst notes', color: '#6575d7', icon: '✎' },
                        { id: 'objects', label: 'MISP objects', color: '#249790', icon: '◇' },
                        { id: 'attributes', label: 'MISP attributes', color: '#d49635', icon: '⌁' },
                        { id: 'files', label: 'Files & evidence', color: '#bb7395', icon: '▤' }
                    ],
                    view: saved_timeline_view(),
                    textScale: savedFlowtimeTextScale(),
                    label: 'Case investigation timeline',
                    timeZone: 'UTC',
                    customViews: [createFlowtimeGraphView({
                        caseId: props.case_id,
                        getCasesInfo: () => props.cases_info,
                        onEventsChanged: fetch_timeline_events
                    })],
                    actions: [
                        {
                            id: 'add-event', label: 'Add Event', icon: '+', variant: 'primary',
                            visible: () => can_manage_events.value,
                            onClick: () => {
                                if (can_manage_events.value) show_add_form.value = !show_add_form.value
                            }
                        },
                        {
                            id: 'import-data', label: 'Import Data', icon: '↥',
                            visible: () => can_manage_events.value,
                            onClick: () => {
                                if (can_manage_events.value) return open_import_modal()
                            }
                        }
                    ],
                    onEdit: can_manage_events.value ? event => open_inspector_edit(event.source) : undefined,
                    onDelete: can_manage_events.value ? event => {
                        if (can_manage_events.value) return delete_event(event.source.id)
                    } : undefined
                })
            }
            timeline_current_view.value = timeline.view
        }

        watch(() => props.initial_view, view => {
            if (timeline && timeline_views.includes(view) && timeline.view !== view) timeline.setView(view)
        })

        // Optional picker next to the free-text date field (see
        // timeline_date_picker.js); the date is applied on "Validate".
        function open_date_picker(event, target) {
            const current = target === 'edit' ? edit_date_text.value : new_date_text.value
            open_timeline_date_picker(event.currentTarget, current, value => {
                if (target === 'edit') edit_date_text.value = value
                else new_date_text.value = value
            })
        }

        // Mirrors the formats accepted by CaseCore.parse_date(). Kept loose on
        // purpose: the server is the source of truth, this just gives the user
        // immediate feedback before the round-trip.
        function is_valid_date_text(text) {
            const t = (text || '').trim()
            if (!t) return false
            const patterns = [
                /^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$/,
                /^\d{4}-\d{2}-\d{2} \d{1,2}h(\d{2})?$/,
                /^\d{4}\/\d{2}\/\d{2}( \d{2}:\d{2}(:\d{2})?)?$/,
                /^\d{4}\/\d{2}\/\d{2} \d{1,2}h(\d{2})?$/,
                /^\d{2}[\/-]\d{2}[\/-]\d{2,4}( \d{2}:\d{2}(:\d{2})?)?$/,
                /^\d{2}[\/-]\d{2}[\/-]\d{2,4} \d{1,2}h(\d{2})?$/,
                /^[A-Za-z]{3,9} \d{1,2}, \d{4}( \d{2}:\d{2}(:\d{2})?)?$/
            ]
            return patterns.some(re => re.test(t))
        }

        async function add_event() {
            if (!new_date_text.value.trim()) {
                create_message('Date/time is required', 'warning-subtle')
                return
            }
            if (!is_valid_date_text(new_date_text.value)) {
                create_message('Invalid date format. Use e.g. 2024-03-15 14:30, 15/03/2024, 01/12/26 14h30 or Mar 15, 2024.', 'danger-subtle')
                return
            }
            if (!new_description.value.trim()) {
                create_message('Event is required', 'warning-subtle')
                return
            }
            const res = await fetch('/case/' + props.case_id + '/create_timeline_event', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({
                    date_text: new_date_text.value,
                    description: new_description.value,
                    additional_note: new_additional_note.value
                })
            })
            if (res.status === 200) {
                new_date_text.value = ''
                new_description.value = ''
                new_additional_note.value = ''
                show_add_form.value = false
                touchCaseLastModif(props.cases_info)
                await fetch_timeline_events()
            }
            await display_toast(res)
        }

        async function open_inspector_edit(ev) {
            if (!can_manage_events.value || !ev) return
            inspector_edit_open.value = true
            start_edit(ev)
            await nextTick()
            if (!unmounted) inspector_edit_dialog.value?.showModal()
        }

        function start_edit(ev) {
            edit_error.value = ''
            editing_event_id.value = ev.id
            edit_date_text.value = ev.date_text
            edit_description.value = ev.description
            edit_additional_note.value = ev.additional_note || ''
        }

        function cancel_edit() {
            inspector_edit_open.value = false
            if (inspector_edit_dialog.value?.open) inspector_edit_dialog.value.close()
            edit_error.value = ''
            editing_event_id.value = null
            edit_date_text.value = ''
            edit_description.value = ''
            edit_additional_note.value = ''
        }

        async function save_edit(ev_id) {
            if (edit_saving.value) return
            edit_error.value = ''
            if (!edit_date_text.value.trim() || !edit_description.value.trim()) {
                edit_error.value = 'Date and event are required'
                create_message(edit_error.value, 'warning-subtle')
                return
            }
            if (!is_valid_date_text(edit_date_text.value)) {
                edit_error.value = 'Invalid date format. Use e.g. 2026-11-19 14:30.'
                create_message(edit_error.value, 'danger-subtle')
                return
            }
            edit_saving.value = true
            try {
                const res = await fetch('/case/' + props.case_id + '/edit_timeline_event/' + ev_id, {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                    body: JSON.stringify({
                        date_text: edit_date_text.value,
                        description: edit_description.value,
                        additional_note: edit_additional_note.value
                    })
                })
                if (unmounted) return
                if (res.status === 200) {
                    cancel_edit()
                    touchCaseLastModif(props.cases_info)
                    await fetch_timeline_events()
                } else {
                    edit_error.value = 'Unable to save this event. Check the date and your permissions, then try again.'
                }
                await display_toast(res)
            } catch (error) {
                if (!unmounted) {
                    edit_error.value = 'Unable to save this event. Please try again.'
                    create_message(edit_error.value, 'danger-subtle')
                }
            } finally {
                edit_saving.value = false
            }
        }

        async function delete_event(ev_id) {
            const ok = await confirmDelete({
                title: 'Delete timeline event?',
                message: 'Are you sure you want to delete this timeline event? This cannot be undone.'
            })
            if (!ok) return
            const res = await fetch('/case/' + props.case_id + '/delete_timeline_event/' + ev_id)
            if (res.status === 200) {
                touchCaseLastModif(props.cases_info)
                await fetch_timeline_events()
            }
            await display_toast(res)
        }

        // --- Import modal helpers ---
        async function open_import_modal() {
            const [objRes, attrRes, fileRes] = await Promise.all([
                fetch('/case/' + props.case_id + '/get_case_misp_object'),
                fetch('/case/' + props.case_id + '/get_case_misp_attributes'),
                fetch('/case/' + props.case_id + '/get_timeline_import_files')
            ])

            let canOpen = false

            if (objRes.status === 200) {
                const locObjects = await objRes.json()
                misp_objects.value = locObjects['misp-object'] || []
                canOpen = true
            } else {
                await display_toast(objRes)
                misp_objects.value = []
            }

            if (attrRes.status === 200) {
                const locAttrs = await attrRes.json()
                misp_attributes.value = locAttrs.attributes || []
                canOpen = true
            } else {
                await display_toast(attrRes)
                misp_attributes.value = []
            }

            if (fileRes.status === 200) {
                const locFiles = await fileRes.json()
                files.value = locFiles.files || []
                canOpen = true
            } else {
                await display_toast(fileRes)
                files.value = []
            }

            if (canOpen) {
                selected_ids.value = []
                selected_attribute_ids.value = []
                selected_file_ids.value = []
                select_all.value = false
                select_all_attributes.value = false
                select_all_files.value = false
                show_import_modal.value = true
            }
        }

        function toggle_select_all() {
            // `select_all` is already updated by v-model when this handler runs,
            // so act based on its current value.
            if (select_all.value) {
                // select only those that are not already imported
                selected_ids.value = misp_objects.value.filter(o => !o.is_imported).map(o => o.object_id)
            } else {
                selected_ids.value = []
            }
        }

        function toggle_select_all_attributes() {
            if (select_all_attributes.value) {
                selected_attribute_ids.value = misp_attributes.value.filter(a => !a.is_imported).map(a => a.id)
            } else {
                selected_attribute_ids.value = []
            }
        }

        function toggle_select_all_files() {
            if (select_all_files.value) {
                selected_file_ids.value = files.value.filter(f => !f.is_imported).map(f => f.id)
            } else {
                selected_file_ids.value = []
            }
        }

        async function perform_import() {
            const importableObjectIds = (selected_ids.value || []).filter(id => {
                const obj = misp_objects.value.find(o => Number(o.object_id) === Number(id))
                return obj && !obj.is_imported
            })
            const importableAttributeIds = (selected_attribute_ids.value || []).filter(id => {
                const attr = misp_attributes.value.find(a => Number(a.id) === Number(id))
                return attr && !attr.is_imported
            })
            const importableFileIds = (selected_file_ids.value || []).filter(id => {
                const file = files.value.find(f => Number(f.id) === Number(id))
                return file && !file.is_imported
            })

            if (importableObjectIds.length === 0 && importableAttributeIds.length === 0 && importableFileIds.length === 0) {
                create_message('Select at least one object, standalone attribute or file to import', 'warning-subtle')
                return
            }

            const responses = []
            if (importableObjectIds.length > 0 || importableAttributeIds.length > 0) {
                responses.push(await fetch('/case/' + props.case_id + '/import_misp_to_timeline', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                    body: JSON.stringify({
                        object_ids: importableObjectIds,
                        attribute_ids: importableAttributeIds
                    })
                }))
            }
            if (importableFileIds.length > 0) {
                responses.push(await fetch('/case/' + props.case_id + '/import_files_to_timeline', {
                    method: 'POST',
                    headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                    body: JSON.stringify({ file_ids: importableFileIds })
                }))
            }

            const allOk = responses.length > 0 && responses.every(res => res.status === 200)
            if (allOk) {
                show_import_modal.value = false
                touchCaseLastModif(props.cases_info)
                await fetch_timeline_events()
            }
            for (const res of responses) {
                await display_toast(res)
            }
        }

        function close_import_modal() {
            show_import_modal.value = false
            selected_ids.value = []
            selected_attribute_ids.value = []
            selected_file_ids.value = []
            select_all.value = false
            select_all_attributes.value = false
            select_all_files.value = false
        }

        onMounted(() => {
            const listener_options = { signal: timeline_listeners.signal }
            timeline_embed.value.addEventListener('flowtime:viewchange', remember_timeline_view, listener_options)
            timeline_embed.value.addEventListener('flowtime:filterchange', remember_timeline_filter, listener_options)
            timeline_embed.value.addEventListener('flowtime:textscalechange', rememberFlowtimeTextScale, listener_options)
            return fetch_timeline_events()
        })

        onUnmounted(() => {
            unmounted = true
            timeline_request?.abort()
            timeline_listeners.abort()
            timeline?.destroy()
            timeline = null
        })

        return {
            timeline_events,
            timeline_current_view,
            timeline_embed,
            timeline_rejected_count,
            timeline_load_error,
            show_add_form,
            new_date_text,
            open_date_picker,
            new_description,
            new_additional_note,
            editing_event_id,
            edit_date_text,
            edit_description,
            edit_additional_note,
            inspector_edit_dialog,
            inspector_edit_open,
            edit_saving,
            edit_error,
            can_manage_events,
            sorted_events,
            sort_asc,
            toggle_sort,
            add_event,
            start_edit,
            cancel_edit,
            save_edit,
            delete_event,
            open_import_modal,
            perform_import,
            show_import_modal,
            misp_objects,
            misp_attributes,
            files,
            selected_ids,
            selected_attribute_ids,
            selected_file_ids,
            select_all,
            select_all_attributes,
            select_all_files,
            toggle_select_all,
            toggle_select_all_attributes,
            toggle_select_all_files,
            close_import_modal,
            fetch_timeline_events
        }
    },
    template: `
    <div>
        <!-- Add Event Form -->
        <div v-if="show_add_form" class="card mb-3">
            <div class="card-body">
                <h6 class="card-title mb-3">New timeline event</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Date / Time <span class="text-danger" aria-hidden="true">*</span><span class="visually-hidden">(required)</span></label>
                        <div class="input-group input-group-sm">
                            <input type="text" class="form-control form-control-sm" v-model="new_date_text"
                                   placeholder="e.g. 2024-03-15 14:30, 01/12/26 14h30..." required>
                            <button type="button" class="btn btn-outline-secondary" @click="open_date_picker($event, 'new')" title="Pick a date (optional)" aria-label="Pick a date">
                                <i class="fa-regular fa-calendar"></i>
                            </button>
                        </div>
                        <div class="form-text">Saved as YYYY-MM-DD HH:MM</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Event <span class="text-danger" aria-hidden="true">*</span><span class="visually-hidden">(required)</span></label>
                        <input type="text" class="form-control form-control-sm" v-model="new_description"
                               placeholder="Short event summary" required>
                    </div>
                    <div class="col-12">
                        <label class="form-label">Additional Note</label>
                        <textarea class="form-control form-control-sm" v-model="new_additional_note" rows="3"
                                  placeholder="Optional details"></textarea>
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-success btn-sm me-1" @click="add_event()">
                        <i class="fa-solid fa-check me-1"></i>Save
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" @click="show_add_form = false">Cancel</button>
                </div>
            </div>
        </div>

        <!-- Import Selection Modal -->
        <div v-if="show_import_modal" class="modal d-block" tabindex="-1" style="background: rgba(0,0,0,0.5);">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content">
                    <div class="modal-header">
                        <h5 class="modal-title">Import Data To Timeline</h5>
                        <button type="button" class="btn-close" @click="close_import_modal()"></button>
                    </div>
                    <div class="modal-body">
                        <h6 class="mb-2">MISP Objects</h6>
                        <div class="mb-2">
                            <input type="checkbox" id="select_all" v-model="select_all" @change="toggle_select_all()">
                            <label for="select_all" class="ms-1">Select all objects</label>
                        </div>
                        <div v-if="misp_objects.length === 0" class="text-muted">No MISP objects found for this case.</div>
                        <div v-else class="list-group" style="max-height:400px; overflow:auto;">
                            <label v-for="o in misp_objects" :key="o.object_id" class="list-group-item d-flex justify-content-between align-items-start">
                                <div class="d-flex align-items-start">
                                    <input type="checkbox" class="form-check-input me-2 mt-1" :value="o.object_id" v-model="selected_ids" :disabled="o.is_imported">
                                    <div>
                                        <strong>[[ o.object_name ]]</strong>
                                        <div class="text-muted small">Created: [[ o.object_creation_date ]]</div>
                                        <div class="small" v-if="o.attributes && o.attributes.length">[[ o.attributes.map(a => a.object_relation + ': ' + a.value).slice(0,3).join(', ') ]]</div>
                                    </div>
                                </div>
                                <div class="text-end">
                                    <span v-if="o.is_imported" class="badge bg-success me-2">Imported</span>
                                    <span v-else class="badge bg-secondary rounded-pill">[[ o.attributes.length ]] attrs</span>
                                </div>
                            </label>
                        </div>

                        <hr>
                        <h6 class="mb-2">Standalone MISP Attributes</h6>
                        <div class="mb-2">
                            <input type="checkbox" id="select_all_attributes" v-model="select_all_attributes" @change="toggle_select_all_attributes()">
                            <label for="select_all_attributes" class="ms-1">Select all standalone attributes</label>
                        </div>
                        <div v-if="misp_attributes.length === 0" class="text-muted">No standalone MISP attributes found for this case.</div>
                        <div v-else class="list-group" style="max-height:320px; overflow:auto;">
                            <label v-for="a in misp_attributes" :key="a.id" class="list-group-item d-flex justify-content-between align-items-start">
                                <div class="d-flex align-items-start">
                                    <input type="checkbox" class="form-check-input me-2 mt-1" :value="a.id" v-model="selected_attribute_ids" :disabled="a.is_imported">
                                    <div>
                                        <strong>[[ a.type ]]</strong>
                                        <span class="ms-1">[[ a.value ]]</span>
                                        <div class="text-muted small" v-if="a.object_relation">Relation: [[ a.object_relation ]]</div>
                                        <div class="text-muted small" v-if="a.first_seen">First seen: [[ a.first_seen ]]</div>
                                    </div>
                                </div>
                                <div class="text-end">
                                    <span v-if="a.is_imported" class="badge bg-success me-2">Imported</span>
                                    <span v-else class="badge text-bg-warning rounded-pill">Standalone attr</span>
                                </div>
                            </label>
                        </div>

                        <hr>
                        <h6 class="mb-2">Files</h6>
                        <div class="mb-2">
                            <input type="checkbox" id="select_all_files" v-model="select_all_files" @change="toggle_select_all_files()">
                            <label for="select_all_files" class="ms-1">Select all files</label>
                        </div>
                        <div v-if="files.length === 0" class="text-muted">No files found for this case.</div>
                        <div v-else class="list-group" style="max-height:320px; overflow:auto;">
                            <label v-for="f in files" :key="f.id" class="list-group-item d-flex justify-content-between align-items-start">
                                <div class="d-flex align-items-start">
                                    <input type="checkbox" class="form-check-input me-2 mt-1" :value="f.id" v-model="selected_file_ids" :disabled="f.is_imported">
                                    <div>
                                        <strong><i class="fa-solid fa-file me-1 text-success"></i>[[ f.name ]]</strong>
                                        <div class="text-muted small">[[ f.location === 'task' ? 'Task' : 'Case' ]]: [[ f.location_label ]]</div>
                                        <div class="small">Uploaded: [[ f.upload_date ]] - [[ f.file_type ]] - <template v-if="f.file_size !== 'Unknown'">[[ (f.file_size / 1024).toFixed(2) ]] KB</template><template v-else>Unknown size</template></div>
                                    </div>
                                </div>
                                <div class="text-end">
                                    <span v-if="f.is_imported" class="badge bg-success me-2">Imported</span>
                                    <span v-else class="badge text-bg-success rounded-pill">File</span>
                                </div>
                            </label>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="close_import_modal()">Cancel</button>
                        <button class="btn btn-primary" @click="perform_import()">Import selected ([[ selected_ids.length + selected_attribute_ids.length + selected_file_ids.length ]])</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Flowtime owns the contents of this host; Vue owns the surrounding forms. -->
        <div v-if="timeline_load_error" class="alert alert-danger d-flex align-items-center justify-content-between" role="alert">
            <span>[[ timeline_load_error ]]</span>
            <button type="button" class="btn btn-outline-danger btn-sm ms-2" @click="fetch_timeline_events()">Retry</button>
        </div>
        <p v-if="timeline_rejected_count" class="alert alert-warning" role="status">
            [[ timeline_rejected_count ]] event(s) have no valid date and cannot be placed in the viewer. You can correct them in the Events table below.
        </p>
        <div ref="timeline_embed" class="case-flowtime"></div>

        <!-- Inspector editing uses the same validated save path as the Events table. -->
        <dialog ref="inspector_edit_dialog" class="case-timeline-edit-dialog" aria-labelledby="timeline-inspector-edit-title"
                @close="cancel_edit()" @cancel="edit_saving && $event.preventDefault()">
            <form @submit.prevent="save_edit(editing_event_id)">
                <div class="d-flex align-items-center justify-content-between mb-3">
                    <h5 id="timeline-inspector-edit-title" class="m-0">Edit timeline event</h5>
                    <button type="button" class="btn-close" aria-label="Close event editor" :disabled="edit_saving" @click="cancel_edit()"></button>
                </div>
                <fieldset :disabled="edit_saving">
                    <label for="timeline-inspector-date" class="form-label">Date / Time (UTC)</label>
                    <input id="timeline-inspector-date" type="text" class="form-control form-control-sm mb-3" v-model="edit_date_text" placeholder="YYYY-MM-DD HH:MM" required>
                    <label for="timeline-inspector-description" class="form-label">Event</label>
                    <input id="timeline-inspector-description" type="text" class="form-control form-control-sm mb-3" v-model="edit_description" required autofocus>
                    <label for="timeline-inspector-note" class="form-label">Additional Note</label>
                    <textarea id="timeline-inspector-note" class="form-control form-control-sm mb-3" v-model="edit_additional_note" rows="4"></textarea>
                    <p v-if="edit_error" class="alert alert-danger" role="alert">[[ edit_error ]]</p>
                    <div class="d-flex justify-content-end gap-2">
                        <button type="button" class="btn btn-outline-secondary btn-sm" @click="cancel_edit()">Cancel</button>
                        <button type="submit" class="btn btn-primary btn-sm">[[ edit_saving ? 'Saving…' : 'Save changes' ]]</button>
                    </div>
                </fieldset>
            </form>
        </dialog>

        <!-- Event List Table -->
        <div v-if="timeline_current_view !== 'graph' && timeline_events.length > 0" class="mt-4">
            <h6><i class="fa-solid fa-list me-1"></i>Events</h6>
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th style="width:200px; cursor:pointer; user-select:none;" @click="toggle_sort()">
                            Date/Time
                            <i class="fa-solid fa-sm ms-1" :class="sort_asc ? 'fa-arrow-up-short-wide' : 'fa-arrow-down-wide-short'"></i>
                        </th>
                        <th>Event</th>
                        <th>Additional Note</th>
                        <th style="width:90px">Source</th>
                        <th style="width:120px">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="ev in sorted_events" :key="ev.id" :class="ev.misp_object_id && Number(ev.misp_object_id) > 0 ? 'table-info' : (ev.misp_object_id && Number(ev.misp_object_id) < 0 ? 'table-warning' : (ev.file_id ? 'table-success' : ''))">
                        <template v-if="editing_event_id === ev.id && !inspector_edit_open">
                            <td>
                                <div class="input-group input-group-sm">
                                    <input type="text" class="form-control form-control-sm" v-model="edit_date_text">
                                    <button type="button" class="btn btn-outline-secondary" @click="open_date_picker($event, 'edit')" title="Pick a date (optional)" aria-label="Pick a date">
                                        <i class="fa-regular fa-calendar"></i>
                                    </button>
                                </div>
                            </td>
                            <td>
                                <input type="text" class="form-control form-control-sm" v-model="edit_description">
                            </td>
                            <td>
                                <textarea class="form-control form-control-sm" v-model="edit_additional_note" rows="2"></textarea>
                            </td>
                            <td>
                                <span v-if="ev.misp_object_id && Number(ev.misp_object_id) > 0" class="badge text-bg-info" title="Linked to MISP object">
                                    <i class="misp-icon misp-icon-object misp-simple me-1"></i>Object
                                </span>
                                <span v-else-if="ev.misp_object_id && Number(ev.misp_object_id) < 0" class="badge text-bg-warning" title="Linked to standalone MISP attribute">
                                    <i class="misp-icon misp-icon-attribute misp-simple me-1"></i>Standalone Attr
                                </span>
                                <span v-else-if="ev.file_id" class="badge text-bg-success" title="Linked to imported file">
                                    <i class="fa-solid fa-file me-1"></i>File
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-success btn-sm me-1" @click="save_edit(ev.id)" title="Save">
                                    <i class="fa-solid fa-check"></i>
                                </button>
                                <button class="btn btn-outline-secondary btn-sm" @click="cancel_edit()" title="Cancel">
                                    <i class="fa-solid fa-xmark"></i>
                                </button>
                            </td>
                        </template>
                        <template v-else>
                            <td><code>[[ ev.date_text ]]</code></td>
                            <td>[[ ev.description ]]</td>
                            <td style="white-space: pre-wrap;">[[ ev.additional_note || '' ]]</td>
                            <td>
                                <span v-if="ev.misp_object_id && Number(ev.misp_object_id) > 0" class="badge text-bg-info" title="Linked to MISP object">
                                    <i class="misp-icon misp-icon-object misp-simple me-1"></i>Object
                                </span>
                                <span v-else-if="ev.misp_object_id && Number(ev.misp_object_id) < 0" class="badge text-bg-warning" title="Linked to standalone MISP attribute">
                                    <i class="misp-icon misp-icon-attribute misp-simple me-1"></i>Standalone Attr
                                </span>
                                <span v-else-if="ev.file_id" class="badge text-bg-success" title="Linked to imported file">
                                    <i class="fa-solid fa-file me-1"></i>File
                                </span>
                            </td>
                            <td>
                                <button class="btn btn-outline-primary btn-sm me-1" @click="start_edit(ev)" title="Edit">
                                    <i class="fa-solid fa-pen fa-sm"></i>
                                </button>
                                <button class="btn btn-outline-danger btn-sm" @click="delete_event(ev.id)" title="Delete">
                                    <i class="fa-solid fa-trash fa-sm"></i>
                                </button>
                            </td>
                        </template>
                    </tr>
                </tbody>
            </table>
        </div>
    </div>
    `
}
