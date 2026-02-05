import { display_toast } from '/static/js/toaster.js'

// Render markdown on the server (Mermaid handled server-side)
export async function renderMarkdownServer(markdownText = '', format = 'svg') {
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
}
