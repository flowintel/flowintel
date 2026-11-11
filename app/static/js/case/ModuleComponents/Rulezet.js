/**
 * Rulezet.js — Rulezet tab of a case (module component, loaded by case_view.html when a
 * Rulezet connector is linked to the case).
 *
 * - Search the Rulezet instance (text + format) and add rules to the case in one click,
 *   or add one by its Rulezet id / URL.
 * - Each rule of the case: format chip with Rulezet's own logo and colour, metadata,
 *   the rule in a code viewer, copy / download, a "changed on Rulezet" check, resync.
 * - Syntax check by the Rulezet instance (a rule using other rules is compiled with them).
 * - Editing: an edited rule is saved in the case only when Rulezet says it is valid, then it
 *   can be sent to Rulezet: a direct update when you are its author there, otherwise (or by
 *   choice) an edit proposal for its author.
 * - Dependencies: the rules a rule needs on Rulezet, to add them to the case as well.
 *
 * Server side: app/case/case_rulezet.py (the API key never reaches the browser) and the
 * rulezet_rule module (app/modules/receive_from) used to add / resync a rule.
 */
import { display_toast } from '../../toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import SmartEditor from '/static/js/components/smart-editor.js'
import DiffView from '/static/js/components/diff-view.js'
const { ref, computed, onMounted, onBeforeUnmount, watch } = Vue

// File extension of each format, as Rulezet names its downloads
const EXTENSIONS = {
    yara: 'yar', sigma: 'yml', suricata: 'rules', sagan: 'rules', snort: 'rules', zeek: 'zeek',
    wazuh: 'xml', nse: 'nse', crs: 'conf', nova: 'nov', splunk: 'yml', elastic: 'toml', kql: 'kql',
    kunai: 'kun', atr: 'yaml', plum: 'yaml',
}

