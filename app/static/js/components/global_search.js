/**
 * global_search.js — the search of the top bar: autocomplete over cases, tasks, task
 * notes, MISP attributes, tags & galaxies, templates (and users / organisations for
 * admins), plus the pages of Flowintel.
 *
 *   <global_search :is-admin="true" :can-create="true"></global_search>
 *
 * Results come from /search/quick (app/search/search_core.py), which applies the user's
 * rights in SQL and bounds every query, so a common word on a huge instance stays fast.
 * In the browser: requests are debounced, an older request is aborted when a newer one
 * starts, answers are cached (small LRU) and at most a few rows per kind are drawn.
 *
 * Keyboard: Ctrl/⌘+K or "/" to focus, ↑ ↓ to move, Enter to open (Ctrl/⌘+Enter: new tab),
 * Tab / Shift+Tab to change the kind, Esc to close. Prefixes narrow the kind:
 * "case: …", "task: …", "note: …", "attr: …", "tag: …", "tpl: …", "user: …", "org: …".
 * "#123" also matches case / task ids.
 * Styles: /static/css/components/global_search.css
 */
import tag_badge from './tag-badge.js'
import user_chip from './user-chip.js'

const DEBOUNCE_MS = 180
// "All" view: one request per batch, in parallel (the big tables each get their own)
const BATCHES = ['cases,tags,templates,users,orgs', 'tasks', 'notes', 'attributes']
const CACHE_SIZE = 40
const RECENT_KEY = 'flowintel.search.recent'
const RECENT_MAX = 6

const KINDS = [
    { key: '',           label: 'All',        icon: 'fa-solid fa-layer-group' },
    { key: 'cases',      label: 'Cases',      icon: 'fa-solid fa-folder-open', prefix: ['case', 'cases', 'c'] },
    { key: 'tasks',      label: 'Tasks',      icon: 'fa-solid fa-list-check', prefix: ['task', 'tasks', 't'] },
    { key: 'notes',      label: 'Notes',      icon: 'fa-solid fa-note-sticky', prefix: ['note', 'notes', 'n'] },
    { key: 'attributes', label: 'Attributes', icon: 'fa-solid fa-fingerprint', prefix: ['attr', 'attribute', 'ioc', 'a'] },
    { key: 'tags',       label: 'Tags',       icon: 'fa-solid fa-tags', prefix: ['tag', 'tags', 'galaxy', 'cluster'] },
    { key: 'templates',  label: 'Templates',  icon: 'fa-solid fa-clone', prefix: ['tpl', 'template', 'templates'] },
    { key: 'users',      label: 'Users',      icon: 'fa-solid fa-user', prefix: ['user', 'users', 'u'], admin: true },
    { key: 'orgs',       label: 'Orgs',       icon: 'fa-solid fa-building', prefix: ['org', 'orgs', 'o'], admin: true },
]

