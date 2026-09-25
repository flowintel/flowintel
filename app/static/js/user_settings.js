/**
 * user_settings.js — Apply and save the user settings (UserSettings) in the browser.
 *
 * Loaded synchronously in <head> (base.html) so the saved theme and font are applied
 * before the first paint. The server writes the saved values on <html>:
 *   data-theme-pref="light|dark|auto"   ("auto" follows the operating system)
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
            const resolved = value === 'dark' || value === 'light' ? value : (media && media.matches ? 'dark' : 'light')
            root.setAttribute('data-theme-pref', value)
            root.setAttribute('data-bs-theme', resolved)
        },
        font(value) {
            root.setAttribute('data-font', value)
        },
    }

    const current = {
        theme: () => root.getAttribute('data-theme-pref') || 'auto',
        font: () => root.getAttribute('data-font') || 'rubik',
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
            if (!res.ok) console.warn('Setting not saved', name, value, res.status)
        } catch (e) {
            console.warn('Could not save the setting', name, e)
        }
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
