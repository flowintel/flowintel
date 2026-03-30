/**
 * Flowintel Note Variables Resolver (Client-side)
 * 
 * Resolves @-prefixed variable references in notes by calling the backend API.
 * 
 * Usage:
 *   import { resolveNoteVariables, renderWithVariables } from './note_variables.js'
 *   
 *   // Resolve variables in text
 *   const resolved = await resolveNoteVariables(caseId, text, taskId)
 *   
 *   // Or use the helper that wraps md.render()
 *   const html = await renderWithVariables(md, caseId, text, taskId)
 */

// Cache resolved results to avoid redundant API calls
const _cache = new Map()
const CACHE_TTL = 30000 // 30 seconds

function _cacheKey(caseId, text, taskId, mark) {
    return `${caseId}:${taskId || ''}:${mark ? 'm' : ''}:${text}`
}

// Regex matching the same pattern as the backend
// Include `user` and `me` roots so client-side detection matches server-side
const VARIABLE_PATTERN = /@((?:this|case|task|now|today|user|me)(?:\.[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|\.[a-zA-Z_][a-zA-Z0-9_]*|\.\d+)*)/g

/**
 * Check if text contains any @variable references
 */
function hasVariables(text) {
    if (!text) return false
    VARIABLE_PATTERN.lastIndex = 0
    return VARIABLE_PATTERN.test(text)
}

/**
 * Resolve @-prefixed variable references via the backend API.
 * Returns the text with variables replaced by their values.
 * 
 * @param {number} caseId - Current case ID
 * @param {string} text - Raw text containing @variables
 * @param {number|null} taskId - Current task ID (optional)
 * @param {boolean} mark - Whether to wrap resolved values with markers for styling
 * @returns {Promise<string>} Resolved text
 */
async function resolveNoteVariables(caseId, text, taskId = null, mark = false) {
    if (!text || !hasVariables(text)) {
        return text || ''
    }

    const key = _cacheKey(caseId, text, taskId, mark)
    const cached = _cache.get(key)
    if (cached && (Date.now() - cached.time) < CACHE_TTL) {
        return cached.value
    }

    try {
        const body = { text: text }
        if (taskId) {
            body.task_id = taskId
        }
        if (mark) {
            body.mark = true
        }

        const res = await fetch(`/case/${caseId}/resolve_note_variables`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': (typeof $ !== 'undefined' && $("#csrf_token").length) ? $("#csrf_token").val() : ''
            },
            body: JSON.stringify(body)
        })

        if (res.ok) {
            const data = await res.json()
            const resolved = data.resolved || text
            _cache.set(key, { value: resolved, time: Date.now() })
            return resolved
        }
    } catch (e) {
        console.warn('Note variable resolution failed:', e)
    }

    return text
}

/**
 * Synchronous variable resolver using cached results only.
 * Returns original text if not cached. Used for live preview.
 * 
 * @param {number} caseId 
 * @param {string} text 
 * @param {number|null} taskId
 * @returns {string}
 */
function resolveNoteVariablesSync(caseId, text, taskId = null) {
    if (!text || !hasVariables(text)) {
        return text || ''
    }
    const key = _cacheKey(caseId, text, taskId, false)
    const cached = _cache.get(key)
    if (cached && (Date.now() - cached.time) < CACHE_TTL) {
        return cached.value
    }
    return text
}

/**
 * Clear the resolution cache
 */
function clearVariableCache() {
    _cache.clear()
}

/**
 * Style @variable references in rendered HTML.
 * In edit mode, wraps unresolved @variables with a styled span.
 * 
 * @param {string} html - The rendered HTML  
 * @returns {string} HTML with styled variable references
 */
function styleUnresolvedVariables(html) {
    if (!html) return html
    return html.replace(
        /@((?:this|case|task|now|today|user|me)(?:\.[a-zA-Z_][a-zA-Z0-9_]*|\.[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}|\.\d+)*)/g,
        '<code class="note-variable unresolved" title="Unresolved variable">@$1</code>'
    )
}

/**
 * Post-process rendered HTML to replace ⟪@var⦂value⟫ markers with styled spans.
 * Call this AFTER md.render() on text that was resolved with mark=true.
 *
 * The backend wraps resolved variable values with ⟪@var.name⦂value⟫ using
 * ⟪ (U+27EA), ⦂ (U+2982) and ⟫ (U+27EB) unicode markers.
 * These survive markdown rendering as plain text. This function
 * converts them into styled <span> elements with a title tooltip
 * showing the original variable name.
 *
 * @param {string} html - HTML output from md.render()
 * @returns {string} HTML with resolved variable values wrapped in styled spans
 */
function postProcessVarMarkers(html) {
    if (!html) return html
    return html.replace(/\u27ea(@[^\u2982]*)\u2982([^\u27eb]*)\u27eb/g,
        '<span class="note-var-resolved" title="$1">$2</span>')
}

/**
 * Render markdown text with variables resolved and styled.
 * Full pipeline: resolve vars (with markers) → md.render() → post-process markers.
 *
 * @param {Object} md - markdown-it instance
 * @param {number} caseId - Current case ID
 * @param {string} text - Raw markdown text with @variables
 * @param {number|null} taskId - Current task ID (optional)
 * @returns {Promise<string>} Rendered HTML with styled resolved variables
 */
async function renderNoteWithVars(md, caseId, text, taskId = null) {
    if (!text) return ''
    const resolved = await resolveNoteVariables(caseId, text, taskId, true)
    const html = md.render(resolved)
    return postProcessVarMarkers(html)
}

/**
 * Create a debounced preview resolver for live editing.
 * Returns a function that can be called on each editor change.
 * It debounces the API calls and updates a Vue ref with the rendered HTML.
 *
 * @param {Object} md - markdown-it instance
 * @param {number} caseId - Current case ID
 * @param {number} delay - Debounce delay in ms (default 500)
 * @param {Function|null} onAfterUpdate - Optional callback invoked after the DOM ref is updated (e.g. to re-run mermaid)
 * @returns {Object} { update(text, taskId, targetRef), cancel() }
 */
function createPreviewResolver(md, caseId, delay = 500, onAfterUpdate = null) {
    let timer = null
    let lastText = ''

    function cancel() {
        if (timer) {
            clearTimeout(timer)
            timer = null
        }
    }

    async function update(text, taskId, targetRef) {
        lastText = text
        // Immediately render raw markdown
        const rawHtml = md.render(text || '')
        targetRef.value = rawHtml
        if (onAfterUpdate) onAfterUpdate()

        cancel()

        if (!text || !hasVariables(text)) {
            return
        }

        // Debounce the variable resolution
        timer = setTimeout(async () => {
            // Check if text is still current (user may have typed more)
            if (text !== lastText) return

            try {
                const resolved = await resolveNoteVariables(caseId, text, taskId, true)
                // Double-check text is still current after async call
                if (text !== lastText) return
                const html = md.render(resolved)
                targetRef.value = postProcessVarMarkers(html)
                if (onAfterUpdate) onAfterUpdate()
            } catch (e) {
                console.warn('Preview variable resolution failed:', e)
            }
        }, delay)
    }

    return { update, cancel }
}

// Export for use as ES module or global
if (typeof window !== 'undefined') {
    window.FlowintelNoteVariables = {
        resolveNoteVariables,
        resolveNoteVariablesSync,
        hasVariables,
        clearVariableCache,
        styleUnresolvedVariables,
        postProcessVarMarkers,
        renderNoteWithVars,
        createPreviewResolver
    }
}
