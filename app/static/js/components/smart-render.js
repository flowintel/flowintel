/**
 * smart-render.js — Read-only viewer for code, JSON, and markdown content
 *
 * Read-only counterpart to smart-editor.js.
 *
 * Props:
 *   code          String   (required) — source content to display
 *   language      String   — 'json' | 'markdown' | 'javascript' | 'python' | 'bash'
 *                            | 'sql' | 'html' | 'css' | 'text' | 'auto'  (default: 'auto')
 *   title         String   — optional filename shown in header
 *   maxHeight     String   — CSS value, e.g. '500px' (default: '520px')
 *   foldable      Boolean  — enable JSON fold/unfold tree (default: true for JSON)
 *   showLines     Boolean  — show line numbers (default: true)
 *
 * Features:
 *   - Syntax highlighting via highlight.js (lazy-loaded from /static/js/hljs.min.js)
 *   - Markdown rendering with ```mermaid diagram support (shared with smart-editor.js,
 *     via markdown-render.js) — toggle between rendered view and raw source
 *   - JSON interactive tree: collapse/expand any object or array
 *   - Integrated search: real-time highlight, prev/next, match counter
 *   - Line numbers (sync-scrolled with code pane)
 *   - Word-wrap toggle
 *   - Copy to clipboard
 *   - Language badge + auto-detection
 *   - Colors adapt to every theme via CSS variables
 *
 * Usage:
 *   import SmartRender from '/static/js/components/smart-render.js'
 *   <smart_render :code="source" language="json" title="config.json"></smart_render>
 *   <smart_render :code="case.description" language="markdown"></smart_render>
 */

const { ref, computed, watch, onMounted, nextTick } = Vue
import { renderMarkdown, runMermaid } from './markdown-render.js'

// ── highlight.js lazy loader ───────────────────────────────────────────────────
// Injects a <script> tag once, reuses window.hljs for all instances.

let _hljs_ready = null

function load_hljs() {
    if (_hljs_ready) return _hljs_ready
    if (window.hljs) { _hljs_ready = Promise.resolve(window.hljs); return _hljs_ready }
    _hljs_ready = new Promise((resolve, reject) => {
        const s = document.createElement('script')
        s.src = '/static/js/hljs.min.js'
        s.onload = () => resolve(window.hljs)
        s.onerror = () => reject(new Error('highlight.js failed to load'))
        document.head.appendChild(s)
    })
    return _hljs_ready
}

// ── HTML escaping ──────────────────────────────────────────────────────────────

