import {display_toast, create_message} from '../toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
import flow_loader from '/static/js/components/flow_loader.js'
const { ref, onMounted, onBeforeUnmount, nextTick } = Vue

export default {
    delimiters: ['[[', ']]'],
    components: { flow_loader },
    props: {
        case_id: Number,
        cases_info: Object
    },
    emits: ['navigate'],
    setup(props, { emit }) {
        const graph_events = ref([])
        const graph_links = ref([])
        const graph_total = ref(0)      // events in the case (the graph draws at most graph_max)
        const graph_max = ref(0)
        const selected_node = ref(null)
        const show_help = ref(false)
        // Chronology links tie each event to the next one with the time between them.
        // They are not relations, so they are off unless asked for.
        const show_chronology = ref(false)
        // Flowintel loading screen over the graph while it is built and centred
        const graph_loading = ref(true)
        // Breadcrumb mode: one level at a time (days → kinds of a day → events), with a path above
        let saved_drill = false
        try { saved_drill = localStorage.getItem('tlg-drill') === '1' } catch (e) {}
        const drill_mode = ref(saved_drill)
        const drill_path = ref([])        // [{ day }, { kind }]
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
        const LINK_COLORS = { analyst: '#1f3763', misp: '#2f6fb0', chronology: '#9aa5b8', timeline: '#0f7b6c' }

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
            const badge = day_badge(node.getData().day)
            if (badge) head.appendChild(badge)
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
            if (node && node.isGroup && node.info) return group_header(el, node.info)
            const ev = event_by_node(node)
            if (!ev) return undefined          // edges, Today: Pivotick's default header
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

        // sidebar header of a group: same look as its card (icon, date, how many events)
        function group_header(el, group) {
            const kind = group.rule === 'day-kind' || group.rule === 'by-kind' ? group_kind(group) : null
            el.innerHTML = ''
            const head = el.appendChild(document.createElement('div'))
            head.className = 'tlg-side-head'
            head.style.setProperty('--tlg-accent', kind ? kind.color : '#1f3763')
            head.appendChild(el_icon(kind ? kind.icon : 'fa-solid fa-calendar-day', 'tlg-side-icon'))
            const text = head.appendChild(document.createElement('div'))
            text.className = 'tlg-side-text'
            const n = group.members.length
            text.appendChild(el_text('span', 'tlg-side-kind', kind ? n + ' ' + kind.label + (n > 1 ? 's' : '') : n + ' event' + (n > 1 ? 's' : '')))
            text.appendChild(el_text('span', 'tlg-side-title', group_title(group)))
            return el
        }

        function prop(icon, text, cls) {
            const v = document.createElement('span')
            v.className = 'tlg-prop' + (cls ? ' ' + cls : '')
            v.appendChild(el_icon(icon))
            v.appendChild(document.createTextNode(' ' + text))
            return v
        }

        // "Go to": the MISP object / attribute or the file the event comes from, in its tab
        function go_to_target(ev) {
            const id = Number(ev.misp_object_id)
            if (id > 0) return { tab: 'misp', misp_object: id, label: 'Open the MISP object', icon: 'fa-solid fa-cube' }
            if (id < 0) return { tab: 'misp', misp_attr: -id, label: 'Open the MISP attribute', icon: 'fa-solid fa-tag' }
            if (ev.file_id) return { tab: 'files', label: 'Open the Files tab', icon: 'fa-solid fa-file-lines' }
            return null
        }
        async function go_to(target) {
            if (document.fullscreenElement) { try { await document.exitFullscreen() } catch (e) {} }
            emit('navigate', target)
        }
        function go_to_button(ev) {
            const target = go_to_target(ev)
            if (!target) return null
            const b = document.createElement('button')
            b.type = 'button'
            b.className = 'tlg-goto'
            b.appendChild(el_icon(target.icon))
            b.appendChild(document.createTextNode(' ' + target.label))
            b.appendChild(el_icon('fa-solid fa-arrow-right tlg-goto-arrow'))
            b.addEventListener('click', () => go_to(target))
            return b
        }

        function node_properties(node) {
            const ev = event_by_node(node)
            if (!ev) return undefined
            const out = []
            const goto = go_to_button(ev)
            if (goto) out.push({ name: 'Go to', value: goto })
            out.push({ name: 'When', value: prop('fa-regular fa-clock', ev.date_text) })
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
            const kind = { analyst: 'Your link', misp: 'MISP relationship', chronology: 'Time between events', timeline: 'Next day in the timeline' }[d.link_type] || 'Link'
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
            if (d.today) {
                tip.style.setProperty('--tlg-accent', '#0f7b6c')
                const head = tip.appendChild(el('div', 'tlg-tip-head'))
                head.appendChild(el('span', 'tlg-tip-icon')).appendChild(el('i', 'fa-solid fa-calendar-check'))
                const text = head.appendChild(el('div', 'tlg-tip-text'))
                text.appendChild(el('span', 'tlg-tip-kind', 'Today'))
                text.appendChild(el('span', 'tlg-tip-title', d.since_last + ' day' + (d.since_last === 1 ? '' : 's') + ' since the last event'))
                return tip
            }
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
            const kinds = { analyst: ['Your link', LINK_COLORS.analyst], misp: ['MISP relationship', LINK_COLORS.misp], chronology: ['Time between events', LINK_COLORS.chronology], timeline: ['Next day in the timeline', LINK_COLORS.timeline] }
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

        // red "today" badge on the cards of today
        function day_badge(day) {
            if (!day) return null
            const today = window.dayjs ? dayjs().format('YYYY-MM-DD') : new Date().toISOString().slice(0, 10)
            if (day !== today) return null           // only the cards of today get the badge
            const b = el('span', 'tlg-day-badge', 'today')
            b.title = 'This happened today'
            return b
        }

        // "Today" marker, added when nothing happened today: how long since the last / first event
        const TODAY_ID = 'today'
        function today_card(node) {
            const d = node.getData()
            const card = el('div', 'tlg-today')
            const head = el('div', 'tlg-group-head')
            const icon = el('span', 'tlg-today-icon')
            icon.appendChild(el('i', 'fa-solid fa-calendar-check'))
            head.appendChild(icon)
            const text = el('div', 'tlg-group-text')
            const label = el('span', 'tlg-today-label', 'Today')
            label.appendChild(el('span', 'tlg-today-here', 'You are here'))
            text.appendChild(label)
            text.appendChild(el('span', 'tlg-group-title', window.dayjs ? dayjs().format('ddd D MMM YYYY') : d.day))
            head.appendChild(text)
            card.appendChild(head)
            const stats = el('div', 'tlg-today-stats')
            const stat = (n, label) => {
                const b = el('span', 'tlg-today-stat')
                b.appendChild(el('b', '', String(n)))
                b.appendChild(document.createTextNode(' ' + label))
                stats.appendChild(b)
            }
            stat(d.since_last, 'day' + (d.since_last === 1 ? '' : 's') + ' since the last event')
            if (d.since_first !== d.since_last) stat(d.since_first, 'day' + (d.since_first === 1 ? '' : 's') + ' since the first')
            card.appendChild(stats)
            return card
        }

        // ---- groups (Simplify): one clean card per day / per kind ---------------------------
        // the day of a drawn node: its own, or (for a group made by an earlier rule) its members'
        function node_day(n) {
            if (n.isGroup) {
                const m = n.info && n.info.members && n.info.members[0]
                return m && m.getData ? m.getData().day : null
            }
            return n.getData ? n.getData().day : null
        }

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
            if (group.rule === 'by-day' || group.rule === 'day-kind') return group_day(group)
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
            // a day: calendar, navy, one chip per kind · a kind (inside a day, or "by kind"): its colour and icon
            const kind = group.rule === 'day-kind' || group.rule === 'by-kind' ? group_kind(group) : null
            const card = el('div', 'tlg-group')
            if (kind) card.style.setProperty('--tlg-accent', kind.color)
            const head = el('div', 'tlg-group-head')
            const icon = el('span', 'tlg-group-icon')
            icon.appendChild(el('i', kind ? kind.icon : (group.rule === 'by-day' ? 'fa-solid fa-calendar-day' : 'fa-solid fa-layer-group')))
            head.appendChild(icon)
            const text = el('div', 'tlg-group-text')
            const n = group.members.length
            text.appendChild(el('span', 'tlg-group-kind-label', kind ? n + ' ' + kind.label + (n > 1 ? 's' : '') : n + ' event' + (n > 1 ? 's' : '')))
            text.appendChild(el('span', 'tlg-group-title', group_title(group)))
            head.appendChild(text)
            const first = group.members[0] && group.members[0].getData()
            const badge = day_badge(first && first.day)
            if (badge) head.appendChild(badge)
            card.appendChild(head)
            const foot = el('div', 'tlg-group-foot')
            if (!kind) {
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
            foot.appendChild(el('span', 'tlg-group-hint', drill_mode.value ? 'Click to open' : 'Double-click to open'))
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

        // The days on one line, in time order: each day has its slot, an opened day takes the
        // width of what it shows, and nothing of another day ever sits in it. Run on every tick.
        const SLOT = 360, HALF_W = 160, MARGIN = 40, PULL = 0.25
        const moved_by_hand = new Set()       // ids the user dragged: never put back on the line
        let dragging = false
        function layout_timeline() {
            if (dragging || !graph || typeof graph.getCanvasNodes !== 'function') return
            const per_day = new Map()
            for (const n of graph.getCanvasNodes()) {
                if (!Number.isFinite(n.x) || !Number.isFinite(n.y) || moved_by_hand.has(String(n.id))) continue
                const d = node_day(n) || '~'                  // no date: after the last day
                if (!per_day.has(d)) per_day.set(d, [])
                per_day.get(d).push(n)
            }
            const days = [...per_day.keys()].sort()
            const slots = days.map(d => {
                const nodes = per_day.get(d)
                if (nodes.length === 1) return { d, nodes, width: SLOT }
                const x1 = Math.min(...nodes.map(n => n.x)), x2 = Math.max(...nodes.map(n => n.x))
                return { d, nodes, width: Math.max(SLOT, x2 - x1 + 2 * HALF_W + MARGIN), x1, x2 }
            })
            let x = -slots.reduce((w, sl) => w + sl.width, 0) / 2
            for (const sl of slots) {
                const center = x + sl.width / 2
                x += sl.width
                if (sl.nodes.length === 1) {                 // a closed day (or a lone event): pinned on the line
                    const n = sl.nodes[0]
                    n.fx = center; n.fy = 0
                    continue
                }
                // an opened day: free inside its slot, pulled to its centre and to the line —
                // until the user moves something: from then on, nothing is pulled anywhere
                if (moved_by_hand.size) { for (const n of sl.nodes) { n.fx = null; n.fy = null } continue }
                const y1 = Math.min(...sl.nodes.map(n => n.y)), y2 = Math.max(...sl.nodes.map(n => n.y))
                const dx = (center - (sl.x1 + sl.x2) / 2) * PULL, dy = (0 - (y1 + y2) / 2) * PULL
                for (const n of sl.nodes) {
                    n.fx = null; n.fy = null
                    // keep the opened day compact: each card drawn toward the slot centre
                    // (the collisions keep them apart)
                    n.x += dx + (center - n.x) * 0.06
                    n.y += dy + (0 - n.y) * 0.06
                }
            }
        }

        // Two open groups (not one inside the other) never share space: their areas are pushed
        // apart, half the overlap each, along the axis where they overlap the least.
        const ZONE_PAD = 30
        function zone_nodes(group, drawn, out) {
            for (const p of group.parts || []) {
                if (drawn.has(p)) out.add(p)
                if (p.isGroup && p.info && p.info.open) zone_nodes(p, drawn, out)
            }
            return out
        }
        function separate_open_groups() {
            const simplify = graph && graph.simplify
            if (dragging || !simplify || typeof simplify.getOpenGroupNodes !== 'function') return
            const open = simplify.getOpenGroupNodes()
            if (open.length < 2) return
            const drawn = new Set(graph.getCanvasNodes())
            const zones = open.map(g => {
                const nodes = [...zone_nodes(g, drawn, new Set())].filter(n => Number.isFinite(n.x) && Number.isFinite(n.y))
                if (!nodes.length) return null
                return {
                    g, nodes, set: new Set(nodes),
                    x1: Math.min(...nodes.map(n => n.x)) - HALF_W - ZONE_PAD, x2: Math.max(...nodes.map(n => n.x)) + HALF_W + ZONE_PAD,
                    y1: Math.min(...nodes.map(n => n.y)) - 80 - ZONE_PAD, y2: Math.max(...nodes.map(n => n.y)) + 80 + ZONE_PAD,
                }
            }).filter(Boolean)
            for (let i = 0; i < zones.length; i++) for (let j = i + 1; j < zones.length; j++) {
                const a = zones[i], b = zones[j]
                // nested (one holds the other): not a clash
                if ([...b.set].every(n => a.set.has(n)) || [...a.set].every(n => b.set.has(n))) continue
                const ox = Math.min(a.x2, b.x2) - Math.max(a.x1, b.x1), oy = Math.min(a.y2, b.y2) - Math.max(a.y1, b.y1)
                if (ox <= 0 || oy <= 0) continue
                const along_x = ox <= oy
                const sign = along_x ? ((a.x1 + a.x2) <= (b.x1 + b.x2) ? -1 : 1) : ((a.y1 + a.y2) <= (b.y1 + b.y2) ? -1 : 1)
                const half = (along_x ? ox : oy) / 2 + 1
                const move = (zone, k) => {
                    for (const n of zone.nodes) {
                        if (b.set.has(n) && a.set.has(n)) continue        // shared: leave it
                        if (along_x) { n.x += k * half; if (n.fx != null) n.fx += k * half }
                        else { n.y += k * half; if (n.fy != null) n.fy += k * half }
                    }
                }
                move(a, sign)
                move(b, -sign)
            }
        }

        // Centre the view on today's day, or on the closest day when nothing happened today
        function focus_today() {
            if (!graph || typeof graph.focusElement !== 'function') return
            const marker = graph.getNode && graph.getNode(TODAY_ID)
            if (marker) return graph.focusElement(marker)
            const today = window.dayjs ? dayjs().format('YYYY-MM-DD') : new Date().toISOString().slice(0, 10)
            const dated = graph_events.value.filter(ev => day_of(ev))
            if (!dated.length) return
            const t = Date.parse(today)
            const best = dated.reduce((a, b) => Math.abs(Date.parse(day_of(b)) - t) < Math.abs(Date.parse(day_of(a)) - t) ? b : a)
            const node = graph.getNode ? graph.getNode(String(best.id)) : null
            if (node) graph.focusElement(node)
        }

        // ---- breadcrumb mode ------------------------------------------------------------------
        // A folder is a fake group (a day, or a kind inside a day) drawn with the group card.
        function folder_card(node) {
            const d = node.getData()
            const members = d.members.map(m => ({ id: m.id, getData: () => m.data }))
            return group_card({ rule: d.level === 'day' ? 'by-day' : 'day-kind', members, typeCounts: d.typeCounts })
        }

        function drill_view(nodes, edges, by_day) {
            const path = drill_path.value
            const events = nodes.filter(n => n.data.event)
            const out = [], rep = new Map()
            const add_folder = (id, level, day, members) => {
                const typeCounts = {}
                for (const m of members) typeCounts[m.data.kind] = (typeCounts[m.data.kind] || 0) + 1
                out.push({ id, data: { folder: true, level, day, kind: 'folder', fkind: members[0].data.kind, label: id,
                                       members: members.map(m => ({ id: m.id, data: m.data })), typeCounts } })
                for (const m of members) rep.set(m.id, id)
            }
            const add_node = (n) => { out.push(n); rep.set(n.id, n.id) }
            if (!path.length) {
                const days = new Map()
                for (const n of events) {
                    if (!n.data.day) { add_node(n); continue }
                    if (!days.has(n.data.day)) days.set(n.data.day, [])
                    days.get(n.data.day).push(n)
                }
                for (const [day, members] of days) add_folder('day:' + day, 'day', day, members)
                const today = nodes.find(n => n.id === TODAY_ID)
                if (today) add_node(today)
            } else {
                const day = path[0].day
                const in_day = events.filter(n => n.data.day === day)
                const kinds = new Map()
                for (const n of in_day) {
                    if (!kinds.has(n.data.kind)) kinds.set(n.data.kind, [])
                    kinds.get(n.data.kind).push(n)
                }
                if (path.length === 1 && kinds.size > 1) {
                    for (const [kind, members] of kinds) {
                        if (members.length === 1) add_node(members[0])          // a lone event: no folder for it
                        else add_folder('kind:' + day + ':' + kind, 'kind', day, members)
                    }
                } else {
                    const kind = path[1] ? path[1].kind : null
                    for (const n of in_day) if (!kind || n.data.kind === kind) add_node(n)
                }
            }
            // relations between what is shown; several between the same two become one "N relations"
            const agg = new Map()
            for (const e of edges) {
                if (e.data.link_type === 'timeline') continue
                const a = rep.get(e.from), b = rep.get(e.to)
                if (!a || !b || a === b) continue
                const key = a + '|' + b
                if (!agg.has(key)) agg.set(key, { list: [], a, b })
                agg.get(key).list.push(e)
            }
            const out_edges = []
            for (const { list, a, b } of agg.values()) {
                if (list.length === 1 && !a.includes(':') && !b.includes(':')) { out_edges.push(list[0]); continue }
                out_edges.push({ id: 'agg-' + a + '-' + b, from: a, to: b,
                                 data: { label: list.length > 1 ? list.length + ' relations' : (list[0].data.label || ''), link_type: list[0].data.link_type, computed: true } })
            }
            // days in time order
            if (!path.length) {
                const order = by_day.map(b => 'day:' + b.day)
                if (out.some(n => n.id === TODAY_ID)) order.push(TODAY_ID)
                for (let i = 1; i < order.length; i++) {
                    const prev = order[i - 1], cur = order[i]
                    const t1 = Date.parse(prev.slice(4)), t2 = cur === TODAY_ID ? Date.now() : Date.parse(cur.slice(4))
                    out_edges.push({ id: 'next-' + prev + '-' + cur, from: prev, to: cur,
                                     data: { label: '⏱ ' + elapsed(t2 - t1), link_type: 'timeline', computed: true } })
                }
            }
            return { nodes: out, edges: out_edges }
        }

        function open_folder(node) {
            const d = node && node.getData ? node.getData() : null
            if (!d || !d.folder) return false
            drill_path.value = d.level === 'day' ? [{ day: d.day }] : [drill_path.value[0], { kind: d.fkind }]
            moved_by_hand.clear()
            render_graph()
            return true
        }
        function drill_to(depth) {
            drill_path.value = drill_path.value.slice(0, depth)
            moved_by_hand.clear()
            render_graph()
        }
        function toggle_drill() {
            drill_mode.value = !drill_mode.value
            try { localStorage.setItem('tlg-drill', drill_mode.value ? '1' : '0') } catch (e) {}
            drill_path.value = []
            moved_by_hand.clear()
            render_graph()
        }
        // the path drawn inside Pivotick's root, so it stays there in full screen
        function draw_crumbs(container) {
            const root = container.querySelector('.pivotick') || container
            root.querySelectorAll('.tlg-crumbs').forEach(n => n.remove())
            if (!drill_mode.value) return
            const nav = el('nav', 'tlg-crumbs tlg-crumbs--overlay')
            nav.setAttribute('aria-label', 'Where you are in the timeline')
            const crumb = (icon, text, depth, current) => {
                const b = el('button', 'tlg-crumb' + (current ? ' is-current' : ''))
                b.type = 'button'
                b.disabled = current
                b.appendChild(el('i', icon))
                b.appendChild(document.createTextNode(text))
                b.addEventListener('click', () => drill_to(depth))
                nav.appendChild(b)
            }
            const path = drill_path.value
            crumb('fa-solid fa-timeline', 'Timeline', 0, !path.length)
            path.forEach((c, i) => {
                nav.appendChild(el('i', 'fa-solid fa-chevron-right tlg-crumb-sep'))
                crumb(c.day ? 'fa-solid fa-calendar-day' : 'fa-solid fa-shapes', crumb_label(c), i + 1, i === path.length - 1)
            })
            root.appendChild(nav)
        }

        function crumb_label(c) {
            if (c.day) return window.dayjs ? dayjs(c.day).format('ddd D MMM YYYY') : c.day
            return (EVENT_KINDS[c.kind] || EVENT_KINDS.event).label + 's'
        }

        // Loading cover inside Pivotick's canvas, between the drawing and its tools: the search,
        // rail, legend and zoom stay visible, only the drawing is hidden while it settles.
        const SKELETON = '<div class="tlg-skeleton" aria-hidden="true">' +
            Array.from({ length: 4 }, (_, i) => '<span class="tlg-sk-card"><span class="tlg-sk-icon"></span><span class="tlg-sk-lines"><span></span><span></span></span></span>' + (i < 3 ? '<span class="tlg-sk-link"></span>' : '')).join('') +
            '</div>'
        function cover_drawing(canvas) {
            const host = canvas.querySelector('.pvt-canvas')
            if (!host) return () => {}
            const cover = document.createElement('div')
            cover.className = 'tlg-loading tlg-loading--inner'
            cover.setAttribute('role', 'status')
            cover.innerHTML = SKELETON + '<div class="tlg-loading-badge"><div class="tlg-fl"></div><span>Building the graph…</span></div>'
            host.appendChild(cover)
            let app = null
            try { app = Vue.createApp(flow_loader, { size: 110, label: 'Building the graph' }); app.mount(cover.querySelector('.tlg-fl')) } catch (e) {}
            return () => { try { app && app.unmount() } catch (e) {} cover.remove() }
        }

        // selecting something opens the details panel on the side
        function show_sidebar() {
            try { graph && graph.UIManager && graph.UIManager.sidebar && graph.UIManager.sidebar.showSidebar() } catch (e) {}
        }

        function render_graph() {
            const container = document.getElementById('timeline-graph-container')
            const canvas = document.getElementById('timeline-graph-canvas')
            if (!container || !canvas) return
            graph_loading.value = true

            if (graph) {
                graph.destroy()
                graph = null
            }

            if (!graph_events.value.length) {
                graph_loading.value = false
                canvas.innerHTML = ''
                const empty = canvas.appendChild(document.createElement('div'))
                empty.className = 'tlg-empty'
                empty.innerHTML = '<i class="fa-solid fa-diagram-project"></i><p>No event yet.</p><small>Add an event, or import MISP objects / files from the Timeline tab.</small>'
                return
            }

            canvas.innerHTML = ''

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
            // the timeline: last event of a day → first event of the next day, always drawn.
            // Once the days are grouped, it links the day cards in time order.
            const by_day = []
            for (const ev of ordered) {
                const d = day_of(ev)
                if (!d) continue
                if (!by_day.length || by_day[by_day.length - 1].day !== d) by_day.push({ day: d, events: [] })
                by_day[by_day.length - 1].events.push(ev)
            }
            for (let i = 1; i < by_day.length; i++) {
                const prev = by_day[i - 1].events[by_day[i - 1].events.length - 1], cur = by_day[i].events[0]
                edges.push({
                    id: 'day-' + by_day[i - 1].day + '-' + by_day[i].day,
                    from: String(prev.id),
                    to: String(cur.id),
                    data: { label: '⏱ ' + elapsed(event_time(cur) - event_time(prev)), link_type: 'timeline', computed: true }
                })
            }
            const today = window.dayjs ? dayjs().format('YYYY-MM-DD') : new Date().toISOString().slice(0, 10)
            if (by_day.length && !by_day.some(b => b.day === today)) {
                const last = by_day[by_day.length - 1].events.slice(-1)[0], first = by_day[0].events[0]
                const days_since = ev => Math.max(0, Math.floor((Date.parse(today) - Date.parse(day_of(ev))) / 86400000))
                nodes.push({ id: TODAY_ID, data: { label: 'Today', kind: 'today', day: today, today: true,
                                                   since_last: days_since(last), since_first: days_since(first) } })
                edges.push({ id: 'day-today', from: String(last.id), to: TODAY_ID,
                             data: { label: '⏱ ' + elapsed(Date.now() - event_time(last)), link_type: 'timeline', computed: true } })
            }
            for (let i = 1; show_chronology.value && i < ordered.length; i++) {
                const prev = ordered[i - 1], cur = ordered[i]
                edges.push({
                    id: 'chrono-' + prev.id + '-' + cur.id,
                    from: String(prev.id),
                    to: String(cur.id),
                    data: { label: '⏱ ' + elapsed(event_time(cur) - event_time(prev)), link_type: 'chronology', computed: true }
                })
            }

            let view_nodes = nodes, view_edges = edges
            if (drill_mode.value) ({ nodes: view_nodes, edges: view_edges } = drill_view(nodes, edges, by_day))

            const nodeStyleMap = {}
            nodeStyleMap.folder = { shape: 'none', color: '#1f3763', text: '', layoutSize: 150, html: folder_card }
            for (const [key, kind] of Object.entries(EVENT_KINDS)) {
                nodeStyleMap[key] = { shape: 'none', color: kind.color, text: '', layoutSize: 140, html: build_card }
            }
            nodeStyleMap.today = { shape: 'none', color: '#0f7b6c', text: '', layoutSize: 130, html: today_card }

            const dark = document.documentElement.getAttribute('data-bs-theme') === 'dark'
            const editable = !!(props.cases_info && props.cases_info.permission &&
                (props.cases_info.permission.admin || (!props.cases_info.permission.read_only && props.cases_info.present_in_case)))

            const options = {
                isDirected: true,
                i18n: { locale: 'en', messages: messages_for_events() },
                // force layout: opening a group makes room, the other cards are pushed away
                layout: { type: 'tree', horizontal: true, spacing: 'manual', levelSpacing: 0.6, siblingSpacing: 0.6 },
                // strong repulsion, wide collisions, little gravity: an opened group clears its area,
                // the other cards are pushed out of it instead of floating inside
                simulation: {
                    fitViewOnExpandCollapse: true,
                    d3ManyBodyStrength: -120,
                    d3CollideRadiusMultiplier: 1.15,
                    d3LinkDistance: 160,
                    // no pull toward the centre of the canvas: a card left alone stays where it is
                    d3GravityStrength: 0,
                    d3GravityStrengthConnected: 0,
                },
                UI: {
                    mode: 'full',
                    theme: dark ? 'dark' : 'light',
                    sidebar: { enabled: true, collapsed: 'auto' },
                    mainHeader: { render: sidebar_header },
                    propertiesPanel: { enabled: true, nodePropertiesMap: node_properties, edgePropertiesMap: edge_properties },
                    neighborsPanel: { enabled: true },
                    // simplified from the start: one group per day (and per kind, optional)
                    simplify: {
                        enabled: !drill_mode.value,           // breadcrumb mode shows one level, no groups
                        typeOf: (node) => node.getData().kind,
                        colorOf: (node) => (EVENT_KINDS[node.getData().kind] || EVENT_KINDS.event).color,
                        typeLabel: (type, count) => count + ' × ' + ((EVENT_KINDS[type] || {}).label || type),
                        rules: [
                            // Nested groups: a rule can fold the groups made by the rules before it.
                            // 1. the events of a day grouped by kind (MISP objects, MISP attributes, files, events)
                            { kind: 'custom', id: 'day-kind', label: 'Inside a day: group by kind', description: 'The events of a day grouped by kind',
                              // only for the days holding several kinds: a one-kind day stays a plain day group
                              minSize: 2, partition: (view) => {
                                  const kinds_of_day = new Map()
                                  for (const n of view.nodes) if (!n.isGroup && n.getData().day) {
                                      const d = n.getData().day
                                      if (!kinds_of_day.has(d)) kinds_of_day.set(d, new Set())
                                      kinds_of_day.get(d).add(n.getData().kind)
                                  }
                                  return new Map(view.nodes.filter(n => !n.isGroup && n.getData().day && kinds_of_day.get(n.getData().day).size > 1)
                                      .map(n => [n.id, n.getData().day + '|' + n.getData().kind]))
                              } },
                            // 2. one group per day, holding the kind groups above and the events left alone
                            { kind: 'custom', id: 'by-day', label: 'Group by day', description: 'One group per day',
                              minSize: 2, partition: (view) => new Map(view.nodes.map(n => [n.id, node_day(n)]).filter(([, d]) => d)) },
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
                    // our own switches in Pivotick's top bar: still there in full screen
                    topBar: { enabled: true, actions: [
                        // the label names the mode the click goes to
                        { id: 'tlg-breadcrumb', placement: 'start',
                          iconClass: drill_mode.value ? 'fa-solid fa-layer-group' : 'fa-solid fa-folder-tree',
                          text: () => drill_mode.value ? 'Grouped view' : 'Breadcrumb mode',
                          title: () => drill_mode.value ? 'Back to the grouped view: days you open in place' : 'One level at a time: days, then the kinds of a day, then its events',
                          onclick: () => { setTimeout(toggle_drill, 0) } },
                        // same rule: the label says what the click does
                        { id: 'tlg-chrono', placement: 'start', iconClass: show_chronology.value ? 'fa-solid fa-eye-slash' : 'fa-solid fa-clock-rotate-left',
                          text: () => show_chronology.value ? 'Hide time between events' : 'Show time between events',
                          title: () => show_chronology.value ? 'Remove the links giving the time between two events' : 'Link each event to the next one with the time between them',
                          onclick: () => { setTimeout(toggle_chronology, 0) } },
                    ] },
                    // no tooltip on hover: selecting a card opens its details in the sidebar
                    tooltip: { enabled: false },
                    minimap: true,
                    notes: { enabled: false },
                    history: { enabled: false },          // no undo / redo arrows: changes are saved in the case
                    pivotMode: false,
                    legend: {
                        position: 'bottom-left',
                        sections: [
                            { key: 'kind', title: 'Event', entries: Object.entries(EVENT_KINDS).map(([id, k]) => ({ id, label: k.label, color: k.color })) },
                            { key: 'link_type', title: 'Link', scope: 'edge', entries: [
                                { id: 'analyst', label: 'Your links', color: LINK_COLORS.analyst },
                                { id: 'misp', label: 'MISP relationship', color: LINK_COLORS.misp },
                                { id: 'timeline', label: 'Next day', color: LINK_COLORS.timeline },
                                { id: 'chronology', label: 'Time between', color: LINK_COLORS.chronology },
                            ] },
                        ],
                    },
                },
                render: {
                    groupStyle: (group) => ({ shape: 'none', text: '', tiers: [], badges: [], layoutSize: 150, html: () => group_card(group) }),
                    groupOutline: (group) => group_title(group) + ' · ' + group.members.length + ' ' + (group.rule === 'day-kind' ? group_kind(group).label + (group.members.length > 1 ? 's' : '') : 'events'),
                    nodeTypeAccessor: (node) => node.getData().kind,
                    nodeStyleMap: nodeStyleMap,
                    edgeTypeAccessor: (edge) => edge.getData().link_type,
                    edgeStyleMap: {
                        analyst: { strokeColor: LINK_COLORS.analyst, strokeWidth: 2 },
                        misp: { strokeColor: LINK_COLORS.misp, dashed: true, animateDash: false },
                        chronology: { strokeColor: LINK_COLORS.chronology, dashed: true, animateDash: false },
                        timeline: { strokeColor: LINK_COLORS.timeline, strokeWidth: 3, markerEnd: 'arrow' },
                    },
                },
                callbacks: {
                    onSimulationTick: () => { layout_timeline(); separate_open_groups() },
                    // a card moved by hand is left to the user from the first move, and the line
                    // layout pauses while dragging (it would pull the card back on every tick)
                    onNodeDragging: (evt, node) => { dragging = true; if (node) moved_by_hand.add(String(node.id)) },
                    onNodeDragended: (evt, node) => { dragging = false; if (node) moved_by_hand.add(String(node.id)) },
                    onBeforeNodeCreate: persist_node_create,
                    onBeforeNodeEditCommit: persist_node_edit,
                    onBeforeEdgeEditCommit: persist_edge_edit,
                    onBeforeDelete: persist_delete,
                    onNodeClick: (evt, node) => { if (drill_mode.value) open_folder(node) },
                    onNodeSelect: (node) => {
                        const ev = graph_events.value.find(e => String(e.id) === String(node.id))
                        if (ev) selected_node.value = ev
                        show_sidebar()
                    },
                    onEdgeSelect: () => show_sidebar(),
                    onNodeBlur: () => { selected_node.value = null },
                }
            }

            graph = new Pivotick(canvas, { nodes: view_nodes, edges: view_edges }, options)
            container.__tlgGraph = graph          // handy from the console
            // hide the build: the loading screen stays until the layout has settled and the
            // view is centred (with a ceiling, so it never stays forever)
            const built = graph
            const uncover = cover_drawing(canvas)
            graph_loading.value = false
            const reveal = () => uncover()
            const settled = (graph.renderer && graph.renderer.fitAndCenterWhenSettled) ? graph.renderer.fitAndCenterWhenSettled() : Promise.resolve()
            Promise.race([settled, new Promise(r => setTimeout(r, 3500))])
                .then(() => { if (graph === built) focus_today() })
                .finally(() => setTimeout(reveal, 250))
            watch_buttons(container)
            draw_crumbs(container)
            // Pivotick puts its own root in full screen, and a redraw (changing mode) replaces it,
            // which leaves full screen. Our container is never replaced: full screen goes on it.
            if (graph.UIManager) {
                graph.UIManager.toggleFullscreen = async (forced) => {
                    const on = forced !== undefined ? forced : !document.fullscreenElement
                    if (on && !document.fullscreenElement) await container.requestFullscreen()
                    else if (!on && document.fullscreenElement) await document.exitFullscreen()
                }
            }
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
            graph_loading,
            drill_mode,
            drill_path,
            drill_to,
            toggle_drill,
            crumb_label,
            fetch_graph_data
        }
    },
    template: `
    <div class="tlg">
        <div class="tlg-toolbar">
            <span class="tlg-toolbar-hint">
                <i class="fa-solid fa-hand-pointer"></i><b>Create</b> (left rail): click the canvas to add an event · click a card for its details · double-click a group to open it
            </span>
            <button class="btn btn-sm ms-auto" :class="show_help ? 'btn-secondary' : 'btn-outline-secondary'"
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
        <div id="timeline-graph-container" class="tlg-container">
            <div id="timeline-graph-canvas" class="tlg-canvas"></div>
            <!-- first load, before Pivotick exists; afterwards the cover is inside Pivotick (cover_drawing) -->
            <div v-if="graph_loading" class="tlg-loading" role="status" aria-live="polite">
                <div class="tlg-loading-badge">
                    <flow_loader :size="110" label="Building the graph"></flow_loader>
                    <span>Building the graph…</span>
                </div>
            </div>
        </div>
    </div>
    `
}
