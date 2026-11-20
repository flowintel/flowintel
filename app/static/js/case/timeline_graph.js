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
        const new_date_text = ref('')
        const new_description = ref('')
        const new_additional_note = ref('')
        const selected_node = ref(null)
        const show_help = ref(false)
        // Chronology links tie each event to the next one with the time between them.
        // They are not relations, so they are off unless asked for.
        const show_chronology = ref(false)
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
        // Flowintel palette (navy / blue / teal / amber), the same on every theme
        const EVENT_KINDS = {
            event: { label: 'Event', color: '#1f3763', icon: 'fa-solid fa-clock' },
            misp_object: { label: 'MISP object', color: '#2f6fb0', icon: 'fa-solid fa-cube' },
            misp_attribute: { label: 'MISP attribute', color: '#c25b12', icon: 'fa-solid fa-tag' },
            file: { label: 'Imported file', color: '#0f7b6c', icon: 'fa-solid fa-file-lines' },
        }
        const LINK_COLORS = { analyst: '#1f3763', misp: '#2f6fb0', chronology: '#9aa5b8' }

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

        // ---- details shown in the Pivotick sidebar (header + properties) -------------------
        function day_of(ev) { return (ev.date_parsed || '').slice(0, 10) || null }
        function event_by_node(node) { return node && node.getData && node.getData().event }

        function sidebar_header(el, ctx) {
            const node = ctx && ctx.node
            const ev = event_by_node(node)
            if (!ev) return undefined          // groups, edges: Pivotick's default header
            const kind = EVENT_KINDS[event_kind(ev)]
            el.innerHTML = ''
            const head = el.appendChild(document.createElement('div'))
            head.className = 'tlg-side-head'
            head.style.setProperty('--tlg-accent', kind.color)
            const icon = head.appendChild(el_icon(kind.icon, 'tlg-side-icon'))
            const text = head.appendChild(document.createElement('div'))
            text.className = 'tlg-side-text'
            text.appendChild(el_text('span', 'tlg-side-kind', kind.label + (node.getData().step ? ' · #' + node.getData().step : '')))
            text.appendChild(el_text('span', 'tlg-side-title', ev.description))
            return el
        }

        function prop(icon, text, cls) {
            const v = document.createElement('span')
            v.className = 'tlg-prop' + (cls ? ' ' + cls : '')
            v.appendChild(el_icon(icon))
            v.appendChild(document.createTextNode(' ' + text))
            return v
        }

        function node_properties(node) {
            const ev = event_by_node(node)
            if (!ev) return undefined
            const out = [{ name: 'When', value: prop('fa-regular fa-clock', ev.date_text) }]
            const day = day_of(ev)
            if (day && window.dayjs) out.push({ name: 'Since', value: prop('fa-solid fa-hourglass-half', dayjs(ev.date_parsed).fromNow()) })
            if (ev.additional_note) out.push({ name: 'Note', value: el_text('span', 'tlg-prop-note', ev.additional_note) })
            if (ev.file && ev.file.name) {
                const a = document.createElement('a')
                a.className = 'tlg-prop'
                a.href = '/case/' + props.case_id + '/download_case_file/' + ev.file.id
                a.appendChild(el_icon('fa-solid fa-paperclip'))
                a.appendChild(document.createTextNode(' ' + ev.file.name))
                out.push({ name: 'File', value: a })
            }
            if (ev.misp_object_id) out.push({ name: 'Source', value: prop(EVENT_KINDS[event_kind(ev)].icon, EVENT_KINDS[event_kind(ev)].label + ' #' + Math.abs(ev.misp_object_id)) })
            const links = graph_links.value.filter(l => String(l.source_event_id) === String(ev.id) || String(l.target_event_id) === String(ev.id))
            out.push({ name: 'Links', value: prop('fa-solid fa-link', links.length ? links.length + ' link' + (links.length > 1 ? 's' : '') : 'none') })
            out.push({ name: 'Added', value: prop('fa-solid fa-calendar-plus', ev.creation_date) })
            return out
        }

        function edge_properties(edge) {
            const d = edge.getData ? edge.getData() : {}
            const kind = { analyst: 'Your link', misp: 'MISP relationship', chronology: 'Time between events' }[d.link_type] || 'Link'
            return [
                { name: 'Kind', value: prop('fa-solid fa-link', kind) },
                { name: 'Label', value: el_text('span', '', d.label || '—') },
            ]
        }

        function el_icon(cls, wrapCls) {
            const i = document.createElement('i')
            i.className = cls
            if (!wrapCls) return i
            const w = document.createElement('span')
            w.className = wrapCls
            w.appendChild(i)
            return w
        }
        function el_text(tag, cls, text) { const n = document.createElement(tag); if (cls) n.className = cls; n.textContent = text; return n }

        // ---- writes from the graph itself (Pivotick editors), saved in the case -------------
        const csrf = () => document.getElementById('csrf_token').value
        async function post(url, body) {
            const res = await fetch(url, { method: 'POST', headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() }, body: JSON.stringify(body) })
            display_toast(res.clone ? res.clone() : res)
            return res
        }

        async function persist_edge_create({ source, target, promptLabel }) {
            if (!can_edit()) return false
            const label = promptLabel ? await promptLabel() : ''
            if (label === null) return false
            const res = await post('/case/' + props.case_id + '/create_timeline_event_link',
                { source_event_id: parseInt(source.id), target_event_id: parseInt(target.id), label: label || '' })
            if (res.status !== 200) return false
            const lk = (await res.json()).link
            graph_links.value.push(lk)
            touchCaseLastModif(props.cases_info)
            return { accept: true, id: String(lk.id), data: { label: lk.label || '', link_id: String(lk.id), automatic: false, link_type: 'analyst' } }
        }

        async function persist_node_edit({ node, nextData }) {
            const ev = event_by_node(node)
            if (!ev || !can_edit()) return false
            const res = await post('/case/' + props.case_id + '/edit_timeline_event/' + ev.id, {
                date_text: nextData.date_text ?? ev.date_text, description: nextData.description ?? ev.description,
                additional_note: nextData.additional_note ?? ev.additional_note ?? '',
            })
            if (res.status !== 200) return false
            await fetch_graph_data()          // date may move the card: redraw in time order
            touchCaseLastModif(props.cases_info)
            return true
        }

        async function persist_edge_edit({ edge, nextData }) {
            const d = edge.getData()
            if (d.link_type !== 'analyst' || !can_edit()) {
                create_message('Only the links you added can be edited here.', 'info-subtle')
                return false
            }
            const res = await post('/case/' + props.case_id + '/edit_timeline_event_link/' + d.link_id, { label: nextData.label || '' })
            if (res.status !== 200) return false
            const lk = graph_links.value.find(l => String(l.id) === String(d.link_id))
            if (lk) lk.label = nextData.label || ''
            touchCaseLastModif(props.cases_info)
            return true
        }

        async function persist_delete({ nodes, edges }) {
            if (!can_edit()) return false
            const ok = await confirmDelete({
                title: 'Delete from the case?',
                message: (nodes.length ? nodes.length + ' event(s)' : '') + (nodes.length && edges.length ? ' and ' : '') + (edges.length ? edges.length + ' link(s)' : '') + ' will be removed from the case timeline.'
            })
            if (!ok) return false
            for (const n of nodes) {
                const ev = event_by_node(n)
                if (ev) await fetch('/case/' + props.case_id + '/delete_timeline_event/' + ev.id)
            }
            for (const e of edges) {
                const d = e.getData ? e.getData() : {}
                if (d.link_type === 'analyst') await fetch('/case/' + props.case_id + '/delete_timeline_event_link/' + d.link_id)
            }
            touchCaseLastModif(props.cases_info)
            await fetch_graph_data()
            return false                       // the graph is redrawn from the case data
        }

        function can_edit() {
            const p = props.cases_info && props.cases_info.permission
            const ok = !!(p && (p.admin || (!p.read_only && props.cases_info.present_in_case)))
            if (!ok) create_message('You cannot edit this case.', 'warning-subtle')
            return ok
        }

        // ---- groups (Simplify): one clean card per day / per kind ---------------------------
        function group_title(group) {
            if (group.title) return group.title
            const first = group.members[0] && group.members[0].getData()
            if (group.rule === 'by-day' && first && first.day) {
                return window.dayjs ? dayjs(first.day).format('ddd D MMM YYYY') : first.day
            }
            if (group.rule === 'by-kind' && first) return (EVENT_KINDS[first.kind] || EVENT_KINDS.event).label + 's'
            return 'Group'
        }

        function group_card(group) {
            const card = el('div', 'tlg-group')
            const head = el('div', 'tlg-group-head')
            const icon = el('span', 'tlg-group-icon')
            icon.appendChild(el('i', group.rule === 'by-kind' ? 'fa-solid fa-shapes' : 'fa-solid fa-calendar-day'))
            head.appendChild(icon)
            const text = el('div', 'tlg-group-text')
            text.appendChild(el('span', 'tlg-group-title', group_title(group)))
            const n = group.members.length
            text.appendChild(el('span', 'tlg-group-count', n + ' event' + (n > 1 ? 's' : '')))
            head.appendChild(text)
            card.appendChild(head)
            const kinds = el('div', 'tlg-group-kinds')
            for (const [type, count] of Object.entries(group.typeCounts || {})) {
                const k = EVENT_KINDS[type] || EVENT_KINDS.event
                const chip = el('span', 'tlg-group-kind')
                chip.style.setProperty('--tlg-accent', k.color)
                chip.title = count + ' × ' + k.label
                chip.appendChild(el('i', k.icon))
                chip.appendChild(document.createTextNode(' ' + count))
                kinds.appendChild(chip)
            }
            card.appendChild(kinds)
            card.appendChild(el('div', 'tlg-group-hint', 'Double-click to open'))
            return card
        }

        function render_graph() {
            const container = document.getElementById('timeline-graph-container')
            if (!container) return

            if (graph) {
                graph.destroy()
                graph = null
            }

            if (!graph_events.value.length) {
                container.innerHTML = ''
                const empty = container.appendChild(document.createElement('div'))
                empty.className = 'tlg-empty'
                empty.innerHTML = '<i class="fa-solid fa-diagram-project"></i><p>No event yet.</p><small>Add an event, or import MISP objects / files from the Timeline tab.</small>'
                return
            }

            container.innerHTML = ''

            const ordered = chronological(graph_events.value)
            const step_of = new Map(ordered.map((ev, i) => [ev.id, i + 1]))

            const nodes = graph_events.value.map(ev => ({
                id: String(ev.id),
                data: {
                    label: ev.description,
                    description: ev.date_text,
                    kind: event_kind(ev),
                    day: day_of(ev),
                    step: step_of.get(ev.id) || null,
                    event: ev,
                    // editable fields (Pivotick node editor)
                    date_text: ev.date_text,
                    additional_note: ev.additional_note || '',
                }
            }))

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
            for (let i = 1; show_chronology.value && i < ordered.length; i++) {
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
                nodeStyleMap[key] = { shape: 'none', color: kind.color, text: '', layoutSize: 140, html: build_card }
            }

            const dark = document.documentElement.getAttribute('data-bs-theme') === 'dark'
            const editable = !!(props.cases_info && props.cases_info.permission &&
                (props.cases_info.permission.admin || (!props.cases_info.permission.read_only && props.cases_info.present_in_case)))

            const options = {
                isDirected: true,
                layout: { type: 'structured', gap: 48, trayPosition: 'bottom' },
                UI: {
                    mode: 'full',
                    theme: dark ? 'dark' : 'light',
                    sidebar: { enabled: true, collapsed: 'auto' },
                    mainHeader: { render: sidebar_header },
                    propertiesPanel: { enabled: true, nodePropertiesMap: node_properties, edgePropertiesMap: edge_properties },
                    neighborsPanel: { enabled: true },
                    // simplified from the start: one group per day (and per kind, optional)
                    simplify: {
                        enabled: true,
                        typeOf: (node) => node.getData().kind,
                        colorOf: (node) => (EVENT_KINDS[node.getData().kind] || EVENT_KINDS.event).color,
                        typeLabel: (type, count) => count + ' × ' + ((EVENT_KINDS[type] || {}).label || type),
                        rules: [
                            { kind: 'custom', id: 'by-day', label: 'Group by day', description: 'One group per day with several events',
                              minSize: 2, partition: (view) => new Map(view.nodes.map(n => [n.id, n.getData().day]).filter(([, d]) => d)) },
                            { kind: 'custom', id: 'by-kind', label: 'Group by kind', description: 'Events of the same kind together',
                              minSize: 3, enabled: false, partition: (view) => new Map(view.nodes.map(n => [n.id, n.getData().kind])) },
                        ],
                    },
                    editors: {
                        nodeCreator: { enabled: false },             // events need a date: created with "Add event"
                        edgeCreator: { enabled: editable },
                        nodeEditor: { enabled: editable, fields: [
                            { key: 'description', label: 'Event', type: 'text' },
                            { key: 'date_text', label: 'Date / time', type: 'text', placeholder: '2024-03-15 14:30' },
                            { key: 'additional_note', label: 'Note', type: 'textarea', allowEmpty: true },
                        ] },
                        edgeEditor: { enabled: editable, labelPrompt: 'inline', fields: [{ key: 'label', label: 'Label', type: 'text', allowEmpty: true }] },
                        deletion: { enabled: editable },
                    },
                    table: { open: false },
                    minimap: true,
                    notes: { enabled: false },
                    pivotMode: false,
                    legend: {
                        position: 'bottom-left',
                        sections: [
                            { key: 'kind', title: 'Event', entries: Object.entries(EVENT_KINDS).map(([id, k]) => ({ id, label: k.label, color: k.color })) },
                            { key: 'link_type', title: 'Link', scope: 'edge', entries: [
                                { id: 'analyst', label: 'Your links', color: LINK_COLORS.analyst },
                                { id: 'misp', label: 'MISP relationship', color: LINK_COLORS.misp },
                                { id: 'chronology', label: 'Time between', color: LINK_COLORS.chronology },
                            ] },
                        ],
                    },
                },
                render: {
                    groupStyle: (group) => ({ shape: 'none', text: '', tiers: [], badges: [], layoutSize: 135, html: () => group_card(group) }),
                    groupOutline: (group) => group_title(group) + ' · ' + group.members.length + ' events',
                    nodeTypeAccessor: (node) => node.getData().kind,
                    nodeStyleMap: nodeStyleMap,
                    edgeTypeAccessor: (edge) => edge.getData().link_type,
                    edgeStyleMap: {
                        analyst: { strokeColor: LINK_COLORS.analyst, strokeWidth: 2 },
                        misp: { strokeColor: LINK_COLORS.misp, dashed: true, animateDash: false },
                        chronology: { strokeColor: LINK_COLORS.chronology, dashed: true, animateDash: false },
                    },
                },
                callbacks: {
                    onBeforeEdgeCreate: persist_edge_create,
                    onBeforeNodeEditCommit: persist_node_edit,
                    onBeforeEdgeEditCommit: persist_edge_edit,
                    onBeforeDelete: persist_delete,
                    onNodeSelect: (node) => {
                        const ev = graph_events.value.find(e => String(e.id) === String(node.id))
                        if (ev) selected_node.value = ev
                    },
                    onNodeBlur: () => { selected_node.value = null },
                }
            }

            graph = new Pivotick(container, { nodes: nodes, edges: edges }, options)
        }

        function toggle_chronology() {
            show_chronology.value = !show_chronology.value
            render_graph()
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

        // Optional picker next to the free-text date field (see
        // timeline_date_picker.js); the date is applied on "Validate".
        function open_date_picker(event) {
            open_timeline_date_picker(event.currentTarget, new_date_text.value, value => {
                new_date_text.value = value
            })
        }

        onMounted(() => {
            fetch_graph_data()
        })

        return {
            graph_events,
            graph_links,
            show_add_event,
            new_date_text,
            open_date_picker,
            new_description,
            new_additional_note,
            selected_node,
            show_help,
            show_chronology,
            toggle_chronology,
            add_graph_event,
            fetch_graph_data
        }
    },
    template: `
    <div class="tlg">
        <div class="tlg-toolbar">
            <button class="btn btn-primary btn-sm" @click="show_add_event = !show_add_event" title="Add an event to the case timeline">
                <i class="fa-solid fa-plus me-1"></i>Add event
            </button>
            <span class="tlg-toolbar-hint">
                <i class="fa-solid fa-hand-pointer"></i>Click a card for its details · drag from a card to another to link them · double-click a group to open it
            </span>
            <button class="btn btn-sm ms-auto" :class="show_chronology ? 'btn-secondary' : 'btn-outline-secondary'"
                    @click="toggle_chronology()" :aria-pressed="show_chronology"
                    title="Link each event to the next one with the time between them">
                <i class="fa-solid fa-clock-rotate-left me-1"></i>Time between events
            </button>
            <button class="btn btn-sm" :class="show_help ? 'btn-secondary' : 'btn-outline-secondary'"
                    @click="show_help = !show_help" title="How to read this graph" aria-label="How to read this graph">
                <i class="fa-solid fa-question"></i>
            </button>
        </div>

        <!-- Add event -->
        <div v-if="show_add_event" class="tlg-form">
            <div class="tlg-form-head">
                <span class="tlg-form-icon"><i class="fa-solid fa-clock"></i></span>
                <div><b>New event</b><small>It appears in the timeline and in the graph, at its place in time.</small></div>
                <button class="btn-close ms-auto" @click="show_add_event = false" aria-label="Close" title="Close"></button>
            </div>
            <div class="row g-3">
                <div class="col-md-4">
                    <label class="form-label">Date / time</label>
                    <div class="input-group input-group-sm">
                        <input type="text" class="form-control form-control-sm" v-model="new_date_text"
                               placeholder="e.g. 2024-03-15 14:30, 01/12/26 14h30…" @keyup.enter="add_graph_event()">
                        <button type="button" class="btn btn-outline-secondary" @click="open_date_picker($event)" title="Pick a date (optional)" aria-label="Pick a date">
                            <i class="fa-regular fa-calendar"></i>
                        </button>
                    </div>
                </div>
                <div class="col-md-8">
                    <label class="form-label">Event</label>
                    <input type="text" class="form-control form-control-sm" v-model="new_description" placeholder="Short event summary" @keyup.enter="add_graph_event()">
                </div>
                <div class="col-12">
                    <label class="form-label">Note <small class="text-body-secondary">(optional)</small></label>
                    <textarea class="form-control form-control-sm" v-model="new_additional_note" rows="2" placeholder="Details"></textarea>
                </div>
            </div>
            <div class="tlg-form-foot">
                <button class="btn btn-secondary btn-sm" @click="show_add_event = false">Cancel</button>
                <button class="btn btn-primary btn-sm" @click="add_graph_event()"><i class="fa-solid fa-plus me-1"></i>Add event</button>
            </div>
        </div>

        <!-- How to read the graph -->
        <div v-if="show_help" class="tlg-form tlg-help">
            <div class="tlg-form-head">
                <span class="tlg-form-icon"><i class="fa-solid fa-circle-question"></i></span>
                <div><b>How to read this graph</b><small>It starts simplified: events of the same day are grouped.</small></div>
                <button class="btn-close ms-auto" @click="show_help = false" aria-label="Close" title="Close"></button>
            </div>
            <div class="row g-3">
                <div class="col-md-4">
                    <div class="tlg-help-title">Cards</div>
                    <ul class="tlg-help-list">
                        <li><span class="tlg-help-dot" style="background:#1f3763"></span>Event added by hand</li>
                        <li><span class="tlg-help-dot" style="background:#2f6fb0"></span>From a MISP object</li>
                        <li><span class="tlg-help-dot" style="background:#c25b12"></span>From a MISP attribute</li>
                        <li><span class="tlg-help-dot" style="background:#0f7b6c"></span>From an imported file</li>
                    </ul>
                    <small class="text-body-secondary"><span class="tlg-card-step">#3</span> is the place of the event in time.</small>
                </div>
                <div class="col-md-4">
                    <div class="tlg-help-title">Links</div>
                    <ul class="tlg-help-list">
                        <li><span class="tlg-help-line" style="--c:#1f3763"></span>Your links: drag from a card to another, double-click to rename</li>
                        <li><span class="tlg-help-line tlg-help-line-dashed" style="--c:#2f6fb0"></span>MISP relationships (managed in the MISP tab)</li>
                        <li><span class="tlg-help-line tlg-help-line-dashed" style="--c:#9aa5b8"></span>Time between two events (“Time between events”)</li>
                    </ul>
                </div>
                <div class="col-md-4">
                    <div class="tlg-help-title">Groups &amp; tools</div>
                    <ul class="tlg-help-list tlg-help-plain">
                        <li><i class="fa-solid fa-layer-group"></i>Double-click a group to open it, × to close it</li>
                        <li><i class="fa-solid fa-wand-magic-sparkles"></i>Simplify (left rail): group by day / by kind on or off</li>
                        <li><i class="fa-solid fa-table"></i>Table, search and filters in the graph toolbar</li>
                        <li><i class="fa-solid fa-trash"></i>Delete / Suppr removes the selection from the case</li>
                    </ul>
                </div>
            </div>
        </div>

        <!-- Graph -->
        <div id="timeline-graph-container" class="tlg-container"></div>
    </div>
    `
}
