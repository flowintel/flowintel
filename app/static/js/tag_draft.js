/**
 * tag_draft.js — recover tags/clusters/galaxies/custom tags picked on a
 * creation form (create_case, create_task, ...) across a failed submit.
 *
 * Those forms do a native (non-AJAX) POST; a server-side validation error
 * (duplicate title, missing field, ...) re-renders the whole page from
 * scratch, which would otherwise silently drop everything already picked
 * in the tag editor. Callers save a draft right before submitting and
 * restore it once on mount; restoring removes it, so it only survives a
 * single reload and never resurfaces on a later, unrelated visit.
 */

const PREFIX = 'flowintel_tag_draft:'

function save_tag_draft(key, data) {
    try {
        sessionStorage.setItem(PREFIX + key, JSON.stringify(data))
    } catch (e) {
        // storage unavailable/full — draft recovery is a convenience, not critical
    }
}

function restore_tag_draft(key) {
    try {
        const raw = sessionStorage.getItem(PREFIX + key)
        if (!raw) return null
        sessionStorage.removeItem(PREFIX + key)
        return JSON.parse(raw)
    } catch (e) {
        return null
    }
}

export { save_tag_draft, restore_tag_draft }