// Pages of Flowintel, matched in the browser (no request)
const PAGES = [
    { title: 'Home', url: '/', icon: 'fa-solid fa-house', words: 'dashboard' },
    { title: 'Cases', url: '/case/', icon: 'fa-solid fa-folder-open', words: 'case list index' },
    { title: 'New case', url: '/case/create_case', icon: 'fa-solid fa-plus', words: 'create add', create: true },
    { title: 'My assignments', url: '/my_assignment/', icon: 'fa-solid fa-clipboard-check', words: 'my tasks assigned' },
    { title: 'Calendar', url: '/calendar/', icon: 'fa-solid fa-calendar-days', words: 'deadline agenda' },
    { title: 'Alerting', url: '/alerting', icon: 'fa-solid fa-bell', words: 'alerts external' },
    { title: 'Notifications', url: '/notification/', icon: 'fa-solid fa-bell', words: 'notif inbox' },
    { title: 'Case templates', url: '/templating/cases', icon: 'fa-solid fa-clone', words: 'templating' },
    { title: 'Task templates', url: '/templating/tasks', icon: 'fa-solid fa-clone', words: 'templating' },
    { title: 'Note templates', url: '/tools/note_template_index', icon: 'fa-solid fa-note-sticky', words: 'templating notes' },
    { title: 'Custom tags', url: '/custom_tags/', icon: 'fa-solid fa-tag', words: 'tags' },
    { title: 'Taxonomies', url: '/admin/taxonomies', icon: 'fa-solid fa-tags', words: 'misp tags' },
    { title: 'Galaxies', url: '/admin/galaxies', icon: 'fa-solid fa-meteor', words: 'misp clusters' },
    { title: 'Analyzer', url: '/analyzer/misp-modules', icon: 'fa-solid fa-flask', words: 'misp modules enrichment' },
    { title: 'Connectors', url: '/connectors/', icon: 'fa-solid fa-plug', words: 'misp ail instances' },
    { title: 'Search attribute value', url: '/tools/search_attr', icon: 'fa-solid fa-magnifying-glass-location', words: 'ioc value attributes misp objects' },
    { title: 'Statistics', url: '/tools/stats', icon: 'fa-solid fa-chart-line', words: 'stats charts' },
    { title: 'Settings', url: '/account/settings', icon: 'fa-solid fa-gear', words: 'theme font preferences' },
    { title: 'My profile', url: '/account/', icon: 'fa-solid fa-user', words: 'account api key' },
    { title: 'Users', url: '/admin/users', icon: 'fa-solid fa-users', words: 'admin accounts', admin: true },
    { title: 'Organisations', url: '/admin/orgs', icon: 'fa-solid fa-building', words: 'admin orgs', admin: true },
    { title: 'Roles', url: '/admin/roles', icon: 'fa-solid fa-user-shield', words: 'admin permissions', admin: true },
    { title: 'Modules', url: '/tools/module', icon: 'fa-solid fa-puzzle-piece', words: 'admin tabs', admin: true },
    { title: 'System settings', url: '/tools/system_settings', icon: 'fa-solid fa-sliders', words: 'admin config', admin: true },
    { title: 'Audit logs', url: '/tools/audit_logs', icon: 'fa-solid fa-scroll', words: 'admin history', admin: true },
]

// Split `text` around the matches of `needle` → [{ t, hit }], drawn without v-html
function highlight(text, needle) {
    text = String(text ?? '')
    if (!needle) return [{ t: text, hit: false }]
    const low = text.toLowerCase(), n = needle.toLowerCase(), out = []
    let i = 0, j
    while ((j = low.indexOf(n, i)) !== -1 && out.length < 20) {
        if (j > i) out.push({ t: text.slice(i, j), hit: false })
        out.push({ t: text.slice(j, j + n.length), hit: true })
        i = j + n.length
    }
    if (i < text.length) out.push({ t: text.slice(i), hit: false })
    return out
}

