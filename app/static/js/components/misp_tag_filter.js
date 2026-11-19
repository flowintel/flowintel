// Tag / galaxy filter drawn exactly like MISP's (Overmind) index filter bar
// pickers: a button per kind opens MISP's own column browser
// (misp-index-filter-browser.js) as a floating panel. Click a value to
// include it, Exclude (or Shift+Enter) to exclude it, and "Any of / All of"
// in its tray once two are included. The filter applies when the panel closes.
//
// Same props, event and exposed method as tag_filter.js, so it drops in its
// place. In the change payload an excluded tag / cluster is "!name"
// (FilteringAbstract.split_excluded); "All of" sends or_and_* = false.
import { display_toast } from '../toaster.js'
import { BROWSER_STRINGS } from './misp_browser_strings.js'
import { loadBrowser } from './misp_tag_editor.js'
import tag_badge from './tag-badge.js'
const { ref, computed, onMounted, onBeforeUnmount } = Vue

const NOUNS = { case: 'Cases', task: 'Tasks', case_template: 'Templates', task_template: 'Templates' }

// The bar of index-filters.js is not here: closePicker() hands the new value
// to IndexFilters.load(btn, IndexFilters.urlWith(btn, changes)). This stand-in
// passes it back to the picker as an `ifb-apply` event.
function ensureIndexFilters() {
    if (window.IndexFilters) return
    window.IndexFilters = {
        urlWith: (btn, changes) => changes,
        load: (btn, changes) => {
            btn.dispatchEvent(new CustomEvent('ifb-apply', { detail: changes, bubbles: true }))
        },
    }
}

// "a|!b" or "a&b" (closePicker's serialize()) → [{value, exclude}], allOf
function parse(value) {
    if (!value) return { items: [], allOf: false }
    const allOf = value.includes('&') && !value.includes('|')
    const items = value.split(allOf ? '&' : '|').filter(Boolean).map(v =>
        v.startsWith('!') ? { value: v.slice(1), exclude: true } : { value: v, exclude: false })
    return { items, allOf }
}

