/**
 * history_log.js — Compact viewer for a long activity log (case history, audit logs).
 *
 * Built for thousands of entries: one dense line per entry, grouped by day under
 * sticky headers, inside its own scroll area. Only the first rows are rendered and
 * more are added as the user scrolls. Above the list: an activity bar (one bar
 * per day, click to keep only that day), a search box, a user filter and one chip
 * per kind of action.
 *
 * Props:
 *   entries: [{ date: 'YYYY-MM-DD HH:MM', user: '...', text: '...' }]  (any order)
 *   exports: [{ label, href }]  download links shown in the toolbar
 *   empty_text: what to show when there is nothing at all
 */
const { ref, computed, watch, onMounted, onBeforeUnmount, nextTick } = Vue

const PAGE = 150

// Kind of an entry, from its text. The first rule that matches wins.
const KINDS = [
    { key: 'misp', label: 'MISP', icon: 'fa-solid fa-shield-halved', test: /misp/i },
    { key: 'file', label: 'Files', icon: 'fa-solid fa-paperclip', test: /\bfile/i },
    { key: 'note', label: 'Notes', icon: 'fa-solid fa-note-sticky', test: /\bnote/i },
    { key: 'status', label: 'Status', icon: 'fa-solid fa-flag', test: /status|complete|finished|revive/i },
    { key: 'user', label: 'People', icon: 'fa-solid fa-user', test: /assign|\buser|\borg/i },
    { key: 'tag', label: 'Tags', icon: 'fa-solid fa-tags', test: /\btag|galax|cluster|taxonom/i },
    { key: 'link', label: 'Links', icon: 'fa-solid fa-link', test: /\blink|connector|reference/i },
    { key: 'task', label: 'Tasks', icon: 'fa-solid fa-list-check', test: /\btask/i },
    { key: 'other', label: 'Case', icon: 'fa-solid fa-briefcase', test: /./ },
]

// What happened, for the colour of the row's marker
function action_of(text) {
    if (/delet|remov|unlink/i.test(text)) return 'delete'
    if (/creat|added|\badd\b|new /i.test(text)) return 'create'
    return 'edit'
}

function day_key(date) {
    return date.slice(0, 10)
}

function initials(name) {
    return name.split(/\s+/).filter(Boolean).slice(0, 2).map(p => p[0].toUpperCase()).join('') || '?'
}

// A stable hue per user, so a person keeps one colour across the whole log
function user_hue(name) {
    let h = 0
    for (const c of name) h = (h * 31 + c.charCodeAt(0)) % 360
    return h
}

