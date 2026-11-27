import {display_toast, create_message} from '../toaster.js'
import { open_timeline_date_picker } from './timeline_date_picker.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
import TimelineImportDialog from './timeline_import_dialog.js'
import { Flowtime } from '../vendor/vitrine/flowtime.js'
import { fromFlowintel } from './flowtime_adapter.js'
import { createFlowtimeGraphView } from './flowtime_graph_view.js'
import { savedFlowtimeTextScale, rememberFlowtimeTextScale } from './flowtime_preferences.js'
const { ref, onMounted, onUnmounted, nextTick, computed, watch } = Vue

export default {
    delimiters: ['[[', ']]'],
    components: { TimelineImportDialog },
    props: {
        case_id: Number,
        cases_info: Object,
        initial_view: { type: String, default: '' }
    },
    emits: ['view-change', 'navigate'],
    setup(props, { emit }) {
        const show_add_form = ref(false)
        const new_date_text = ref('')
        const new_description = ref('')
        const new_additional_note = ref('')
        const editing_event_id = ref(null)
        const edit_date_text = ref('')
        const edit_description = ref('')
        const edit_additional_note = ref('')
        const inspector_edit_dialog = ref(null)
        const edit_saving = ref(false)
        const edit_error = ref('')
        const can_manage_events = computed(() => {
            const permission = props.cases_info?.permission
            return Boolean(permission && !permission.read_only && (permission.admin || props.cases_info.present_in_case))
        })
        const timeline_embed = ref(null)
        const timeline_rejected_count = ref(0)
        const timeline_load_error = ref('')
        const timeline_view_key = 'flowintel:case:' + props.case_id + ':timeline-view'
        let timeline = null
        let timeline_filter = null
        let timeline_request = null
        let unmounted = false
        const timeline_listeners = new AbortController()

        const show_import_modal = ref(false)

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
                render_timeline(data.events)
                timeline_load_error.value = ''
            } catch (error) {
                if (unmounted || request.signal.aborted) return
                timeline_load_error.value = 'Unable to load timeline events. Please try again.'
                console.error('Flowtime render or load error:', error)
            } finally {
                if (timeline_request === request) timeline_request = null
            }
        }

        function render_timeline(records) {
            const container = timeline_embed.value
            if (!container) return
            const { events, rejected } = fromFlowintel(records)
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
                        onEventsChanged: fetch_timeline_events,
                        onNavigate: target => emit('navigate', target)
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
                                if (can_manage_events.value) show_import_modal.value = true
                            }
                        }
                    ],
                    onEdit: can_manage_events.value ? event => open_inspector_edit(event.source) : undefined,
                    onDelete: can_manage_events.value ? event => {
                        if (can_manage_events.value) return delete_event(event.source.id)
                    } : undefined
                })
            }
        }

        watch(() => props.initial_view, view => {
            if (timeline && timeline_views.includes(view) && timeline.view !== view) timeline.setView(view)
        })

        // Optional picker next to the free-text date field (see
        // timeline_date_picker.js); the date is applied on "Validate".
        function open_date_picker(event) {
            open_timeline_date_picker(event.currentTarget, new_date_text.value, value => {
                new_date_text.value = value
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
            edit_error.value = ''
            editing_event_id.value = ev.id
            edit_date_text.value = ev.date_text
            edit_description.value = ev.description
            edit_additional_note.value = ev.additional_note || ''
            await nextTick()
            if (!unmounted) inspector_edit_dialog.value?.showModal()
        }

        function cancel_edit() {
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

        function on_timeline_import() {
            touchCaseLastModif(props.cases_info)
            return fetch_timeline_events()
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
            edit_saving,
            edit_error,
            can_manage_events,
            add_event,
            cancel_edit,
            save_edit,
            delete_event,
            show_import_modal,
            on_timeline_import,
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
                            <button type="button" class="btn btn-outline-secondary" @click="open_date_picker($event)" title="Pick a date (optional)" aria-label="Pick a date">
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

        <TimelineImportDialog v-if="show_import_modal" :case_id="case_id"
                              @close="show_import_modal = false" @imported="on_timeline_import" />

        <!-- Flowtime owns the contents of this host; Vue owns the surrounding forms. -->
        <div v-if="timeline_load_error" class="alert alert-danger d-flex align-items-center justify-content-between" role="alert">
            <span>[[ timeline_load_error ]]</span>
            <button type="button" class="btn btn-outline-danger btn-sm ms-2" @click="fetch_timeline_events()">Retry</button>
        </div>
        <p v-if="timeline_rejected_count" class="alert alert-warning" role="status">
            [[ timeline_rejected_count ]] [[ timeline_rejected_count === 1 ? 'event has' : 'events have' ]] no valid date for the timeline.
        </p>
        <div ref="timeline_embed" class="case-flowtime"></div>

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
    </div>
    `
}
