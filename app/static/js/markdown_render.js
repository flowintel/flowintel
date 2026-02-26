import { display_toast } from '/static/js/toaster.js'

let activeRenders = 0
let spinnerEl = null

function ensureSpinner() {
    if (spinnerEl && document.body.contains(spinnerEl)) return spinnerEl
    spinnerEl = document.createElement('div')
    spinnerEl.id = 'markdown-render-spinner'
    spinnerEl.setAttribute('aria-live', 'polite')
    spinnerEl.style.position = 'fixed'
    spinnerEl.style.top = '1rem'
    spinnerEl.style.right = '1rem'
    spinnerEl.style.zIndex = '2000'
    spinnerEl.style.padding = '0.5rem 0.75rem'
    spinnerEl.style.borderRadius = '0.5rem'
    spinnerEl.style.background = 'rgba(0,0,0,0.7)'
    spinnerEl.style.color = 'white'
    spinnerEl.style.fontSize = '0.9rem'
    spinnerEl.style.display = 'none'
    spinnerEl.style.alignItems = 'center'
    spinnerEl.style.gap = '0.5rem'

    // Minimal inline spinner dot
    const dot = document.createElement('span')
    dot.style.width = '0.85rem'
    dot.style.height = '0.85rem'
    dot.style.border = '2px solid rgba(255,255,255,0.4)'
    dot.style.borderTopColor = 'white'
    dot.style.borderRadius = '50%'
    dot.style.display = 'inline-block'
    dot.style.animation = 'markdown-spin 0.8s linear infinite'

    const text = document.createElement('span')
    text.textContent = 'Rendering markdown…'

    spinnerEl.appendChild(dot)
    spinnerEl.appendChild(text)

    // Add a tiny keyframe once
    if (!document.getElementById('markdown-render-style')) {
        const style = document.createElement('style')
        style.id = 'markdown-render-style'
        style.textContent = '@keyframes markdown-spin { from { transform: rotate(0deg);} to { transform: rotate(360deg);} }'
        document.head.appendChild(style)
    }

    document.body.appendChild(spinnerEl)
    return spinnerEl
}

function setLoading(isLoading) {
    const el = ensureSpinner()
    if (isLoading) {
        activeRenders += 1
        el.style.display = 'flex'
    } else {
        activeRenders = Math.max(0, activeRenders - 1)
        if (activeRenders === 0) {
            el.style.display = 'none'
        }
    }
}

// Render markdown on the server (Mermaid handled server-side)
export async function renderMarkdownServer(markdownText = '', format = 'svg') {
    setLoading(true)
    try {
        const res = await fetch('/markdown/render', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': document.getElementById('csrf_token')?.value || ''
            },
            body: JSON.stringify({ markdown: markdownText, format })
        })
        if (res.ok) {
            const data = await res.json()
            return data.html || ''
        }
        // Show toast if available
        try { display_toast(res) } catch (_) { /* noop */ }
        return ''
    } finally {
        setLoading(false)
    }
}
