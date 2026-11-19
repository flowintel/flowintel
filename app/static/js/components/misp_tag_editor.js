// Tag / galaxy editor drawn exactly like MISP's (Overmind theme) "Edit Tags" and
// "Edit Galaxy Clusters" modals and its index filter pickers: MISP's own column
// browser (misp-index-filter-browser.js, mounted in a host) on top, the picked
// values as MISP chips (misp-tag-chips.js) below, each with a × to remove it.
//
// Same props and events as case/edition_select.js, so it drops in its place:
// st/sc/sg/sct add, delete_st/delete_sc/delete_sg/delete_sct remove by index.
//
// The browser keeps one panel per page (MISP opens one modal at a time), so the
// Tags / Galaxies switch mounts it for one kind at a time.
import { display_toast } from '../toaster.js'
import { BROWSER_STRINGS } from './misp_browser_strings.js'
import tag_badge from './tag-badge.js'
const { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } = Vue

const ASSETS = {
    css: '/static/css/misp-index-filter-browser.css',
    js: '/static/js/misp-index-filter-browser.js',
}

// MISP's mispOvermind.js loadIndexFilterBrowser(), with Flowintel's paths.
let loading = null
export function loadBrowser() {
    if (window.IndexFilterBrowser) {
        return window.IndexFilterBrowser.mount ? Promise.resolve() : Promise.reject()
    }
    if (loading) return loading
    if (!document.querySelector('link[href^="' + ASSETS.css + '"]')) {
        const link = document.createElement('link')
        link.rel = 'stylesheet'
        link.href = ASSETS.css
        document.head.appendChild(link)
    }
    loading = new Promise((resolve, reject) => {
        const script = document.createElement('script')
        script.src = ASSETS.js
        script.onload = resolve
        script.onerror = () => { loading = null; reject() }
        document.head.appendChild(script)
    })
    return loading
}

const KINDS = {
    tag: {
        label: 'Tags',
        accent: 'var(--fi-misp-tag, #0d6efd)',
        cfg: {
            kind: 'tag',
            scopes: '/case/picker/tag_scopes',
            source: '/case/picker/tag_search',
            tree: '/case/picker/tag_tree',
            label: 'Tags',
        },
    },
    galaxy: {
        label: 'Galaxies',
        accent: 'var(--fi-misp-galaxy, #8B5CF6)',
        cfg: {
            kind: 'galaxy',
            scopes: '/case/picker/galaxy_scopes',
            source: '/case/picker/cluster_search',
            label: 'Galaxy clusters',
        },
    },
}

// Picked values: MISP context chips, or the compact chips of the indexes (tag_badge).
const VIEW_KEY = 'flowintel_tag_editor_view'
const OPEN_KEY = 'flowintel_tag_editor_open'

const OBJECT_URLS = {
    case: '/case/get_{}_case/',
    task: '/case/get_{}_task/',
    case_template: '/templating/get_{}_case/',
    task_template: '/templating/get_{}_task/',
}

