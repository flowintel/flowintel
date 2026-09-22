/**
 * tag_filter.js — self-contained "filter by taxonomies/tags, galaxies/clusters,
 * custom tags" panel. Wraps <namespace_accordion> (x2) + <picker_pane> plus all
 * the fetch/normalize/toggle plumbing, so callers (case list, task list, ...)
 * just drop it in and react to @change instead of re-implementing it.
 *
 * Only browses/offers items actually applied to at least one object in the
 * given `scope` (via the backend's get_used_* endpoints) rather than every
 * taxonomy/galaxy/tag that exists in MISP's vocab — there's no point making
 * someone hunt through hundreds of unused tags to filter a handful of cases.
 *
 * Props:
 *   scope   String  'case' | 'task' — picks which get_used_* endpoints to hit
 *
 * Emits:
 *   change({ tags, taxonomies, clusters, galaxies, custom_tags, or_and_taxo, or_and_galaxies })
 *     fired whenever the actual filter changes (never on pure browse/expand —
 *     collapsing a namespace never touches the filter, see namespace_accordion.js).
 *     All of tags/taxonomies/clusters/galaxies/custom_tags are arrays of names.
 *
 * Exposed method (via template ref): has_active_filters() — for callers that
 * want to reflect filter state in a button/badge outside this component.
 */
import { display_toast } from '../toaster.js'
import picker_pane from './picker_pane.js'
import namespace_accordion from './namespace_accordion.js'
const { ref, computed, watch } = Vue

const SCOPE_URLS = {
    case: {
        taxonomies: '/case/get_used_taxonomies',
        tags: '/case/get_used_tags',
        galaxies: '/case/get_used_galaxies',
        clusters: '/case/get_used_clusters',
        custom_tags: '/case/get_used_custom_tags',
    },
    task: {
        taxonomies: '/case/get_used_taxonomies_task',
        tags: '/case/get_used_tags_task',
        galaxies: '/case/get_used_galaxies_task',
        clusters: '/case/get_used_clusters_task',
        custom_tags: '/case/get_used_custom_tags_task',
    },
}

