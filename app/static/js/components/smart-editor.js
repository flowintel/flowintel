/**
 * smart-editor.js — Intelligent text/markdown/code editor form field
 *
 * Props:
 *   modelValue   String   content (v-model)
 *   mode         String   'text' | 'markdown' | 'code' | 'json'  (default: 'text')
 *   language     String   initial code language, 'code' mode only (default: 'javascript') —
 *                         'json' mode always highlights as JSON and additionally shows a
 *                         live valid/invalid indicator and a "Format" (pretty-print) button
 *   placeholder  String
 *   name         String   HTML name for form submission (renders hidden input)
 *   minHeight    String   CSS value e.g. '220px'
 *   maxHeight    String   CSS value e.g. '600px'
 *   readonly     Boolean
 *   showLineNumbers Boolean  markdown mode only — initial state of the line-number gutter
 *                            in the write pane (toggleable at runtime via the toolbar)
 *   allowFileImport Boolean  markdown mode only — show the "import from file" toolbar
 *                            button, which replaces the content with a picked file's text
 *                            (default: true)
 *   allowAtVariables Boolean markdown mode only — @variable autocomplete (case/task note
 *                            variables, e.g. @this.case.title) plus a toolbar button to
 *                            insert "@" and open the suggestion list (default: true)
 *
 * Emits:
 *   update:modelValue  (v-model compatible)
 *
 * Usage:
 *   import SmartEditor from '/static/js/components/smart-editor.js'
 *
 *   <!-- v-model -->
 *   <smart-editor v-model="body" mode="markdown"></smart-editor>
 *
 *   <!-- plain form field -->
 *   <smart-editor name="content" mode="code" language="python"></smart-editor>
 *   <button type="submit">Save</button>
 */

import { renderMarkdown, runMermaid, loadNoteVariables } from './markdown-render.js'
import { attachAtVariableComplete } from './at-variable-complete.js'

// ── Module-level singletons ────────────────────────────────────────────────────

const PAIRS   = { '{': '}', '[': ']', '(': ')', '"': '"', "'": "'", '`': '`' }
const CLOSERS = new Set([')', ']', '}', '"', "'", '`'])

const _KNOWN_HLJS = new Set([
    'bash','c','cpp','css','diff','go','html','http','java','javascript','json',
    'kotlin','lua','markdown','nginx','php','plaintext','python','ruby','rust',
    'shell','sql','swift','typescript','xml','yaml','text',
])
const _LANG_ALIASES = { nse:'lua', sigma:'yaml', wazuh:'xml', yara:'text', suricata:'text', zeek:'text', crs:'text', nova:'text' }
function _resolve_lang(lang) {
    const mapped = _LANG_ALIASES[lang] || lang
    return _KNOWN_HLJS.has(mapped) ? mapped : 'text'
}

let _hljs_p = null

function load_hljs() {
    if (window.hljs)  return Promise.resolve(window.hljs)
    if (_hljs_p) return _hljs_p
    _hljs_p = new Promise((res, rej) => {
        const s = document.createElement('script')
        s.src   = '/static/js/hljs.min.js'
        s.onload  = () => res(window.hljs)
        s.onerror = rej
        document.head.appendChild(s)
    })
    return _hljs_p
}

// ── Component ──────────────────────────────────────────────────────────────────

const { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } = Vue

const LINE_H = 21   // px — must match CSS line-height on .se-overlay / .se-ta--code
const PAD_Y  = 24   // px — top + bottom padding inside code area

const MD_ACTIONS = [
    { id: 'bold',    icon: 'fa-bold',        title: 'Bold'          },
    { id: 'italic',  icon: 'fa-italic',      title: 'Italic'        },
    { id: 'h2',      icon: 'fa-heading',     title: 'Heading'       },
    { id: 'code',    icon: 'fa-terminal',    title: 'Inline code'   },
    { id: 'link',    icon: 'fa-link',        title: 'Link'          },
    { id: 'ul',      icon: 'fa-list-ul',     title: 'Bullet list'   },
    { id: 'ol',      icon: 'fa-list-ol',     title: 'Numbered list' },
    { id: 'quote',   icon: 'fa-quote-right', title: 'Blockquote'    },
    { id: 'hr',      icon: 'fa-minus',       title: 'Horizontal rule' },
]