export default {
    name: 'MispTagFilter',
    delimiters: ['[[', ']]'],
    props: {
        scope: { type: String, default: 'case' },
        caseId: { type: [Number, String], default: null },
    },
    components: { tag_badge },
    emits: ['change'],
    setup(props, { emit, expose }) {
        // A tag value with no "namespace:" is a custom tag (the browser's "Custom tags" scope).
        const is_custom = (v) => !String(v).includes(':')
        const bar = ref(null)
        const tag_picker = ref(null)
        const cluster_picker = ref(null)
        const ready = ref(false)

        // Picked values, as the browser keeps them: {value, label, style, exclude}
        const tags = ref([])
        const clusters = ref([])
        const tags_all_of = ref(false)
        const clusters_all_of = ref(false)
        // cluster tag → cluster (the backend filters clusters by name)
        const cluster_data = ref({})


        const strings = Object.assign({}, BROWSER_STRINGS, {
            matchAllTitle: (NOUNS[props.scope] || 'Items') + ' with every one of them',
            matchAnyTitle: (NOUNS[props.scope] || 'Items') + ' with at least one of them',
        })
        const bar_json = JSON.stringify({ browser: strings })

        // Only what is set on at least one object of the scope, as tag_filter.js offered.
        let used = '?used=' + encodeURIComponent(props.scope)
        if (props.scope === 'task' && props.caseId != null) used += '&case_id=' + encodeURIComponent(props.caseId)

        function picker_json(kind) {
            const isTag = kind === 'tag'
            return JSON.stringify({
                name: kind,
                label: isTag ? 'Tags' : 'Galaxy clusters',
                source: (isTag ? '/case/picker/tag_search' : '/case/picker/cluster_search') + used,
                sep: '|',
                allOfMode: true,
                allOf: isTag ? tags_all_of.value : clusters_all_of.value,
                selected: (isTag ? tags.value : clusters.value).map(s => Object.assign({}, s, { unresolved: false })),
                browser: isTag
                    ? { kind: 'tag', scopes: '/case/picker/tag_scopes' + used, tree: '/case/picker/tag_tree' + used }
                    : { kind: 'galaxy', scopes: '/case/picker/galaxy_scopes' + used },
            })
        }
        const tag_json = computed(() => picker_json('tag'))
        const cluster_json = computed(() => picker_json('galaxy'))

        function open(kind) {
            if (!ready.value) return
            window.IndexFilterBrowser.toggle(kind === 'tag' ? tag_picker.value : cluster_picker.value)
        }

        // ---- applying ----

        async function on_apply(e) {
            const changes = e.detail || {}
            const kind = Object.keys(changes)[0]
            if (!kind) return
            const { items, allOf } = parse(changes[kind])
            const names = kind === 'tag'
                ? { tags: items.map(i => i.value), custom_tags: items.map(i => i.value).filter(is_custom) }
                : { clusters: items.map(i => i.value) }
            let data = { tags: [], clusters: [] }
            if (items.length) {
                const res = await fetch('/case/picker/resolve?names=' + encodeURIComponent(JSON.stringify(names)))
                if (!res.ok) { display_toast(res); return }
                data = await res.json()
            }
            if (kind === 'tag') {
                const by = {}
                data.tags.concat(data.custom_tags || []).forEach(t => { by[t.name] = t })
                tags.value = items.map(i => ({
                    value: i.value, label: i.value, exclude: i.exclude,
                    style: { colour: by[i.value] ? by[i.value].color : null },
                    icon: by[i.value] ? by[i.value].icon : null,
                    desc: by[i.value] ? by[i.value].description : null,
                }))
                tags_all_of.value = allOf
            } else {
                data.clusters.forEach(c => { cluster_data.value[c.tag] = c })
                clusters.value = items.map(i => {
                    const c = cluster_data.value[i.value]
                    return {
                        value: i.value, label: c ? c.name : i.value, exclude: i.exclude,
                        style: { galaxy: c ? c.galaxy : null, icon: c && c.icon ? 'fas fa-' + c.icon : null },
                    }
                })
                clusters_all_of.value = allOf
            }
            emit_change()
        }

        function emit_change() {
            const taxo_tags = tags.value.filter(t => !is_custom(t.value))
            const custom = tags.value.filter(t => is_custom(t.value))
            const inc_tags = taxo_tags.filter(t => !t.exclude).map(t => t.value)
            const inc_clusters = clusters.value.filter(c => !c.exclude).map(c => cluster_data.value[c.value]).filter(Boolean)
            emit('change', {
                tags: taxo_tags.map(t => (t.exclude ? '!' : '') + t.value),
                taxonomies: [...new Set(inc_tags.map(n => n.split(':')[0]))],
                clusters: clusters.value.map(c => {
                    const d = cluster_data.value[c.value]
                    return (c.exclude ? '!' : '') + (d ? d.name : c.label)
                }),
                galaxies: [...new Set(inc_clusters.map(c => c.galaxy))],
                custom_tags: custom.map(t => (t.exclude ? '!' : '') + t.value),
                or_and_taxo: !tags_all_of.value,
                or_and_galaxies: !clusters_all_of.value,
            })
        }

        function remove(kind, value) {
            const list = kind === 'tag' ? tags : clusters
            list.value = list.value.filter(s => s.value !== value)
            emit_change()
        }

        function clear_all() {
            tags.value = []
            clusters.value = []
            emit_change()
        }

        const has_active_filters = computed(() =>
            tags.value.length > 0 || clusters.value.length > 0)
        expose({ has_active_filters: () => has_active_filters.value })

        // ---- setup ----

        onMounted(() => {
            ensureIndexFilters()
            bar.value.addEventListener('ifb-apply', on_apply)
            loadBrowser().then(() => { ready.value = true }, () => {})
        })
        onBeforeUnmount(() => {
            if (window.IndexFilterBrowser) window.IndexFilterBrowser.close(false)
        })

        function chip_title(s) { return (s.exclude ? 'not ' : '') + s.value }

        return {
            bar, tag_picker, cluster_picker, ready, bar_json, tag_json, cluster_json, open,
            tags, clusters, tags_all_of, clusters_all_of, remove, clear_all, chip_title,
            has_active_filters, is_custom, cluster_data,
        }
    },
    template: `
    <div class="misp-tag-filter card" ref="bar" :data-ifp-bar="bar_json">
      <div class="card-body d-flex flex-column gap-3">
        <div class="d-flex flex-wrap align-items-center gap-2">
            <div class="mtf-picker" ref="tag_picker" :data-ifp-picker="tag_json">
                <button type="button" class="ifp-btn btn btn-sm btn-outline-secondary" aria-haspopup="dialog"
                        :disabled="!ready" @click="open('tag')">
                    <i class="fas fa-tags me-1"></i>Tags
                    <span v-if="tags.length" class="badge text-bg-secondary ms-1">[[ tags.length ]]</span>
                    <i class="fas fa-chevron-down ms-1 small"></i>
                </button>
            </div>
            <div class="mtf-picker" ref="cluster_picker" :data-ifp-picker="cluster_json">
                <button type="button" class="ifp-btn btn btn-sm btn-outline-secondary" aria-haspopup="dialog"
                        :disabled="!ready" @click="open('galaxy')">
                    <i class="fas fa-earth-europe me-1"></i>Galaxies
                    <span v-if="clusters.length" class="badge text-bg-secondary ms-1">[[ clusters.length ]]</span>
                    <i class="fas fa-chevron-down ms-1 small"></i>
                </button>
            </div>
            <button v-if="has_active_filters" type="button" class="btn btn-sm btn-link ms-auto" @click="clear_all">Clear</button>
        </div>

        <div v-if="tags.length">
            <div class="mte-head"><i class="fas fa-tags"></i> Tags
                <span v-if="tags.filter(t => !t.exclude).length > 1" class="badge text-bg-light border fw-normal">[[ tags_all_of ? 'All of' : 'Any of' ]]</span>
            </div>
            <div class="d-flex flex-wrap gap-1">
                <span v-for="t in tags" :key="t.value" class="mtf-chip" :class="{ 'is-not': t.exclude }" :title="chip_title(t)">
                    <span v-if="t.exclude" class="mtf-not">not</span>
                    <tag_badge :kind="is_custom(t.value) ? 'custom' : 'taxonomy'" :label="t.value"
                               :color="t.style && t.style.colour || ''" :icon-class="t.icon || ''" :title="t.desc || t.value"></tag_badge>
                    <button type="button" class="mte-x" aria-label="Remove" title="Remove" @click="remove('tag', t.value)">&times;</button>
                </span>
            </div>
        </div>

        <div v-if="clusters.length">
            <div class="mte-head"><i class="fas fa-earth-europe"></i> Galaxy clusters
                <span v-if="clusters.filter(c => !c.exclude).length > 1" class="badge text-bg-light border fw-normal">[[ clusters_all_of ? 'All of' : 'Any of' ]]</span>
            </div>
            <div class="d-flex flex-wrap gap-1">
                <span v-for="c in clusters" :key="c.value" class="mtf-chip" :class="{ 'is-not': c.exclude }" :title="chip_title(c)">
                    <span v-if="c.exclude" class="mtf-not">not</span>
                    <tag_badge kind="cluster" :label="c.value" :icon-name="cluster_data[c.value] ? cluster_data[c.value].icon : ''"
                               :title="cluster_data[c.value] && cluster_data[c.value].description || c.value"
                               :meta="cluster_data[c.value] && cluster_data[c.value].meta || ''"></tag_badge>
                    <button type="button" class="mte-x" aria-label="Remove" title="Remove" @click="remove('galaxy', c.value)">&times;</button>
                </span>
            </div>
        </div>

      </div>
    </div>
    `
}