export default {
    name: 'TagFilter',
    delimiters: ['[[', ']]'],
    components: { picker_pane, namespace_accordion },
    props: {
        scope: { type: String, default: 'case' },
    },
    emits: ['change'],
    setup(props, { emit, expose }) {
        const urls = SCOPE_URLS[props.scope] || SCOPE_URLS.case

        const taxonomies = ref([])
        const tags_list = ref({})
        const expanded_taxo = ref([])
        const selected_tags = ref([])
        const loading_tags = ref(false)

        const galaxies = ref([])
        const cluster_list = ref({})
        const expanded_galaxies = ref([])
        const selected_clusters = ref([])
        const loading_clusters = ref(false)

        const custom_tags = ref([])
        const selected_custom_tags = ref([])

        const or_and_taxo = ref(false)
        const or_and_galaxies = ref(false)

        // Persistent name -> tag/cluster data maps, merged in (never cleared)
        // as tags/clusters get fetched, so a selected item's color/icon/galaxy
        // stay resolvable even after its taxonomy/galaxy is collapsed and
        // re-fetched out of tags_list/cluster_list.
        const tag_data_map = ref({})
        const cluster_data_map = ref({})

        // The taxonomies/galaxies filter dimensions are derived from what's
        // actually selected, not from what's expanded (browsing is purely visual).
        const selected_taxo = computed(() => [...new Set(selected_tags.value.map(name => name.split(':')[0]))])
        const selected_galaxies = computed(() => {
            const ids = new Set(selected_clusters.value.map(name => cluster_data_map.value[name]?.galaxy_id).filter(id => id != null))
            return galaxies.value.filter(g => ids.has(g.id)).map(g => g.name)
        })

        const has_active_filters = computed(() =>
            selected_tags.value.length > 0 ||
            selected_clusters.value.length > 0 ||
            selected_custom_tags.value.length > 0
        )

        function emit_change() {
            emit('change', {
                tags: [...selected_tags.value],
                taxonomies: [...selected_taxo.value],
                clusters: [...selected_clusters.value],
                galaxies: [...selected_galaxies.value],
                custom_tags: [...selected_custom_tags.value],
                or_and_taxo: or_and_taxo.value,
                or_and_galaxies: or_and_galaxies.value,
            })
        }

        async function fetch_taxonomies(){
            const res = await fetch(urls.taxonomies)
            if (await res.status == 400) display_toast(res)
            else taxonomies.value = (await res.json())["taxonomies"]
        }
        fetch_taxonomies()

        async function fetch_galaxies(){
            const res = await fetch(urls.galaxies)
            if (await res.status == 400) display_toast(res)
            else galaxies.value = (await res.json())["galaxies"]
        }
        fetch_galaxies()

        async function fetch_custom_tags(){
            const res = await fetch(urls.custom_tags)
            if (await res.status == 400) display_toast(res)
            else custom_tags.value = await res.json()
        }
        fetch_custom_tags()

        async function fetch_tags(){
            loading_tags.value = true
            tags_list.value = {}
            if (expanded_taxo.value.length){
                const res = await fetch(urls.tags + "?taxonomies=" + JSON.stringify(expanded_taxo.value))
                if (await res.status == 400) {
                    display_toast(res)
                } else {
                    tags_list.value = (await res.json())["tags"]
                    for (const taxo in tags_list.value){
                        for (const tag of tags_list.value[taxo]) tag_data_map.value[tag.name] = tag
                    }
                }
            }
            loading_tags.value = false
        }

        async function fetch_cluster(){
            loading_clusters.value = true
            cluster_list.value = {}
            if (expanded_galaxies.value.length){
                const res = await fetch(urls.clusters + "?galaxies=" + JSON.stringify(expanded_galaxies.value))
                if (await res.status == 400) {
                    display_toast(res)
                } else {
                    cluster_list.value = (await res.json())["clusters"]
                    for (const galaxy in cluster_list.value){
                        for (const cluster of cluster_list.value[galaxy]) cluster_data_map.value[cluster.name] = cluster
                    }
                }
            }
            loading_clusters.value = false
        }

        // ---- normalize backend data for <namespace_accordion>/<picker_pane> ----
        // (identifiers are .name everywhere, matching what the sort/filter
        // endpoints expect for their tags/taxonomies/galaxies/clusters/custom_tags params)

        const taxonomy_items = computed(() => taxonomies.value.map(taxo => ({ id: taxo, label: taxo, raw: taxo })))
        const tag_items = computed(() => {
            const out = []
            for (const taxo in tags_list.value){
                for (const tag of tags_list.value[taxo]){
                    out.push({ id: tag.name, label: tag.name, color: tag.color, title: tag.description, group: taxo, raw: tag })
                }
            }
            return out
        })
        const selected_tag_display_items = computed(() =>
            selected_tags.value.map(name => {
                const tag = tag_data_map.value[name]
                return tag ? { id: name, label: name, color: tag.color, title: tag.description } : { id: name, label: name }
            })
        )

        const galaxy_items = computed(() => galaxies.value.map(galaxy => ({
            id: galaxy.name, label: galaxy.name, iconName: galaxy.icon, title: galaxy.description, raw: galaxy
        })))
        const cluster_items = computed(() => {
            const out = []
            for (const galaxy in cluster_list.value){
                for (const cluster of cluster_list.value[galaxy]){
                    out.push({
                        id: cluster.name, label: cluster.tag, iconName: cluster.icon,
                        title: 'Description: ' + cluster.description, group: galaxy, raw: cluster
                    })
                }
            }
            return out
        })
        const selected_cluster_display_items = computed(() =>
            selected_clusters.value.map(name => {
                const cluster = cluster_data_map.value[name]
                return cluster
                    ? { id: name, label: cluster.tag, iconName: cluster.icon, title: 'Description: ' + cluster.description }
                    : { id: name, label: name }
            })
        )

        const custom_tag_items = computed(() => custom_tags.value.map(tag => ({
            id: tag.name, label: tag.name, color: tag.color, iconClass: tag.icon, raw: tag
        })))

        // ---- search-driven auto-expand ----

        function resolve_taxo_for_query(query) {
            // Case-insensitive ("DML:", "dml:", "Dml:" are all the same
            // taxonomy) — but return the taxonomy's real stored casing, since
            // that's what taxonomy_items' id actually is.
            const colon_idx = query.indexOf(':')
            if (colon_idx === -1) return null
            const prefix = query.slice(0, colon_idx).toLowerCase()
            const match = taxonomies.value.find(t => t.toLowerCase() === prefix)
            return match || null
        }
        function resolve_galaxy_for_query(query) {
            const m = query.match(/^misp-galaxy:([^=]+)=/i)
            if (!m) return null
            const type_query = m[1].toLowerCase()
            const galaxy = galaxies.value.find(g => (g.type || '').toLowerCase() === type_query)
            return galaxy ? galaxy.name : null
        }
        function taxo_search_prefix(ns) { return ns.raw + ':' }
        function galaxy_search_prefix(ns) { return 'misp-galaxy:' + (ns.raw.type || '') + '=' }

        // ---- toggle handlers ----

        function toggle_taxo(ns){
            // Pure browse toggle — never touches selected_tags.
            const idx = expanded_taxo.value.indexOf(ns.raw)
            if (idx > -1) expanded_taxo.value.splice(idx, 1)
            else expanded_taxo.value.push(ns.raw)
            fetch_tags()
        }
        function toggle_tag(item){
            const idx = selected_tags.value.indexOf(item.id)
            if (idx > -1) selected_tags.value.splice(idx, 1)
            else selected_tags.value.push(item.id)
            emit_change()
        }
        function toggle_galaxy(ns){
            // Pure browse toggle — never touches selected_clusters.
            const idx = expanded_galaxies.value.indexOf(ns.raw.name)
            if (idx > -1) expanded_galaxies.value.splice(idx, 1)
            else expanded_galaxies.value.push(ns.raw.name)
            fetch_cluster()
        }
        function toggle_cluster(item){
            const idx = selected_clusters.value.indexOf(item.id)
            if (idx > -1) selected_clusters.value.splice(idx, 1)
            else selected_clusters.value.push(item.id)
            emit_change()
        }
        function toggle_custom_tag(item){
            const idx = selected_custom_tags.value.indexOf(item.id)
            if (idx > -1) selected_custom_tags.value.splice(idx, 1)
            else selected_custom_tags.value.push(item.id)
            emit_change()
        }
        function toggle_or_and_taxo(){
            or_and_taxo.value = !or_and_taxo.value
            emit_change()
        }
        function toggle_or_and_galaxies(){
            or_and_galaxies.value = !or_and_galaxies.value
            emit_change()
        }

        expose({ has_active_filters })

        return {
            taxonomy_items, tag_items, expanded_taxo, selected_tags, selected_tag_display_items, loading_tags,
            galaxy_items, cluster_items, expanded_galaxies, selected_clusters, selected_cluster_display_items, loading_clusters,
            custom_tag_items, selected_custom_tags,
            resolve_taxo_for_query, resolve_galaxy_for_query, taxo_search_prefix, galaxy_search_prefix,
            toggle_taxo, toggle_tag, toggle_galaxy, toggle_cluster, toggle_custom_tag,
            toggle_or_and_taxo, toggle_or_and_galaxies,
        }
    },
    template: `
    <div>
        <div><i class="misp-icon misp-icon-taxonomy misp-simple me-1"></i>Taxonomies:</div>
        <div class="d-flex w-100 justify-content-center">
            <div style="display:flex">
                <span style="margin-right: 10px">OR</span>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch" @click="toggle_or_and_taxo()">
                    <label class="form-check-label">AND</label>
                </div>
            </div>
        </div>
        <namespace_accordion
            title="Taxonomies"
            :namespaces="taxonomy_items"
            :items="tag_items"
            :expanded-ids="expanded_taxo"
            :selected-items="selected_tag_display_items"
            :selected-item-ids="selected_tags"
            :loading-items="loading_tags"
            :resolve-namespace-id="resolve_taxo_for_query"
            :namespace-search-prefix="taxo_search_prefix"
            namespace-empty-text="No taxonomy used on any case yet."
            item-empty-text="No tag in this taxonomy."
            no-selection-text="No taxonomy/tag filter applied."
            search-placeholder="Search taxonomies or tags..."
            @toggle-namespace="toggle_taxo"
            @toggle-item="toggle_tag">
        </namespace_accordion>
        <hr>

        <div><i class="misp-icon misp-icon-galaxy misp-simple me-1"></i>Galaxies:</div>
        <div class="d-flex w-100 justify-content-center">
            <div style="display:flex">
                <span style="margin-right: 10px">OR</span>
                <div class="form-check form-switch">
                    <input class="form-check-input" type="checkbox" role="switch" @click="toggle_or_and_galaxies()">
                    <label class="form-check-label">AND</label>
                </div>
            </div>
        </div>
        <namespace_accordion
            title="Galaxies"
            :namespaces="galaxy_items"
            :items="cluster_items"
            :expanded-ids="expanded_galaxies"
            :selected-items="selected_cluster_display_items"
            :selected-item-ids="selected_clusters"
            :loading-items="loading_clusters"
            :resolve-namespace-id="resolve_galaxy_for_query"
            :namespace-search-prefix="galaxy_search_prefix"
            namespace-empty-text="No galaxy used on any case yet."
            item-empty-text="No cluster in this galaxy."
            no-selection-text="No galaxy/cluster filter applied."
            search-placeholder="Search galaxies or clusters..."
            @toggle-namespace="toggle_galaxy"
            @toggle-item="toggle_cluster">
        </namespace_accordion>
        <hr>

        <div><i class="misp-icon misp-icon-tag misp-simple me-1"></i>Custom Tags:</div>
        <picker_pane
            title="Custom tags"
            :items="custom_tag_items"
            :selected-ids="selected_custom_tags"
            empty-text="No custom tag used on any case yet."
            search-placeholder="Search custom tags..."
            @toggle="toggle_custom_tag">
        </picker_pane>
    </div>
    `
}
