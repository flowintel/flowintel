/**
 * markdown-render.js — shared markdown + mermaid rendering helpers
 *
 * Used by both smart-editor.js (editable) and smart-render.js (read-only) so every
 * markdown surface in these components renders identically, including ```mermaid
 * fences.
 *
 * Lazy-loads marked.min.js, purify.min.js and the official mermaid.min.js from
 * /static/js/ only when a caller actually needs them.
 *
 * Usage:
 *   import { renderMarkdown, runMermaid } from '/static/js/components/markdown-render.js'
 *   const html = await renderMarkdown(sourceText)
 *   // ... set html via v-html, then once it's in the DOM:
 *   await runMermaid(containerEl)
 */

let _marked_p = null
function loadMarked() {
    if (window.marked) return Promise.resolve(window.marked)
    if (_marked_p) return _marked_p
    _marked_p = new Promise((res, rej) => {
        const s = document.createElement('script')
        s.src   = '/static/js/marked.min.js'
        s.onload  = () => res(window.marked)
        s.onerror = rej
        document.head.appendChild(s)
    })
    return _marked_p
}

let _purify_p = null
function loadPurify() {
    if (window.DOMPurify) return Promise.resolve(window.DOMPurify)
    if (_purify_p) return _purify_p
    _purify_p = new Promise((res, rej) => {
        const s = document.createElement('script')
        s.src   = '/static/js/purify.min.js'
        s.onload  = () => res(window.DOMPurify)
        s.onerror = rej
        document.head.appendChild(s)
    })
    return _purify_p
}

// Official mermaid.js UMD build (window.mermaid) — self-contained, no markdown-it
// plugin or stub-object tricks needed.
let _mermaid_p = null
function loadMermaid() {
    if (window.mermaid) return Promise.resolve(window.mermaid)
    if (_mermaid_p) return _mermaid_p
    _mermaid_p = new Promise((res, rej) => {
        const s = document.createElement('script')
        s.src   = '/static/js/mermaid.min.js'
        s.onload  = () => res(window.mermaid)
        s.onerror = rej
        document.head.appendChild(s)
    })
    return _mermaid_p
}

let _mermaid_initialized = false
function ensureMermaidInitialized(mermaid) {
    if (_mermaid_initialized) return
    try {
        mermaid.initialize({
            startOnLoad: false,
            theme: 'default',
            securityLevel: 'strict'
        })
    } catch {}
    _mermaid_initialized = true
}

function mermaidEnabled() {
    return window.ENABLE_MERMAID !== false
}

function sanitizeHtml(html) {
    if (window.DOMPurify) return window.DOMPurify.sanitize(html)
    // DOMPurify failed to load — fall back to a minimal strip as last resort
    const tmp = document.createElement('div')
    tmp.innerHTML = html
    tmp.querySelectorAll('script, iframe, object, embed, form').forEach(el => el.remove())
    tmp.querySelectorAll('*').forEach(el => {
        for (const attr of [...el.attributes]) {
            const n = attr.name.toLowerCase()
            const v = attr.value
            if (n.startsWith('on') ||
                ((n === 'href' || n === 'src' || n === 'action') && /^javascript:/i.test(v.trim()))) {
                el.removeAttribute(attr.name)
            }
        }
    })
    return tmp.innerHTML
}

// marked renders a ```mermaid fence as <pre><code class="language-mermaid"> (HTML
// escaped). Swap that for the bare <pre class="mermaid"> markup mermaid.js itself
// expects — same shape the app's markdown-it plugin produces elsewhere.
function mermaidify(html) {
    return html.replace(
        /<pre><code class="language-mermaid">([\s\S]*?)<\/code><\/pre>\n?/g,
        (_m, escaped) => '<pre class="mermaid">' + escaped + '</pre>'
    )
}

// note_variables.js (already used for case/task notes elsewhere in the app) exposes
// styleUnresolvedVariables(), which wraps @this.case.title-style references in a
// styled <code> badge. Reused here so @variables read clearly in any markdown
// preview, not just after the backend has actually resolved them.
let _note_vars_p = null
export function loadNoteVariables() {
    if (window.FlowintelNoteVariables) return Promise.resolve(window.FlowintelNoteVariables)
    if (_note_vars_p) return _note_vars_p
    _note_vars_p = new Promise((res, rej) => {
        const s = document.createElement('script')
        s.src   = '/static/js/note_variables.js'
        s.onload  = () => res(window.FlowintelNoteVariables)
        s.onerror = rej
        document.head.appendChild(s)
    })
    return _note_vars_p
}

// styleUnresolvedVariables() does a blind string replace — applying it to the whole
// HTML string would also match "@this..." patterns sitting inside attribute values
// (e.g. a title="@this.case.title" on some inline HTML in the markdown source) and
// splice a <code> tag into the middle of an attribute, corrupting the markup. Only
// touch actual text-node content (between a ">" and the next "<"), same technique
// smart-render.js's own search-match highlighting uses for the same reason.
function styleVariablesInTextNodes(html) {
    if (!window.FlowintelNoteVariables) return html
    return html.replace(/>([^<]*)</g, (full, text) => {
        if (!text) return full
        return '>' + window.FlowintelNoteVariables.styleUnresolvedVariables(text) + '<'
    })
}

// Renders markdown source to sanitized HTML, with ```mermaid fences left ready for
// runMermaid() to turn into SVG once the HTML is mounted in the DOM.
export async function renderMarkdown(text, { breaks = true, styleVariables = true } = {}) {
    if (!window.marked) await loadMarked()
    if (!window.DOMPurify) await loadPurify()
    if (styleVariables && !window.FlowintelNoteVariables) await loadNoteVariables().catch(() => {})
    try {
        let html = mermaidify(window.marked.parse(text ?? '', { breaks }))
        // Resolved ⟪@var⦂value⟫ markers (see note_variables.js) must only be turned
        // into <span> markup AFTER marked.parse() — the value survives marked's raw
        // HTML passthrough as inert plain text up to this point, and only becomes
        // markup here, right before DOMPurify gets the final say on it. Callers must
        // never pre-process these markers themselves before handing text to
        // renderMarkdown().
        if (window.FlowintelNoteVariables) {
            html = window.FlowintelNoteVariables.postProcessVarMarkers(html)
        }
        if (styleVariables) {
            html = styleVariablesInTextNodes(html)
        }
        return sanitizeHtml(html)
    } catch {
        return '<p><em>Render error</em></p>'
    }
}

// Turns any <pre class="mermaid"> blocks inside `container` into rendered SVG
// diagrams. Loads mermaid.min.js lazily, and only if such a block exists.
// Sizing is left entirely to mermaid itself (its own useMaxWidth behavior) — the
// caller's CSS just needs to give the container room; see .mermaid in
// smart-editor.css / smart-render.css.
export async function runMermaid(container) {
    if (!container) return
    if (!mermaidEnabled()) return
    const nodes = container.querySelectorAll('.mermaid')
    if (!nodes.length) return
    const mermaid = await loadMermaid()
    if (!mermaid) return
    ensureMermaidInitialized(mermaid)
    try { await mermaid.run({ nodes }) } catch {}
}
