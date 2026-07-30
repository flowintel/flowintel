/**
 * at-variable-complete.js — @variable autocomplete dropdown for plain <textarea>s
 *
 * Thin adapter over window.FlowintelVarComplete (note_variable_completions.js),
 * which already implements the suggestion data/logic and a CodeMirror 6 extension.
 * That module's public API was already designed with this in mind — see its
 * getSuggestionsForToken()/getTokenBefore()/computeInsertText() — so this file only
 * adds the missing piece: a dropdown UI wired to a plain textarea's input/keydown
 * events instead of CodeMirror's.
 *
 * Usage:
 *   import { attachAtVariableComplete } from '/static/js/components/at-variable-complete.js'
 *   const complete = attachAtVariableComplete(textareaEl, {
 *       onPick(insertText, from, to) { ... replace value[from:to] with insertText ... }
 *   })
 *   complete.check()     // re-evaluate now (e.g. after inserting "@" programmatically)
 *   complete.destroy()   // when the textarea unmounts
 */

let _loadPromise = null
function loadVarComplete() {
    if (window.FlowintelVarComplete) return Promise.resolve(window.FlowintelVarComplete)
    if (_loadPromise) return _loadPromise
    _loadPromise = new Promise((res, rej) => {
        const s = document.createElement('script')
        s.src   = '/static/js/note_variable_completions.js'
        s.onload  = () => res(window.FlowintelVarComplete)
        s.onerror = rej
        document.head.appendChild(s)
    })
    return _loadPromise
}

const STYLE_ID = 'at-var-suggest-style'
function ensureStyle() {
    if (document.getElementById(STYLE_ID)) return
    const s = document.createElement('style')
    s.id = STYLE_ID
    s.textContent = [
        '.var-suggest-dropdown { font-family: system-ui, sans-serif; }',
        '.var-suggest-item { transition: background .1s; }',
    ].join('\n')
    document.head.appendChild(s)
}

// Mirror-div technique: measures where the caret would fall on screen by rendering
// the same text in an identical (hidden) div and reading a marker span's position.
// Textareas have no native API for this.
const MIRROR_PROPS = [
    'boxSizing', 'width', 'height', 'overflowX', 'overflowY',
    'borderTopWidth', 'borderRightWidth', 'borderBottomWidth', 'borderLeftWidth',
    'paddingTop', 'paddingRight', 'paddingBottom', 'paddingLeft',
    'fontStyle', 'fontVariant', 'fontWeight', 'fontStretch', 'fontSize', 'fontSizeAdjust',
    'lineHeight', 'fontFamily', 'textAlign', 'textTransform', 'textIndent',
    'textDecoration', 'letterSpacing', 'wordSpacing', 'tabSize', 'whiteSpace', 'wordWrap',
]

function caretRect(textarea, pos) {
    const style = getComputedStyle(textarea)
    const div = document.createElement('div')
    div.style.position = 'absolute'
    div.style.visibility = 'hidden'
    div.style.top = '0'
    div.style.left = '-9999px'
    MIRROR_PROPS.forEach(p => { div.style[p] = style[p] })

    div.textContent = textarea.value.slice(0, pos)
    const marker = document.createElement('span')
    marker.textContent = textarea.value.slice(pos) || '.'
    div.appendChild(marker)
    document.body.appendChild(div)

    const taRect     = textarea.getBoundingClientRect()
    const divRect    = div.getBoundingClientRect()
    const markerRect = marker.getBoundingClientRect()
    document.body.removeChild(div)

    const lineHeight = parseFloat(style.lineHeight) || 18
    return {
        left:   taRect.left + (markerRect.left - divRect.left) - textarea.scrollLeft,
        bottom: taRect.top + (markerRect.top - divRect.top) - textarea.scrollTop + lineHeight,
    }
}