function esc(s) {
    return String(s ?? '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
}

// ── Search injection ───────────────────────────────────────────────────────────
// Injects <mark> tags into already-highlighted HTML while staying outside HTML tags.

function inject_search_marks(html, term, matches_map, focus_key) {
    if (!term) return html
    let match_n = 0
    return html.replace(/>([^<]*)</g, (full, text) => {
        if (!text) return full
        const re = new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
        const marked = text.replace(re, m => {
            const key = match_n++
            const cls = key === focus_key ? 'cv-match cv-match--focus' : 'cv-match'
            return `<mark class="${cls}" data-match="${key}">${m}</mark>`
        })
        return `>${marked}<`
    })
}

// Counts matches of a search term in a plain-text string.
function count_matches(text, term) {
    if (!term) return 0
    try {
        return (text.match(new RegExp(term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')) || []).length
    } catch { return 0 }
}

// ── Auto-highlight (non-interactive) ────────────────────────────────────────────
// Independent from the search box: marks every occurrence of the given terms in
// orange, e.g. to show which YARA string patterns were found in a test. Terms are
// escaped and OR'd into one pass so overlapping/adjacent matches don't double-wrap.

function escape_re(s) {
    return String(s).replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
}

function inject_auto_marks(html, terms) {
    const list = (terms || []).filter(Boolean).map(String)
    if (!list.length) return html
    const pattern = list.map(escape_re).join('|')
    let re
    try { re = new RegExp(pattern, 'gi') } catch { return html }
    return html.replace(/>([^<]*)</g, (full, text) => {
        if (!text) return full
        const marked = text.replace(re, m => `<mark class="cv-match cv-match--auto">${m}</mark>`)
        return `>${marked}<`
    })
}

// ── JSON tree builder ──────────────────────────────────────────────────────────
// Builds a flat array of display lines with fold metadata.

function esc_str(s) {
    return String(s)
        .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
}

function build_json_tree(json_str) {
    let obj
    try { obj = JSON.parse(json_str) } catch { return null }

    const lines = []

    function walk(val, depth, key, is_last) {
        const ind = '  '.repeat(depth)
        const k = key !== null ? `<span class="cv-key">"${esc_str(String(key))}"</span><span class="cv-punct">: </span>` : ''
        const tail = is_last ? '' : '<span class="cv-punct">,</span>'

        if (val === null) {
            lines.push({ depth, type: 'leaf', html: `${ind}${k}<span class="cv-null">null</span>${tail}` })
        } else if (typeof val === 'boolean') {
            lines.push({ depth, type: 'leaf', html: `${ind}${k}<span class="cv-bool">${val}</span>${tail}` })
        } else if (typeof val === 'number') {
            lines.push({ depth, type: 'leaf', html: `${ind}${k}<span class="cv-num">${val}</span>${tail}` })
        } else if (typeof val === 'string') {
            lines.push({ depth, type: 'leaf', html: `${ind}${k}<span class="cv-str">"${esc_str(val)}"</span>${tail}` })
        } else if (Array.isArray(val)) {
            const open_idx = lines.length
            lines.push({
                depth, type: 'open', bracket: '[', open_idx, close_idx: -1,
                size: val.length, html: `${ind}${k}<span class="cv-punct">[</span>`
            })
            val.forEach((v, i) => walk(v, depth + 1, null, i === val.length - 1))
            lines[open_idx].close_idx = lines.length
            lines.push({ depth, type: 'close', open_idx, html: `${ind}<span class="cv-punct">]</span>${tail}` })
        } else {
            const keys = Object.keys(val)
            const open_idx = lines.length
            lines.push({
                depth, type: 'open', bracket: '{', open_idx, close_idx: -1,
                size: keys.length, html: `${ind}${k}<span class="cv-punct">{</span>`
            })
            keys.forEach((k2, i) => walk(val[k2], depth + 1, k2, i === keys.length - 1))
            lines[open_idx].close_idx = lines.length
            lines.push({ depth, type: 'close', open_idx, html: `${ind}<span class="cv-punct">}</span>${tail}` })
        }
    }

    walk(obj, 0, null, true)
    return lines
}

// ── Auto language detection ────────────────────────────────────────────────────

const KNOWN_HLJS_LANGS = new Set([
    'bash','c','cpp','css','diff','go','html','http','java','javascript','json',
    'kotlin','lua','markdown','nginx','php','plaintext','python','ruby','rust',
    'shell','sql','swift','typescript','xml','yaml','text',
])

const LANG_ALIASES = {
    nse: 'lua',       // Nmap Script Engine = Lua
    sigma: 'yaml',    // Sigma rules are YAML
    atr: 'yaml',      // ATR format is YAML
    wazuh: 'xml',     // Wazuh rules are XML
    yara: 'text',     // no hljs yara grammar
    suricata: 'text',
    zeek: 'text',
    crs: 'text',
    nova: 'text',
}

function detect_language(code, hint) {
    if (hint && hint !== 'auto') {
        const mapped = LANG_ALIASES[hint] || hint
        return KNOWN_HLJS_LANGS.has(mapped) ? mapped : 'text'
    }
    const t = String(code || '').trimStart()
    if (/^[\[{]/.test(t)) {
        try { JSON.parse(code); return 'json' } catch { }
    }
    if (/^(def |class |import |from |#!.*python)/.test(t)) return 'python'
    if (/^(<!DOCTYPE|<html)/i.test(t)) return 'html'
    if (/^(SELECT|INSERT|UPDATE|DELETE|CREATE|DROP)/i.test(t)) return 'sql'
    if (/^(#!.*bash|#!.*sh|^\$\s)/.test(t) || /\$\(/.test(t)) return 'bash'
    if (/^(const |let |var |function |import |export |=>)/.test(t)) return 'javascript'
    return 'text'
}

// ── Component ──────────────────────────────────────────────────────────────────

export default {
    name: 'SmartRender',

    props: {
        code: { type: String, required: true },
        language: { type: String, default: 'auto' },
        title: { type: String, default: '' },
        maxHeight: { type: String, default: '520px' },
        foldable: { type: Boolean, default: true },
        showLines: { type: Boolean, default: true },
        initialSearch: { type: String, default: '' },
        // Non-interactive: terms always highlighted, independent of the search box
        // — e.g. the exact byte sequences a rule test matched.
        extraHighlights: { type: Array, default: () => [] },
        // Wrap long lines instead of pushing them into horizontal scroll —
        // on by default everywhere; pass :word-wrap="false" to opt out.
        wordWrap: { type: Boolean, default: true },
    },

    template: `
    <div class="cv-root">

        <!-- ── Header ──────────────────────────────────────────────── -->
        <div class="cv-header">
            <div class="cv-header-left">
                <span v-if="title" class="cv-title">
                    <i class="fas fa-file-code"></i> {{ title }}
                </span>
                <span class="cv-lang-badge" v-if="effective_lang !== 'text'">{{ effective_lang }}</span>
            </div>

            <div class="cv-header-center">
                <template v-if="!markdown_mode">
                    <div class="cv-search-wrap">
                        <i class="fas fa-search cv-search-icon"></i>
                        <input
                            class="cv-search-input"
                            type="text"
                            placeholder="Search…"
                            v-model="search_term"
                            @keydown.enter.prevent="go_next_match"
                            @keydown.shift.enter.prevent="go_prev_match"
                            :class="{ 'cv-search-input--has-val': search_term }"
                        />
                        <span class="cv-search-count" v-if="search_term">
                            <template v-if="total_matches">{{ cur_match + 1 }} / {{ total_matches }}</template>
                            <template v-else>no match</template>
                        </span>
                        <button v-if="search_term" class="cv-search-clear" @click="search_term = ''; cur_match = 0">
                            <i class="fas fa-xmark"></i>
                        </button>
                    </div>
                    <div class="cv-search-nav" v-if="search_term && total_matches > 1">
                        <button class="cv-btn cv-btn--icon" @click="go_prev_match" title="Previous (Shift+Enter)">
                            <i class="fas fa-chevron-up"></i>
                        </button>
                        <button class="cv-btn cv-btn--icon" @click="go_next_match" title="Next (Enter)">
                            <i class="fas fa-chevron-down"></i>
                        </button>
                    </div>
                </template>
            </div>

            <div class="cv-header-right">
                <span class="cv-line-count" v-if="!markdown_mode">{{ line_count }} lines</span>

                <button
                    v-if="effective_lang === 'markdown'"
                    class="cv-btn cv-btn--sm"
                    :class="{ 'is-active': markdown_mode }"
                    @click="markdown_mode = !markdown_mode"
                    title="Toggle rendered markdown view">
                    <i class="fas fa-eye"></i>
                    <span>Rendered</span>
                </button>

                <button
                    v-if="effective_lang === 'json' && foldable"
                    class="cv-btn cv-btn--sm"
                    :class="{ 'is-active': json_mode }"
                    @click="json_mode = !json_mode"
                    title="Toggle JSON tree view">
                    <i class="fas fa-diagram-project"></i>
                    <span>Tree</span>
                </button>

                <button
                    v-if="json_mode"
                    class="cv-btn cv-btn--sm"
                    @click="collapse_all"
                    title="Collapse all">
                    <i class="fas fa-minimize"></i>
                </button>
                <button
                    v-if="json_mode"
                    class="cv-btn cv-btn--sm"
                    @click="expand_all"
                    title="Expand all">
                    <i class="fas fa-maximize"></i>
                </button>

                <button v-if="!markdown_mode" class="cv-btn cv-btn--sm" @click="wrap = !wrap" :class="{ 'is-active': wrap }" title="Toggle word wrap">
                    <i class="fas fa-arrow-turn-down"></i>
                </button>

                <button class="cv-btn cv-btn--sm" @click="copy_code" title="Copy source">
                    <i :class="copied ? 'fas fa-check' : 'fas fa-copy'"></i>
                </button>
            </div>
        </div>

        <!-- ── Rendered markdown mode ───────────────────────────────── -->
        <!-- No maxHeight cap here (unlike the code/JSON panes below) — markdown
             content, especially mermaid diagrams, reads better with the page's own
             scroll than squeezed into a small fixed-height box. -->
        <div
            v-if="markdown_mode"
            class="cv-md-body"
            ref="md_preview_ref"
            v-html="rendered_md">
        </div>

        <!-- ── Loading ───────────────────────────────────────────────── -->
        <div v-else-if="!hljs_ready" class="cv-loading">
            <i class="fas fa-spinner fa-spin"></i> Loading…
        </div>

        <!-- ── JSON tree mode ────────────────────────────────────────── -->
        <div v-else-if="json_mode && json_lines" class="cv-body" :style="{ maxHeight: maxHeight }">
            <div class="cv-gutter" v-if="showLines" aria-hidden="true">
                <div v-for="(line, i) in visible_json_lines" :key="i" class="cv-lnum">{{ i + 1 }}</div>
            </div>
            <pre class="cv-pre" :class="{ 'cv-pre--wrap': wrap }"><div
                v-for="(line, i) in visible_json_lines"
                :key="line.open_idx ?? ('l' + i)"
                class="cv-json-line"
                :class="'cv-json-line--d' + Math.min(line.depth, 8)"
                :data-match-line="i"
            ><button
                v-if="line.type === 'open'"
                class="cv-fold-btn"
                @click="toggle_fold(line.open_idx)"
                :title="collapsed.has(line.open_idx) ? 'Expand' : 'Collapse'">
                <i :class="collapsed.has(line.open_idx) ? 'fas fa-chevron-right' : 'fas fa-chevron-down'"></i>
            </button><span
                v-else
                class="cv-fold-spacer"></span><span
                class="cv-json-content"
                v-html="inject_marks(line.html, i)"></span><span
                v-if="line.type === 'open' && collapsed.has(line.open_idx)"
                class="cv-fold-summary"
                @click="toggle_fold(line.open_idx)"
            > {{ line.bracket === '{' ? '{' : '[' }} <span class="cv-fold-count">{{ line.size }} {{ line.size === 1 ? 'item' : 'items' }}</span> {{ line.bracket === '{' ? '}' : ']' }}</span
            ></div></pre>
        </div>

        <!-- ── Plain highlight mode ──────────────────────────────────── -->
        <div v-else-if="hljs_ready" class="cv-body" ref="body_ref" :style="{ maxHeight: maxHeight }">
            <div class="cv-gutter" v-if="showLines" ref="gutter_ref" aria-hidden="true">
                <div v-for="n in line_count" :key="n" class="cv-lnum">{{ n }}</div>
            </div>
            <pre
                class="cv-pre"
                :class="{ 'cv-pre--wrap': wrap }"
                v-html="highlighted_with_search"
                ref="pre_ref"
                @scroll="sync_gutter_scroll">
            </pre>
        </div>

    </div>
    `,

    setup(props) {

        // ── Core state ────────────────────────────────────────────────
        const hljs_ready = ref(false)
        const hljs_ref = ref(null)
        const wrap = ref(props.wordWrap)
        const copied = ref(false)
        const json_mode = ref(false)
        const markdown_mode = ref(false)
        const rendered_md = ref('')

        // ── Search ────────────────────────────────────────────────────
        const search_term = ref(props.initialSearch || '')
        const cur_match = ref(0)

        watch(() => props.initialSearch, v => { search_term.value = v || ''; cur_match.value = 0 })

        // ── JSON fold ─────────────────────────────────────────────────
        const collapsed = ref(new Set())

        // ── Refs ──────────────────────────────────────────────────────
        const body_ref = ref(null)
        const gutter_ref = ref(null)
        const pre_ref = ref(null)
        const md_preview_ref = ref(null)

        // ── Derived ───────────────────────────────────────────────────
        // Content can arrive with \r\n or lone \r line endings (rules ported
        // from Windows tooling or old malware-sample sets) — split('\n') alone
        // then treats the whole thing as one giant line. Normalize once, up
        // front, and read this everywhere instead of props.code directly.
        const normalized_code = computed(() => String(props.code ?? '').replace(/\r\n?/g, '\n'))

        const effective_lang = computed(() => detect_language(normalized_code.value, props.language))

        const line_count = computed(() => {
            if (!normalized_code.value) return 0
            return normalized_code.value.split('\n').length
        })

        // ── Markdown + mermaid rendering (shared with smart-editor.js) ──
        async function render_markdown_content() {
            rendered_md.value = await renderMarkdown(normalized_code.value, { breaks: true })
            nextTick(() => runMermaid(md_preview_ref.value))
        }

        watch(normalized_code, () => { if (markdown_mode.value) render_markdown_content() })
        watch(markdown_mode, (on) => { if (on) render_markdown_content() })

        // Highlight.js output (raw, no search marks)
        const highlighted_html = computed(() => {
            if (!hljs_ref.value) return esc(normalized_code.value)
            const lang = effective_lang.value
            if (lang === 'text') return esc(normalized_code.value)
            try {
                const res = hljs_ref.value.highlight(normalized_code.value, { language: lang, ignoreIllegals: true })
                return res.value
            } catch {
                try {
                    const res = hljs_ref.value.highlightAuto(normalized_code.value)
                    return res.value
                } catch {
                    return esc(normalized_code.value)
                }
            }
        })

        // Total matches for current search
        const total_matches = computed(() => count_matches(normalized_code.value, search_term.value))

        // Auto-highlighted HTML (extraHighlights only, no interactive search yet)
        const highlighted_with_extras = computed(() => {
            const html = highlighted_html.value
            if (!props.extraHighlights || !props.extraHighlights.length) return html
            // Plain-text mode (e.g. YARA/text language): no HTML tags to anchor on —
            // match directly against the escaped code, escaping each term the same way.
            if (!html.includes('<')) {
                const terms = props.extraHighlights.filter(Boolean).map(t => esc(String(t)))
                if (!terms.length) return html
                let re
                try { re = new RegExp(terms.map(escape_re).join('|'), 'gi') } catch { return html }
                return html.replace(re, m => `<mark class="cv-match cv-match--auto">${m}</mark>`)
            }
            return inject_auto_marks(html, props.extraHighlights)
        })

        // Highlighted HTML with search marks injected. A manual search takes over
        // from the auto-highlights entirely (avoids re-processing already-marked
        // HTML) — extras come back as soon as the search box is cleared.
        const highlighted_with_search = computed(() => {
            if (!search_term.value) return highlighted_with_extras.value
            const html = highlighted_html.value
            // Plain-text mode: highlighted_html is just escaped text with no HTML tags.
            // inject_search_marks relies on >text< patterns; none exist here.
            // Instead, search directly on the escaped text using the escaped term.
            if (!html.includes('<')) {
                const term = search_term.value
                const escapedTerm = esc(term)
                const re = new RegExp(escapedTerm.replace(/[.*+?^${}()|[\]\\]/g, '\\$&'), 'gi')
                let match_n = 0
                return html.replace(re, m => {
                    const key = match_n++
                    const cls = key === cur_match.value ? 'cv-match cv-match--focus' : 'cv-match'
                    return `<mark class="${cls}" data-match="${key}">${m}</mark>`
                })
            }
            return inject_search_marks(html, search_term.value, null, cur_match.value)
        })

        // JSON tree lines
        const json_lines = computed(() => {
            if (effective_lang.value !== 'json') return null
            return build_json_tree(normalized_code.value)
        })

        // Visible JSON lines (accounting for collapsed nodes)
        const visible_json_lines = computed(() => {
            const lines = json_lines.value
            if (!lines) return []
            if (!collapsed.value.size) return lines

            const result = []
            let skip_until = -1

            for (let i = 0; i < lines.length; i++) {
                const line = lines[i]

                if (i <= skip_until) {
                    // Inside a collapsed block — only show close bracket as hidden
                    if (i === skip_until) {
                        // skip_until is the close line — skip it too
                    }
                    continue
                }

                result.push(line)

                if (line.type === 'open' && collapsed.value.has(line.open_idx)) {
                    // Hide everything up to and including the matching close
                    skip_until = line.close_idx
                }
            }
            return result
        })

        // ── Search navigation ─────────────────────────────────────────
        function go_next_match() {
            if (!total_matches.value) return
            cur_match.value = (cur_match.value + 1) % total_matches.value
            scroll_to_match()
        }

        function go_prev_match() {
            if (!total_matches.value) return
            cur_match.value = (cur_match.value - 1 + total_matches.value) % total_matches.value
            scroll_to_match()
        }

        async function scroll_to_match() {
            await nextTick()
            const container = body_ref.value || pre_ref.value
            if (!container) return
            const el = container.querySelector(`[data-match="${cur_match.value}"]`)
            if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
        }

        // Reset to first match on new search
        watch(search_term, () => { cur_match.value = 0 })

        // ── JSON fold controls ────────────────────────────────────────
        function toggle_fold(open_idx) {
            const s = new Set(collapsed.value)
            if (s.has(open_idx)) s.delete(open_idx)
            else s.add(open_idx)
            collapsed.value = s
        }

        function collapse_all() {
            const lines = json_lines.value
            if (!lines) return
            const s = new Set()
            lines.forEach(l => { if (l.type === 'open') s.add(l.open_idx) })
            collapsed.value = s
        }

        function expand_all() {
            collapsed.value = new Set()
        }

        // ── Inject search marks in JSON tree ──────────────────────────
        function inject_marks(html, line_idx) {
            if (!search_term.value) return html
            // Count matches before this line to offset the global match index
            let offset = 0
            const lines = visible_json_lines.value
            for (let i = 0; i < line_idx; i++) {
                offset += count_matches(
                    lines[i].html.replace(/<[^>]+>/g, ''),
                    search_term.value
                )
            }
            return inject_search_marks(html, search_term.value, null, cur_match.value - offset)
        }

        // Auto-enable JSON tree when language is JSON, rendered view when markdown
        watch(effective_lang, (lang) => {
            if (lang === 'json' && props.foldable) json_mode.value = true
            else json_mode.value = false
            markdown_mode.value = (lang === 'markdown')
        }, { immediate: true })

        // ── Gutter scroll sync ────────────────────────────────────────
        function sync_gutter_scroll() {
            if (pre_ref.value && gutter_ref.value) {
                gutter_ref.value.scrollTop = pre_ref.value.scrollTop
            }
        }

        // ── Copy ──────────────────────────────────────────────────────
        function copy_code() {
            navigator.clipboard?.writeText(props.code)
            copied.value = true
            setTimeout(() => { copied.value = false }, 1800)
        }

        // ── Load highlight.js ─────────────────────────────────────────
        onMounted(async () => {
            try {
                hljs_ref.value = await load_hljs()
                hljs_ready.value = true
            } catch (e) {
                hljs_ready.value = true // degrade gracefully: show plain text
            }
            if (search_term.value) scroll_to_match()
        })

        return {
            hljs_ready, wrap, copied, json_mode, markdown_mode, rendered_md,
            search_term, cur_match, total_matches,
            collapsed,
            body_ref, gutter_ref, pre_ref, md_preview_ref,
            effective_lang, line_count,
            highlighted_with_search,
            json_lines, visible_json_lines,
            go_next_match, go_prev_match,
            toggle_fold, collapse_all, expand_all,
            inject_marks,
            sync_gutter_scroll,
            copy_code,
        }
    },
}
