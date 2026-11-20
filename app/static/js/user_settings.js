/**
 * user_settings.js — Apply and save the user settings (UserSettings) in the browser.
 *
 * Loaded synchronously in <head> (base.html) so the saved theme and font are applied
 * before the first paint. The server writes the saved values on <html>:
 *   data-theme-pref="<theme>"           (light, dark, auto, christmas... see utils/themes.py;
 *                                        "auto" follows the operating system)
 *   data-font="rubik|system|readable"
 *
 * Any element with data-setting="<name>" data-value="<value>" changes that setting on
 * click, applies it at once and saves it (POST /account/settings {"<name>": "<value>"}).
 */
(function () {
    const root = document.documentElement
    const media = window.matchMedia ? window.matchMedia('(prefers-color-scheme: dark)') : null

    // How each setting is applied to the page
    const APPLY = {
        theme(value) {
            // Bootstrap mode the theme is drawn on (window.FI_THEME_BASES, set in base.html)
            const base = (window.FI_THEME_BASES || {})[value] || value
            const resolved = base === 'dark' || base === 'light' ? base : (media && media.matches ? 'dark' : 'light')
            root.setAttribute('data-theme-pref', value)
            root.setAttribute('data-bs-theme', resolved)
            // shape and text layer of some themes (css/themes/styled.css)
            root.toggleAttribute('data-theme-styled', (window.FI_THEMES_STYLED || []).includes(value))
        },
        font(value) {
            root.setAttribute('data-font', value)
        },
        // nothing to draw: read by the case index on its next load (default table / cards)
        case_view(value) {
            root.setAttribute('data-case-view', value)
        },
        // default look of the tags in the case view (read by case/tags_edition.js)
        tag_view(value) {
            root.setAttribute('data-tag-view', value)
        },
        // top bar fixed or not while scrolling (css: [data-sticky-header] in core.css)
        sticky_header(value) {
            root.setAttribute('data-sticky-header', value)
        },
    }

    const current = {
        theme: () => root.getAttribute('data-theme-pref') || 'auto',
        font: () => root.getAttribute('data-font') || 'rubik',
        // set by a click; before that, the option the server marked active (settings page)
        case_view: () => root.getAttribute('data-case-view')
            || document.querySelector('[data-setting="case_view"].active')?.getAttribute('data-value') || 'cards',
        tag_view: () => root.getAttribute('data-tag-view') || 'compact',
        sticky_header: () => root.getAttribute('data-sticky-header') || 'fixed',
    }

    function markSelected() {
        document.querySelectorAll('[data-setting][data-value]').forEach(el => {
            const name = el.getAttribute('data-setting')
            if (!current[name]) return
            const selected = el.getAttribute('data-value') === current[name]()
            el.classList.toggle('active', selected)
            if (el.getAttribute('role') === 'radio') el.setAttribute('aria-checked', selected ? 'true' : 'false')
        })
    }

    async function save(name, value) {
        const token = document.getElementById('csrf_token')
        try {
            const res = await fetch('/account/settings', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json', 'X-CSRFToken': token ? token.value : '' },
                body: JSON.stringify({ [name]: value })
            })
            if (res.ok) toast(`${LABELS[name] || 'Setting'} saved`, 'success-subtle')
            else { console.warn('Setting not saved', name, value, res.status); toast('Setting not saved', 'danger-subtle') }
        } catch (e) {
            console.warn('Could not save the setting', name, e)
            toast('Could not save the setting', 'danger-subtle')
        }
    }

    // toasts come from the ES module toaster.js (this file is a classic script)
    const LABELS = { theme: 'Theme', font: 'Font', case_view: 'Case list display', tag_view: 'Tag display', sticky_header: 'Top bar' }
    function toast(message, cls) {
        import('/static/js/toaster.js').then(m => m.create_message(message, cls)).catch(() => {})
    }

    // Before first paint
    APPLY.theme(current.theme())

    // Follow the OS while the theme is "auto"
    if (media && media.addEventListener) {
        media.addEventListener('change', () => { if (current.theme() === 'auto') APPLY.theme('auto') })
    }

    document.addEventListener('click', event => {
        const item = event.target.closest('[data-setting][data-value]')
        if (!item) return
        const name = item.getAttribute('data-setting'), value = item.getAttribute('data-value')
        if (!APPLY[name]) return
        event.preventDefault()
        APPLY[name](value)
        markSelected()
        save(name, value)
    })

    document.addEventListener('DOMContentLoaded', markSelected)
})()
