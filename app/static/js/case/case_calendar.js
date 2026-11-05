import { create_message } from '/static/js/toaster.js'
/**
 * case_calendar.js — Calendar panel of a case: everything dated in the case in one place.
 *
 * Data from /case/<id>/calendar (case_calendar_core.py). Drawn with FullCalendar,
 * the library of the Calendar section, in month, week and list views. Above it:
 * a search box and one chip per kind of item to show or hide it.
 * A click on an item emits `navigate` with its target ({tab, task}) so the case
 * page can open the right tab or task.
 */
const { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue

const KINDS = [
    { key: 'deadline', label: 'Deadlines', icon: 'fa-solid fa-hourglass-half', color: '#dc3545', hint: 'Deadlines of the case and of its tasks' },
    { key: 'task', label: 'Tasks', icon: 'fa-solid fa-list-check', color: '#0d6efd', hint: 'Tasks created and finished' },
    { key: 'case', label: 'Case', icon: 'fa-solid fa-briefcase', color: '#6f42c1', hint: 'Case created, completed, recurrence' },
    { key: 'timeline', label: 'Timeline', icon: 'fa-solid fa-timeline', color: '#d63384', hint: 'Events of the case timeline, at their own date' },
    { key: 'misp', label: 'MISP', icon: 'fa-solid fa-shield-halved', color: '#0d9fb8', hint: 'MISP objects, attributes and references added' },
    { key: 'seen', label: 'First / last seen', icon: 'fa-solid fa-eye', color: '#20a0a0', hint: 'First seen and last seen of MISP attributes' },
    { key: 'sync', label: 'MISP sync', icon: 'fa-solid fa-rotate', color: '#e8730c', hint: 'Sync runs, next scheduled sync, conflicts' },
    { key: 'file', label: 'Files', icon: 'fa-solid fa-paperclip', color: '#198754', hint: 'Files uploaded to the case and its tasks' },
    { key: 'history', label: 'History', icon: 'fa-solid fa-clock-rotate-left', color: '#6c757d', hint: 'Every line of the case history' },
    { key: 'audit', label: 'Audit', icon: 'fa-solid fa-user-shield', color: '#adb5bd', hint: 'Audit log of the case' },
]
// At first the case itself, its tasks, the incident timeline and MISP syncs, so the month
// stays readable. Deadlines and everything else are one chip away.
const HIDDEN_BY_DEFAULT = ['deadline', 'file', 'misp', 'seen', 'history', 'audit']

function date_only(iso) {
    const d = new Date(iso)
    return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
}

function next_day(iso) {
    const d = new Date(iso)
    d.setDate(d.getDate() + 1)
    return date_only(d.toISOString())
}

export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
    },
    emits: ['navigate'],
    setup(props, { emit }) {
        const items = ref([])
        const loading = ref(true)
        const include_logs = ref(false)
        const search = ref('')
        const hidden = ref(new Set(HIDDEN_BY_DEFAULT))
        const holder = ref(null)
        const month_picker = ref(null)
        const modal_el = ref(null)
        const preview = ref(null)        // item under the mouse: small floating card
        const preview_pos = ref({ x: 0, y: 0 })
        const opened = ref(null)         // item clicked: full detail modal
        let calendar = null
        let modal = null
        let preview_timer = null

        const counts = computed(() => {
            const c = {}
            for (const it of items.value) c[it.kind] = (c[it.kind] || 0) + 1
            return c
        })
        const kinds = computed(() => KINDS.filter(k => counts.value[k.key]))
        const shown_kinds = computed(() => kinds.value.filter(k => !hidden.value.has(k.key)).length)
        const filtered_out = computed(() => shown_kinds.value < kinds.value.length)

        const visible = computed(() => {
            const q = search.value.trim().toLowerCase()
            return items.value.filter(it =>
                !hidden.value.has(it.kind) &&
                (!q || (it.title + ' ' + it.detail).toLowerCase().includes(q)))
        })

        function kind_info(key) {
            return KINDS.find(k => k.key === key) || KINDS[KINDS.length - 1]
        }

        function to_event(it) {
            const kind = kind_info(it.kind)
            // Same look as the Calendar page: a solid bar in the kind's colour, white text
            const ev = {
                id: it.id,
                title: it.title,
                backgroundColor: kind.color,
                borderColor: kind.color,
                textColor: '#fff',
                // Items of a finished task look disabled, so what is done reads at a glance
                classNames: ['ccal-event', 'ccal-' + it.kind].concat(it.target && it.target.completed ? ['ccal-done'] : []),
                extendedProps: { item: it, color: kind.color, icon: kind.icon },
            }
            if (it.all_day) {
                // FullCalendar's all-day end is exclusive: a bar ending on the 17th stops on the 18th
                ev.allDay = true
                ev.start = date_only(it.start)
                ev.end = it.end ? next_day(it.end) : undefined
            } else {
                ev.start = it.start
                if (it.end) ev.end = it.end
            }
            ev.display = 'block'
            return ev
        }

        // Duration of a task / the case, for the progress bar of its preview:
        // from creation to completion (or to the deadline), where today stands, time left
        function period_info(item) {
            const p = item && item.period
            if (!p || !p.start) return null
            const day = 86400000
            const start = new Date(p.start).getTime()
            const deadline = p.deadline ? new Date(p.deadline).getTime() : null
            const finish = p.finish ? new Date(p.finish).getTime() : null
            const now = Date.now()
            const end = finish || deadline
            const short = t => new Date(t).toLocaleDateString(undefined, { day: '2-digit', month: 'short' })
            const span_days = t => { const d = Math.round(Math.abs(t) / day); return d <= 0 ? 'less than a day' : d + ' day' + (d > 1 ? 's' : '') }

            let percent = null, state = 'open', status = ''
            if (finish) {
                percent = 100
                state = deadline && finish > deadline ? 'late' : 'done'
                status = deadline
                    ? (finish > deadline ? 'Finished ' + span_days(finish - deadline) + ' after the deadline' : 'Finished ' + span_days(deadline - finish) + ' before the deadline')
                    : 'Finished in ' + span_days(finish - start)
            } else if (deadline) {
                percent = Math.max(0, Math.min(100, (now - start) / Math.max(1, deadline - start) * 100))
                state = now > deadline ? 'late' : (deadline - now < 2 * day ? 'soon' : 'open')
                status = now > deadline ? span_days(now - deadline) + ' overdue' : span_days(deadline - now) + ' left'
            } else {
                status = 'Open for ' + span_days(now - start) + ', no deadline'
            }
            return {
                from: short(start),
                to: end ? short(end) : 'no deadline',
                to_label: finish ? 'Finished' : 'Deadline',
                percent, state, status,
                time_required: p.time_required,
            }
        }

        // A deadline also colours its whole day
        function deadline_background(it) {
            return {
                id: it.id + '-bg',
                start: date_only(it.start),
                allDay: true,
                display: 'background',
                classNames: ['ccal-deadline-bg'],
                backgroundColor: kind_info('deadline').color,
            }
        }

        // One event: kind icon, time, title. Built with textContent only.
        function event_content(arg) {
            const p = arg.event.extendedProps
            // The day tint behind a deadline is a background event with no item: nothing to draw
            if (!p.item) return { domNodes: [] }
            const box = document.createElement('div')
            box.className = 'ccal-ev'
            box.style.setProperty('--ccal-c', p.color)
            const icon = document.createElement('i')
            icon.className = (p.item.target && p.item.target.completed ? 'fa-solid fa-circle-check' : p.icon) + ' ccal-ev-icon'
            box.appendChild(icon)
            if (!arg.event.allDay && arg.timeText && arg.view.type !== 'listMonth') {
                const t = document.createElement('span')
                t.className = 'ccal-ev-time'
                t.textContent = arg.timeText
                box.appendChild(t)
            }
            // A deadline says whose it is: "Task" or "Case"
            // A deadline says whose it is ("Task" / "Case"), a task entry what happened to it
            const tag_text = p.item.kind === 'deadline' && p.item.label ? p.item.label.split(' ')[0]
                : p.item.kind === 'task' ? ({ 'Task created': 'New', 'Task finished': 'Done', 'Task created and finished': 'New · Done' })[p.item.label]
                : null
            if (tag_text) {
                const tag = document.createElement('span')
                tag.className = 'ccal-ev-tag ccal-ev-tag-' + p.item.kind
                tag.textContent = tag_text
                box.appendChild(tag)
            }
            const title = document.createElement('span')
            title.className = 'ccal-ev-title'
            title.textContent = arg.event.title
            box.appendChild(title)
            // Straight to the right place, without the detail window
            const go = document.createElement('button')
            go.type = 'button'
            go.className = 'ccal-ev-go'
            go.title = target_label(p.item.target)
            go.setAttribute('aria-label', go.title)
            const arrow = document.createElement('i')
            arrow.className = 'fa-solid fa-arrow-right'
            go.appendChild(arrow)
            go.addEventListener('click', (e) => {
                e.preventDefault()
                e.stopPropagation()
                hide_preview()
                close_more_popover()
                emit('navigate', p.item.target)
            })
            box.appendChild(go)
            if (p.item.status && arg.view.type === 'listMonth') {
                const b = document.createElement('span')
                b.className = 'badge rounded-pill ms-2 text-bg-' + (p.item.status.style || 'secondary')
                b.textContent = p.item.status.name
                box.appendChild(b)
            }
            return { domNodes: [box] }
        }

        // The "+N more" popover of a day stays open on its own: close it when an item
        // opens the detail window or leads somewhere else
        function close_more_popover() {
            holder.value?.querySelectorAll('.fc-popover .fc-popover-close').forEach(btn => btn.click())
        }

        function show_preview(item, jsEvent) {
            clearTimeout(preview_timer)
            preview_timer = setTimeout(() => {
                const w = 320, margin = 14
                let x = jsEvent.clientX + margin, y = jsEvent.clientY + margin
                if (x + w > window.innerWidth - 8) x = jsEvent.clientX - w - margin
                if (y + 260 > window.innerHeight) y = Math.max(8, jsEvent.clientY - 260 - margin)
                preview_pos.value = { x, y }
                preview.value = item
            }, 180)
        }

        function hide_preview() {
            clearTimeout(preview_timer)
            preview.value = null
        }

        function open_item(item) {
            hide_preview()
            close_more_popover()
            opened.value = item
            if (!modal) modal = new bootstrap.Modal(modal_el.value)
            modal.show()
        }

        // Leaving the panel unmounts it. Wait for the modal to be fully closed first,
        // otherwise Bootstrap is cut mid-animation: its backdrop stays and the page no
        // longer scrolls.
        function go_to(item) {
            const el = modal_el.value
            if (modal && el && el.classList.contains('show')) {
                el.addEventListener('hidden.bs.modal', () => emit('navigate', item.target), { once: true })
                modal.hide()
            } else {
                emit('navigate', item.target)
            }
        }

        function format_when(item) {
            const opts = { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' }
            const start = new Date(item.start)
            if (item.all_day) {
                const a = start.toLocaleDateString(undefined, opts)
                return item.end ? a + ' → ' + new Date(item.end).toLocaleDateString(undefined, opts) : a
            }
            const a = start.toLocaleString(undefined, { ...opts, hour: '2-digit', minute: '2-digit' })
            return item.end ? a + ' → ' + new Date(item.end).toLocaleString(undefined, { ...opts, hour: '2-digit', minute: '2-digit' }) : a
        }

        function item_label(item) {
            return item.label || kind_info(item.kind).label
        }

        function target_label(target) {
            if (!target) return 'Open'
            if (target.task) return 'Open the task'
            return { main: 'Open the case', timeline: 'Open the timeline', misp: 'Open MISP', files: 'Open the files', history: 'Open the history' }[target.tab] || 'Open'
        }

        function refresh_events() {
            if (!calendar) return
            calendar.batchRendering(() => {
                // Drop the previous sources too: removing only their events would let them pile up
                calendar.getEventSources().forEach(src => src.remove())
                const events = visible.value.map(to_event)
                for (const it of visible.value) if (it.kind === 'deadline') events.push(deadline_background(it))
                calendar.addEventSource(events)
            })
        }

        function toggle_kind(key) {
            const s = new Set(hidden.value)
            s.has(key) ? s.delete(key) : s.add(key)
            hidden.value = s
        }

        function show_all() {
            hidden.value = new Set()
        }

        function reset_kinds() {
            hidden.value = new Set(HIDDEN_BY_DEFAULT)
        }

        function go_today() {
            calendar && calendar.today()
        }

        async function fetch_items() {
            loading.value = true
            const res = await fetch('/case/' + props.case_id + '/calendar')
            if (res.status === 200) {
                const data = await res.json()
                items.value = data.items
                include_logs.value = data.include_logs
            }
            loading.value = false
        }

        function build_calendar() {
            calendar = new FullCalendar.Calendar(holder.value, {
                initialView: 'dayGridMonth',
                height: 'auto',
                firstDay: 1,
                nowIndicator: true,
                dayMaxEvents: 3,
                eventOrder: (a, b) => {
                    // Durations first, then deadlines, then the rest by time
                    // The entry reached from "See in the calendar" first, so it is never under "+N more"
                    const rank = e => (e.extendedProps.item?.id === focused_item_id ? -1 : e.extendedProps.item?.kind === 'deadline' ? 0 : 1)
                    return rank(a) - rank(b) || a.start - b.start
                },
                headerToolbar: {
                    left: 'prev,next today',
                    center: 'title',
                    right: 'dayGridMonth,listMonth',
                },
                buttonText: { today: 'Today', month: 'Month', list: 'List' },
                eventTimeFormat: { hour: '2-digit', minute: '2-digit', hour12: false },
                eventContent: event_content,
                eventMouseEnter: (info) => {
                    const it = info.event.extendedProps.item
                    if (it) show_preview(it, info.jsEvent)
                },
                eventMouseLeave: hide_preview,
                eventClick: (info) => {
                    info.jsEvent.preventDefault()
                    if (!info.event.extendedProps.item) return
                    open_item(info.event.extendedProps.item)
                },
            })
            calendar.render()
            refresh_events()

            // Month picker above the calendar, as on the Calendar page
            if (month_picker.value && typeof flatpickr !== 'undefined') {
                const plugins = typeof monthSelectPlugin !== 'undefined'
                    ? [new monthSelectPlugin({ shorthand: true, dateFormat: 'Y-m', altFormat: 'F Y' })] : []
                flatpickr(month_picker.value, {
                    dateFormat: 'Y-m',
                    plugins,
                    onChange: (dates) => { if (dates.length) calendar.gotoDate(dates[0]) },
                })
            }
        }

        watch(visible, refresh_events)

        // "See in the calendar" from a task: show its kind, go to its date, open its detail,
        // as if it had been clicked here. Prefers the open / finish entry, then the deadline.
        async function focus_pending_task() {
            const pending = window.flowintel_calendar_focus
            if (!pending || !calendar) return
            window.flowintel_calendar_focus = null
            const rank = it => ({ task: 0, deadline: 1 })[it.kind] ?? 2
            const item = items.value
                .filter(it => it.target && it.target.task === pending.task && it.kind !== 'history' && it.kind !== 'audit')
                .sort((a, b) => rank(a) - rank(b) || (a.start < b.start ? 1 : -1))[0]
            if (!item) {
                create_message('Nothing dated for this task in the calendar', 'info-subtle')
                return
            }
            if (hidden.value.has(item.kind)) {
                const h = new Set(hidden.value)
                h.delete(item.kind)
                hidden.value = h
            }
            search.value = ''
            if (calendar.view.type !== 'dayGridMonth') calendar.changeView('dayGridMonth')
            calendar.gotoDate(new Date(item.start))
            await nextTick()
            // First bring the day into view, then open its detail
            const cell = mark_day(item)
            if (cell) {
                cell.scrollIntoView({ behavior: 'smooth', block: 'center' })
                await new Promise(r => setTimeout(r, 650))
            }
            open_item(item)
        }

        let focused_item_id = null

        // Outline the day of an item and its entry, until another one is marked
        function mark_day(item) {
            focused_item_id = item.id
            if (!holder.value || !calendar) return
            holder.value.querySelectorAll('.ccal-day-focus').forEach(el => el.classList.remove('ccal-day-focus'))
            calendar.getEvents().forEach(ev => {
                if (ev.classNames.includes('ccal-ev-focus')) ev.setProp('classNames', ev.classNames.filter(c => c !== 'ccal-ev-focus'))
            })
            const day = date_only(item.start)
            const cell = holder.value.querySelector('.fc-daygrid-day[data-date="' + day + '"]')
            if (cell) cell.classList.add('ccal-day-focus')
            const ev = calendar.getEventById(item.id)
            if (ev) ev.setProp('classNames', ev.classNames.concat(['ccal-ev-focus']))
            return cell
        }
        const on_focus_now = () => focus_pending_task()

        onMounted(async () => {
            await fetch_items()
            await nextTick()
            if (holder.value && typeof FullCalendar !== 'undefined') build_calendar()
            window.addEventListener('calendar-focus-now', on_focus_now)
            focus_pending_task()
        })
        onBeforeUnmount(() => {
            window.removeEventListener('calendar-focus-now', on_focus_now)
            clearTimeout(preview_timer)
            calendar && calendar.destroy()
            if (modal) {
                // Never leave Bootstrap's scroll lock or backdrop behind
                const shown = modal_el.value && modal_el.value.classList.contains('show')
                if (!shown) {
                    try { modal.dispose() } catch (e) {}
                }
                if (shown || !document.querySelector('.modal.show')) {
                    document.querySelectorAll('.modal-backdrop').forEach(b => b.remove())
                    document.body.classList.remove('modal-open')
                    document.body.style.removeProperty('overflow')
                    document.body.style.removeProperty('padding-right')
                }
            }
        })

        return {
            items, loading, include_logs, search, hidden, shown_kinds, filtered_out, holder, month_picker, counts, kinds, visible,
            modal_el, preview, preview_pos, opened,
            toggle_kind, show_all, reset_kinds, go_today, period_info, kind_info, item_label, format_when, target_label, go_to,
        }
    },
    template: `
    <div class="ccal">
        <!-- Same bar as the task list of the case: a filter button and a search field -->
        <div class="ccal-bar">
            <div class="input-group input-group-sm ccal-search-group">
                <div class="dropdown">
                    <button type="button" data-bs-toggle="dropdown" data-bs-auto-close="outside" aria-expanded="false"
                            :class="['btn btn-sm ccal-filter-btn', filtered_out ? 'btn-filter-active' : 'btn-outline-primary']"
                            :title="filtered_out ? 'Some kinds are hidden - click to choose' : 'Choose what the calendar shows'">
                        <i class="fa-solid fa-filter fa-sm"></i>
                        <span class="ms-1">[[ shown_kinds ]] / [[ kinds.length ]]</span>
                    </button>
                    <div class="dropdown-menu ccal-show-menu">
                        <div class="ccal-menu-head">
                            <span>Show in the calendar</span>
                            <span class="ccal-menu-actions">
                                <button type="button" @click="show_all()">All</button>
                                <span aria-hidden="true">·</span>
                                <button type="button" @click="reset_kinds()">Default</button>
                            </span>
                        </div>
                        <div class="ccal-menu-list">
                            <label v-for="k in kinds" :key="k.key" :class="['ccal-menu-row', { on: !hidden.has(k.key) }]" :style="{ '--ccal-c': k.color }">
                                <span class="ccal-menu-icon"><i :class="k.icon"></i></span>
                                <span class="ccal-menu-text">
                                    <span class="ccal-menu-label">[[ k.label ]] <span class="ccal-menu-count">[[ counts[k.key] ]]</span></span>
                                    <span class="ccal-menu-hint">[[ k.hint ]]</span>
                                </span>
                                <span class="form-check form-switch m-0">
                                    <input class="form-check-input" type="checkbox" role="switch" :checked="!hidden.has(k.key)" @change="toggle_kind(k.key)" :aria-label="'Show ' + k.label">
                                </span>
                            </label>
                        </div>
                    </div>
                </div>
                <input type="search" class="form-control form-control-sm rounded ccal-search-input" v-model="search" placeholder="Search the calendar">
            </div>
            <span class="text-muted small"><b>[[ visible.length ]]</b> / [[ items.length ]] items</span>
        </div>
        <input ref="month_picker" class="form-control ccal-month-picker" placeholder="Select month">
        <div v-if="!loading && !include_logs" class="form-text mb-2">
            <i class="fa-solid fa-lock me-1"></i>History and audit entries need the Admin, Case Admin or Audit Viewer permission.
        </div>
        <div v-if="loading" class="text-muted py-4 text-center"><span class="spinner-border spinner-border-sm me-2"></span>Loading…</div>
        <div ref="holder" class="ccal-calendar"></div>

        <!-- Hover preview -->
        <div v-if="preview" class="ccal-preview" :style="{ left: preview_pos.x + 'px', top: preview_pos.y + 'px', '--ccal-c': kind_info(preview.kind).color }">
            <div class="ccal-preview-head">
                <span class="ccal-preview-kind"><i :class="kind_info(preview.kind).icon"></i> [[ item_label(preview) ]]</span>
                <span v-if="preview.status" :class="'badge rounded-pill text-bg-' + (preview.status.style || 'secondary')">[[ preview.status.name ]]</span>
            </div>
            <div class="ccal-preview-title">[[ preview.title ]]</div>
            <div class="ccal-preview-when"><i class="fa-regular fa-clock me-1"></i>[[ format_when(preview) ]]</div>
            <div v-if="period_info(preview)" :class="['ccal-period', 'ccal-period-' + period_info(preview).state]">
                <div class="ccal-period-ends"><span>[[ period_info(preview).from ]]</span><span>[[ period_info(preview).to_label ]] · [[ period_info(preview).to ]]</span></div>
                <div class="ccal-period-track"><div v-if="period_info(preview).percent !== null" class="ccal-period-fill" :style="{ width: period_info(preview).percent + '%' }"></div></div>
                <div class="ccal-period-status">
                    <span>[[ period_info(preview).status ]]</span>
                    <span v-if="period_info(preview).time_required" class="ccal-period-req"><i class="fa-solid fa-stopwatch me-1"></i>[[ period_info(preview).time_required ]]</span>
                </div>
            </div>
            <dl v-if="preview.meta.length" class="ccal-preview-meta">
                <template v-for="m in preview.meta.slice(0, 5)" :key="m[0]">
                    <dt>[[ m[0] ]]</dt><dd>[[ m[1] ]]</dd>
                </template>
            </dl>
            <div v-if="preview.body" class="ccal-preview-body">[[ preview.body ]]</div>
            <div class="ccal-preview-hint">Click for details · <i class="fa-solid fa-arrow-right"></i> [[ target_label(preview.target) ]]</div>
        </div>

        <!-- Detail modal, same look as the Calendar page -->
        <div class="modal fade" ref="modal_el" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-lg modal-dialog-centered">
                <div class="modal-content ccal-modal" v-if="opened" :style="{ '--ccal-c': kind_info(opened.kind).color }">
                    <div class="modal-header ccal-modal-header">
                        <span class="ccal-modal-icon"><i :class="kind_info(opened.kind).icon"></i></span>
                        <div class="ccal-modal-titles">
                            <div class="ccal-modal-kind">[[ item_label(opened) ]]</div>
                            <h5 class="modal-title">[[ opened.title ]]</h5>
                        </div>
                        <span v-if="opened.status" :class="'badge rounded-pill ms-auto text-bg-' + (opened.status.style || 'secondary')">[[ opened.status.name ]]</span>
                        <button type="button" class="btn-close" :class="{ 'ms-auto': !opened.status }" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body ccal-modal-body">
                        <div v-if="period_info(opened)" :class="['ccal-period ccal-period-lg mb-3', 'ccal-period-' + period_info(opened).state]">
                            <div class="ccal-period-ends"><span>Created · [[ period_info(opened).from ]]</span><span>[[ period_info(opened).to_label ]] · [[ period_info(opened).to ]]</span></div>
                            <div class="ccal-period-track"><div v-if="period_info(opened).percent !== null" class="ccal-period-fill" :style="{ width: period_info(opened).percent + '%' }"></div></div>
                            <div class="ccal-period-status">
                                <span>[[ period_info(opened).status ]]</span>
                                <span v-if="period_info(opened).time_required" class="ccal-period-req"><i class="fa-solid fa-stopwatch me-1"></i>Time required: [[ period_info(opened).time_required ]]</span>
                            </div>
                        </div>
                        <div class="ccal-meta-grid">
                            <div class="ccal-meta-item">
                                <span class="ccal-meta-label">When</span>
                                <span class="ccal-meta-value">[[ format_when(opened) ]]</span>
                            </div>
                            <div v-for="m in opened.meta" :key="m[0]" class="ccal-meta-item">
                                <span class="ccal-meta-label">[[ m[0] ]]</span>
                                <span class="ccal-meta-value">[[ m[1] ]]</span>
                            </div>
                        </div>
                        <div v-if="opened.detail && !opened.meta.length" class="ccal-section mt-3">
                            <div class="ccal-section-title">Details</div>
                            <div>[[ opened.detail ]]</div>
                        </div>
                        <div v-if="opened.body" class="ccal-section mt-3">
                            <div class="ccal-section-title">Description</div>
                            <pre class="ccal-body">[[ opened.body ]]</pre>
                        </div>
                    </div>
                    <div class="modal-footer ccal-modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                        <button type="button" class="btn btn-primary" @click="go_to(opened)">
                            <i class="fa-solid fa-arrow-right me-1"></i>[[ target_label(opened.target) ]]
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `
}
