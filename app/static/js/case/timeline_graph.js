import {display_toast, create_message} from '../toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
const { ref, onMounted, onBeforeUnmount, nextTick } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        cases_info: Object
    },
    setup(props) {
        const graph_events = ref([])
        const graph_links = ref([])
        const graph_total = ref(0)      // events in the case (the graph draws at most graph_max)
        const graph_max = ref(0)
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
                graph_total.value = data.total || data.events.length
                graph_max.value = data.max || 0
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

        // "Create" tool of Pivotick: a small form (date, event, note) saved in the case
        async function persist_node_create({ promptData }) {
            if (!can_edit()) return false
            let refs = {}
            const values = await promptData({
                title: 'New event', submitLabel: 'Add event',
                render: (body) => {
                    body.classList.add('tlg-prompt')
                    body.innerHTML = ''
                    const field = (label, tag, attrs) => {
                        const wrap = body.appendChild(document.createElement('label'))
                        wrap.className = 'tlg-prompt-field'
                        wrap.appendChild(el_text('span', 'tlg-prompt-label', label))
                        const input = wrap.appendChild(document.createElement(tag))
                        Object.assign(input, attrs)
                        input.className = 'form-control form-control-sm'
                        return input
                    }
                    refs.date = field('Date / time', 'input', { type: 'text', placeholder: 'e.g. 2024-03-15 14:30, 01/12/26 14h30…', value: dayjs ? dayjs().format('YYYY-MM-DD HH:mm') : '' })
                    refs.description = field('Event', 'input', { type: 'text', placeholder: 'Short event summary' })
                    refs.note = field('Note (optional)', 'textarea', { rows: 2, placeholder: 'Details' })
                    setTimeout(() => refs.description.focus(), 50)
                },
                getValues: () => ({ date_text: refs.date.value.trim(), description: refs.description.value.trim(), additional_note: refs.note.value.trim() }),
            })
            if (!values) return false
            if (!values.date_text || !values.description) {
                create_message('Date/time and event are required', 'warning-subtle')
                return false
            }
            const res = await post('/case/' + props.case_id + '/create_timeline_event', values)
            if (res.status === 200) {
                touchCaseLastModif(props.cases_info)
                await fetch_graph_data()        // drawn at its place in time
            }
            return false
        }

        // tooltip on hover: a small card in the Flowintel style
        function tooltip_card(element) {
            const d = element.getData ? element.getData() : {}
            const ev = d.event
            const tip = el('div', 'tlg-tip')
            if (ev) {
                const kind = EVENT_KINDS[event_kind(ev)]
                tip.style.setProperty('--tlg-accent', kind.color)
                const head = tip.appendChild(el('div', 'tlg-tip-head'))
                const icon = head.appendChild(el('span', 'tlg-tip-icon'))
                icon.appendChild(el('i', kind.icon))
                const text = head.appendChild(el('div', 'tlg-tip-text'))
                text.appendChild(el('span', 'tlg-tip-kind', kind.label + (d.step ? ' · #' + d.step : '')))
                text.appendChild(el('span', 'tlg-tip-title', ev.description))
                const meta = tip.appendChild(el('div', 'tlg-tip-meta'))
                const when = meta.appendChild(el('span', ''))
                when.appendChild(el('i', 'fa-regular fa-clock'))
                when.appendChild(document.createTextNode(' ' + ev.date_text + (window.dayjs && ev.date_parsed ? ' · ' + dayjs(ev.date_parsed).fromNow() : '')))
                if (ev.file && ev.file.name) {
                    const f = meta.appendChild(el('span', ''))
                    f.appendChild(el('i', 'fa-solid fa-paperclip'))
                    f.appendChild(document.createTextNode(' ' + ev.file.name))
                }
                if (ev.additional_note) tip.appendChild(el('div', 'tlg-tip-note', ev.additional_note.length > 160 ? ev.additional_note.slice(0, 160) + '…' : ev.additional_note))
                return tip
            }
            // a link
            const kinds = { analyst: ['Your link', LINK_COLORS.analyst], misp: ['MISP relationship', LINK_COLORS.misp], chronology: ['Time between events', LINK_COLORS.chronology] }
            const [label, color] = kinds[d.link_type] || ['Link', LINK_COLORS.analyst]
            tip.style.setProperty('--tlg-accent', color)
            const head = tip.appendChild(el('div', 'tlg-tip-head'))
            const icon = head.appendChild(el('span', 'tlg-tip-icon'))
            icon.appendChild(el('i', 'fa-solid fa-link'))
            const text = head.appendChild(el('div', 'tlg-tip-text'))
            text.appendChild(el('span', 'tlg-tip-kind', label))
            text.appendChild(el('span', 'tlg-tip-title', d.label || 'No label'))
            return tip
        }

        function can_edit() {
            const p = props.cases_info && props.cases_info.permission
            const ok = !!(p && (p.admin || (!p.read_only && props.cases_info.present_in_case)))
            if (!ok) create_message('You cannot edit this case.', 'warning-subtle')
            return ok
        }

        // ---- groups (Simplify): one clean card per day / per kind ---------------------------
        function group_kind(group) {
            const first = group.members[0] && group.members[0].getData()
            return EVENT_KINDS[first && first.kind] || EVENT_KINDS.event
        }
        function group_day(group) {
            const first = group.members[0] && group.members[0].getData()
            if (!first || !first.day) return ''
            return window.dayjs ? dayjs(first.day).format('ddd D MMM YYYY') : first.day
        }
        function group_title(group) {
            if (group.title) return group.title
            if (group.rule === 'by-day') return group_day(group)
            if (group.rule === 'by-kind') return group_kind(group).label + 's'
            return 'Group'
        }
        // relations of a group: inside it (shown once opened) and with other events
        function group_links(group) {
            const ids = new Set(group.members.map(m => String(m.id)))
            let inside = 0, outside = 0
            for (const l of graph_links.value) {
                const a = ids.has(String(l.source_event_id)), b = ids.has(String(l.target_event_id))
                if (a && b) inside++
                else if (a || b) outside++
            }
            return { inside, outside }
        }

        function group_card(group) {
            const kind = group.rule === 'by-day' || group.rule === 'by-kind' ? group_kind(group) : null
            const card = el('div', 'tlg-group')
            if (kind) card.style.setProperty('--tlg-accent', kind.color)
            const head = el('div', 'tlg-group-head')
            const icon = el('span', 'tlg-group-icon')
            icon.appendChild(el('i', kind ? kind.icon : 'fa-solid fa-layer-group'))
            head.appendChild(icon)
            const text = el('div', 'tlg-group-text')
            const n = group.members.length
            if (kind) text.appendChild(el('span', 'tlg-group-kind-label', n + ' ' + kind.label + (n > 1 ? 's' : '')))
            text.appendChild(el('span', 'tlg-group-title', group_title(group)))
            head.appendChild(text)
            card.appendChild(head)
            const foot = el('div', 'tlg-group-foot')
            if (group.rule !== 'by-day') {
                for (const [type, count] of Object.entries(group.typeCounts || {})) {
                    const k = EVENT_KINDS[type] || EVENT_KINDS.event
                    const chip = el('span', 'tlg-group-kind')
                    chip.style.setProperty('--tlg-accent', k.color)
                    chip.appendChild(el('i', k.icon))
                    chip.appendChild(document.createTextNode(' ' + count))
                    foot.appendChild(chip)
                }
            }
            const links = group_links(group)
            const rel = (n, icon, title) => {
                const chip = el('span', 'tlg-group-rel')
                chip.title = title
                chip.appendChild(el('i', icon))
                chip.appendChild(document.createTextNode(' ' + n))
                foot.appendChild(chip)
            }
            if (links.inside) rel(links.inside, 'fa-solid fa-diagram-project', links.inside + ' relation' + (links.inside > 1 ? 's' : '') + ' between these events (open the group to see them)')
            if (links.outside) rel(links.outside, 'fa-solid fa-link', links.outside + ' relation' + (links.outside > 1 ? 's' : '') + ' with other events')
            foot.appendChild(el('span', 'tlg-group-hint', 'Double-click to open'))
            card.appendChild(foot)
            return card
        }

        // Pivotick's own text speaks of "nodes" and "edges": here they are events and links
        // (rail, editors, right-click menus, sidebar, modals). Built once from its English catalogue.
        let event_messages = null
        function to_events(text) {
            if (typeof text !== 'string') return text
            return text.replace(/(?<!\{)\b(node|edge)(s?)\b(?!\})/gi, (m, word, plural) => {
                const to = word.toLowerCase() === 'node' ? 'event' : 'link'
                const out = to + plural.toLowerCase()
                if (m === m.toUpperCase()) return out.toUpperCase()
                return m[0] === m[0].toUpperCase() ? out[0].toUpperCase() + out.slice(1) : out
            })
        }
        function messages_for_events() {
            if (event_messages) return event_messages
            const en = (window.Pivotick && window.Pivotick.messagesEn) || {}
            event_messages = {}
            for (const [key, value] of Object.entries(en)) {
                if (typeof value === 'string') event_messages[key] = to_events(value)
                else if (typeof value === 'function') event_messages[key] = (p, i) => to_events(value(p, i))
                else if (value && typeof value === 'object') event_messages[key] = Object.fromEntries(Object.entries(value).map(([f, t]) => [f, to_events(t)]))
            }
            return event_messages
        }

        // Pivotick's buttons (sidebar, table, panels) have text only: add a Font Awesome icon
        const BUTTON_ICONS = [
            [/^open\b/i, 'fa-solid fa-folder-open'], [/^close\b/i, 'fa-solid fa-xmark'], [/^select members/i, 'fa-solid fa-object-group'],
            [/^view in table/i, 'fa-solid fa-table'], [/^delete\b/i, 'fa-solid fa-trash'], [/^edit\b/i, 'fa-solid fa-pen'],
            [/^pull out/i, 'fa-solid fa-arrow-right-from-bracket'], [/^rename/i, 'fa-solid fa-i-cursor'], [/^ungroup/i, 'fa-solid fa-object-ungroup'],
            [/^group\b/i, 'fa-solid fa-object-group'], [/^neighbo/i, 'fa-solid fa-diagram-project'], [/^stats/i, 'fa-solid fa-chart-simple'],
            [/^list\b/i, 'fa-solid fa-list'], [/^focus/i, 'fa-solid fa-crosshairs'], [/^hide\b/i, 'fa-solid fa-eye-slash'],
            [/^show\b/i, 'fa-solid fa-eye'], [/^pin\b/i, 'fa-solid fa-thumbtack'], [/^unpin/i, 'fa-solid fa-thumbtack-slash'],
            [/^export/i, 'fa-solid fa-download'], [/^copy/i, 'fa-regular fa-copy'], [/^add\b/i, 'fa-solid fa-plus'], [/^save\b/i, 'fa-solid fa-check'],
            [/^cancel\b/i, 'fa-solid fa-xmark'],
        ]
        const BUTTON_SELECTOR = '.pvt-sidebar-group-action, .pvt-table-row-action, .pvt-sidebar .pivotick-button, .pvt-modal .pivotick-button'
        let icon_observer = null
        function decorate_buttons(root) {
            for (const b of root.querySelectorAll(BUTTON_SELECTOR)) {
                if (b.dataset.tlgIcon || b.querySelector('i, svg')) continue
                const text = b.textContent.trim()
                const hit = BUTTON_ICONS.find(([re]) => re.test(text))
                b.dataset.tlgIcon = '1'
                if (!hit) continue
                const i = document.createElement('i')
                i.className = hit[1] + ' tlg-btn-icon'
                b.prepend(i)
            }
        }
        function watch_buttons(container) {
            if (icon_observer) icon_observer.disconnect()
            let pending = false
            icon_observer = new MutationObserver(() => {
                if (pending) return
                pending = true
                requestAnimationFrame(() => { pending = false; decorate_buttons(container); decorate_buttons(document.body) })
            })
            icon_observer.observe(container, { childList: true, subtree: true })
            decorate_buttons(container)
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
                i18n: { locale: 'en', messages: messages_for_events() },
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
                            // one group per day and per kind (MISP objects, MISP attributes, files, events):
                            // relations between objects and attributes stay visible between the groups
                            { kind: 'custom', id: 'by-day', label: 'Group by day and kind', description: 'Events of the same day and the same kind together',
                              minSize: 2, partition: (view) => new Map(view.nodes.map(n => [n.id, n.getData().day ? n.getData().day + '|' + n.getData().kind : null]).filter(([, k]) => k)) },
                            { kind: 'custom', id: 'by-kind', label: 'Group by kind', description: 'Events of the same kind together',
                              minSize: 3, enabled: false, partition: (view) => new Map(view.nodes.map(n => [n.id, n.getData().kind])) },
                        ],
                    },
                    editors: {
                        nodeCreator: { enabled: editable },          // asks for date / event / note, saved in the case
                        edgeCreator: { enabled: false },             // no "Add link": the timeline has no relations of its own to create here
                        nodeEditor: { enabled: editable, fields: [
                            { key: 'description', label: 'Event', type: 'text' },
                            { key: 'date_text', label: 'Date / time', type: 'text', placeholder: '2024-03-15 14:30' },
                            { key: 'additional_note', label: 'Note', type: 'textarea', allowEmpty: true },
                        ] },
                        edgeEditor: { enabled: editable, labelPrompt: 'inline', fields: [{ key: 'label', label: 'Label', type: 'text', allowEmpty: true }] },
                        deletion: { enabled: editable },
                    },
                    table: { open: false },
                    tooltip: { enabled: { nodes: true, edges: true, groups: true }, render: tooltip_card },
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
                    groupOutline: (group) => group_title(group) + ' · ' + group.members.length + ' ' + (group.rule === 'by-day' ? group_kind(group).label.toLowerCase() + (group.members.length > 1 ? 's' : '') : 'events'),
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
                    onBeforeNodeCreate: persist_node_create,
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
            watch_buttons(container)
        }

        function toggle_chronology() {
            show_chronology.value = !show_chronology.value
            render_graph()
        }

        // full screen in and out: the canvas changes size, fit the graph to it again
        function on_fullscreen() {
            setTimeout(() => { try { graph && graph.renderer && graph.renderer.fitAndCenterWhenSettled() } catch (e) {} }, 150)
        }
        document.addEventListener('fullscreenchange', on_fullscreen)

        onBeforeUnmount(() => {
            document.removeEventListener('fullscreenchange', on_fullscreen)
            if (icon_observer) icon_observer.disconnect()
            if (graph) graph.destroy()
        })

        onMounted(() => {
            fetch_graph_data()
        })

        return {
            graph_events,
            graph_links,
            graph_total,
            graph_max,
            selected_node,
            show_help,
            show_chronology,
            toggle_chronology,
            fetch_graph_data
        }
    },
    template: `
    <div class="tlg">
        <div class="tlg-toolbar">
            <span class="tlg-toolbar-hint">
                <i class="fa-solid fa-hand-pointer"></i><b>Create</b> (left rail): click the canvas to add an event · click a card for its details · double-click a group to open it
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
                        <li><span class="tlg-help-line" style="--c:#1f3763"></span>Links added on the case: double-click to rename</li>
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

        <div v-if="graph_max && graph_total > graph_max" class="tlg-cap">
            <i class="fa-solid fa-gauge-high"></i>
            <span>This case has <b>[[ graph_total.toLocaleString() ]]</b> events: the graph shows the <b>[[ graph_max.toLocaleString() ]]</b> most recent ones to stay fast. The Timeline tab lists them all.</span>
        </div>

        <!-- Graph -->
        <div id="timeline-graph-container" class="tlg-container"></div>
    </div>
    `
}