export default {
    delimiters: ['[[', ']]'],
    components: { SmartEditor, DiffView },
    props: {
        case_id: Number,
        cases_info: Object,
        connector_instances: Array,
        connector_type: String
    },
    setup(props) {
        const can_manage_rules = computed(() => {
            const info = props.cases_info
            const permission = info && info.permission
            return !!(permission && !permission.read_only &&
                (permission.admin || (permission.misp_editor && info.present_in_case)))
        })

        const selected_instance = ref(props.connector_instances && props.connector_instances.length ? props.connector_instances[0] : null)
        const ciid = computed(() => selected_instance.value ? selected_instance.value.case_task_instance_id : null)
        const base_url = computed(() => selected_instance.value ? (selected_instance.value.details.url || '').replace(/\/+$/, '') : '')

        const formats = ref([])
        const loading_formats = ref(false)
        const rules = ref([])
        const loading_rules = ref(true)
        const module_name = ref(null)

        // search
        const show_search = ref(false)
        const search_q = ref('')
        const search_format = ref('')
        const search_mine = ref(false)  // only my rules on Rulezet (needs an API key)
        const search_page = ref(1)
        const search = ref(null)        // {rules, total, page, pages, can_add}
        const searching = ref(false)
        const preview = ref(new Set())   // search results whose rule is shown
        const add_id = ref('')
        const adding = ref(null)

        // per-rule UI state, by local rule id
        const open_code = ref(new Set())
        const editing = ref({})         // id -> edited content
        const checks = ref({})          // id -> {valid, errors, warnings} | 'loading'
        const remote = ref({})          // id -> {remote, changed} | 'loading' | 'error'
        const busy = ref({})            // id -> 'resync' | 'remove' | 'save' | 'publish'
        const messages = ref({})        // id -> message for the author with a proposal
        const deps = ref({})            // id -> {requires, required_by} | 'loading' | 'error'

        const format_map = computed(() => Object.fromEntries(formats.value.map(f => [f.key, f])))
        function fmt(key) {
            const k = (key || '').toLowerCase()
            return format_map.value[k] || { key: k, title: key || 'Unknown', color: '#6C757D', icon: 'fa-file-code', logo: null }
        }

        async function get_json(url, opts) {
            const res = await fetch(url, opts)
            let data = {}
            try { data = await res.json() } catch (e) {}
            return { ok: res.ok, status: res.status, data }
        }

        function post_opts(body) {
            return {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': $('#csrf_token').val() },
                body: JSON.stringify(body)
            }
        }

        async function load_formats() {
            if (!ciid.value) return
            loading_formats.value = true
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/formats`)
            loading_formats.value = false
            if (r.ok) formats.value = r.data.formats || []
        }

        async function load_rules() {
            if (!selected_instance.value) return
            loading_rules.value = true
            const r = await get_json(`/case/${props.case_id}/rulezet_rules?instance_id=${selected_instance.value.details.id}`)
            if (r.ok) rules.value = r.data.rules || []
            loading_rules.value = false
            for (const rule of rules.value) check_remote(rule)
        }

        async function load_module() {
            const r = await get_json('/case/get_case_modules')
            if (!r.ok) return
            for (const [key, m] of Object.entries(r.data.modules || {})) {
                if (m.config && m.config.connector === 'rulezet') { module_name.value = key; break }
            }
        }

        // ---- search & add ----
        async function run_search(page = 1) {
            if (!ciid.value) return
            searching.value = true
            search_page.value = page
            const params = new URLSearchParams({ q: search_q.value.trim(), format: search_format.value, page, mine: search_mine.value ? 1 : 0 })
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/search?${params}`)
            searching.value = false
            if (r.ok) search.value = r.data
            else display_toast({ message: r.data.message || 'Search failed', toast_class: 'danger-subtle' })
        }

        function toggle_preview(r) {
            const k = r.id || r.uuid
            const s = new Set(preview.value)
            s.has(k) ? s.delete(k) : s.add(k)
            preview.value = s
        }

        function in_case(remote_id) {
            return rules.value.some(r => String(r.remote_id) === String(remote_id))
        }

        // Rulezet id from "1234", or from a rule URL (…/rule/detail_rule/1234)
        function parse_id(text) {
            const t = (text || '').trim()
            const m = t.match(/(?:detail_rule|edit_rule|detail)\/(\d+)/) || t.match(/^(\d+)$/)
            return m ? m[1] : null
        }

        async function add_rule(remote_id, silent = false) {
            if (!can_manage_rules.value || !remote_id) return false
            if (!module_name.value) {
                display_toast({ message: 'The Rulezet module is not installed on this Flowintel', toast_class: 'warning-subtle' })
                return false
            }
            adding.value = String(remote_id)
            const r = await get_json(`/case/${props.case_id}/call_connector_module_case`,
                post_opts({ module: module_name.value, case_task_instance_id: ciid.value, query: String(remote_id) }))
            adding.value = null
            if (r.ok) {
                if (!silent) display_toast({ message: 'Rule added to the case', toast_class: 'success-subtle' })
                await load_rules()
                return true
            }
            display_toast({ message: r.data.message || 'Could not add the rule', toast_class: 'danger-subtle' })
            return false
        }

        async function add_by_id() {
            const id = parse_id(add_id.value)
            if (!id) return display_toast({ message: 'Give a Rulezet rule id or URL', toast_class: 'warning-subtle' })
            if (await add_rule(id)) add_id.value = ''
        }

        // ---- rules of the case ----
        async function check_remote(rule) {
            if (!ciid.value || !rule.remote_id) return
            remote.value = { ...remote.value, [rule.id]: 'loading' }
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/rule/${rule.id}/remote`)
            remote.value = { ...remote.value, [rule.id]: r.ok ? r.data : 'error' }
        }

        function remote_of(rule) {
            const r = remote.value[rule.id]
            return r && typeof r === 'object' ? r : null
        }

        function rule_url(rule) {
            return rule.remote_id && base_url.value ? `${base_url.value}/rule/detail_rule/${encodeURIComponent(rule.remote_id)}` : null
        }

        function toggle_code(rule) {
            const s = new Set(open_code.value)
            s.has(rule.id) ? s.delete(rule.id) : s.add(rule.id)
            open_code.value = s
        }

        // Resync: first show what would change (diff between the case and Rulezet),
        // warn when the rule was also edited here (conflict), then sync or cancel
        const resync_modal_el = ref(null)
        const resync_target = ref(null)   // {rule, data} | {rule, loading: true} | {rule, error}
        let resync_modal = null

        async function resync(rule) {
            resync_target.value = { rule, loading: true }
            if (!resync_modal) resync_modal = new bootstrap.Modal(resync_modal_el.value)
            resync_modal.show()
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/rule/${rule.id}/remote`)
            if (resync_target.value && resync_target.value.rule.id === rule.id) {
                resync_target.value = r.ok ? { rule, data: r.data } : { rule, error: r.data.message || 'Could not read the rule on Rulezet' }
                if (r.ok) remote.value = { ...remote.value, [rule.id]: r.data }
            }
        }

        async function confirm_resync() {
            const t = resync_target.value
            if (!t || !t.rule) return
            busy.value = { ...busy.value, [t.rule.id]: 'resync' }
            const ok = await add_rule(t.rule.remote_id, true)
            busy.value = { ...busy.value, [t.rule.id]: null }
            if (ok) {
                display_toast({ message: 'Rule synced with Rulezet', toast_class: 'success-subtle' })
                const e = { ...editing.value }; delete e[t.rule.id]; editing.value = e
                resync_modal.hide()
            }
        }

        onBeforeUnmount(() => { try { resync_modal && resync_modal.dispose() } catch (e) {} })

        async function remove(rule) {
            const ok = await confirmDelete({ title: 'Remove this rule?', message: `"${rule.title}" will be removed from this case (not from Rulezet).` })
            if (!ok) return
            busy.value = { ...busy.value, [rule.id]: 'remove' }
            const r = await get_json(`/case/${props.case_id}/rulezet_rule_remove`, post_opts({ id: rule.id }))
            busy.value = { ...busy.value, [rule.id]: null }
            display_toast({ message: r.data.message || (r.ok ? 'Rule removed' : 'Could not remove the rule'), toast_class: r.ok ? 'success-subtle' : 'danger-subtle' })
            if (r.ok) await load_rules()
        }

        async function copy(rule) {
            const text = editing.value[rule.id] ?? rule.content ?? ''
            try {
                await navigator.clipboard.writeText(text)
                display_toast({ message: 'Rule copied', toast_class: 'success-subtle' })
            } catch (e) {
                display_toast({ message: 'Could not copy the rule', toast_class: 'warning-subtle' })
            }
        }

        function download(rule) {
            const ext = EXTENSIONS[(rule.format || '').toLowerCase()] || 'txt'
            const name = (rule.title || 'rule').replace(/[^\w.-]+/g, '_').slice(0, 80) + '.' + ext
            const blob = new Blob([rule.content || ''], { type: 'text/plain' })
            const a = document.createElement('a')
            a.href = URL.createObjectURL(blob)
            a.download = name
            a.click()
            setTimeout(() => URL.revokeObjectURL(a.href), 1000)
        }

        // ---- syntax check & edit ----
        async function check_syntax(rule) {
            const content = editing.value[rule.id] ?? rule.content
            checks.value = { ...checks.value, [rule.id]: 'loading' }
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/validate`, post_opts({ format: rule.format, content, rule_id: rule.id }))
            checks.value = { ...checks.value, [rule.id]: r.ok ? r.data : { valid: false, errors: [r.data.message || 'Check failed'], warnings: [] } }
        }

        function check_of(rule) {
            const c = checks.value[rule.id]
            return c && typeof c === 'object' ? c : null
        }

        // Details of each problem found by Rulezet: the line it points at (when given, e.g.
        // "line 6: undefined string ...") and that line's text in the checked rule
        function check_items(rule) {
            const c = check_of(rule)
            if (!c) return []
            const content = editing.value[rule.id] ?? rule.content ?? ''
            const lines = content.split('\n')
            const parse = (text, kind) => {
                const msg = String(text ?? '')
                const m = msg.match(/^\s*line\s+(\d+)\s*[:,-]?\s*(.*)$/i) || msg.match(/^(.*?)\s*\(?\bline\s+(\d+)\)?\s*$/i)
                let line = null, message = msg
                if (m) {
                    if (/^\d+$/.test(m[1])) { line = parseInt(m[1]); message = m[2] || msg }
                    else { line = parseInt(m[2]); message = m[1] || msg }
                }
                const code = line && line >= 1 && line <= lines.length ? lines[line - 1] : null
                return { kind, line, message, code }
            }
            return [...(c.errors || []).map(e => parse(e, 'error')), ...(c.warnings || []).map(w => parse(w, 'warning'))]
        }

        function start_edit(rule) {
            editing.value = { ...editing.value, [rule.id]: rule.content || '' }
            const s = new Set(open_code.value); s.add(rule.id); open_code.value = s
            const c = { ...checks.value }; delete c[rule.id]; checks.value = c
        }

        function cancel_edit(rule) {
            const e = { ...editing.value }; delete e[rule.id]; editing.value = e
            const c = { ...checks.value }; delete c[rule.id]; checks.value = c
        }

        async function save_edit(rule) {
            busy.value = { ...busy.value, [rule.id]: 'save' }
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/rule/${rule.id}/save`, post_opts({ content: editing.value[rule.id] }))
            busy.value = { ...busy.value, [rule.id]: null }
            if (r.ok) {
                display_toast({ message: 'Rule saved in the case', toast_class: 'success-subtle' })
                const e = { ...editing.value }; delete e[rule.id]; editing.value = e
                checks.value = { ...checks.value, [rule.id]: { valid: true, errors: [], warnings: r.data.warnings || [] } }
                await load_rules()
            } else {
                checks.value = { ...checks.value, [rule.id]: { valid: false, errors: r.data.errors || [r.data.message], warnings: r.data.warnings || [] } }
                display_toast({ message: r.data.message || 'Could not save the rule', toast_class: 'warning-subtle' })
            }
        }

        // Send the edited rule to Rulezet. mode 'edit': direct update (only its author there);
        // mode 'proposal': an edit proposal the author reviews. Saved in the case as well.
        async function publish(rule, mode) {
            const rem = remote_of(rule)
            if (!rem || !rem.has_key) {
                // No API key: copy the rule and open its edit page on Rulezet
                await copy(rule)
                window.open(base_url.value + '/rule/edit_rule/' + encodeURIComponent(rule.remote_id), '_blank', 'noopener')
                return
            }
            busy.value = { ...busy.value, [rule.id]: 'publish' }
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/rule/${rule.id}/publish`, post_opts({
                content: editing.value[rule.id], mode, message: messages.value[rule.id] || '',
                base_last_modif: rem.remote.last_modif,
            }))
            busy.value = { ...busy.value, [rule.id]: null }
            if (r.ok) {
                display_toast({ message: r.data.message, toast_class: 'success-subtle' })
                if (r.data.mode === 'proposal' && r.data.url) window.open(r.data.url, '_blank', 'noopener')
                const e = { ...editing.value }; delete e[rule.id]; editing.value = e
                const m = { ...messages.value }; delete m[rule.id]; messages.value = m
                await load_rules()
            } else {
                display_toast({ message: r.data.message || 'Could not send the rule to Rulezet', toast_class: 'warning-subtle' })
                // The rule changed on Rulezet meanwhile: refresh what we know of it
                if (r.data.conflict) check_remote(rule)
            }
        }

        // Rules this rule needs on Rulezet (and the ones needing it)
        async function toggle_deps(rule) {
            if (deps.value[rule.id] && deps.value[rule.id] !== 'error') {
                const d = { ...deps.value }; delete d[rule.id]; deps.value = d
                return
            }
            deps.value = { ...deps.value, [rule.id]: 'loading' }
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/rule/${rule.id}/dependencies`)
            deps.value = { ...deps.value, [rule.id]: r.ok ? r.data : 'error' }
        }

        function deps_of(rule) {
            const d = deps.value[rule.id]
            return d && typeof d === 'object' ? d : null
        }

        async function add_missing_deps(rule) {
            const d = deps_of(rule)
            if (!d) return
            for (const dep of d.requires.filter(x => !x.in_case && !in_case(x.id))) await add_rule(dep.id, true)
            display_toast({ message: 'Rules needed by this rule added to the case', toast_class: 'success-subtle' })
            deps.value = { ...deps.value, [rule.id]: 'loading' }
            const r = await get_json(`/case/${props.case_id}/rulezet/${ciid.value}/rule/${rule.id}/dependencies`)
            deps.value = { ...deps.value, [rule.id]: r.ok ? r.data : 'error' }
        }

        function select_instance(ev) {
            const iid = parseInt(ev.target.value)
            const found = props.connector_instances.find(c => c.details.id === iid)
            if (found) selected_instance.value = found
        }

        function cves(value) {
            if (Array.isArray(value)) return value.slice(0, 6)
            const raw = typeof value === 'string' ? value : ''
            return (raw.match(/(CVE-\d{4}-\d+|GHSA-[\w-]+)/gi) || []).slice(0, 6)
        }

        function line_count(rule) {
            return (rule.content || '').split('\n').length
        }

        function short_date(d) {
            if (!d) return ''
            const x = dayjs(d)
            return x.isValid() ? x.format('YYYY-MM-DD') : d
        }

        watch(selected_instance, () => { load_formats(); load_rules(); search.value = null })

        onMounted(async () => {
            await Promise.all([load_formats(), load_module(), load_rules()])
        })

        return {
            can_manage_rules, selected_instance, base_url, formats, loading_formats, rules, loading_rules,
            show_search, search_q, search_format, search_mine, search, messages, deps, toggle_deps, deps_of, add_missing_deps, searching, run_search, search_page,
            add_id, adding, add_rule, add_by_id, parse_id, in_case, preview, toggle_preview,
            open_code, editing, checks, remote, busy, toggle_code, remote_of, rule_url,
            resync, confirm_resync, resync_modal_el, resync_target, remove, copy, download, check_syntax, check_of, check_items, start_edit, cancel_edit, save_edit, publish,
            select_instance, fmt, cves, short_date, line_count,
        }
    },
    template: `
    <div class="rz">
        <!-- header: instance, counts, actions -->
        <div class="rz-head">
            <div class="rz-head-title">
                <span class="rz-logo rz-head-logo" role="img" aria-label="Rulezet"><img class="rz-logo-light" src="/static/image/connectors/rulezet.png" alt=""><img class="rz-logo-dark" src="/static/image/connectors/rulezet-dark.png" alt=""></span>
                <div>
                    <div class="rz-head-name">Rulezet</div>
                    <a v-if="base_url" :href="base_url" target="_blank" rel="noopener" class="rz-head-url">[[ base_url.replace(/^https?:\\/\\//, '') ]] <i class="fa-solid fa-arrow-up-right-from-square fa-2xs"></i></a>
                </div>
            </div>
            <select v-if="connector_instances && connector_instances.length > 1" class="form-select form-select-sm rz-instance" @change="select_instance($event)">
                <option v-for="inst in connector_instances" :key="inst.case_task_instance_id" :value="inst.details.id">[[ inst.details.name ]]</option>
            </select>
            <span class="rz-count"><b>[[ rules.length ]]</b> [[ rules.length === 1 ? 'rule' : 'rules' ]] in this case
                <span v-if="loading_rules && rules.length" class="spinner-border spinner-border-sm ms-1" title="Updating…"></span></span>
            <a v-if="base_url" :href="base_url + '/rule/create_rule'" target="_blank" rel="noopener" class="btn btn-sm btn-outline-primary ms-auto" title="Write a new rule on Rulezet (opens in a new tab)">
                <i class="fa-solid fa-pen-to-square me-1"></i>Write a rule
            </a>
            <button v-if="can_manage_rules" class="btn btn-sm" :class="[show_search ? 'btn-secondary' : 'btn-primary', { 'ms-auto': !base_url }]" @click="show_search = !show_search">
                <i :class="show_search ? 'fa-solid fa-xmark' : 'fa-solid fa-plus'" class="me-1"></i>[[ show_search ? 'Close' : 'Add rules' ]]
            </button>
        </div>

        <!-- search Rulezet and add rules -->
        <section v-if="show_search && can_manage_rules" class="rz-search">
            <div class="rz-search-bar">
                <div class="rz-search-input">
                    <i class="fa-solid fa-magnifying-glass"></i>
                    <input class="form-control form-control-sm" v-model="search_q" placeholder="Search Rulezet: title, content, author…" @keyup.enter="run_search(1)">
                </div>
                <div class="form-check form-switch rz-mine" title="Only the rules you published on Rulezet (needs an API key on the connector)">
                    <input class="form-check-input" type="checkbox" id="rz-mine" v-model="search_mine" @change="run_search(1)">
                    <label class="form-check-label small" for="rz-mine">My rules</label>
                </div>
                <button class="btn btn-primary btn-sm" @click="run_search(1)" :disabled="searching">
                    <span v-if="searching" class="spinner-border spinner-border-sm me-1"></span>Search
                </button>
                <div class="rz-add-id">
                    <input class="form-control form-control-sm" v-model="add_id" placeholder="Rule id or URL" @keyup.enter="add_by_id()">
                    <button class="btn btn-outline-primary btn-sm" @click="add_by_id()" :disabled="!!adding" title="Add a rule by its Rulezet id or URL">
                        <span v-if="adding && adding === parse_id(add_id)" class="spinner-border spinner-border-sm me-1"></span>Add
                    </button>
                </div>
            </div>
            <div v-if="loading_formats && !formats.length" class="rz-loading rz-loading--inline"><span class="spinner-border spinner-border-sm"></span>Loading the formats from Rulezet…</div>
            <div v-else class="rz-formats">
                <button type="button" :class="['rz-chip rz-chip--all', { active: !search_format }]" @click="search_format = ''; run_search(1)">All formats</button>
                <button v-for="f in formats" :key="f.key" type="button" :class="['rz-chip', { active: search_format === f.key }]" :style="{ '--fmt': f.color }"
                        :title="f.rule_count ? f.rule_count.toLocaleString() + ' rules on Rulezet' : f.title" @click="search_format = f.key; run_search(1)">
                    <span class="rz-chip-logo"><img v-if="f.logo" :src="f.logo" alt=""><i v-else :class="'fa-solid ' + f.icon"></i></span>[[ f.title ]]
                </button>
            </div>

            <div v-if="searching" class="rz-loading"><span class="spinner-border"></span><span>Searching Rulezet…</span></div>
            <div v-else-if="search" class="rz-results">
                <div class="rz-results-head">
                    <span><b>[[ search.total.toLocaleString() ]]</b> rules found</span>
                    <span v-if="!search.can_add" class="text-warning-emphasis small"><i class="fa-solid fa-key me-1"></i>Add an API key to the connector to add rules straight from the search.</span>
                </div>
                <div class="rz-result-grid">
                    <article v-for="r in search.rules" :key="r.uuid || r.id" :class="['rz-result', { 'rz-result--open': preview.has(r.id || r.uuid) }]" :style="{ '--fmt': fmt(r.format).color }">
                        <div class="rz-result-top">
                            <span class="rz-chip rz-chip--sm" :style="{ '--fmt': fmt(r.format).color }"><span class="rz-chip-logo"><img v-if="fmt(r.format).logo" :src="fmt(r.format).logo" alt=""><i v-else :class="'fa-solid ' + fmt(r.format).icon"></i></span>[[ fmt(r.format).title ]]</span>
                            <span class="rz-result-date">[[ short_date(r.creation_date) ]]</span>
                        </div>
                        <a class="rz-result-title" :title="r.title" :href="r.id ? base_url + '/rule/detail_rule/' + r.id : base_url + '/rule/detail_rule/' + r.uuid" target="_blank" rel="noopener">[[ r.title ]]</a>
                        <p class="rz-result-desc" :title="r.description">[[ r.description ]]</p>
                        <smart-editor v-if="preview.has(r.id || r.uuid)" :model-value="r.to_string || r.content || ''" mode="code"
                                      :language="(r.format || 'text').toLowerCase()" :readonly="true" min-height="80px" max-height="320px"></smart-editor>
                        <div class="rz-result-foot">
                            <span class="rz-result-author" :title="r.author"><i class="fa-solid fa-user-pen fa-xs me-1"></i>[[ (r.author || 'Unknown').split(',')[0] ]]</span>
                            <span v-if="r.vote_up" class="rz-votes" title="Likes on Rulezet"><i class="fa-solid fa-thumbs-up fa-xs"></i> [[ r.vote_up ]]</span>
                            <!-- always the same place: View, then Add / In case -->
                            <div class="rz-result-actions">
                                <button v-if="r.to_string || r.content" type="button" :class="['btn btn-sm btn-outline-secondary rz-view', { active: preview.has(r.id || r.uuid) }]"
                                        @click="toggle_preview(r)" :title="preview.has(r.id || r.uuid) ? 'Hide the rule' : 'View the rule'">
                                    <i :class="preview.has(r.id || r.uuid) ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i> View
                                </button>
                                <span v-if="r.id && in_case(r.id)" class="rz-in-case"><i class="fa-solid fa-check"></i> In case</span>
                                <button v-else-if="search.can_add && r.id" class="btn btn-sm btn-outline-primary rz-add" @click="add_rule(r.id)" :disabled="adding === String(r.id)" title="Add this rule to the case">
                                    <span v-if="adding === String(r.id)" class="spinner-border spinner-border-sm"></span><i v-else class="fa-solid fa-plus"></i> Add
                                </button>
                            </div>
                        </div>
                    </article>
                </div>
                <div v-if="search.pages > 1" class="rz-pager">
                    <button class="btn btn-sm btn-outline-secondary" :disabled="search_page <= 1 || searching" @click="run_search(search_page - 1)"><i class="fa-solid fa-chevron-left"></i></button>
                    <span>Page [[ search_page ]] / [[ search.pages ]]</span>
                    <button class="btn btn-sm btn-outline-secondary" :disabled="search_page >= search.pages || searching" @click="run_search(search_page + 1)"><i class="fa-solid fa-chevron-right"></i></button>
                </div>
            </div>
        </section>

        <!-- rules of the case -->
        <div v-if="loading_rules && !rules.length" class="rz-loading"><span class="spinner-border"></span><span>Loading the rules of this case…</span></div>
        <div v-else-if="!rules.length" class="rz-empty">
            <span class="rz-logo rz-empty-logo" role="img" aria-label="Rulezet"><img class="rz-logo-light" src="/static/image/connectors/rulezet.png" alt=""><img class="rz-logo-dark" src="/static/image/connectors/rulezet-dark.png" alt=""></span>
            <p>No Rulezet rule in this case yet.</p>
            <button v-if="can_manage_rules" class="btn btn-primary btn-sm" @click="show_search = true"><i class="fa-solid fa-plus me-1"></i>Add rules</button>
        </div>

        <article v-for="rule in rules" :key="rule.id" class="rz-rule" :style="{ '--fmt': fmt(rule.format).color }">
            <header class="rz-rule-head">
                <span class="rz-chip" :style="{ '--fmt': fmt(rule.format).color }">
                    <span class="rz-chip-logo"><img v-if="fmt(rule.format).logo" :src="fmt(rule.format).logo" alt=""><i v-else :class="'fa-solid ' + fmt(rule.format).icon"></i></span>[[ fmt(rule.format).title ]]
                </span>
                <a v-if="rule_url(rule)" :href="rule_url(rule)" target="_blank" rel="noopener" class="rz-rule-title">[[ rule.title || 'Untitled rule' ]]</a>
                <span v-else class="rz-rule-title">[[ rule.title || 'Untitled rule' ]]</span>
                <span v-if="rule.version" class="rz-pill">v[[ rule.version ]]</span>
                <span v-if="remote_of(rule) && remote_of(rule).changed" class="rz-pill rz-pill--warn" title="The rule on Rulezet differs from the one in this case (it was updated there, or edited here)">
                    <i class="fa-solid fa-code-compare me-1"></i>Differs from Rulezet
                </span>
                <span v-else-if="remote_of(rule)" class="rz-pill rz-pill--ok" title="Same as on Rulezet"><i class="fa-solid fa-check me-1"></i>Up to date</span>
                <span v-if="rule.edited_locally" class="rz-pill rz-pill--edit" title="Edited in Flowintel since it was taken from Rulezet"><i class="fa-solid fa-pen me-1"></i>Edited here</span>
                <span v-else-if="remote[rule.id] === 'error'" class="rz-pill" title="The rule could not be read on Rulezet"><i class="fa-solid fa-circle-exclamation me-1"></i>Not reachable</span>
                <span v-else-if="remote[rule.id] === 'loading'" class="rz-pill" title="Comparing with the rule on Rulezet"><span class="spinner-border spinner-border-sm me-1"></span>Checking Rulezet…</span>
                <div class="rz-card-actions">
                    <button class="rz-act" @click="check_syntax(rule)" :disabled="checks[rule.id] === 'loading'" title="Check the syntax with Rulezet">
                        <span v-if="checks[rule.id] === 'loading'" class="spinner-border spinner-border-sm"></span><i v-else class="fa-solid fa-spell-check"></i>
                    </button>
                    <button class="rz-act" @click="copy(rule)" title="Copy the rule"><i class="fa-regular fa-copy"></i></button>
                    <button v-if="can_manage_rules && editing[rule.id] === undefined" class="rz-act rz-act--primary" @click="start_edit(rule)" :title="remote_of(rule) && remote_of(rule).owner ? 'Edit the rule (you are its author on Rulezet)' : 'Edit the rule (you can propose the change to its author on Rulezet)'"><i class="fa-solid fa-pen"></i></button>
                    <button v-if="can_manage_rules" class="rz-act rz-act--primary" @click="resync(rule)" :disabled="busy[rule.id] === 'resync'" title="Compare with Rulezet and resync">
                        <span v-if="busy[rule.id] === 'resync'" class="spinner-border spinner-border-sm"></span><i v-else class="fa-solid fa-rotate"></i>
                    </button>
                    <div class="rz-menu-wrap" @click.stop>
                        <button class="rz-act" title="More actions"><i class="fa-solid fa-ellipsis-vertical"></i></button>
                        <div class="rz-menu">
                            <a v-if="rule_url(rule)" :href="rule_url(rule)" target="_blank" rel="noopener" class="rz-menu-item"><i class="fa-solid fa-arrow-up-right-from-square"></i>Open on Rulezet</a>
                            <button class="rz-menu-item" @click="download(rule)"><i class="fa-solid fa-download"></i>Download</button>
                            <button class="rz-menu-item" @click="toggle_deps(rule)"><i class="fa-solid fa-diagram-project"></i>[[ deps[rule.id] ? 'Hide dependencies' : 'Dependencies' ]]</button>
                            <template v-if="can_manage_rules">
                                <div class="rz-menu-divider"></div>
                                <button class="rz-menu-item rz-menu-item--danger" @click="remove(rule)" :disabled="busy[rule.id] === 'remove'"><i class="fa-solid fa-trash"></i>Remove from case</button>
                            </template>
                        </div>
                    </div>
                </div>
            </header>

            <div class="rz-meta">
                <span v-if="remote_of(rule) && remote_of(rule).remote.source" :title="remote_of(rule).remote.source"><i class="fa-solid fa-user-pen"></i>[[ remote_of(rule).remote.source.split(',')[0] ]]</span>
                <span v-if="remote_of(rule) && remote_of(rule).remote.license"><i class="fa-solid fa-scale-balanced"></i>[[ remote_of(rule).remote.license ]]</span>
                <span v-if="rule.remote_id"><i class="fa-solid fa-hashtag"></i>Rulezet [[ rule.remote_id ]]</span>
                <span><i class="fa-regular fa-calendar-plus"></i>Added [[ short_date(rule.date_added) ]]</span>
                <template v-if="remote_of(rule)">
                    <span v-for="c in cves(remote_of(rule).remote.cve_id)" :key="c" class="rz-cve">[[ c ]]</span>
                    <span v-for="t in remote_of(rule).remote.attacks" :key="'att-' + t" class="rz-attack" title="MITRE ATT&CK technique"><i class="fa-solid fa-crosshairs"></i>[[ t ]]</span>
                    <span v-for="t in remote_of(rule).remote.tags" :key="'tag-' + t" class="rz-tag"><i class="fa-solid fa-tag"></i>[[ t ]]</span>
                </template>
            </div>
            <p v-if="rule.description" class="rz-rule-desc">[[ rule.description ]]</p>

            <!-- dependencies on Rulezet -->
            <div v-if="deps[rule.id]" class="rz-deps">
                <div v-if="deps[rule.id] === 'loading'" class="text-muted small"><span class="spinner-border spinner-border-sm me-1"></span>Reading the dependencies on Rulezet…</div>
                <div v-else-if="deps[rule.id] === 'error'" class="text-danger small"><i class="fa-solid fa-circle-exclamation me-1"></i>Could not read the dependencies on Rulezet.</div>
                <template v-else>
                    <div class="rz-deps-head">
                        <i class="fa-solid fa-diagram-project"></i>
                        <b>Needs</b>
                        <span v-if="!deps_of(rule).requires.length" class="text-muted">no other rule</span>
                        <button v-if="can_manage_rules && deps_of(rule).requires.some(d => !d.in_case && !in_case(d.id))" class="btn btn-sm btn-outline-primary ms-auto" @click="add_missing_deps(rule)" :disabled="!!adding">
                            <span v-if="adding" class="spinner-border spinner-border-sm me-1"></span><i v-else class="fa-solid fa-plus me-1"></i>Add the missing ones to the case
                        </button>
                    </div>
                    <ul v-if="deps_of(rule).requires.length" class="rz-deps-list">
                        <li v-for="d in deps_of(rule).requires" :key="d.id">
                            <span class="rz-chip rz-chip--sm" :style="{ '--fmt': fmt(d.format).color }">[[ fmt(d.format).title ]]</span>
                            <a :href="base_url + '/rule/detail_rule/' + d.id" target="_blank" rel="noopener">[[ d.title ]]</a>
                            <span v-if="d.depth > 1" class="text-muted small">via another rule</span>
                            <span v-if="d.in_case || in_case(d.id)" class="rz-in-case ms-auto"><i class="fa-solid fa-check"></i> In case</span>
                            <button v-else-if="can_manage_rules" class="btn btn-sm btn-link ms-auto" @click="add_rule(d.id)" :disabled="adding === String(d.id)">Add</button>
                        </li>
                    </ul>
                    <div v-if="deps_of(rule).required_by.length" class="rz-deps-head mt-2">
                        <i class="fa-solid fa-arrow-turn-up"></i><b>Used by</b>
                        <span class="text-muted">[[ deps_of(rule).required_by.map(d => d.title).join(', ') ]]</span>
                    </div>
                </template>
            </div>

            <button type="button" :class="['rz-show', { 'is-open': open_code.has(rule.id) }]" @click="toggle_code(rule)" :aria-expanded="open_code.has(rule.id)">
                <i class="fa-solid fa-code"></i>
                <span>[[ open_code.has(rule.id) ? 'Hide the rule' : 'Show the rule' ]]</span>
                <span class="rz-show-meta">[[ fmt(rule.format).title ]] · [[ line_count(rule) ]] lines</span>
                <i class="fa-solid fa-chevron-down rz-show-chevron"></i>
            </button>

            <!-- syntax check result: summary, then each problem with its line -->
            <div v-if="check_of(rule)" :class="['rz-check', check_of(rule).valid ? 'rz-check--ok' : 'rz-check--bad']">
                <div class="rz-check-title">
                    <i :class="check_of(rule).valid ? 'fa-solid fa-circle-check' : 'fa-solid fa-circle-xmark'"></i>
                    <span v-if="check_of(rule).valid">Valid [[ fmt(rule.format).title ]] rule</span>
                    <span v-else>Invalid [[ fmt(rule.format).title ]] rule</span>
                    <span class="rz-check-count">
                        <span v-if="check_of(rule).errors.length">[[ check_of(rule).errors.length ]] [[ check_of(rule).errors.length === 1 ? 'error' : 'errors' ]]</span>
                        <span v-if="check_of(rule).warnings.length">[[ check_of(rule).warnings.length ]] [[ check_of(rule).warnings.length === 1 ? 'warning' : 'warnings' ]]</span>
                    </span>
                    <span class="rz-check-by">checked by Rulezet</span>
                </div>
                <ol v-if="check_items(rule).length" class="rz-issues">
                    <li v-for="(it, i) in check_items(rule)" :key="i" :class="'rz-issue rz-issue--' + it.kind">
                        <div class="rz-issue-head">
                            <i :class="it.kind === 'error' ? 'fa-solid fa-circle-xmark' : 'fa-solid fa-triangle-exclamation'"></i>
                            <span v-if="it.line" class="rz-issue-line">Line [[ it.line ]]</span>
                            <span class="rz-issue-msg">[[ it.message ]]</span>
                        </div>
                        <pre v-if="it.code !== null" class="rz-issue-code"><span class="rz-issue-ln">[[ it.line ]]</span>[[ it.code || ' ' ]]</pre>
                    </li>
                </ol>
            </div>

            <!-- code: read-only viewer, or the editor while editing -->
            <div v-if="open_code.has(rule.id)" class="rz-code">
                <template v-if="editing[rule.id] !== undefined">
                    <smart-editor v-model="editing[rule.id]" mode="code" :language="(rule.format || 'text').toLowerCase()" min-height="220px" max-height="560px"></smart-editor>
                    <input v-if="remote_of(rule) && remote_of(rule).has_key" class="form-control form-control-sm rz-edit-msg" v-model="messages[rule.id]" maxlength="2000"
                           placeholder="What changed and why (empty: &quot;Change proposed from Flowintel.&quot;)">
                    <div class="rz-edit-bar">
                        <button class="btn btn-sm btn-outline-secondary" @click="check_syntax(rule)" :disabled="checks[rule.id] === 'loading'"><i class="fa-solid fa-spell-check me-1"></i>Check syntax</button>
                        <button class="btn btn-sm btn-success" @click="save_edit(rule)" :disabled="busy[rule.id] === 'save'" title="Saved in the case only if Rulezet says the syntax is valid">
                            <span v-if="busy[rule.id] === 'save'" class="spinner-border spinner-border-sm me-1"></span><i v-else class="fa-solid fa-floppy-disk me-1"></i>Save in case
                        </button>
                        <template v-if="remote_of(rule) && remote_of(rule).has_key">
                            <button v-if="remote_of(rule).owner" class="btn btn-sm btn-primary" @click="publish(rule, 'edit')" :disabled="busy[rule.id] === 'publish'" title="You are the author: update the rule on Rulezet (new version)">
                                <span v-if="busy[rule.id] === 'publish'" class="spinner-border spinner-border-sm me-1"></span><i v-else class="fa-solid fa-cloud-arrow-up me-1"></i>Update on Rulezet
                            </button>
                            <button class="btn btn-sm btn-outline-primary" @click="publish(rule, 'proposal')" :disabled="busy[rule.id] === 'publish'" title="Create an edit proposal on Rulezet for the author to review">
                                <i class="fa-solid fa-code-pull-request me-1"></i>Propose the change
                            </button>
                        </template>
                        <button v-else class="btn btn-sm btn-outline-primary" @click="publish(rule)" title="No API key on the connector: the rule is copied and its edit page opens on Rulezet, paste it there">
                            <i class="fa-solid fa-cloud-arrow-up me-1"></i>Copy & open on Rulezet
                        </button>
                        <button class="btn btn-sm btn-link" @click="cancel_edit(rule)">Cancel</button>
                    </div>
                </template>
                <smart-editor v-else :model-value="rule.content || ''" mode="code" :language="(rule.format || 'text').toLowerCase()" :readonly="true" min-height="120px" max-height="520px"></smart-editor>
            </div>
        </article>

        <!-- resync: diff between the case and Rulezet, conflict warning, sync or cancel -->
        <div class="modal fade" ref="resync_modal_el" tabindex="-1" aria-hidden="true">
            <div class="modal-dialog modal-xl modal-dialog-centered modal-dialog-scrollable">
                <div class="modal-content rz-modal" v-if="resync_target">
                    <div class="modal-header">
                        <span class="rz-logo rz-modal-logo" role="img" aria-label="Rulezet"><img class="rz-logo-light" src="/static/image/connectors/rulezet.png" alt=""><img class="rz-logo-dark" src="/static/image/connectors/rulezet-dark.png" alt=""></span>
                        <div class="rz-modal-titles">
                            <div class="rz-modal-kind">Resync from Rulezet</div>
                            <h5 class="modal-title">[[ resync_target.rule.title ]]</h5>
                        </div>
                        <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Cancel"></button>
                    </div>
                    <div class="modal-body">
                        <div v-if="resync_target.loading" class="text-center text-muted py-4"><span class="spinner-border spinner-border-sm me-2"></span>Reading the rule on Rulezet…</div>
                        <div v-else-if="resync_target.error" class="alert alert-danger mb-0">[[ resync_target.error ]]</div>
                        <template v-else>
                            <div v-if="resync_target.data.conflict" class="rz-sync-state rz-sync-state--conflict">
                                <i class="fa-solid fa-triangle-exclamation"></i>
                                <div><b>Conflict.</b> This rule was edited in Flowintel <u>and</u> updated on Rulezet. Syncing replaces your edits with the Rulezet version: check the diff below first.</div>
                            </div>
                            <div v-else-if="resync_target.data.local_changed && !resync_target.data.remote_changed" class="rz-sync-state rz-sync-state--warn">
                                <i class="fa-solid fa-pen"></i>
                                <div><b>Edited in Flowintel.</b> Rulezet did not change, so syncing only drops your edits and goes back to the Rulezet version.</div>
                            </div>
                            <div v-else-if="resync_target.data.changed" class="rz-sync-state rz-sync-state--new">
                                <i class="fa-solid fa-cloud-arrow-down"></i>
                                <div><b>Rulezet has a newer version.</b> Syncing replaces the rule of this case with it.</div>
                            </div>
                            <div v-else class="rz-sync-state rz-sync-state--ok">
                                <i class="fa-solid fa-circle-check"></i>
                                <div><b>Already up to date.</b> The rule is the same as on Rulezet.</div>
                            </div>
                            <diff-view :old-text="resync_target.rule.content || ''" :new-text="resync_target.data.remote_content"
                                       old-name="In this case" new-name="On Rulezet" max-height="55vh"></diff-view>
                        </template>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                        <button v-if="resync_target.data && resync_target.data.changed" type="button"
                                :class="['btn', resync_target.data.conflict ? 'btn-danger' : 'btn-primary']"
                                @click="confirm_resync()" :disabled="busy[resync_target.rule.id] === 'resync'">
                            <span v-if="busy[resync_target.rule.id] === 'resync'" class="spinner-border spinner-border-sm me-1"></span>
                            <i v-else class="fa-solid fa-rotate me-1"></i>[[ resync_target.data.conflict ? 'Replace my edits and sync' : 'Sync with Rulezet' ]]
                        </button>
                    </div>
                </div>
            </div>
        </div>
    </div>
    `
}
