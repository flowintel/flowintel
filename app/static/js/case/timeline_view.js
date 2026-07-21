import {display_toast, create_message} from '../toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
const { ref, onMounted, nextTick, computed } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        cases_info: Object
    },
    setup(props) {
        const timeline_events = ref([])
        const show_add_form = ref(false)
        const new_date_text = ref('')
        const new_description = ref('')
        const editing_event_id = ref(null)
        const edit_date_text = ref('')
        const edit_description = ref('')
        const sort_asc = ref(true)

        // Import modal state
        const show_import_modal = ref(false)
        const misp_objects = ref([])
        const misp_attributes = ref([])
        const selected_ids = ref([])
        const selected_attribute_ids = ref([])
        const select_all = ref(false)
        const select_all_attributes = ref(false)

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

        async function fetch_timeline_events() {
            const res = await fetch('/case/' + props.case_id + '/get_timeline_events')
            if (res.status === 200) {
                let loc = await res.json()
                timeline_events.value = loc.events
                await nextTick()
                render_timeline()
            } else {
                display_toast(res)
            }
        }

        function parseDateForTimeline(date_text, date_parsed) {
            let d = null
            if (date_parsed) {
                d = new Date(date_parsed.replace(' ', 'T'))
            }
            if (!d || isNaN(d.getTime())) {
                d = new Date(date_text)
            }
            if (!d || isNaN(d.getTime())) {
                return null
            }
            return {
                year: String(d.getFullYear()),
                month: String(d.getMonth() + 1).padStart(2, '0'),
                day: String(d.getDate()).padStart(2, '0'),
                hour: String(d.getHours()).padStart(2, '0'),
                minute: String(d.getMinutes()).padStart(2, '0')
            }
        }

        function render_timeline() {
            if (!timeline_events.value || timeline_events.value.length === 0) {
                const container = document.getElementById('case-timeline-embed')
                if (container) container.innerHTML = '<p class="text-muted text-center mt-4">No timeline events yet. Add events or import from MISP objects and standalone attributes to build your timeline.</p>'
                return
            }

            const events = []
            for (const ev of timeline_events.value) {
                const startDate = parseDateForTimeline(ev.date_text, ev.date_parsed)
                if (!startDate) continue

                let text = ev.description.replace(/</g, '&lt;').replace(/>/g, '&gt;')
                text = text.replace(/\n/g, '<br>')

                let headline
                if (ev.misp_object_id) {
                    const isStandaloneAttr = Number(ev.misp_object_id) < 0
                    const cleanText = text.split('—')[0]
                    const headlineText = cleanText.includes(']') ? (cleanText.split(']').slice(1).join(']').trim() || cleanText) : cleanText
                    if (isStandaloneAttr) {
                        headline = '<span style="color:#fd7e14;"><i class="fa-solid fa-tag me-1"></i></span> ' + headlineText
                    } else {
                        headline = '<span style="color:#17a2b8;"><i class="fa-solid fa-cubes me-1"></i></span> ' + headlineText
                    }
                } else {
                    headline = text
                }

                events.push({
                    start_date: startDate,
                    text: {
                        headline: headline,
                        text: '<div style="max-width:500px">' + text + '</div>'
                    }
                })
            }

            if (events.length === 0) {
                const container = document.getElementById('case-timeline-embed')
                if (container) container.innerHTML = '<p class="text-muted text-center mt-4">No events with valid dates to display on the timeline.</p>'
                return
            }

            const timelineJson = { events: events }
            const container = document.getElementById('case-timeline-embed')
            if (container) {
                container.innerHTML = ''
                try {
                    new TL.Timeline('case-timeline-embed', timelineJson, {
                        width: '100%',
                        height: 500
                    })
                } catch (e) {
                    console.error('Timeline render error:', e)
                }
            }
        }

        // Mirrors the formats accepted by CaseCore.parse_date(). Kept loose on
        // purpose: the server is the source of truth, this just gives the user
        // immediate feedback before the round-trip.
        function is_valid_date_text(text) {
            const t = (text || '').trim()
            if (!t) return false
            const patterns = [
                /^\d{4}-\d{2}-\d{2}([ T]\d{2}:\d{2}(:\d{2})?)?$/,
                /^\d{4}\/\d{2}\/\d{2}( \d{2}:\d{2}(:\d{2})?)?$/,
                /^\d{2}[\/-]\d{2}[\/-]\d{4}( \d{2}:\d{2}(:\d{2})?)?$/,
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
                create_message('Invalid date format. Use e.g. 2024-03-15 14:30, 15/03/2024 or Mar 15, 2024.', 'danger-subtle')
                return
            }
            if (!new_description.value.trim()) {
                create_message('Description is required', 'warning-subtle')
                return
            }
            const res = await fetch('/case/' + props.case_id + '/create_timeline_event', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({
                    date_text: new_date_text.value,
                    description: new_description.value
                })
            })
            if (res.status === 200) {
                new_date_text.value = ''
                new_description.value = ''
                show_add_form.value = false
                touchCaseLastModif(props.cases_info)
                await fetch_timeline_events()
            }
            await display_toast(res)
        }

        function start_edit(ev) {
            editing_event_id.value = ev.id
            edit_date_text.value = ev.date_text
            edit_description.value = ev.description
        }

        function cancel_edit() {
            editing_event_id.value = null
            edit_date_text.value = ''
            edit_description.value = ''
        }

        async function save_edit(ev_id) {
            if (!edit_date_text.value.trim() || !edit_description.value.trim()) {
                create_message('Date and description are required', 'warning-subtle')
                return
            }
            if (!is_valid_date_text(edit_date_text.value)) {
                create_message('Invalid date format. Use e.g. 2024-03-15 14:30, 15/03/2024 or Mar 15, 2024.', 'danger-subtle')
                return
            }
            const res = await fetch('/case/' + props.case_id + '/edit_timeline_event/' + ev_id, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({
                    date_text: edit_date_text.value,
                    description: edit_description.value
                })
            })
            if (res.status === 200) {
                editing_event_id.value = null
                touchCaseLastModif(props.cases_info)
                await fetch_timeline_events()
            }
            await display_toast(res)
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
            const [objRes, attrRes] = await Promise.all([
                fetch('/case/' + props.case_id + '/get_case_misp_object'),
                fetch('/case/' + props.case_id + '/get_case_misp_attributes')
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

            if (canOpen) {
                selected_ids.value = []
                selected_attribute_ids.value = []
                select_all.value = false
                select_all_attributes.value = false
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

        async function perform_import() {
            const importableObjectIds = (selected_ids.value || []).filter(id => {
                const obj = misp_objects.value.find(o => Number(o.object_id) === Number(id))
                return obj && !obj.is_imported
            })
            const importableAttributeIds = (selected_attribute_ids.value || []).filter(id => {
                const attr = misp_attributes.value.find(a => Number(a.id) === Number(id))
                return attr && !attr.is_imported
            })

            if (importableObjectIds.length === 0 && importableAttributeIds.length === 0) {
                create_message('Select at least one object or standalone attribute to import', 'warning-subtle')
                return
            }
            const res = await fetch('/case/' + props.case_id + '/import_misp_to_timeline', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({
                    object_ids: importableObjectIds,
                    attribute_ids: importableAttributeIds
                })
            })
            if (res.status === 200) {
                show_import_modal.value = false
                touchCaseLastModif(props.cases_info)
                await fetch_timeline_events()
            }
            await display_toast(res)
        }

        function close_import_modal() {
            show_import_modal.value = false
            selected_ids.value = []
            selected_attribute_ids.value = []
            select_all.value = false
            select_all_attributes.value = false
        }

        onMounted(() => {
            fetch_timeline_events()
        })

        return {
            timeline_events,
            show_add_form,
            new_date_text,
            new_description,
            editing_event_id,
            edit_date_text,
            edit_description,
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
            selected_ids,
            selected_attribute_ids,
            select_all,
            select_all_attributes,
            toggle_select_all,
            toggle_select_all_attributes,
            close_import_modal,
            fetch_timeline_events
        }
    },
    template: `
    <div>
        <div class="d-flex justify-content-between align-items-center mb-3">
            <div>
                <button class="btn btn-primary btn-sm me-2" @click="show_add_form = !show_add_form">
                    <i class="fa-solid fa-plus me-1"></i>Add Event
                </button>
                <button class="btn btn-outline-secondary btn-sm" @click="open_import_modal()" title="Import selected MISP objects and standalone attributes as timeline events">
                    <i class="fa-solid fa-cubes me-1"></i>Import MISP Data
                </button>
            </div>
        </div>

        <!-- Add Event Form -->
        <div v-if="show_add_form" class="card mb-3">
            <div class="card-body">
                <h6 class="card-title mb-3">New timeline event</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Date / Time <span class="text-danger" aria-hidden="true">*</span><span class="visually-hidden">(required)</span></label>
                        <input type="text" class="form-control form-control-sm" v-model="new_date_text"
                               placeholder="e.g. 2024-03-15 14:30, Mar 15, 2024, 15/03/2024..." required>
                        <div class="form-text">Any common date format is accepted</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Description</label>
                        <textarea class="form-control form-control-sm" v-model="new_description" rows="2"
                                  placeholder="What happened at this point in time?"></textarea>
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
                        <h5 class="modal-title">Import MISP Data To Timeline</h5>
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
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" @click="close_import_modal()">Cancel</button>
                        <button class="btn btn-primary" @click="perform_import()">Import selected ([[ selected_ids.length + selected_attribute_ids.length ]])</button>
                    </div>
                </div>
            </div>
        </div>

        <!-- Timeline Graphical View -->
        <div id="case-timeline-embed" style="width:100%; min-height:500px;"></div>

        <!-- Event List Table -->
        <div v-if="timeline_events.length > 0" class="mt-4">
            <h6><i class="fa-solid fa-list me-1"></i>Events</h6>
            <table class="table table-sm table-hover">
                <thead>
                    <tr>
                        <th style="width:200px; cursor:pointer; user-select:none;" @click="toggle_sort()">
                            Date/Time
                            <i class="fa-solid fa-sm ms-1" :class="sort_asc ? 'fa-arrow-up-short-wide' : 'fa-arrow-down-wide-short'"></i>
                        </th>
                        <th>Description</th>
                        <th style="width:50px">MISP</th>
                        <th style="width:120px">Actions</th>
                    </tr>
                </thead>
                <tbody>
                    <tr v-for="ev in sorted_events" :key="ev.id" :class="ev.misp_object_id && Number(ev.misp_object_id) > 0 ? 'table-info' : (ev.misp_object_id && Number(ev.misp_object_id) < 0 ? 'table-warning' : '')">
                        <template v-if="editing_event_id === ev.id">
                            <td>
                                <input type="text" class="form-control form-control-sm" v-model="edit_date_text">
                            </td>
                            <td>
                                <textarea class="form-control form-control-sm" v-model="edit_description" rows="1"></textarea>
                            </td>
                            <td>
                                <span v-if="ev.misp_object_id && Number(ev.misp_object_id) > 0" class="badge text-bg-info" title="Linked to MISP object">
                                    <i class="fa-solid fa-cubes me-1"></i>Object
                                </span>
                                <span v-else-if="ev.misp_object_id && Number(ev.misp_object_id) < 0" class="badge text-bg-warning" title="Linked to standalone MISP attribute">
                                    <i class="fa-solid fa-tag me-1"></i>Standalone Attr
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
                            <td>
                                <span v-if="ev.misp_object_id && Number(ev.misp_object_id) > 0" class="badge text-bg-info" title="Linked to MISP object">
                                    <i class="fa-solid fa-cubes me-1"></i>Object
                                </span>
                                <span v-else-if="ev.misp_object_id && Number(ev.misp_object_id) < 0" class="badge text-bg-warning" title="Linked to standalone MISP attribute">
                                    <i class="fa-solid fa-tag me-1"></i>Standalone Attr
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
