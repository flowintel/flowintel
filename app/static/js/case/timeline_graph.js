import {display_toast, create_message} from '../toaster.js'
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
        const link_source = ref('')
        const link_target = ref('')
        const link_label = ref('')
        const selected_edge = ref(null)
        const selected_node = ref(null)
        const edit_link_label = ref('')
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

            const nodes = graph_events.value.map(ev => {
                let label = ev.date_text + '\n' + ev.description
                let color = ev.misp_object_id ? '#17a2b8' : '#6c757d'
                return {
                    id: String(ev.id),
                    data: { label: label, event_id: ev.id },
                    style: { color: color }
                }
            })

            const edges = graph_links.value.map(lk => ({
                id: String(lk.id),
                from: String(lk.source_event_id),
                to: String(lk.target_event_id),
                data: { label: lk.label || '', link_id: lk.id }
            }))

            const data = { nodes: nodes, edges: edges }

            const options = {
                isDirected: true,
                layout: { type: 'force' },
                simulation: {
                    useWorker: false,
                    d3ManyBodyStrength: -300
                },
                render: {
                    defaultEdgeStyle: {
                        markerEnd: 'arrow'
                    }
                },
                callbacks: {
                    onEdgeClick: (event, edge) => {
                        selected_node.value = null
                        const lk = graph_links.value.find(l => String(l.id) === edge.id)
                        if (lk) {
                            selected_edge.value = lk
                            edit_link_label.value = lk.label || ''
                        }
                    },
                    onNodeClick: (event, node) => {
                        selected_edge.value = null
                        edit_link_label.value = ''
                        const ev = graph_events.value.find(e => String(e.id) === node.id)
                        if (ev) {
                            selected_node.value = ev
                        }
                    },
                    onCanvasClick: () => {
                        selected_edge.value = null
                        selected_node.value = null
                        edit_link_label.value = ''
                    }
                },
                UI: { mode: 'full' }
            }

            graph = new Pivotick.Pivotick(container, data, options)
        }

        async function add_graph_event() {
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
                show_add_event.value = false
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
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function save_edge_label() {
            if (!selected_edge.value) return
            const res = await fetch('/case/' + props.case_id + '/edit_timeline_event_link/' + selected_edge.value.id, {
                method: 'POST',
                headers: {'Content-Type': 'application/json', 'X-CSRFToken': document.getElementById("csrf_token").value},
                body: JSON.stringify({ label: edit_link_label.value })
            })
            if (res.status === 200) {
                selected_edge.value = null
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function delete_selected_edge() {
            if (!selected_edge.value) return
            if (!confirm('Delete this link?')) return
            const res = await fetch('/case/' + props.case_id + '/delete_timeline_event_link/' + selected_edge.value.id)
            if (res.status === 200) {
                selected_edge.value = null
                await fetch_graph_data()
            }
            await display_toast(res)
        }

        async function delete_selected_node() {
            if (!selected_node.value) {
                create_message('Click a node first to select it', 'warning-subtle')
                return
            }
            if (!confirm('Delete this event and all its links?')) return
            const res = await fetch('/case/' + props.case_id + '/delete_timeline_event/' + selected_node.value.id)
            if (res.status === 200) {
                selected_node.value = null
                await fetch_graph_data()
            }
            await display_toast(res)
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
            new_description,
            link_source,
            link_target,
            link_label,
            selected_edge,
            selected_node,
            edit_link_label,
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
        </div>

        <!-- Add Event Form -->
        <div v-if="show_add_event" class="card mb-3">
            <div class="card-body">
                <h6 class="card-title mb-3">New Event Node</h6>
                <div class="row g-3">
                    <div class="col-md-4">
                        <label class="form-label">Date / Time</label>
                        <input type="text" class="form-control form-control-sm" v-model="new_date_text"
                               placeholder="e.g. 2024-03-15 14:30, Mar 15 2024...">
                        <div class="form-text">Any common date format is accepted</div>
                    </div>
                    <div class="col-md-8">
                        <label class="form-label">Description</label>
                        <textarea class="form-control form-control-sm" v-model="new_description" rows="2"
                                  placeholder="What happened at this point in time?"></textarea>
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
                <h6 class="card-title mb-3">New Link Between Events</h6>
                <div class="row g-3">
                    <div class="col-md-5">
                        <label class="form-label">Source Event</label>
                        <select class="form-select form-select-sm" v-model="link_source">
                            <option value="">-- Select source --</option>
                            <option v-for="ev in graph_events" :key="ev.id" :value="ev.id">[[ event_label(ev) ]]</option>
                        </select>
                    </div>
                    <div class="col-md-5">
                        <label class="form-label">Target Event</label>
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
                    <input type="text" class="form-control form-control-sm" v-model="edit_link_label" placeholder="Link label" style="max-width: 200px;">
                    <button class="btn btn-success btn-sm" @click="save_edge_label()" title="Save label">
                        <i class="fa-solid fa-check"></i>
                    </button>
                    <button class="btn btn-outline-danger btn-sm" @click="delete_selected_edge()" title="Delete link">
                        <i class="fa-solid fa-trash"></i>
                    </button>
                    <button class="btn btn-outline-secondary btn-sm" @click="selected_edge = null" title="Deselect">
                        <i class="fa-solid fa-xmark"></i>
                    </button>
                </div>
            </div>
        </div>

        <!-- Graph Container -->
        <div id="timeline-graph-container" style="width:100%; height:550px; border:1px solid #dee2e6; border-radius: 6px;"></div>

        <div class="mt-2">
            <small class="text-muted">
                <i class="fa-solid fa-circle-info me-1"></i>
                Drag nodes to rearrange. Click an edge to select it. Click a node to select it for deletion. MISP-imported events are shown in blue.
            </small>
        </div>
    </div>
    `
}