export default {
    delimiters: ['[[', ']]'],
    props: {
        type_object: String,
        object_id: Number,
        initialTags: { type: Array, default: () => [] },
        initialClusters: { type: Array, default: () => [] },
        initialGalaxies: { type: Array, default: () => [] },
        initialCustomTags: { type: Array, default: () => [] },
        hasDraft: { type: Boolean, default: false },
        // Which browser shows first: 'tag' or 'galaxy'.
        start: { type: String, default: 'tag' },
    },
    components: { tag_badge },
    emits: ['st', 'sc', 'sct', 'sg', 'delete_st', 'delete_sc', 'delete_sg', 'delete_sct'],
    setup(props, { emit }) {
        const kind = ref(props.start === 'galaxy' ? 'galaxy' : 'tag')
        const host = ref(null)
        const tag_list = ref(null)
        const cluster_list = ref(null)
        const load_failed = ref(false)
        let saved_view = 'context'
        try { saved_view = localStorage.getItem(VIEW_KEY) || 'context' } catch (e) {}
        const view = ref(saved_view === 'compact' ? 'compact' : 'context')
        let saved_open = '1'
        try { saved_open = localStorage.getItem(OPEN_KEY) ?? '1' } catch (e) {}
        const open = ref(saved_open !== '0')
        function toggle_open() {
            open.value = !open.value
            try { localStorage.setItem(OPEN_KEY, open.value ? '1' : '0') } catch (e) {}
            // The browser measures its host: draw it once it is visible again.
            if (open.value) nextTick(() => { if (window.IndexFilterBrowser) mount(); renderLists() })
        }
        function set_view(v) {
            view.value = v
            try { localStorage.setItem(VIEW_KEY, v) } catch (e) {}
        }

        const use_initial = !props.object_id || props.hasDraft
        const selected_tags = ref(use_initial ? [...props.initialTags] : [])
        const selected_clusters = ref(use_initial ? [...props.initialClusters] : [])
        const selected_galaxies = ref(use_initial ? [...props.initialGalaxies] : [])
        const selected_custom_tags = ref(use_initial ? [...props.initialCustomTags] : [])
        const custom_tags = ref([])

        if (use_initial) {
            if (selected_tags.value.length) emit('st', selected_tags.value)
            if (selected_clusters.value.length) emit('sc', selected_clusters.value)
            if (selected_galaxies.value.length) emit('sg', selected_galaxies.value)
            if (selected_custom_tags.value.length) emit('sct', selected_custom_tags.value)
        }

        let browser = null

        // ---- what the browser ticks ----

        function browserSelection() {
            // Custom tags live in the tag browser's "Custom tags" scope (MISP's "No namespace").
            if (kind.value === 'tag') {
                return selected_tags.value.map(t => ({ value: t.name }))
                    .concat(selected_custom_tags.value.map(t => ({ value: t.name })))
            }
            return selected_clusters.value.map(c => ({ value: c.tag }))
        }

        function changed() {
            renderLists()
            if (browser) browser.select(browserSelection())
        }

        // ---- picking and removing ----

        async function resolve(key, id) {
            const res = await fetch('/case/picker/resolve?' + key + '=' + encodeURIComponent(id))
            if (!res.ok) { display_toast(res); return null }
            return res.json()
        }

        function addGalaxyOf(cluster, galaxies) {
            if (selected_galaxies.value.some(g => g.id === cluster.galaxy_id)) return
            const galaxy = galaxies[cluster.galaxy_id]
            if (!galaxy) return
            selected_galaxies.value.push(galaxy)
            emit('sg', galaxy)
        }

        // A galaxy stays marked while one of its clusters is picked.
        function dropGalaxyOf(cluster) {
            if (selected_clusters.value.some(c => c.galaxy_id === cluster.galaxy_id)) return
            const i = selected_galaxies.value.findIndex(g => g.id === cluster.galaxy_id)
            if (i === -1) return
            selected_galaxies.value.splice(i, 1)
            emit('delete_sg', i)
        }

        function removeTag(name) {
            const i = selected_tags.value.findIndex(t => t.name === name)
            if (i === -1) return
            selected_tags.value.splice(i, 1)
            emit('delete_st', i)
        }

        function removeCluster(tag) {
            const i = selected_clusters.value.findIndex(c => c.tag === tag)
            if (i === -1) return
            const [cluster] = selected_clusters.value.splice(i, 1)
            emit('delete_sc', i)
            dropGalaxyOf(cluster)
        }

        function removeCustomTag(name) {
            const i = selected_custom_tags.value.findIndex(t => t.name === name)
            if (i === -1) return
            selected_custom_tags.value.splice(i, 1)
            emit('delete_sct', i)
        }

        async function onToggleCustom(row, on) {
            if (!on) { removeCustomTag(row.value); changed(); return }
            if (selected_custom_tags.value.some(t => t.name === row.value)) return
            const res = await fetch('/case/picker/resolve?names=' + encodeURIComponent(JSON.stringify({ custom_tags: [row.value] })))
            if (!res.ok) { display_toast(res); return }
            const tag = (await res.json()).custom_tags[0]
            if (tag && !selected_custom_tags.value.some(t => t.name === tag.name)) {
                selected_custom_tags.value.push(tag)
                emit('sct', tag)
            }
            changed()
        }

        async function onToggle(row, on) {
            const isTag = kind.value === 'tag'
            // Every taxonomy tag has a "namespace:"; a value without one is a custom tag.
            if (isTag && !String(row.value).includes(':')) return onToggleCustom(row, on)
            if (!on) {
                isTag ? removeTag(row.value) : removeCluster(row.value)
                changed()
                return
            }
            const have = isTag
                ? selected_tags.value.some(t => t.name === row.value)
                : selected_clusters.value.some(c => c.tag === row.value)
            if (have || !row.id) return
            const data = await resolve(isTag ? 'tags' : 'clusters', row.id)
            if (!data) return
            if (isTag) {
                const tag = data.tags[0]
                if (tag && !selected_tags.value.some(t => t.name === tag.name)) {
                    selected_tags.value.push(tag)
                    emit('st', tag)
                }
            } else {
                const cluster = data.clusters[0]
                if (cluster && !selected_clusters.value.some(c => c.tag === cluster.tag)) {
                    selected_clusters.value.push(cluster)
                    emit('sc', cluster)
                    addGalaxyOf(cluster, data.galaxies)
                }
            }
            changed()
        }

        function toggleCustomTag(tag) {
            const i = selected_custom_tags.value.findIndex(t => t.name === tag.name)
            if (i > -1) {
                selected_custom_tags.value.splice(i, 1)
                emit('delete_sct', i)
            } else {
                selected_custom_tags.value.push(tag)
                emit('sct', tag)
            }
        }

        // ---- the picked chips, as MISP's tag_picker.ctp / galaxy_picker.ctp draw them ----

        function chipButton(icon, title, onClick) {
            const b = document.createElement('button')
            b.type = 'button'
            b.className = 'hg-act'
            b.title = title
            b.setAttribute('aria-label', title)
            b.innerHTML = icon
            b.addEventListener('click', (e) => {
                e.preventDefault()
                e.stopPropagation()
                onClick()
            })
            return b
        }

        function reveal(kindOf, value) {
            if (kind.value !== kindOf) {
                pendingReveal = value
                kind.value = kindOf
                return
            }
            if (browser) browser.reveal(value)
        }
        let pendingReveal = null

        function wire(el, attr, byKey, onRemove, kindOf) {
            el.querySelectorAll('.hg-unit').forEach((unit) => {
                const node = unit.matches('[' + attr + ']') ? unit : unit.querySelector('[' + attr + ']')
                const item = node ? byKey[node.getAttribute(attr)] : null
                if (!item) return
                unit.title = BROWSER_STRINGS.showWhere
                unit.style.cursor = 'pointer'
                unit.addEventListener('click', (e) => {
                    e.preventDefault()
                    reveal(kindOf, item.value)
                })
                unit.appendChild(chipButton('&times;', BROWSER_STRINGS.remove, () => {
                    onRemove(item.value)
                    changed()
                }))
            })
        }

        function renderLists() {
            if (!window.TagChips || view.value !== 'context') return
            if (tag_list.value) {
                const list = [...selected_tags.value].sort((a, b) => a.name.localeCompare(b.name))
                const byId = {}
                list.forEach(t => { byId[t.id] = { value: t.name } })
                tag_list.value.innerHTML = window.TagChips.collection(
                    list.map(t => ({ id: t.id, name: t.name, colour: t.color })),
                    { searchUrl: '' }
                )
                wire(tag_list.value, 'data-tag-id', byId, removeTag, 'tag')
            }
            if (cluster_list.value) {
                const list = [...selected_clusters.value].sort((a, b) => a.name.localeCompare(b.name))
                const byId = {}
                list.forEach(c => { byId[c.id] = { value: c.tag } })
                cluster_list.value.innerHTML = window.TagChips.clusters(
                    list.map(c => ({
                        id: c.id, value: c.name, galaxy: c.galaxy, description: c.description,
                        iconClass: c.icon ? 'fas fa-' + c.icon : null,
                    })),
                    { href: () => null }
                )
                wire(cluster_list.value, 'data-cluster-id', byId, removeCluster, 'galaxy')
            }
        }

        // ---- mounting the browser ----

        function mount() {
            if (browser) { browser.destroy(); browser = null }
            if (!host.value) return
            const k = KINDS[kind.value]
            host.value.style.setProperty('--ifb-accent', k.accent)
            host.value.innerHTML = ''
            browser = window.IndexFilterBrowser.mount(host.value, Object.assign({}, k.cfg, {
                strings: BROWSER_STRINGS,
                selection: browserSelection(),
                onToggle: onToggle,
                reserve: 490,
            }))
            if (pendingReveal) {
                browser.reveal(pendingReveal)
                pendingReveal = null
            }
        }

        watch(kind, () => nextTick(mount))
        watch(view, () => nextTick(renderLists))

        onMounted(() => {
            loadBrowser().then(mount, () => { load_failed.value = true })
            renderLists()
        })
        onBeforeUnmount(() => { if (browser) browser.destroy() })

        // ---- the object's current tags (edit mode), as edition_select.js loads them ----

        async function load(what, key, ev, target) {
            const url = OBJECT_URLS[props.type_object]
            if (!url) return
            const res = await fetch(url.replace('{}', what) + props.object_id)
            if (!res.ok) { display_toast(res); return }
            const loc = await res.json()
            target.value = loc[key] || []
            emit(ev, target.value)
            changed()
        }

        if (props.object_id && !props.hasDraft) {
            load('taxonomies', 'tags', 'st', selected_tags)
            load('galaxies', 'clusters', 'sc', selected_clusters)
            load('custom_tags', 'custom_tags', 'sct', selected_custom_tags)
        }


        const selected_custom_names = computed(() => selected_custom_tags.value.map(t => t.name))

        return {
            kind, KINDS, host, tag_list, cluster_list, load_failed,
            selected_tags, selected_clusters, custom_tags, selected_custom_names, toggleCustomTag,
            view, set_view, reveal, open, toggle_open,
            remove_tag: (name) => { removeTag(name); changed() },
            remove_cluster: (tag) => { removeCluster(tag); changed() },
            remove_custom: (name) => { removeCustomTag(name); changed() },
            selected_custom_tags,
        }
    },
    template: `
    <div class="misp-tag-editor card">
      <div class="card-header d-flex align-items-center gap-2 mte-toggle" role="button" tabindex="0"
           :aria-expanded="open" @click="toggle_open" @keydown.enter.prevent="toggle_open" @keydown.space.prevent="toggle_open">
        <i class="fa-solid fa-chevron-right mte-chev" :class="{ 'is-open': open }"></i>
        <span class="fw-semibold">Tags, taxonomies and galaxies</span>
        <span class="text-body-secondary small ms-auto">
            [[ selected_tags.length ]] tags · [[ selected_clusters.length ]] clusters · [[ selected_custom_names.length ]] custom
        </span>
      </div>
      <div class="card-body" v-show="open"><div class="d-flex flex-column gap-3">
        <div class="btn-group btn-group-sm align-self-start" role="tablist">
            <button v-for="(k, key) in KINDS" :key="key" type="button" role="tab"
                    class="btn" :class="kind === key ? 'btn-secondary' : 'btn-outline-secondary'"
                    :aria-selected="kind === key" @click="kind = key">
                <i class="fas me-1" :class="key === 'tag' ? 'fa-tags' : 'fa-earth-europe'"></i>[[ k.label ]]
            </button>
        </div>

        <div v-if="load_failed" class="text-center py-4 text-body-secondary small">
            <i class="fas fa-triangle-exclamation me-2"></i>The tag browser could not be loaded.
        </div>
        <!-- Owned by the MISP browser: no Vue child in here, or Vue re-patches under it. -->
        <div class="ifb-accented" ref="host"></div>

        <div class="d-flex justify-content-end">
            <div class="btn-group btn-group-sm" role="group" aria-label="Selected tags view">
                <button type="button" class="btn" :class="view === 'context' ? 'btn-secondary' : 'btn-outline-secondary'"
                        :aria-pressed="view === 'context'" @click="set_view('context')" title="MISP context view">
                    <i class="fa-solid fa-layer-group me-1"></i>Context
                </button>
                <button type="button" class="btn" :class="view === 'compact' ? 'btn-secondary' : 'btn-outline-secondary'"
                        :aria-pressed="view === 'compact'" @click="set_view('compact')" title="Compact view, as in the indexes">
                    <i class="fa-solid fa-grip-lines me-1"></i>Compact
                </button>
            </div>
        </div>

        <div>
            <div class="mte-head">
                <i class="fas fa-tags"></i> Tags
                <span class="fw-normal text-body-secondary" v-if="selected_tags.length">([[ selected_tags.length ]])</span>
            </div>
            <div v-if="view === 'context'" class="d-flex flex-wrap" ref="tag_list"></div>
            <div v-else class="d-flex flex-wrap gap-1">
                <span v-for="t in selected_tags" :key="t.name" class="mte-compact" @click="reveal('tag', t.name)" title="Show where it lives">
                    <tag_badge kind="taxonomy" :label="t.name" :color="t.color" :title="t.description || t.name"></tag_badge>
                    <button type="button" class="mte-x" aria-label="Remove" title="Remove" @click.stop="remove_tag(t.name)">&times;</button>
                </span>
            </div>
            <div class="text-muted small fst-italic" v-if="!selected_tags.length">No tags selected.</div>
        </div>

        <div>
            <div class="mte-head">
                <i class="fas fa-earth-europe"></i> Galaxy clusters
                <span class="fw-normal text-body-secondary" v-if="selected_clusters.length">([[ selected_clusters.length ]])</span>
            </div>
            <div v-if="view === 'context'" class="d-flex flex-wrap" ref="cluster_list"></div>
            <div v-else class="d-flex flex-wrap gap-1">
                <span v-for="c in selected_clusters" :key="c.tag" class="mte-compact" @click="reveal('galaxy', c.tag)" title="Show where it lives">
                    <tag_badge kind="cluster" :label="c.tag" :icon-name="c.icon" :title="c.description || c.tag" :meta="c.meta || ''"></tag_badge>
                    <button type="button" class="mte-x" aria-label="Remove" title="Remove" @click.stop="remove_cluster(c.tag)">&times;</button>
                </span>
            </div>
            <div class="text-muted small fst-italic" v-if="!selected_clusters.length">No clusters selected.</div>
        </div>

        <div>
            <div class="mte-head">
                <i class="fas fa-hashtag"></i> Custom tags
                <span class="fw-normal text-body-secondary" v-if="selected_custom_names.length">([[ selected_custom_names.length ]])</span>
            </div>
            <div class="d-flex flex-wrap gap-1">
                <span v-for="t in selected_custom_tags" :key="t.name" class="mte-compact" @click="reveal('tag', t.name)" title="Show where it lives">
                    <tag_badge kind="custom" :label="t.name" :color="t.color" :icon-class="t.icon"></tag_badge>
                    <button type="button" class="mte-x" aria-label="Remove" title="Remove" @click.stop="remove_custom(t.name)">&times;</button>
                </span>
            </div>
            <div class="text-muted small fst-italic" v-if="!selected_custom_names.length">No custom tags selected.</div>
        </div>
      </div></div>
    </div>
    `
}
