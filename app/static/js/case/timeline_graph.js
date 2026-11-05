import {display_toast, create_message} from '../toaster.js'
import { open_timeline_date_picker } from './timeline_date_picker.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
const { ref, onMounted, nextTick } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        cases_info: Object
    },
    setup(props) {
        const graph_events = ref([])
        const graph_links = ref([])
        const show_add_event = ref(false)
        const show_add_link = ref(false)
        const new_date_text = ref('')
        const new_description = ref('')
        const new_additional_note = ref('')
        const link_source = ref('')
        const link_target = ref('')
        const link_label = ref('')
        const selected_edge = ref(null)
        const selected_node = ref(null)
        const edit_link_label = ref('')
        const show_help = ref(false)
        let graph = null

        async function fetch_graph_data() {
            const res = await fetch('/case/' + props.case_id + '/get_timeline_graph')
            if (res.status === 200) {
                const data = await res.json()
                graph_events.value = data.events
                graph_links.value = data.links
                await nextTick()
                render_graph()
            } else {
                display_toast(res)
            }
        }

        // What a timeline event is: drives the card's colour, icon and legend entry
        const EVENT_KINDS = {
            misp_object: { label: 'MISP object', color: '#0d9fb8', icon: 'fa-solid fa-cube' },
            misp_attribute: { label: 'MISP attribute', color: '#e8730c', icon: 'fa-solid fa-tag' },
            file: { label: 'Imported file', color: '#198754', icon: 'fa-solid fa-file-lines' },
            event: { label: 'Event', color: '#6f42c1', icon: 'fa-solid fa-clock' },
        }

        function event_kind(ev) {
            if (ev.misp_object_id && Number(ev.misp_object_id) > 0) return 'misp_object'
            if (ev.misp_object_id && Number(ev.misp_object_id) < 0) return 'misp_attribute'
            if (ev.file_id) return 'file'
            return 'event'
        }

        // Events in time order: what gives the graph its reading direction
        function event_time(ev) {
            const t = Date.parse((ev.date_parsed || ev.date_text || '').replace(' ', 'T'))
            return isNaN(t) ? null : t
        }

        function chronological(events) {
            return events
                .filter(ev => event_time(ev) !== null)
                .sort((a, b) => event_time(a) - event_time(b) || a.id - b.id)
        }

        // "+2d 4h", "+35m": time between two events, shown on the chronology links
        function elapsed(ms) {
            const m = Math.round(ms / 60000)
            if (m < 1) return 'same time'
            const d = Math.floor(m / 1440), h = Math.floor((m % 1440) / 60), min = m % 60
            if (d) return '+' + d + 'd' + (h ? ' ' + h + 'h' : '')
            if (h) return '+' + h + 'h' + (min ? ' ' + min + 'm' : '')
            return '+' + min + 'm'
        }

        function el(tag, className, text) {
            const node = document.createElement(tag)
            if (className) node.className = className
            if (text !== undefined && text !== null) node.textContent = text
            return node
        }

        // The card drawn for each node. Built with textContent only: event data is
        // never interpolated into markup.
        function build_card(node) {
            const ev = node.getData().event
            const kind = EVENT_KINDS[event_kind(ev)]
            const card = el('div', 'tlg-card')
            card.style.setProperty('--tlg-accent', kind.color)

            const head = el('div', 'tlg-card-head')
            const icon = el('span', 'tlg-card-icon')
            icon.appendChild(el('i', kind.icon))
            head.appendChild(icon)
            const step = node.getData().step
            if (step) head.appendChild(el('span', 'tlg-card-step', '#' + step))
            const when = el('div', 'tlg-card-when')
            when.appendChild(el('span', 'tlg-card-kind', kind.label))
            when.appendChild(el('span', 'tlg-card-date', ev.date_text))
            head.insertBefore(when, head.querySelector('.tlg-card-step'))
            card.appendChild(head)

            card.appendChild(el('div', 'tlg-card-title', ev.description))
            if (ev.additional_note) card.appendChild(el('div', 'tlg-card-note', ev.additional_note))
            if (ev.file && ev.file.name) {
                const file = el('div', 'tlg-card-file')
                file.appendChild(el('i', 'fa-solid fa-paperclip'))
                file.appendChild(document.createTextNode(' ' + ev.file.name))
                card.appendChild(file)
            }
            return card
        }

        function render_graph() {
            const container = document.getElementById('timeline-graph-container')
            if (!container) return

            // Destroy previous graph instance
            if (graph) {
                graph.destroy()
                graph = null
            }

            if (!graph_events.value.length) {
                container.innerHTML = '<p class="text-muted text-center mt-4">No events yet. Add events to build your graph.</p>'
                return
            }

            container.innerHTML = ''

            const ordered = chronological(graph_events.value)
            const step_of = new Map(ordered.map((ev, i) => [ev.id, i + 1]))

            const nodes = graph_events.value.map(ev => ({
                id: String(ev.id),
                data: {
                    label: ev.date_text + ' — ' + ev.description,
                    kind: event_kind(ev),
                    step: step_of.get(ev.id) || null,
                    event: ev,
                }
            }))

            // Three kinds of links, each telling something different:
            //  - analyst: drawn by a user ("drops", "leads to"...), the causality they established
            //  - misp: relationships between the MISP objects the events come from
            //  - chronology: each event to the next one in time, labelled with the time between
            //    them, so the cards read as a timeline and dwell times stand out
            const edges = graph_links.value.map(lk => ({
                id: String(lk.id),
                from: String(lk.source_event_id),
                to: String(lk.target_event_id),
                data: {
                    label: lk.label || (lk.automatic ? 'relationship' : ''),
                    link_id: String(lk.id),
                    automatic: !!lk.automatic,
                    link_type: lk.automatic ? 'misp' : 'analyst'
                }
            }))
            for (let i = 1; i < ordered.length; i++) {
                const prev = ordered[i - 1], cur = ordered[i]
                edges.push({
                    id: 'chrono-' + prev.id + '-' + cur.id,
                    from: String(prev.id),
                    to: String(cur.id),
                    data: { label: elapsed(event_time(cur) - event_time(prev)), link_type: 'chronology', computed: true }
                })
            }

            const nodeStyleMap = {}
            for (const [key, kind] of Object.entries(EVENT_KINDS)) {
                // shape 'none': the card is the whole node; text '' because the card has its own title
                nodeStyleMap[key] = { shape: 'none', color: kind.color, text: '', html: build_card }
            }

            // A focused viewer: the cards, their links, a legend that doubles as a filter,
            // search and the zoom controls. No table, sidebar, notes, pivots or editing:
            // events and links are managed with the buttons above, which save them in the case.
            const options = {
                isDirected: true,
                layout: { type: 'structured', gap: 40, trayPosition: 'right' },
                UI: {
                    mode: 'light',
                    editors: {
                        nodeCreator: { enabled: false },
                        edgeCreator: { enabled: false },
                        nodeEditor: { enabled: false },
                        edgeEditor: { enabled: false },
                        deletion: { enabled: false },
                    },
                    notes: { enabled: false },
                    history: { enabled: false },
                    inspector: { enabled: false },
                    filter: { enabled: false },
                    sidebar: { enabled: false },
                    contextMenu: { enabled: false },
                    viewFlyout: { enabled: false },
                    physicsFlyout: { enabled: false },
                    table: false,
                    minimap: false,
                    pivotMode: false,
                    legend: {
                        position: 'bottom-left',
                        sections: [
                            { key: 'kind', title: 'Event' },
                            { key: 'link_type', title: 'Link', scope: 'edge' },
                        ],
                    },
                },
                render: {
                    nodeTypeAccessor: (node) => node.getData().kind,
                    nodeStyleMap: nodeStyleMap,
                    edgeTypeAccessor: (edge) => edge.getData().link_type,
                    edgeStyleMap: {
                        analyst: { strokeColor: '#6f42c1' },
                        misp: { strokeColor: '#0d9fb8', dashed: true, animateDash: false },
                        chronology: { strokeColor: '#adb5bd', dashed: true, animateDash: false },
                    },
                },
                callbacks: {
                    onNodeSelect: (node) => {
                        const ev = graph_events.value.find(e => String(e.id) === String(node.id))
                        if (ev) selected_node.value = ev
                    },
                    onNodeBlur: () => { selected_node.value = null },
                    onEdgeSelect: (edge) => {
                        if (edge.getData && edge.getData().computed) return
                        const lk = graph_links.value.find(l => String(l.id) === String(edge.id))
                        if (lk) {
                            selected_edge.value = lk
                            edit_link_label.value = lk.label || ''
                        }
                    },
                    onEdgeBlur: () => { selected_edge.value = null }
                }
            }

            graph = new Pivotick(container, { nodes: nodes, edges: edges }, options)
        }

        async function add_graph_event() {
            if (!new_date_text.value.trim()) {
                create_message('Date/time is required', 'warning-subtle')
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
                show_add_event.value = false
                touchCaseLastModif(props.cases_info)
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function add_link() {
            if (!link_source.value || !link_target.value) {
                create_message('Select both source and target events', 'warning-subtle')
                return
            }
            if (link_source.value === link_target.value) {
                create_message('Source and target must be different', 'warning-subtle')
                return
            }
            const res = await fetch('/case/' + props.case_id + '/create_timeline_event_link', {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({
                    source_event_id: parseInt(link_source.value),
                    target_event_id: parseInt(link_target.value),
                    label: link_label.value
                })
            })
            if (res.status === 200) {
                link_source.value = ''
                link_target.value = ''
                link_label.value = ''
                show_add_link.value = false
                touchCaseLastModif(props.cases_info)
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function save_edge_label() {
            if (!selected_edge.value) return
            if (selected_edge.value.automatic) {
                create_message('Automatic MISP relationship links are edited from the MISP relationship UI.', 'info-subtle')
                return
            }
            const res = await fetch('/case/' + props.case_id + '/edit_timeline_event_link/' + selected_edge.value.id, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({ label: edit_link_label.value })
            })
            if (res.status === 200) {
                selected_edge.value = null
                touchCaseLastModif(props.cases_info)
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function delete_selected_edge() {
            if (!selected_edge.value) return
            if (selected_edge.value.automatic) {
                create_message('Automatic MISP relationship links are removed by deleting the MISP relationship.', 'info-subtle')
                return
            }
            const ok = await confirmDelete({
                title: 'Delete link?',
                message: 'Are you sure you want to delete this link? This cannot be undone.'
            })
            if (!ok) return
            const res = await fetch('/case/' + props.case_id + '/delete_timeline_event_link/' + selected_edge.value.id)
            if (res.status === 200) {
                selected_edge.value = null
                touchCaseLastModif(props.cases_info)
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function delete_selected_node() {
            if (!selected_node.value) {
                create_message('Click a node first to select it', 'warning-subtle')
                return
            }
            const ok = await confirmDelete({
                title: 'Delete event?',
                message: 'Are you sure you want to delete this event and all its links? This cannot be undone.'
            })
            if (!ok) return
            const res = await fetch('/case/' + props.case_id + '/delete_timeline_event/' + selected_node.value.id)
            if (res.status === 200) {
                selected_node.value = null
                touchCaseLastModif(props.cases_info)
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        // Optional picker next to the free-text date field (see
        // timeline_date_picker.js); the date is applied on "Validate".
        function open_date_picker(event) {
            open_timeline_date_picker(event.currentTarget, new_date_text.value, value => {
                new_date_text.value = value
            })
        }

        function event_label(ev) {
            return ev.date_text + ' — ' + (ev.description.length > 50 ? ev.description.substring(0, 50) + '…' : ev.description)
        }

        onMounted(() => {
            fetch_graph_data()
        })

        return {
            graph_events,
            graph_links,
            show_add_event,
            show_add_link,
            new_date_text,
            open_date_picker,
            new_description,
            new_additional_note,
            link_source,
            link_target,
            link_label,
            selected_edge,
            selected_node,
            edit_link_label,
            show_help,
            add_graph_event,
            add_link,
            save_edge_label,
            delete_selected_edge,
            delete_selected_node,
            event_label,
            fetch_graph_data
        }
    },
    template: `
    <div>
        <div class="d-flex flex-wrap gap-2 mb-3">
            <button class="btn btn-primary btn-sm" @click="show_add_event = !show_add_event">
                <i class="fa-solid fa-plus me-1"></i>Add Node
            </button>
            <button class="btn btn-outline-primary btn-sm" @click="show_add_link = !show_add_link">
                <i class="fa-solid fa-link me-1"></i>Add Link
            </button>
            <button class="btn btn-outline-danger btn-sm" @click="delete_selected_node()" title="Delete selected node">
                <i class="fa-solid fa-trash me-1"></i>Delete Node
            </button>
            <span v-if="selected_node" class="badge bg-secondary align-self-center">
                <i class="fa-solid fa-circle-dot me-1"></i>Selected: [[ selected_node.date_text ]]
            </span>
            <button class="btn btn-sm ms-auto" :class="show_help ? 'btn-secondary' : 'btn-outline-secondary'"
                    @click="show_help = !show_help" title="How to read this graph" aria-label="How to read this graph">
                <i class="fa-solid fa-question"></i>
            </button>
        </div>

        <!-- Add Event Form -->
        <div v-if="show_add_event" class="card mb-3">
            <div class="card-body">
                <h6 class="card-title mb-3">New event node</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Date / Time</label>
                        <div class="input-group input-group-sm">
                            <input type="text" class="form-control form-control-sm" v-model="new_date_text"
                                   placeholder="e.g. 2024-03-15 14:30, 01/12/26 14h30...">
                            <button type="button" class="btn btn-outline-secondary" @click="open_date_picker($event)" title="Pick a date (optional)" aria-label="Pick a date">
                                <i class="fa-regular fa-calendar"></i>
                            </button>
                        </div>
                        <div class="form-text">Saved as YYYY-MM-DD HH:MM</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Event</label>
                        <input type="text" class="form-control form-control-sm" v-model="new_description"
                               placeholder="Short event summary">
                    </div>
                    <div class="col-12">
                        <label class="form-label">Additional Note</label>
                        <textarea class="form-control form-control-sm" v-model="new_additional_note" rows="3"
                                  placeholder="Optional details"></textarea>
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-success btn-sm me-1" @click="add_graph_event()">
                        <i class="fa-solid fa-check me-1"></i>Save
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" @click="show_add_event = false">Cancel</button>
                </div>
            </div>
        </div>

        <!-- Add Link Form -->
        <div v-if="show_add_link" class="card mb-3">
            <div class="card-body">
                <h6 class="card-title mb-3">New link between events</h6>
                <div class="row g-3">
                    <div class="col-md-5">
                        <label class="form-label">Source event</label>
                        <select class="form-select form-select-sm" v-model="link_source">
                            <option value="">-- Select source --</option>
                            <option v-for="ev in graph_events" :key="ev.id" :value="ev.id">[[ event_label(ev) ]]</option>
                        </select>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Target event</label>
                        <select class="form-select form-select-sm" v-model="link_target">
                            <option value="">-- Select target --</option>
                            <option v-for="ev in graph_events" :key="ev.id" :value="ev.id">[[ event_label(ev) ]]</option>
                        </select>
                    </div>
                    <div class="col-md-2">
                        <label class="form-label">Label</label>
                        <input type="text" class="form-control form-control-sm" v-model="link_label" placeholder="Optional">
                    </div>
                </div>
                <div class="mt-2">
                    <button class="btn btn-success btn-sm me-1" @click="add_link()">
                        <i class="fa-solid fa-check me-1"></i>Create Link
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" @click="show_add_link = false">Cancel</button>
                </div>
            </div>
        </div>

        <!-- Edge editing panel -->
        <div v-if="selected_edge" class="card mb-3 border-primary">
            <div class="card-body py-2">
                <div class="d-flex align-items-center gap-2">
                    <span class="text-muted">Selected link:</span>
                    <span v-if="selected_edge.automatic" class="badge bg-info text-dark">MISP relationship</span>
                    <input type="text" class="form-control form-control-sm" v-model="edit_link_label" placeholder="Link label" style="max-width: 200px;">
                    <button class="btn btn-success btn-sm" @click="save_edge_label()" title="Save label" :disabled="selected_edge.automatic">
                        <i class="fa-solid fa-check"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" @click="delete_selected_edge()" title="Delete link" :disabled="selected_edge.automatic">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" @click="selected_edge = null" title="Deselect">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>
        </div>

        <!-- How to read the graph -->
        <div v-if="show_help" class="card mb-3 tlg-help">
            <div class="card-body py-3">
                <div class="d-flex justify-content-between align-items-start mb-2">
                    <h6 class="mb-0"><i class="fa-solid fa-circle-question me-1"></i>How to read this graph</h6>
                    <button class="btn-close btn-sm" @click="show_help = false" aria-label="Close"></button>
                </div>
                <div class="row g-3">
                    <div class="col-md-6">
                        <div class="tlg-help-title">Cards</div>
                        <p class="mb-2">Each card is a timeline event. The number at its top right (<span class="tlg-card-step">#3</span>) is its place in time order: #1 is the earliest event.</p>
                        <ul class="tlg-help-list">
                            <li><span class="tlg-help-dot" style="background:#6f42c1"></span>Event added by hand</li>
                            <li><span class="tlg-help-dot" style="background:#0d9fb8"></span>Event from a MISP object</li>
                            <li><span class="tlg-help-dot" style="background:#e8730c"></span>Event from a standalone MISP attribute</li>
                            <li><span class="tlg-help-dot" style="background:#198754"></span>Event from an imported file</li>
                        </ul>
                    </div>
                    <div class="col-md-6">
                        <div class="tlg-help-title">Links</div>
                        <ul class="tlg-help-list">
                            <li><span class="tlg-help-line tlg-help-line-dashed" style="--c:#adb5bd"></span><span><b>Chronology</b>, drawn automatically from each event to the next one. Its label is the time between them (<code>+2h 14m</code>): a long gap shows where the attacker waited or went unnoticed.</span></li>
                            <li><span class="tlg-help-line" style="--c:#6f42c1"></span><span><b>Your links</b>, added with <i>Add Link</i>: the cause and effect you established (“drops”, “leads to”…). Click one to rename or delete it.</span></li>
                            <li><span class="tlg-help-line tlg-help-line-dashed" style="--c:#0d9fb8"></span><span><b>MISP relationships</b> between the objects the events come from. They are managed in the MISP tab.</span></li>
                        </ul>
                        <p class="mb-0 text-muted small">The arrow points from the earlier or causing event to the later or resulting one. Click an entry of the legend, at the bottom left of the graph, to hide that kind of card or link.</p>
                    </div>
                </div>
            </div>
        </div>

        <!-- Graph Container -->
        <div id="timeline-graph-container" class="tlg-container"></div>

        <div class="mt-2">
            <small class="text-muted">
                <i class="fa-solid fa-circle-info me-1"></i>
                Cards are numbered in time order. Grey dashed links follow the chronology with the time between two events, purple links are the ones you add, blue dashed links come from MISP relationships. Click a legend entry to hide that kind; click a purple link to edit it, a card to select it.
            </small>
        </div>
    </div>
    `
}