export default {
    name: 'global_search',
    delimiters: ['[[', ']]'],
    components: { tag_badge, user_chip },
    props: {
        isAdmin:   { type: Boolean, default: false },
        canCreate: { type: Boolean, default: false },
    },
    data() {
        return {
            text: '',
            kind: '',            // '' = all kinds
            open: false,
            loading: false,
            result: null,        // last answer of /search/quick
            active: -1,          // index in `flat`
            recent: [],
            recent_cases: null,  // latest open cases, shown when nothing is typed
            statuses: null,
            error: '',
        }
    },
    computed: {
        kinds() { return KINDS.filter(k => !k.admin || this.isAdmin) },
        // text without a "kind:" prefix, and the kind that prefix asks for
        parsed() {
            const m = /^\s*([a-z]+)\s*:\s*(.*)$/i.exec(this.text)
            if (m) {
                const k = this.kinds.find(k => (k.prefix || []).includes(m[1].toLowerCase()))
                if (k) return { kind: k.key, q: m[2].trim() }
            }
            return { kind: this.kind, q: this.text.trim() }
        },
        needle() { return this.parsed.q.replace(/^#(?=\d+$)/, '') },
        pages() {
            const q = this.parsed.q.toLowerCase()
            if (!q || this.parsed.kind) return []
            return PAGES.filter(p => (!p.admin || this.isAdmin) && (!p.create || this.canCreate)
                && (p.title.toLowerCase().includes(q) || p.words.includes(q))).slice(0, 4)
        },
        groups() {
            const out = []
            if (!this.has_query) {
                if (this.recent_cases?.length) out.push({ kind: 'recent', label: 'Recent cases', total: this.recent_cases.length, items: this.recent_cases })
                if (this.recent.length) out.push({ kind: 'searches', label: 'Recent searches', total: this.recent.length,
                    items: this.recent.map(r => ({ id: r, title: r, search: true })) })
                return out
            }
            if (this.pages.length) out.push({ kind: 'pages', label: 'Pages', total: this.pages.length, items: this.pages })
            for (const g of (this.result?.groups || [])) out.push(g)
            return out
        },
        // every selectable row, in display order (keyboard navigation)
        flat() {
            const rows = []
            for (const g of this.groups) for (const it of g.items) rows.push({ g, it })
            for (const g of this.groups) {
                if (g.kind === 'attributes') rows.push({ g, attr_page: true, it: { url: '/tools/search_attr?value=' + encodeURIComponent(this.needle) } })
                if (this.show_more(g)) rows.push({ g, more: true })
            }
            return rows
        },
        has_query() { return this.parsed.q.length > 0 },
        attr_index() { return this.flat.findIndex(r => r.attr_page) },
        empty() { return this.has_query && !this.loading && this.result && !this.result.pending && !this.groups.length },
        kind_icon() { return (k) => k === 'recent' ? 'fa-solid fa-clock-rotate-left' : k === 'searches' ? 'fa-solid fa-magnifying-glass' : k === 'pages' ? 'fa-solid fa-compass' : (KINDS.find(x => x.key === k)?.icon || 'fa-solid fa-circle') },
        shortcut() { return /Mac|iPhone|iPad/.test(navigator.platform) ? '⌘K' : 'Ctrl K' },
    },
    watch: {
        // soft blur of the page behind the open panel (css: body.gs-open)
        open(v) { document.body.classList.toggle('gs-open', v) },
        text() { this.schedule() },
        kind() { this.schedule(true) },
    },
    created() {
        this.cache = new Map()
        this.timer = null
        this.ctrl = null
        try { this.recent = JSON.parse(localStorage.getItem(RECENT_KEY) || '[]').slice(0, RECENT_MAX) } catch (e) { this.recent = [] }
    },
    mounted() {
        this.onKey = (e) => {
            const typing = /^(INPUT|TEXTAREA|SELECT)$/.test(document.activeElement?.tagName) || document.activeElement?.isContentEditable
            if ((e.key === 'k' || e.key === 'K') && (e.ctrlKey || e.metaKey)) { e.preventDefault(); this.focus() }
            else if (e.key === '/' && !typing) { e.preventDefault(); this.focus() }
        }
        this.onDoc = (e) => { if (!this.$el.contains(e.target)) this.open = false }
        document.addEventListener('keydown', this.onKey)
        document.addEventListener('mousedown', this.onDoc)
    },
    unmounted() {
        document.removeEventListener('keydown', this.onKey)
        document.removeEventListener('mousedown', this.onDoc)
        clearTimeout(this.timer)
        this.ctrl?.abort()
        document.body.classList.remove('gs-open')
    },
    methods: {
        highlight,
        since(d) { return d ? dayjs.utc(d).fromNow() : '' },
        focus() { this.$refs.input?.focus(); this.$refs.input?.select(); this.on_focus() },
        schedule(now = false) {
            clearTimeout(this.timer)
            this.active = -1
            this.error = ''
            if (!this.has_query) { this.load_recent(); return }
            this.open = true
            this.timer = setTimeout(() => this.run(), now ? 0 : DEBOUNCE_MS)
        },
        // "All": the kinds go in parallel batches and each group shows as soon as it is in, so
        // the wait is the slowest kind, not the sum (big tables: tasks, notes, attributes).
        async run() {
            const { kind, q } = this.parsed
            const key = kind + '|' + q.toLowerCase()
            if (this.cache.has(key)) {           // LRU: move to the end
                const hit = this.cache.get(key)
                this.cache.delete(key); this.cache.set(key, hit)
                this.result = hit; this.loading = false
                return
            }
            this.ctrl?.abort()
            const ctrl = this.ctrl = new AbortController()
            const batches = kind ? [kind] : (q.startsWith('#') ? [''] : BATCHES)
            const merged = { query: q, groups: [], took_ms: 0, pending: batches.length }
            this.result = null
            this.loading = true
            const order = (g) => KINDS.findIndex(k => k.key === g.kind)
            const one = async (kinds) => {
                const params = new URLSearchParams({ q })
                if (kinds) params.set('kinds', kinds)
                const res = await fetch('/search/quick?' + params, { signal: ctrl.signal })
                if (!res.ok) throw new Error('Search failed (' + res.status + ')')
                const data = await res.json()
                if (ctrl !== this.ctrl) return
                merged.groups = [...merged.groups, ...data.groups].sort((a, b) => order(a) - order(b))
                merged.took_ms = Math.max(merged.took_ms, data.took_ms)
                merged.pending--
                this.result = { ...merged }
            }
            try {
                const results = await Promise.allSettled(batches.map(one))
                const failed = results.find(r => r.status === 'rejected' && r.reason?.name !== 'AbortError')
                if (failed && ctrl === this.ctrl && !merged.groups.length) this.error = failed.reason.message
                if (ctrl === this.ctrl && !failed) {
                    this.cache.set(key, { ...merged, pending: 0 })
                    if (this.cache.size > CACHE_SIZE) this.cache.delete(this.cache.keys().next().value)
                }
                this.load_statuses()
            } finally {
                if (ctrl === this.ctrl) this.loading = false
            }
        },
        // nothing typed (All or Cases): the latest open cases the user can see, fresh on each open
        async load_recent() {
            this.ctrl?.abort()
            this.result = null
            if (this.parsed.kind && this.parsed.kind !== 'cases') { this.loading = false; this.recent_cases = []; return }
            const ctrl = this.ctrl = new AbortController()
            this.loading = true
            try {
                const params = new URLSearchParams({ q: '' })
                if (this.parsed.kind) params.set('kinds', this.parsed.kind)
                const res = await fetch('/search/quick?' + params, { signal: ctrl.signal })
                const data = await res.json()
                if (ctrl === this.ctrl) this.recent_cases = (data.groups.find(g => g.kind === 'recent') || {}).items || []
                this.load_statuses()
            } catch (e) {
                if (e.name !== 'AbortError') this.recent_cases = []
            } finally {
                if (ctrl === this.ctrl) this.loading = false
            }
        },
        on_focus() {
            if (!this.open) { this.open = true; if (!this.has_query) this.load_recent() }
        },
        async load_statuses() {
            if (this.statuses) return
            this.statuses = []
            try {
                const res = await fetch('/case/get_status')
                this.statuses = (await res.json()).status || []
            } catch (e) { /* the badge falls back to a plain dot */ }
        },
        status(id) {
            const s = (this.statuses || []).find(x => x.id === id)
            return s ? { name: s.name, style: s.bootstrap_style } : null
        },
        kind_of(key) { return KINDS.find(k => k.key === key) },
        show_more(g) { return !this.parsed.kind && g.kind !== 'pages' && (g.capped || g.total > g.items.length) },
        index_of(g, it) { return this.flat.findIndex(r => r.g === g && r.it === it && !r.attr_page) },
        more_index(g) { return this.flat.findIndex(r => r.g === g && r.more) },
        total_label(g) { return g.capped ? g.total + '+' : g.total },

        // ---- keyboard ----
        move(step) {
            if (!this.flat.length) return
            this.open = true
            this.active = (this.active + step + this.flat.length) % this.flat.length
            this.$nextTick(() => this.$el.querySelector('.gs-row.is-active')?.scrollIntoView({ block: 'nearest' }))
        },
        cycle_kind(step) {
            const keys = this.kinds.map(k => k.key)
            this.text = this.parsed.q
            this.kind = keys[(keys.indexOf(this.parsed.kind) + step + keys.length) % keys.length]
        },
        enter(e) {
            const row = this.flat[this.active] || (this.active < 0 ? this.flat.find(r => !r.more) : null)
            if (!row) return
            if (row.more) { this.narrow(row.g.kind); return }
            if (row.it.search) { this.use_recent(row.it.title); return }
            this.go(row.it, e.ctrlKey || e.metaKey)
        },
        narrow(kind) { this.text = this.parsed.q; this.kind = kind; this.$refs.input?.focus() },
        go(item, new_tab = false) {
            this.remember(this.parsed.q)
            if (new_tab) window.open(item.url, '_blank')
            else window.location.href = item.url
        },
        close() {
            if (this.open) this.open = false
            else { this.text = ''; this.$refs.input?.blur() }
        },
        clear() { this.text = ''; this.kind = ''; this.result = null; this.$refs.input?.focus() },

        // ---- recent searches (this browser only) ----
        remember(q) {
            q = (q || '').trim()
            if (q.length < 2) return
            this.recent = [q, ...this.recent.filter(r => r.toLowerCase() !== q.toLowerCase())].slice(0, RECENT_MAX)
            try { localStorage.setItem(RECENT_KEY, JSON.stringify(this.recent)) } catch (e) {}
        },
        use_recent(q) { this.text = q; this.$refs.input?.focus() },
        forget_recent() { this.recent = []; try { localStorage.removeItem(RECENT_KEY) } catch (e) {} },
    },
    template: /* html */ `
    <div class="gs" :class="{ 'is-open': open }" role="search">
      <teleport to="body"><div v-if="open" class="gs-backdrop" aria-hidden="true" @mousedown="open = false"></div></teleport>
      <div class="gs-box">
        <i class="fa-solid fa-magnifying-glass gs-icon" aria-hidden="true"></i>
        <span v-if="parsed.kind" class="gs-scope" :title="'Searching ' + kind_of(parsed.kind).label.toLowerCase() + ' only'">
          <i :class="kind_of(parsed.kind).icon"></i>[[ kind_of(parsed.kind).label ]]
        </span>
        <input ref="input" v-model="text" type="search" class="gs-input" autocomplete="off" spellcheck="false"
               placeholder="Search cases, tasks, notes, IOCs, tags…" aria-label="Search Flowintel"
               role="combobox" :aria-expanded="open" aria-controls="gs-panel" aria-autocomplete="list"
               @focus="on_focus" @click="on_focus"
               @keydown.down.prevent="move(1)" @keydown.up.prevent="move(-1)"
               @keydown.enter.prevent="enter($event)" @keydown.esc.prevent="close()"
               @keydown.tab.exact.prevent="cycle_kind(1)" @keydown.shift.tab.prevent="cycle_kind(-1)">
        <span v-if="loading" class="gs-spin" aria-hidden="true"><i class="fa-solid fa-circle-notch fa-spin"></i></span>
        <button v-else-if="text || kind" type="button" class="gs-clear" @click="clear" title="Clear" aria-label="Clear the search"><i class="fa-solid fa-xmark"></i></button>
        <kbd v-else class="gs-kbd" :title="'Focus the search: ' + shortcut + ' or /'">[[ shortcut ]]</kbd>
      </div>

      <div v-if="open" id="gs-panel" class="gs-panel" role="listbox">
        <!-- kinds -->
        <div class="gs-kinds" role="tablist" aria-label="What to search">
          <button v-for="k in kinds" :key="k.key" type="button" role="tab" class="gs-kind"
                  :class="{ 'is-active': parsed.kind === k.key }" :aria-selected="parsed.kind === k.key"
                  @mousedown.prevent @click="narrow(k.key)" :title="k.key ? 'Only ' + k.label.toLowerCase() + (k.prefix ? ' — or type ' + k.prefix[0] + ':' : '') : 'Everything'">
            <i :class="k.icon"></i>[[ k.label ]]
          </button>
        </div>

        <div class="gs-body">
          <!-- first answer on its way -->
          <div v-if="loading && !groups.length" class="gs-skeleton" aria-hidden="true">
            <div v-for="n in 5" :key="n" class="gs-sk-row"><span class="lo-sk" style="width:18px; height:18px; border-radius:5px"></span>
              <span class="gs-sk-text"><span class="lo-sk" :style="{ width: (40 + (n * 13) % 45) + '%' }"></span><span class="lo-sk lo-sk-sm" :style="{ width: (25 + (n * 7) % 30) + '%' }"></span></span></div>
          </div>

          <div v-else-if="error" class="gs-empty gs-error"><i class="fa-solid fa-triangle-exclamation"></i>[[ error ]]</div>

          <div v-else-if="!has_query && !groups.length" class="gs-empty"><i class="fa-solid fa-magnifying-glass"></i>Type to search cases, tasks, notes, IOCs, tags…</div>

          <div v-else-if="empty" class="gs-empty">
            <i class="fa-regular fa-face-meh"></i>Nothing found for “[[ parsed.q ]]”<template v-if="parsed.kind"> in [[ kind_of(parsed.kind).label.toLowerCase() ]]</template>.
            <button v-if="parsed.kind" type="button" class="gs-link" @mousedown.prevent @click="narrow('')">Search everything</button>
          </div>

          <!-- results (more groups may still be coming: result.pending) -->
          <template v-else>
            <div v-if="result && result.pending > 0 && groups.length" class="gs-pending"><i class="fa-solid fa-circle-notch fa-spin"></i>Still searching…</div>
            <div v-for="g in groups" :key="g.kind" class="gs-group" :class="{ 'is-stale': loading }">
              <div class="gs-group-head">
                <span><i :class="kind_icon(g.kind)"></i>[[ g.label ]]</span>
                <button v-if="g.kind === 'searches'" type="button" class="gs-link" @mousedown.prevent @click="forget_recent">Clear</button>
                <span v-else-if="g.kind !== 'recent' && !g.timed_out" class="gs-count">[[ total_label(g) ]]</span>
              </div>

              <div v-if="g.timed_out" class="gs-slow"><i class="fa-solid fa-hourglass-end"></i>Too many [[ g.label.toLowerCase() ]] to scan in time — add a word or pick this kind only.</div>
              <a v-for="it in g.items" :key="g.kind + it.id" :href="it.url" class="gs-row" role="option"
                 :class="{ 'is-active': active === index_of(g, it) }" :aria-selected="active === index_of(g, it)"
                 @mousemove="active = index_of(g, it)" @click.prevent="it.search ? use_recent(it.title) : go(it, $event.ctrlKey || $event.metaKey)">

                <!-- pages -->
                <template v-if="g.kind === 'pages'">
                  <i :class="it.icon + ' gs-row-icon'"></i>
                  <span class="gs-row-main"><span class="gs-row-title"><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span></span>
                  <span class="gs-row-side">Page</span>
                </template>

                <!-- recent searches -->
                <template v-else-if="g.kind === 'searches'">
                  <i class="fa-solid fa-magnifying-glass gs-row-icon"></i>
                  <span class="gs-row-main"><span class="gs-row-title gs-recent-q">[[ it.title ]]</span></span>
                  <span class="gs-row-side">Search again</span>
                </template>

                <!-- cases (and the recent ones) -->
                <template v-else-if="g.kind === 'cases' || g.kind === 'recent'">
                  <i class="fa-solid fa-folder-open gs-row-icon"></i>
                  <span class="gs-row-main">
                    <span class="gs-row-title"><span class="gs-id">#[[ it.id ]]</span><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template>
                      <i v-if="it.is_private" class="fa-solid fa-lock gs-flag" title="Private case"></i><i v-if="it.privileged" class="fa-solid fa-user-shield gs-flag gs-priv" title="Privileged case"></i></span>
                    <span v-if="g.kind === 'recent'" class="gs-row-sub"><i class="fa-solid fa-clock-rotate-left"></i>modified [[ since(it.last_modif) ]]<template v-if="it.sub"> · [[ it.sub ]]</template></span>
                    <span v-else-if="it.sub" class="gs-row-sub"><i class="fa-solid fa-ticket"></i><template v-for="p in highlight(it.sub, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span>
                  </span>
                  <span class="gs-row-side">
                    <span v-if="it.completed" class="gs-badge gs-badge--done">Finished</span>
                    <span v-else-if="status(it.status_id)" :class="'gs-badge text-bg-' + status(it.status_id).style">[[ status(it.status_id).name ]]</span>
                  </span>
                </template>

                <!-- tasks -->
                <template v-else-if="g.kind === 'tasks'">
                  <i class="fa-solid fa-list-check gs-row-icon"></i>
                  <span class="gs-row-main">
                    <span class="gs-row-title"><span class="gs-id">#[[ it.id ]]</span><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span>
                    <span class="gs-row-sub"><i class="fa-solid fa-folder"></i>#[[ it.case_id ]] [[ it.case_title ]]</span>
                  </span>
                  <span class="gs-row-side">
                    <span v-if="it.completed" class="gs-badge gs-badge--done">Done</span>
                    <span v-else-if="status(it.status_id)" :class="'gs-badge text-bg-' + status(it.status_id).style">[[ status(it.status_id).name ]]</span>
                  </span>
                </template>

                <!-- notes -->
                <template v-else-if="g.kind === 'notes'">
                  <i class="fa-solid fa-note-sticky gs-row-icon"></i>
                  <span class="gs-row-main">
                    <span class="gs-row-snippet"><template v-for="p in highlight(it.snippet, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span>
                    <span class="gs-row-sub"><i class="fa-solid fa-list-check"></i>[[ it.title ]] · #[[ it.case_id ]] [[ it.case_title ]]</span>
                  </span>
                </template>

                <!-- MISP attributes -->
                <template v-else-if="g.kind === 'attributes'">
                  <i class="misp-icon misp-icon-attribute misp-simple gs-row-icon"></i>
                  <span class="gs-row-main">
                    <span class="gs-row-title gs-mono"><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span>
                    <span class="gs-row-sub"><i class="fa-solid fa-folder"></i>#[[ it.case_id ]] [[ it.case_title ]]<template v-if="it.object"> · [[ it.object ]]</template></span>
                  </span>
                  <span class="gs-row-side"><span class="gs-badge gs-badge--type">[[ it.type ]]</span></span>
                </template>

                <!-- tags / clusters / custom tags: open the case list filtered on them -->
                <template v-else-if="g.kind === 'tags'">
                  <span class="gs-row-main gs-row-tag">
                    <tag_badge v-if="it.kind === 'custom'" kind="custom" :label="it.title" :color="it.color" :icon-class="it.icon"></tag_badge>
                    <tag_badge v-else-if="it.kind === 'taxonomy'" kind="taxonomy" :label="it.title" :color="it.color" :title="it.description || it.title"></tag_badge>
                    <tag_badge v-else kind="cluster" :label="it.title" :title="it.description || it.title"></tag_badge>
                  </span>
                  <span class="gs-row-side gs-tag-targets">
                    <button v-if="it.on_cases" type="button" class="gs-target" title="Cases with this tag" @click.stop.prevent="go({ url: it.cases_url }, $event.ctrlKey || $event.metaKey)"><i class="fa-solid fa-folder-open"></i>Cases</button>
                    <button v-if="it.on_tasks" type="button" class="gs-target" title="My assigned tasks with this tag" @click.stop.prevent="go({ url: it.tasks_url }, $event.ctrlKey || $event.metaKey)"><i class="fa-solid fa-list-check"></i>Tasks</button>
                  </span>
                </template>

                <!-- templates -->
                <template v-else-if="g.kind === 'templates'">
                  <i :class="(it.kind === 'note' ? 'fa-solid fa-note-sticky' : 'fa-solid fa-clone') + ' gs-row-icon'"></i>
                  <span class="gs-row-main"><span class="gs-row-title"><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span></span>
                  <span class="gs-row-side">[[ it.kind ]] template</span>
                </template>

                <!-- users (admins) -->
                <template v-else-if="g.kind === 'users'">
                  <user_chip :user="it.user" size="sm" no-card no-you class="gs-row-icon"></user_chip>
                  <span class="gs-row-main">
                    <span class="gs-row-title"><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span>
                    <span class="gs-row-sub">[[ it.sub ]]<template v-if="it.org"> · [[ it.org ]]</template></span>
                  </span>
                </template>

                <!-- organisations (admins) -->
                <template v-else>
                  <i class="fa-solid fa-building gs-row-icon"></i>
                  <span class="gs-row-main">
                    <span class="gs-row-title"><template v-for="p in highlight(it.title, needle)"><mark v-if="p.hit">[[ p.t ]]</mark><template v-else>[[ p.t ]]</template></template></span>
                    <span v-if="it.sub" class="gs-row-sub">[[ it.sub ]]</span>
                  </span>
                </template>
              </a>

              <a v-if="g.kind === 'attributes'" :href="'/tools/search_attr?value=' + encodeURIComponent(needle)" class="gs-row gs-more"
                 :class="{ 'is-active': active === attr_index }" @mousemove="active = attr_index" @click="remember(parsed.q)">
                <i class="fa-solid fa-magnifying-glass-location gs-row-icon"></i>Search “[[ needle ]]” in every MISP object of your cases
              </a>
              <button v-if="show_more(g)" type="button" class="gs-row gs-more" :class="{ 'is-active': active === more_index(g) }"
                      @mousemove="active = more_index(g)" @mousedown.prevent @click="narrow(g.kind)">
                <i class="fa-solid fa-angles-right gs-row-icon"></i>Show more [[ g.label.toLowerCase() ]] ([[ total_label(g) ]])
              </button>
            </div>
          </template>
        </div>

        <div class="gs-foot">
          <div class="gs-keys">
            <span><kbd>↑</kbd><kbd>↓</kbd> move</span>
            <span><kbd>Enter</kbd> open</span>
            <span><kbd>Ctrl</kbd><kbd>Enter</kbd> new tab</span>
            <span><kbd>Tab</kbd> kind</span>
            <span><kbd>Esc</kbd> close</span>
          </div>
          <div class="gs-foot-side">
            <span v-if="has_query && result" class="gs-took" :title="'Answered in ' + result.took_ms + ' ms — only what you can access'">[[ result.took_ms ]] ms</span>
            <a v-if="has_query && (!parsed.kind || parsed.kind === 'cases')" :href="'/case/?q=' + encodeURIComponent(parsed.q)" class="gs-link" @click="remember(parsed.q)">Case list <i class="fa-solid fa-arrow-right"></i></a>
          </div>
        </div>
        <div class="gs-tips">
          Narrow with <code>case:</code> <code>task:</code> <code>note:</code> <code>attr:</code> <code>tag:</code> <code>tpl:</code><template v-if="isAdmin"> <code>user:</code> <code>org:</code></template> · <code>#123</code> finds an id
        </div>
      </div>
    </div>
    `,
}