export default {
    name: 'SmartEditor',

    props: {
        modelValue:  { type: String,  default: '' },
        mode:        { type: String,  default: 'text' },
        language:    { type: String,  default: 'javascript' },
        placeholder: { type: String,  default: 'Type here…' },
        name:        { type: String,  default: null },
        minHeight:   { type: String,  default: '220px' },
        maxHeight:   { type: String,  default: '600px' },
        readonly:    { type: Boolean, default: false },
        showLineNumbers: { type: Boolean, default: false },
        allowFileImport: { type: Boolean, default: true },
        allowAtVariables: { type: Boolean, default: true },
        // markdown mode only — optional async (text) => resolvedText hook, called before
        // each preview render. The component itself has no notion of case/task id, so a
        // parent page that does (e.g. case_view.html) wires this to actually resolve
        // @this.case.title-style references to real values in the live preview, instead
        // of just leaving them as raw syntax with the "unresolved" badge.
        resolveVariables: { type: Function, default: null },
    },

    emits: ['update:modelValue'],

    template: `
<div class="se-root" :class="['se-mode--' + mode, { 'se-root--fullscreen': is_fullscreen }]">

    <!-- hidden input for native form submission -->
    <input v-if="name" type="hidden" :name="name" :value="inner_value">

    <!-- ── Toolbar ──────────────────────────────────────────────────── -->
    <div class="se-toolbar">

        <!-- Mode badge (display only) -->
        <span class="se-mode-badge" title="Editor mode">
            <i :class="mode_icon"></i> {{ mode_label }}<template v-if="mode === 'markdown'"> · {{ md_view_label }}</template>
        </span>

        <div class="se-toolbar-sep"></div>

        <!-- Markdown: formatting shortcuts + edit/split/preview toggle -->
        <template v-if="mode === 'markdown'">
            <template v-if="md_view !== 'preview'">
                <button
                    v-for="a in MD_ACTIONS" :key="a.id"
                    class="se-tb-btn"
                    type="button"
                    :title="a.title"
                    @click="md_action(a.id)">
                    <i :class="'fas ' + a.icon"></i>
                </button>
                <div class="se-toolbar-sep"></div>
            </template>
            <div class="se-view-toggle">
                <button
                    class="se-view-btn"
                    :class="{ 'is-active': md_view === 'edit' }"
                    type="button"
                    title="Edit — write raw markdown"
                    @click="set_md_view('edit')">
                    <i class="fas fa-pen"></i>
                </button>
                <button
                    class="se-view-btn"
                    :class="{ 'is-active': md_view === 'split' }"
                    type="button"
                    title="Split — write and preview side by side"
                    @click="set_md_view('split')">
                    <i class="fas fa-columns"></i>
                </button>
                <button
                    class="se-view-btn"
                    :class="{ 'is-active': md_view === 'preview' }"
                    type="button"
                    title="Preview — rendered markdown only"
                    @click="set_md_view('preview')">
                    <i class="fas fa-eye"></i>
                </button>
            </div>
            <button
                v-if="md_view !== 'preview'"
                class="se-tb-btn"
                :class="{ 'is-active': show_line_numbers }"
                type="button"
                :title="show_line_numbers ? 'Hide line numbers' : 'Show line numbers'"
                @click="toggle_line_numbers">
                <i class="fas fa-hashtag"></i>
            </button>
            <template v-if="allowFileImport">
                <input
                    type="file"
                    ref="file_input_ref"
                    accept=".md,.txt"
                    style="display: none"
                    @change="on_file_import">
                <button
                    class="se-tb-btn"
                    type="button"
                    title="Import from file — replaces the current content"
                    @click="file_input_ref.click()">
                    <i class="fas fa-file-import"></i>
                </button>
            </template>
            <button
                v-if="allowAtVariables && md_view !== 'preview'"
                class="se-tb-btn"
                type="button"
                title="Insert a note variable (e.g. @this.case.title)"
                @click="insert_at_variable">
                <i class="fas fa-at"></i>
            </button>
            <div class="se-toolbar-sep"></div>
        </template>

        <!-- Code: language badge (display only) -->
        <span v-if="mode === 'code'" class="se-lang-badge" title="Syntax highlighting language">{{ language }}</span>

        <!-- JSON: live valid/invalid indicator + format button -->
        <template v-if="mode === 'json'">
            <span
                class="se-json-badge"
                :class="json_check.valid ? 'is-valid' : 'is-invalid'"
                :title="json_check.valid ? 'Valid JSON' : json_check.error">
                <i :class="json_check.valid ? 'fas fa-circle-check' : 'fas fa-circle-exclamation'"></i>
                {{ json_check.valid ? 'Valid' : 'Invalid' }}
            </span>
            <button
                class="se-tb-btn"
                type="button"
                :disabled="!json_check.valid || !inner_value.trim()"
                title="Format — pretty-print the JSON"
                @click="format_json">
                <i class="fas fa-broom"></i>
            </button>
        </template>

        <div class="se-toolbar-spacer"></div>

        <!-- Undo / Redo buttons -->
        <button class="se-tb-btn" type="button" title="Undo (Ctrl+Z)"
            :disabled="undo_count === 0" @click="btn_undo">
            <i class="fas fa-rotate-left"></i>
        </button>
        <button class="se-tb-btn" type="button" title="Redo (Ctrl+Y)"
            :disabled="redo_count === 0" @click="btn_redo">
            <i class="fas fa-rotate-right"></i>
        </button>
        <button
            class="se-tb-btn"
            :class="{ 'is-armed': clear_armed }"
            type="button"
            :disabled="!inner_value"
            :title="clear_armed ? 'Click again to confirm — clears everything' : 'Clear all text'"
            @click="clear_content">
            <i class="fas fa-trash-can"></i>
        </button>
        <button class="se-tb-btn" type="button" :title="is_fullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'"
            @click="toggle_fullscreen">
            <i :class="is_fullscreen ? 'fas fa-compress' : 'fas fa-expand'"></i>
        </button>
        <div class="se-toolbar-sep"></div>

        <span class="se-char-count" :title="stat_title">{{ stat_label }}</span>
    </div>

    <!-- ── Body ─────────────────────────────────────────────────────── -->
    <div class="se-body" :style="body_style">

        <!-- TEXT ───────────────────────────────────── -->
        <template v-if="mode === 'text'">
            <textarea
                ref="ta_ref"
                class="se-ta"
                title="Plain text"
                :value="inner_value"
                @input="on_input"
                :placeholder="placeholder"
                :readonly="readonly"
                spellcheck="true"
                @keydown="on_keydown">
            </textarea>
        </template>

        <!-- MARKDOWN ───────────────────────────────── -->
        <template v-else-if="mode === 'markdown'">
            <div class="se-md-body" :class="'se-md-body--' + md_view" :style="code_wrap_style">
                <div class="se-md-write" :class="{ 'se-md-write--numbered': show_line_numbers }" v-show="md_view !== 'preview'">
                    <div v-if="show_line_numbers" class="se-md-gutter" ref="md_gutter_ref" title="Line numbers">
                        <span v-for="n in line_count" :key="n" class="se-md-lnum">{{ n }}</span>
                    </div>
                    <textarea
                        ref="ta_ref"
                        class="se-ta se-ta--md"
                        title="Markdown source"
                        :value="inner_value"
                        @input="on_input"
                        :placeholder="placeholder"
                        :readonly="readonly"
                        spellcheck="false"
                        @keydown="on_keydown"
                        @scroll="on_md_scroll('ta')">
                    </textarea>
                </div>
                <div v-show="md_view !== 'edit'" ref="md_preview_ref" class="se-md-preview" title="Rendered preview" v-html="rendered_md" @scroll="on_md_scroll('preview')"></div>
            </div>
        </template>

        <!-- CODE / JSON ───────────────────────────────── -->
        <template v-else-if="mode === 'code' || mode === 'json'">
            <div class="se-code-wrap" :style="code_wrap_style">
                <div class="se-gutter" ref="gutter_ref" title="Line numbers">
                    <span v-for="n in line_count" :key="n" class="se-lnum">{{ n }}</span>
                </div>
                <div class="se-code-area">
                    <pre
                        class="se-overlay"
                        ref="overlay_ref"
                        aria-hidden="true"
                        v-html="highlighted || escaped_code"></pre>
                    <textarea
                        ref="ta_ref"
                        class="se-ta se-ta--code"
                        title="Code editor"
                        :value="inner_value"
                        @input="on_input"
                        :placeholder="placeholder"
                        :readonly="readonly"
                        spellcheck="false"
                        autocorrect="off"
                        autocapitalize="off"
                        @keydown="on_keydown"
                        @scroll="sync_scroll">
                    </textarea>
                </div>
            </div>
            <div v-if="!hljs_ready" class="se-code-loading">
                <i class="fas fa-spinner fa-spin"></i> Loading syntax engine…
            </div>
        </template>

    </div><!-- /.se-body -->
</div><!-- /.se-root -->
    `,

    setup(props, { emit }) {

        // ── Reactive state ──────────────────────────────────────────────
        const inner_value  = ref(props.modelValue)
        const hljs_ready   = ref(false)
        const highlighted  = ref('')
        const md_view      = ref('edit')   // 'edit' | 'split' | 'preview'
        const rendered_md  = ref('')
        const ta_ref       = ref(null)
        const overlay_ref  = ref(null)
        const gutter_ref   = ref(null)
        const md_preview_ref = ref(null)
        const md_gutter_ref  = ref(null)
        const is_fullscreen  = ref(false)
        const show_line_numbers = ref(props.showLineNumbers)
        const file_input_ref = ref(null)
        const clear_armed = ref(false)
        let _clear_arm_t = null

        // ── Undo / redo history ─────────────────────────────────────────
        const _undo = []   // stack of past string values
        const _redo = []
        let _undo_t    = null   // debounce timer handle
        let _prev_snap = null   // value captured at start of current typing burst
        const undo_count = ref(0)
        const redo_count = ref(0)

        // Sync with parent v-model
        watch(() => props.modelValue, v => { if (v !== inner_value.value) inner_value.value = v })
        watch(inner_value, v => emit('update:modelValue', v))

        // ── Computed ────────────────────────────────────────────────────
        const MODE_META = {
            text:     { label: 'Text',     icon: 'fas fa-align-left' },
            markdown: { label: 'Markdown', icon: 'fas fa-brands fa-markdown' },
            code:     { label: 'Code',     icon: 'fas fa-code' },
            json:     { label: 'JSON',     icon: 'fas fa-file-code' },
        }
        const mode_label = computed(() => MODE_META[props.mode]?.label ?? props.mode)
        const mode_icon  = computed(() => MODE_META[props.mode]?.icon  ?? 'fas fa-file')

        const MD_VIEW_LABELS = { edit: 'Editor', split: 'Editor + Preview', preview: 'Preview' }
        const md_view_label = computed(() => MD_VIEW_LABELS[md_view.value] ?? md_view.value)

        const line_count = computed(() =>
            (inner_value.value.match(/\n/g) || []).length + 1
        )

        const stat_label = computed(() => {
            const c = inner_value.value.length
            if (props.mode === 'text') {
                const w = inner_value.value.trim() ? inner_value.value.trim().split(/\s+/).length : 0
                return `${w}w · ${c}c`
            }
            if (props.mode === 'code' || props.mode === 'json') return `${line_count.value}L · ${c}c`
            return `${c}c`
        })

        const stat_title = computed(() => {
            if (props.mode === 'text') return 'Word count · character count'
            if (props.mode === 'code' || props.mode === 'json') return 'Line count · character count'
            return 'Character count'
        })

        // ── JSON mode: live validity check + pretty-print ────────────────
        const json_check = computed(() => {
            if (props.mode !== 'json') return { valid: true, error: '' }
            const text = inner_value.value.trim()
            if (!text) return { valid: true, error: '' }
            try {
                JSON.parse(text)
                return { valid: true, error: '' }
            } catch (e) {
                return { valid: false, error: e.message }
            }
        })

        // Re-indents JSON text purely by walking the raw characters — never goes
        // through JSON.parse/stringify for the output, so values are never rebuilt
        // (no number-precision loss on huge IDs, no key dedup, no re-escaping of
        // string content). Only the whitespace BETWEEN tokens is touched; every
        // character inside a string (including embedded code/\n escapes) is copied
        // through verbatim.
        function reindent_json_text(src, unit = '  ') {
            let out = ''
            let depth = 0
            let i = 0
            const n = src.length
            const skip_ws = () => { while (i < n && /\s/.test(src[i])) i++ }
            const newline = () => { out += '\n' + unit.repeat(depth) }

            skip_ws()
            while (i < n) {
                const ch = src[i]
                if (ch === '"') {
                    out += ch; i++
                    while (i < n) {
                        const c = src[i]
                        out += c
                        if (c === '\\' && i + 1 < n) { out += src[i + 1]; i += 2; continue }
                        i++
                        if (c === '"') break
                    }
                } else if (ch === '{' || ch === '[') {
                    out += ch; i++
                    skip_ws()
                    const close = ch === '{' ? '}' : ']'
                    if (src[i] === close) { out += src[i]; i++ }
                    else { depth++; newline() }
                } else if (ch === '}' || ch === ']') {
                    depth--; newline()
                    out += ch; i++
                } else if (ch === ',') {
                    out += ch; i++
                    skip_ws(); newline()
                } else if (ch === ':') {
                    out += ': '; i++
                    skip_ws()
                } else if (/\s/.test(ch)) {
                    i++
                } else {
                    out += ch; i++
                }
            }
            return out
        }

        function format_json() {
            if (!json_check.value.valid) return
            const text = inner_value.value.trim()
            if (!text) return
            _save_now()
            inner_value.value = reindent_json_text(text)
        }

        const min_h = computed(() => parseInt(props.minHeight) || 220)
        const max_h = computed(() => parseInt(props.maxHeight) || 600)

        // Content-driven height, capped at maxHeight — grows with typed lines up to the
        // cap, then holds still so the growing pane scrolls internally instead of pushing
        // the rest of the page down. Shared by .se-code-wrap, .se-md-body and (for the
        // text mode) .se-body itself. In fullscreen the root is pinned to the viewport,
        // so this cap is dropped and the pane just fills whatever space it's given.
        const code_wrap_style = computed(() => {
            if (is_fullscreen.value) return {}
            const h = Math.min(max_h.value, Math.max(min_h.value, line_count.value * LINE_H + PAD_Y))
            return { minHeight: h + 'px' }
        })

        const body_style = computed(() =>
            props.mode === 'text' ? code_wrap_style.value : {}
        )

        const escaped_code = computed(() =>
            inner_value.value
                .replace(/&/g, '&amp;')
                .replace(/</g, '&lt;')
                .replace(/>/g, '&gt;')
        )

        // ── highlight.js ────────────────────────────────────────────────
        function refresh_highlight() {
            if (!hljs_ready.value || !window.hljs) return
            const code = inner_value.value
            if (!code) { highlighted.value = ''; return }
            try {
                const lang = props.mode === 'json' ? 'json' : _resolve_lang(props.language)
                if (lang === 'text' || lang === 'plaintext') {
                    highlighted.value = escaped_code.value
                } else {
                    highlighted.value = window.hljs.highlight(code, { language: lang }).value
                }
            } catch {
                highlighted.value = window.hljs.highlightAuto(code).value
            }
        }

        // ── marked + mermaid (shared with code-viewer.js) ────────────────
        async function render_md() {
            let text = inner_value.value
            if (props.resolveVariables) {
                // A page's resolver typically calls window.FlowintelNoteVariables directly —
                // make sure note_variables.js is actually loaded first so the page doesn't
                // need its own <script> tag just for this.
                try {
                    if (!window.FlowintelNoteVariables) await loadNoteVariables()
                    text = await props.resolveVariables(text)
                } catch { /* fall back to raw text */ }
            }
            rendered_md.value = await renderMarkdown(text, { breaks: true })
            nextTick(() => runMermaid(md_preview_ref.value))
        }

        async function set_md_view(view) {
            md_view.value = view
            if (view !== 'edit') await render_md()
        }

        // ── Debounced content watcher ───────────────────────────────────
        let _hl_t = null, _md_t = null

        watch(inner_value, () => {
            if ((props.mode === 'code' || props.mode === 'json') && hljs_ready.value) {
                clearTimeout(_hl_t)
                _hl_t = setTimeout(refresh_highlight, 80)
            }
            if (props.mode === 'markdown' && md_view.value !== 'edit' && window.marked) {
                clearTimeout(_md_t)
                _md_t = setTimeout(render_md, 100)
            }
        })

        // ── Auto-close / smart keydown ──────────────────────────────────
        function on_keydown(e) {
            if (e.isComposing) return
            const ta  = e.target
            const s   = ta.selectionStart
            const sel = ta.selectionEnd
            const val = inner_value.value
            const key = e.key

            // ── Undo / Redo ──────────────────────────────────────────
            if ((e.ctrlKey || e.metaKey) && !e.shiftKey && key === 'z') {
                e.preventDefault(); do_undo(ta); return
            }
            if ((e.ctrlKey || e.metaKey) && (key === 'y' || (e.shiftKey && key === 'z'))) {
                e.preventDefault(); do_redo(ta); return
            }

            // Bracket/quote auto-closing is a code-editing convenience — in prose
            // (text/markdown) it misfires constantly on ordinary apostrophes and
            // quotes, leaving stray closing characters behind. Code/JSON mode only.
            if (props.mode === 'code' || props.mode === 'json') {
                // ── Auto-close pairs ─────────────────────────────────────
                if (PAIRS[key] && !e.ctrlKey && !e.metaKey) {
                    e.preventDefault()
                    _save_now()
                    const selected = val.slice(s, sel)
                    const close = PAIRS[key]
                    const nv = val.slice(0, s) + key + selected + close + val.slice(sel)
                    set_value(ta, nv, s + 1 + selected.length)
                    return
                }

                // ── Skip over auto-inserted closing char ─────────────────
                if (CLOSERS.has(key) && val[s] === key && s === sel) {
                    e.preventDefault()
                    ta.selectionStart = ta.selectionEnd = s + 1
                    return
                }

                // ── Backspace: delete both chars of an empty pair ────────
                if (key === 'Backspace' && s === sel && s > 0) {
                    const prev = val[s - 1], next = val[s]
                    if (PAIRS[prev] === next) {
                        e.preventDefault()
                        _save_now()
                        set_value(ta, val.slice(0, s - 1) + val.slice(s + 1), s - 1)
                        return
                    }
                }
            }

            // ── Tab: indent / dedent ─────────────────────────────────
            if (key === 'Tab') {
                e.preventDefault()
                _save_now()
                if (s === sel) {
                    // No selection: insert 2 spaces at cursor
                    set_value(ta, val.slice(0, s) + '  ' + val.slice(sel), s + 2)
                } else {
                    const before   = val.slice(0, s)
                    const selected = val.slice(s, sel)
                    const after    = val.slice(sel)
                    if (e.shiftKey) {
                        const dedented = selected.replace(/^  /gm, '')
                        set_value(ta, before + dedented + after, s, s + dedented.length)
                    } else {
                        const indented = selected.replace(/^/gm, '  ')
                        set_value(ta, before + indented + after, s, s + indented.length)
                    }
                }
                return
            }

            // ── Enter: preserve indent + open-bracket extra indent ───
            if (key === 'Enter' && !e.shiftKey) {
                const line_start = val.lastIndexOf('\n', s - 1) + 1
                const indent     = val.slice(line_start, s).match(/^(\s+)/)?.[1] ?? ''
                const prev_ch    = val[s - 1]
                const next_ch    = val[s]
                const is_open    = (props.mode === 'code' || props.mode === 'json') && PAIRS[prev_ch] === next_ch

                if (indent || is_open) {
                    e.preventDefault()
                    _save_now()
                    const extra      = is_open ? '  ' : ''
                    const close_line = is_open ? '\n' + indent : ''
                    const nv = val.slice(0, s) + '\n' + indent + extra + close_line + val.slice(sel)
                    set_value(ta, nv, s + 1 + indent.length + extra.length)
                }
            }
        }

        function set_value(ta, new_val, cursor_start, cursor_end = null) {
            inner_value.value = new_val
            nextTick(() => {
                ta.selectionStart = cursor_start
                ta.selectionEnd   = cursor_end ?? cursor_start
            })
        }

        // ── Undo/redo functions ─────────────────────────────────────────

        // Called on every regular @input — captures the pre-burst state debounced.
        function on_input(e) {
            if (_prev_snap === null) _prev_snap = inner_value.value
            inner_value.value = e.target.value
            clearTimeout(_undo_t)
            _undo_t = setTimeout(() => {
                const v = _prev_snap
                _prev_snap = null
                if (_undo[_undo.length - 1] !== v) {
                    _undo.push(v)
                    if (_undo.length > 200) _undo.shift()
                    _redo.length = 0
                }
                undo_count.value = _undo.length
                redo_count.value = _redo.length
            }, 600)
        }

        // Push current value immediately (called before each smart edit).
        function _save_now() {
            clearTimeout(_undo_t); _prev_snap = null
            const v = inner_value.value
            if (_undo[_undo.length - 1] !== v) {
                _undo.push(v)
                if (_undo.length > 200) _undo.shift()
                _redo.length = 0
            }
            undo_count.value = _undo.length
            redo_count.value = _redo.length
        }

        function do_undo(ta) {
            clearTimeout(_undo_t); _prev_snap = null
            if (!_undo.length) return
            _redo.push(inner_value.value)
            inner_value.value = _undo.pop()
            undo_count.value = _undo.length
            redo_count.value = _redo.length
            nextTick(() => { if (ta) { ta.selectionStart = ta.selectionEnd = inner_value.value.length } })
        }

        function do_redo(ta) {
            if (!_redo.length) return
            _undo.push(inner_value.value)
            inner_value.value = _redo.pop()
            undo_count.value = _undo.length
            redo_count.value = _redo.length
            nextTick(() => { if (ta) { ta.selectionStart = ta.selectionEnd = inner_value.value.length } })
        }

        function btn_undo() { do_undo(ta_ref.value) }
        function btn_redo() { do_redo(ta_ref.value) }

        // Exposed so a parent page can focus this editor from e.g. a clicked field label.
        function focus() { ta_ref.value?.focus() }

        // ── Code overlay scroll sync ────────────────────────────────────
        function sync_scroll(e) {
            if (overlay_ref.value) {
                overlay_ref.value.scrollTop  = e.target.scrollTop
                overlay_ref.value.scrollLeft = e.target.scrollLeft
            }
            if (gutter_ref.value) {
                gutter_ref.value.scrollTop = e.target.scrollTop
            }
        }

        // ── Markdown split-view scroll sync (write pane ↔ preview pane) ──
        let _syncing_md_scroll = false
        function on_md_scroll(source) {
            // Line-number gutter always mirrors the textarea 1:1, regardless of view mode.
            if (source === 'ta' && md_gutter_ref.value && ta_ref.value) {
                md_gutter_ref.value.scrollTop = ta_ref.value.scrollTop
            }

            if (md_view.value !== 'split' || _syncing_md_scroll) return
            const ta = ta_ref.value
            const pv = md_preview_ref.value
            if (!ta || !pv) return
            const from = source === 'ta' ? ta : pv
            const to   = source === 'ta' ? pv : ta
            const from_range = from.scrollHeight - from.clientHeight
            const ratio = from_range > 0 ? from.scrollTop / from_range : 0
            _syncing_md_scroll = true
            to.scrollTop = ratio * (to.scrollHeight - to.clientHeight)
            requestAnimationFrame(() => { _syncing_md_scroll = false })
        }

        // ── Fullscreen toggle ─────────────────────────────────────────────
        function toggle_fullscreen() { is_fullscreen.value = !is_fullscreen.value }
        function toggle_line_numbers() { show_line_numbers.value = !show_line_numbers.value }
        function _on_global_keydown(e) {
            if (e.key === 'Escape' && is_fullscreen.value) is_fullscreen.value = false
        }

        // ── Import from file — replaces the whole content with the file's text ──
        function on_file_import(e) {
            const file = e.target.files[0]
            e.target.value = ''   // reset so importing the same file again still fires @change
            if (!file) return
            if (!/\.(md|txt)$/i.test(file.name)) return
            const reader = new FileReader()
            reader.onload = () => {
                _save_now()
                inner_value.value = String(reader.result)
            }
            reader.readAsText(file)
        }

        // ── Clear all — arms on first click, clears on the confirming second click ──
        function clear_content() {
            if (!clear_armed.value) {
                clear_armed.value = true
                clearTimeout(_clear_arm_t)
                _clear_arm_t = setTimeout(() => { clear_armed.value = false }, 3000)
                return
            }
            clear_armed.value = false
            clearTimeout(_clear_arm_t)
            _save_now()
            inner_value.value = ''
        }

        // ── Markdown toolbar actions ────────────────────────────────────
        function md_action(id) {
            const ta = ta_ref.value
            if (!ta) return
            const { selectionStart: s, selectionEnd: e } = ta
            const val = inner_value.value
            const sel = val.slice(s, e)

            const WRAP = {
                bold:   ['**', '**'],
                italic: ['*',  '*'],
                code:   ['`',  '`'],
            }
            const LINE_PREFIX = {
                h2:    '## ',
                ul:    '- ',
                ol:    '1. ',
                quote: '> ',
            }

            if (WRAP[id]) {
                const [o, c] = WRAP[id]
                const text = sel || 'text'
                const nv   = val.slice(0, s) + o + text + c + val.slice(e)
                set_value(ta, nv, s + o.length, s + o.length + text.length)
            } else if (LINE_PREFIX[id]) {
                const pfx   = LINE_PREFIX[id]
                const ls    = val.lastIndexOf('\n', s - 1) + 1
                const nv    = val.slice(0, ls) + pfx + val.slice(ls)
                set_value(ta, nv, s + pfx.length)
            } else if (id === 'link') {
                const text   = sel || 'link text'
                const snippet = '[' + text + '](url)'
                const nv     = val.slice(0, s) + snippet + val.slice(e)
                set_value(ta, nv, s + 1, s + 1 + text.length)
            } else if (id === 'hr') {
                const nv = val.slice(0, s) + '\n\n---\n\n' + val.slice(e)
                set_value(ta, nv, s + 7)
            }

            ta.focus()
        }

        // ── @variable autocomplete (markdown mode) ───────────────────────
        let at_var_complete = null

        function insert_at_variable() {
            const ta = ta_ref.value
            if (!ta) return
            const s = ta.selectionStart, e = ta.selectionEnd
            const val = inner_value.value
            const nv = val.slice(0, s) + '@' + val.slice(e)
            set_value(ta, nv, s + 1)
            nextTick(() => { ta.focus(); at_var_complete?.check() })
        }

        // ── Lifecycle ───────────────────────────────────────────────────
        onMounted(async () => {
            if (props.mode === 'code' || props.mode === 'json') {
                await load_hljs()
                hljs_ready.value = true
                refresh_highlight()
            }
            if (props.mode === 'markdown' && props.allowAtVariables && ta_ref.value) {
                at_var_complete = attachAtVariableComplete(ta_ref.value, {
                    onPick(insertText, from, to) {
                        const val = inner_value.value
                        const nv = val.slice(0, from) + insertText + val.slice(to)
                        set_value(ta_ref.value, nv, from + insertText.length)
                    }
                })
            }
            document.addEventListener('keydown', _on_global_keydown)
        })

        onBeforeUnmount(() => {
            clearTimeout(_hl_t); clearTimeout(_md_t); clearTimeout(_clear_arm_t)
            document.removeEventListener('keydown', _on_global_keydown)
            at_var_complete?.destroy()
        })

        return {
            inner_value, hljs_ready, highlighted, escaped_code,
            md_view, rendered_md, is_fullscreen, show_line_numbers, clear_armed,
            ta_ref, overlay_ref, gutter_ref, md_preview_ref, md_gutter_ref, file_input_ref,
            MD_ACTIONS,
            mode_label, mode_icon, md_view_label,
            line_count, stat_label, stat_title, body_style, code_wrap_style,
            json_check, format_json,
            undo_count, redo_count, btn_undo, btn_redo,
            on_input, on_keydown, sync_scroll, md_action, set_md_view, on_md_scroll,
            toggle_fullscreen, toggle_line_numbers, focus, on_file_import, clear_content,
            insert_at_variable,
        }
    }
}
