/**
 * Keeps the state of the case page (/case/<id>) in its URL, so a reload lands on
 * the same tabs and open panels. Every change goes through history.replaceState
 * (no new history entry per click). Outside the case page these helpers do nothing,
 * as some case components are also used on other pages.
 *
 *   tab=<main tab>  note=<notes sub-tab>  timeline=<timeline sub-tab>  misp=<MISP sub-tab>
 *   history=<history sub-tab>  tasks=<tasks sub-tab>  hide=<closed sections, comma list>
 *   task=<open task ids, comma list>  task_tab_<id>=<tab of that task>
 * A parameter at its default value is left out of the URL.
 */

function on_case_page() {
    return /^\/case\/\d+\/?$/.test(location.pathname)
}

export function url_get(key) {
    if (!on_case_page()) return null
    return new URL(location.href).searchParams.get(key)
}

export function url_set(key, value, default_value = null) {
    if (!on_case_page()) return
    const url = new URL(location.href)
    if (value === null || value === undefined || value === '' || value === default_value) {
        url.searchParams.delete(key)
    } else {
        url.searchParams.set(key, value)
    }
    if (url.href !== location.href) history.replaceState(history.state, '', url)
}

export function url_list(key) {
    const value = url_get(key)
    return value ? value.split(',').filter(Boolean) : []
}

export function url_list_toggle(key, item, present) {
    const list = url_list(key).filter(i => i !== String(item))
    if (present) list.push(String(item))
    url_set(key, list.join(','))
}

// Removes every parameter whose name starts with prefix (e.g. all the task_tab_<id>)
export function url_clear_prefix(prefix) {
    if (!on_case_page()) return
    const url = new URL(location.href)
    for (const key of [...url.searchParams.keys()]) {
        if (key.startsWith(prefix)) url.searchParams.delete(key)
    }
    if (url.href !== location.href) history.replaceState(history.state, '', url)
}