export function attachAtVariableComplete(textarea, { onPick } = {}) {
    ensureStyle()
    loadVarComplete()

    let dropdown = null
    let items = []
    let selectedIdx = 0
    let currentTok = null

    function close() {
        if (dropdown && dropdown.parentElement) dropdown.remove()
        dropdown = null
        items = []
        selectedIdx = 0
        currentTok = null
    }

    function render() {
        dropdown.innerHTML = ''
        items.forEach((it, idx) => {
            const row = document.createElement('div')
            row.className = 'var-suggest-item' + (idx === selectedIdx ? ' var-suggest-active' : '')
            Object.assign(row.style, {
                padding: '4px 10px', cursor: 'pointer', display: 'flex',
                justifyContent: 'space-between', alignItems: 'center',
                background: idx === selectedIdx ? 'var(--bs-primary, #0d6efd)' : 'transparent',
                color: idx === selectedIdx ? '#fff' : 'inherit',
                borderRadius: '3px', margin: '0 4px',
            })
            const lbl = document.createElement('span')
            lbl.textContent = it.label
            lbl.style.fontFamily = 'monospace'
            row.appendChild(lbl)
            if (it.info) {
                const inf = document.createElement('span')
                inf.textContent = it.info
                Object.assign(inf.style, { fontSize: '11px', opacity: '.6', marginLeft: '8px' })
                row.appendChild(inf)
            }
            row.addEventListener('mousedown', (ev) => { ev.preventDefault(); ev.stopPropagation(); pick(it) })
            row.addEventListener('mouseenter', () => { selectedIdx = idx; render() })
            dropdown.appendChild(row)
        })
    }

    function pick(item) {
        if (!currentTok || !window.FlowintelVarComplete) return
        const insertText = window.FlowintelVarComplete.computeInsertText(currentTok.text, item)
        const from = currentTok.from
        const to = textarea.selectionEnd
        close()
        onPick?.(insertText, from, to)
    }

    function open(tok, list) {
        currentTok = tok
        items = list
        selectedIdx = 0
        if (!dropdown) {
            dropdown = document.createElement('div')
            dropdown.className = 'var-suggest-dropdown'
            document.body.appendChild(dropdown)
        }
        const rect = caretRect(textarea, textarea.selectionEnd)
        Object.assign(dropdown.style, {
            position: 'fixed', zIndex: '10000', minWidth: '180px', maxHeight: '220px',
            overflowY: 'auto', background: 'var(--bs-body-bg, #fff)', color: 'var(--bs-body-color, #212529)',
            border: '1px solid var(--bs-border-color, #dee2e6)', borderRadius: '6px',
            boxShadow: '0 4px 12px rgba(0,0,0,.18)', padding: '4px 0', fontSize: '13px',
            left: rect.left + 'px', top: rect.bottom + 2 + 'px',
        })
        render()
    }

    function check() {
        if (!window.FlowintelVarComplete) return
        const pos = textarea.selectionEnd
        const tok = window.FlowintelVarComplete.getTokenBefore(textarea.value, pos)
        if (!tok) { close(); return }
        const suggestions = window.FlowintelVarComplete.getSuggestionsForToken(tok.text)
        if (!suggestions.length) { close(); return }
        open(tok, suggestions)
    }

    // Capture phase + stopImmediatePropagation: while the dropdown is open, these
    // keys are ours alone. Without this, e.g. Tab would also reach smart-editor's
    // own on_keydown (bubble phase) and insert an indent on top of picking a
    // suggestion — preventDefault() alone stops the browser default, not other
    // listeners on the same element.
    function onKeydown(ev) {
        if (!dropdown) return
        if (ev.key === 'ArrowDown') {
            ev.preventDefault(); ev.stopImmediatePropagation()
            selectedIdx = (selectedIdx + 1) % items.length; render()
        } else if (ev.key === 'ArrowUp') {
            ev.preventDefault(); ev.stopImmediatePropagation()
            selectedIdx = (selectedIdx - 1 + items.length) % items.length; render()
        } else if (ev.key === 'Tab' || ev.key === 'Enter') {
            ev.preventDefault(); ev.stopImmediatePropagation()
            if (items[selectedIdx]) pick(items[selectedIdx])
        } else if (ev.key === 'Escape') {
            ev.preventDefault(); ev.stopImmediatePropagation()
            close()
        }
    }

    function onInput() { check() }
    function onClick() { check() }
    function onBlur() {
        // Let a mousedown pick land first (it preventDefaults, so blur won't
        // normally fire from it) — small delay is a safety net regardless.
        setTimeout(close, 100)
    }
    function onOutsideClick(ev) {
        if (dropdown && !dropdown.contains(ev.target) && ev.target !== textarea) close()
    }

    textarea.addEventListener('input', onInput)
    textarea.addEventListener('click', onClick)
    textarea.addEventListener('keydown', onKeydown, true)
    textarea.addEventListener('blur', onBlur)
    document.addEventListener('mousedown', onOutsideClick)

    return {
        check,
        destroy() {
            close()
            textarea.removeEventListener('input', onInput)
            textarea.removeEventListener('click', onClick)
            textarea.removeEventListener('keydown', onKeydown, true)
            textarea.removeEventListener('blur', onBlur)
            document.removeEventListener('mousedown', onOutsideClick)
        },
    }
}