export default {
    delimiters: ['[[', ']]'],
    props: {
        entries: { type: Array, default: () => [] },
        exports: { type: Array, default: () => [] },
        empty_text: { type: String, default: 'No entries' },
        // {date, user, text}: an entry to scroll to and outline (e.g. coming from the Calendar)
        focus: { type: Object, default: null },
    },
    setup(props) {
        const search = ref('')
        const user_filter = ref('')
        const kind_filter = ref([])
        const day_filter = ref('')
        const limit = ref(PAGE)
        const expanded = ref(new Set())
        const collapsed_days = ref(new Set())
        const sentinel = ref(null)
        const scroller = ref(null)
        const focused_id = ref(null)
        const scrolled = ref(false)     // list scrolled down: show the "back to top" button

        function on_scroll() {
            scrolled.value = !!scroller.value && scroller.value.scrollTop > 300
        }

        function to_top() {
            scroller.value && scroller.value.scrollTo({ top: 0, behavior: 'smooth' })
        }
        let observer = null

        // Newest first, with everything the filters and the display need computed once
        const all = computed(() => props.entries
            .map((e, i) => {
                const kind = KINDS.find(k => k.test.test(e.text))
                return {
                    id: i,
                    date: e.date,
                    day: day_key(e.date),
                    time: e.date.slice(11, 16),
                    user: e.user,
                    text: e.text,
                    kind: kind.key,
                    action: action_of(e.text),
                    haystack: (e.user + ' ' + e.text).toLowerCase(),
                }
            })
            .sort((a, b) => (a.date < b.date ? 1 : a.date > b.date ? -1 : b.id - a.id)))

        const users = computed(() => {
            const count = new Map()
            for (const e of all.value) count.set(e.user, (count.get(e.user) || 0) + 1)
            return [...count.entries()].sort((a, b) => b[1] - a[1])
        })

        const kinds = computed(() => {
            const count = new Map()
            for (const e of all.value) count.set(e.kind, (count.get(e.kind) || 0) + 1)
            return KINDS.filter(k => count.has(k.key)).map(k => ({ ...k, count: count.get(k.key) }))
        })

        // Everything but the day filter: the activity bar shows this, so it stays useful
        // to pick a day while other filters are on
        const filtered_no_day = computed(() => {
            const q = search.value.trim().toLowerCase()
            const kf = kind_filter.value
            return all.value.filter(e =>
                (!q || e.haystack.includes(q)) &&
                (!user_filter.value || e.user === user_filter.value) &&
                (!kf.length || kf.includes(e.kind)))
        })

        const filtered = computed(() => day_filter.value
            ? filtered_no_day.value.filter(e => e.day === day_filter.value)
            : filtered_no_day.value)

        // Activity bar: one bar per day between the first and the last entry
        const activity = computed(() => {
            if (!all.value.length) return []
            const count = new Map()
            for (const e of filtered_no_day.value) count.set(e.day, (count.get(e.day) || 0) + 1)
            const last = new Date(all.value[0].day + 'T00:00:00')
            const first = new Date(all.value[all.value.length - 1].day + 'T00:00:00')
            const days = []
            for (let d = new Date(first); d <= last && days.length < 400; d.setDate(d.getDate() + 1)) {
                const key = d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0')
                days.push({ day: key, count: count.get(key) || 0 })
            }
            const max = Math.max(1, ...days.map(d => d.count))
            return days.map(d => ({ ...d, height: d.count ? Math.max(8, Math.round(d.count / max * 100)) : 0 }))
        })

        // The rendered slice, grouped by day
        const groups = computed(() => {
            const out = []
            let cur = null
            for (const e of filtered.value.slice(0, limit.value)) {
                if (!cur || cur.day !== e.day) {
                    cur = { day: e.day, items: [] }
                    out.push(cur)
                }
                cur.items.push(e)
            }
            const per_day = new Map()
            for (const e of filtered.value) per_day.set(e.day, (per_day.get(e.day) || 0) + 1)
            for (const g of out) g.total = per_day.get(g.day)
            return out
        })

        const has_filters = computed(() => !!(search.value || user_filter.value || kind_filter.value.length || day_filter.value))

        function reset_filters() {
            search.value = ''
            user_filter.value = ''
            kind_filter.value = []
            day_filter.value = ''
        }

        function toggle_kind(key) {
            kind_filter.value = kind_filter.value.includes(key)
                ? kind_filter.value.filter(k => k !== key)
                : [...kind_filter.value, key]
        }

        function toggle_day(day) {
            day_filter.value = day_filter.value === day ? '' : day
        }

        function toggle_expanded(id) {
            const s = new Set(expanded.value)
            s.has(id) ? s.delete(id) : s.add(id)
            expanded.value = s
        }

        function toggle_collapsed(day) {
            const s = new Set(collapsed_days.value)
            s.has(day) ? s.delete(day) : s.add(day)
            collapsed_days.value = s
        }

        function day_label(day) {
            const d = new Date(day + 'T00:00:00')
            const today = new Date(); today.setHours(0, 0, 0, 0)
            const diff = Math.round((today - d) / 86400000)
            const long = d.toLocaleDateString(undefined, { weekday: 'short', day: '2-digit', month: 'short', year: 'numeric' })
            if (diff === 0) return 'Today · ' + long
            if (diff === 1) return 'Yesterday · ' + long
            return long
        }

        function kind_info(key) {
            return KINDS.find(k => k.key === key)
        }

        // New filter: back to the top and to the first page
        watch([search, user_filter, kind_filter, day_filter], () => {
            limit.value = PAGE
            if (scroller.value) scroller.value.scrollTop = 0
        })

        // Bring an entry into view: clear the filters, render down to it, open its day,
        // scroll the list (and the page) to it, and keep it outlined
        async function go_to_focus() {
            const f = props.focus
            if (!f || !all.value.length) return
            const target = all.value.find(e => e.date === f.date && e.user === f.user && e.text === f.text)
            if (!target) return
            search.value = ''
            user_filter.value = ''
            kind_filter.value = []
            day_filter.value = ''
            await nextTick()
            const index = filtered.value.findIndex(e => e.id === target.id)
            if (index >= limit.value) limit.value = index + PAGE
            if (collapsed_days.value.has(target.day)) toggle_collapsed(target.day)
            focused_id.value = target.id
            await nextTick()
            const row = scroller.value && scroller.value.querySelector('[data-entry="' + target.id + '"]')
            if (!row) return
            scroller.value.scrollIntoView({ behavior: 'smooth', block: 'start' })
            const top = row.offsetTop - scroller.value.offsetTop - scroller.value.clientHeight / 3
            scroller.value.scrollTo({ top: Math.max(0, top), behavior: 'smooth' })
        }

        watch(() => [props.focus, all.value.length], () => go_to_focus())

        onMounted(async () => {
            await nextTick()
            go_to_focus()
            observer = new IntersectionObserver((items) => {
                if (items.some(i => i.isIntersecting) && limit.value < filtered.value.length) limit.value += PAGE
            }, { root: scroller.value, rootMargin: '300px' })
            if (sentinel.value) observer.observe(sentinel.value)
        })
        onBeforeUnmount(() => observer && observer.disconnect())

        return {
            search, user_filter, kind_filter, day_filter, limit, expanded, collapsed_days,
            sentinel, scroller, all, users, kinds, filtered, activity, groups, has_filters,
            reset_filters, toggle_kind, toggle_day, toggle_expanded, toggle_collapsed,
            day_label, kind_info, initials, user_hue, focused_id, scrolled, on_scroll, to_top,
        }
    },
    template: `
    <div class="hlog">
        <div v-if="!all.length" class="text-muted fst-italic py-3">[[ empty_text ]]</div>
        <template v-else>
            <!-- Toolbar -->
            <div class="hlog-toolbar">
                <div class="input-group input-group-sm hlog-search">
                    <span class="input-group-text"><i class="fa-solid fa-magnifying-glass"></i></span>
                    <input type="search" class="form-control" v-model="search" placeholder="Search the history">
                </div>
                <select class="form-select form-select-sm hlog-user" v-model="user_filter" aria-label="Filter by user">
                    <option value="">All users ([[ users.length ]])</option>
                    <option v-for="u in users" :key="u[0]" :value="u[0]">[[ u[0] ]] · [[ u[1] ]]</option>
                </select>
                <div class="hlog-count">
                    <b>[[ filtered.length ]]</b> / [[ all.length ]] entries
                    <button v-if="has_filters" class="btn btn-link btn-sm p-0 ms-2" @click="reset_filters()">Reset</button>
                </div>
                <div v-if="exports.length" class="dropdown ms-auto">
                    <button class="btn btn-outline-secondary btn-sm dropdown-toggle" data-bs-toggle="dropdown" aria-expanded="false">
                        <i class="fa-solid fa-download me-1"></i>Export
                    </button>
                    <ul class="dropdown-menu dropdown-menu-end">
                        <li v-for="ex in exports" :key="ex.href"><a class="dropdown-item" :href="ex.href">[[ ex.label ]]</a></li>
                    </ul>
                </div>
            </div>

            <!-- Kinds -->
            <div class="hlog-kinds">
                <button v-for="k in kinds" :key="k.key" type="button"
                        :class="['hlog-chip', 'hlog-kind-' + k.key, { active: kind_filter.includes(k.key) }]"
                        @click="toggle_kind(k.key)">
                    <i :class="k.icon"></i>[[ k.label ]]<span>[[ k.count ]]</span>
                </button>
            </div>

            <!-- Activity per day -->
            <div v-if="activity.length > 1" class="hlog-activity" role="group" aria-label="Activity per day">
                <button v-for="d in activity" :key="d.day" type="button"
                        :class="['hlog-bar', { active: day_filter === d.day, empty: !d.count, dim: day_filter && day_filter !== d.day }]"
                        :title="day_label(d.day) + ' — ' + d.count + ' entries'"
                        :disabled="!d.count" @click="toggle_day(d.day)">
                    <span :style="{ height: d.height + '%' }"></span>
                </button>
            </div>

            <!-- Entries -->
            <div class="hlog-scroll-wrap">
            <div class="hlog-scroll" ref="scroller" @scroll.passive="on_scroll">
                <div v-if="!filtered.length" class="text-muted text-center py-4">No entry matches these filters.</div>
                <section v-for="g in groups" :key="g.day" class="hlog-day">
                    <header class="hlog-day-head" @click="toggle_collapsed(g.day)">
                        <i :class="['fa-solid fa-fw', collapsed_days.has(g.day) ? 'fa-chevron-right' : 'fa-chevron-down']"></i>
                        <span>[[ day_label(g.day) ]]</span>
                        <span class="hlog-day-count">[[ g.total ]]</span>
                    </header>
                    <ul v-if="!collapsed_days.has(g.day)" class="hlog-rows">
                        <li v-for="e in g.items" :key="e.id" :data-entry="e.id" :class="['hlog-row', 'hlog-action-' + e.action, { open: expanded.has(e.id) || focused_id === e.id, focused: focused_id === e.id }]"
                            @click="toggle_expanded(e.id)" :title="expanded.has(e.id) ? '' : e.text">
                            <span class="hlog-time">[[ e.time ]]</span>
                            <span :class="['hlog-kind', 'hlog-kind-' + e.kind]" :title="kind_info(e.kind).label"><i :class="kind_info(e.kind).icon"></i></span>
                            <span class="hlog-avatar" :style="{ '--h': user_hue(e.user) }" :title="e.user">[[ initials(e.user) ]]</span>
                            <span class="hlog-user-name">[[ e.user ]]</span>
                            <span class="hlog-text">[[ e.text ]]</span>
                        </li>
                    </ul>
                </section>
                <div ref="sentinel" class="hlog-sentinel">
                    <span v-if="limit < filtered.length" class="text-muted small">Loading more…</span>
                </div>
            </div>
            <button v-show="scrolled" type="button" class="btn btn-primary btn-sm hlog-top" @click="to_top()" title="Back to the top of the list">
                <i class="fa-solid fa-arrow-up me-1"></i>Top
            </button>
            </div>
        </template>
    </div>
    `
}
