import {display_toast, create_message} from '../toaster.js'
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
            // Use date_parsed if available (already in YYYY-MM-DD HH:MM format)
            let d = null
            if (date_parsed) {
                d = new Date(date_parsed.replace(' ', 'T'))
            }
            if (!d || isNaN(d.getTime())) {
                // Try to parse the raw date text
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
                if (container) container.innerHTML = '<p class="text-muted text-center mt-4">No timeline events yet. Add events or import from MISP objects to build your timeline.</p>'
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
                    let loc = text.split('—')[0].split(']')[1].trim()
                    headline = '<i class="fa-solid fa-cubes me-1"></i> ' + loc
                }else{
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
                } catch(e) {
                    console.error('Timeline render error:', e)
                }
            }
        }

        async function add_event() {
            if (!new_date_text.value.trim()) {
                create_message('Date/time is required', 'warning-subtle')
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
                await fetch_timeline_events()
            }
            await display_toast(res)
        }

        async function delete_event(ev_id) {
            if (!confirm('Delete this timeline event?')) return
            const res = await fetch('/case/' + props.case_id + '/delete_timeline_event/' + ev_id)
            if (res.status === 200) {
                await fetch_timeline_events()
            }
            await display_toast(res)
        }

        async function import_misp_objects() {
            const res = await fetch('/case/' + props.case_id + '/import_misp_to_timeline', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({})
            })
            if (res.status === 200) {
                await fetch_timeline_events()
            }
            await display_toast(res)
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
            import_misp_objects,
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
                <button class="btn btn-outline-secondary btn-sm" @click="import_misp_objects()" title="Import MISP objects as timeline events">
                    <i class="fa-solid fa-cubes me-1"></i>Import MISP Objects
                </button>
            </div>
        </div>

        <!-- Add Event Form -->
        <div v-if="show_add_form" class="card mb-3">
            <div class="card-body">
                <h6 class="card-title mb-3">New Timeline Event</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Date / Time</label>
                        <input type="text" class="form-control form-control-sm" v-model="new_date_text"
                               placeholder="e.g. 2024-03-15 14:30, Mar 15 2024, 15/03/2024...">
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
                    <tr v-for="ev in sorted_events" :key="ev.id">
                        <template v-if="editing_event_id === ev.id">
                            <td>
                                <input type="text" class="form-control form-control-sm" v-model="edit_date_text">
                            </td>
                            <td>
                                <textarea class="form-control form-control-sm" v-model="edit_description" rows="1"></textarea>
                            </td>
                            <td>
                                <i v-if="ev.misp_object_id" class="fa-solid fa-cubes text-info" title="Linked to MISP object"></i>
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
                                <i v-if="ev.misp_object_id" class="fa-solid fa-cubes text-info" title="Linked to MISP object"></i>
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
