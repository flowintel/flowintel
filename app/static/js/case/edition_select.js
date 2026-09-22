import { display_toast } from '../toaster.js'
import picker_pane from '/static/js/components/picker_pane.js'
import namespace_accordion from '/static/js/components/namespace_accordion.js'
const { ref, computed } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: { type_object: String, object_id: Number },
    emits: ['st', 'sc', 'sct', 'sg', "delete_st", "delete_sc", "delete_sg", "delete_sct"],
    components: { picker_pane, namespace_accordion },
    setup(props, { emit }) {
        const taxonomies = ref([])
        const galaxies = ref([])
        const tags_list = ref({})
        const cluster_list = ref({})
        const custom_tags = ref([])

        // Taxonomies have no standalone "marker" concept (only the tags picked
        // inside them are ever persisted) so browsing them is a pure, single,
        // collapsible UI concern: at most one taxonomy expanded at a time.
        const expanded_taxo = ref(null)

        // Galaxies DO have a standalone marker concept: a galaxy can be tagged
        // on a task even with no cluster picked from it (see TaskCore.edit_task_core
        // / Task_Galaxy, driven by the 'sg'/'delete_sg' events some consumers of
        // this component still listen for — e.g. edit_task.html). So here,
        // "expanding" a galaxy IS "selecting" it, same as the pre-refactor
        // select2 behaviour, and several galaxies can be expanded/selected at once.
        const selected_galaxies = ref([])

        const selected_tags = ref([])
        const selected_clusters = ref([])
        const selected_custom_tags = ref([])

        const loading_tags = ref(false)
        const loading_clusters = ref(false)

        async function fetch_taxonomies() {
            const res = await fetch("/case/get_taxonomies")
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                taxonomies.value = loc["taxonomies"]
            }
        }
        fetch_taxonomies()

        async function fetch_galaxies() {
            const res = await fetch("/case/get_galaxies")
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                galaxies.value = loc["galaxies"]
            }
        }
        fetch_galaxies()

        async function fetch_tags(taxo_name) {
            loading_tags.value = true
            tags_list.value = {}
            const res = await fetch("/case/get_tags?taxonomies=" + JSON.stringify([taxo_name]))
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                tags_list.value = loc["tags"]
            }
            loading_tags.value = false
        }

        async function fetch_clusters() {
            loading_clusters.value = true
            cluster_list.value = {}
            const galaxy_names = selected_galaxies.value.map(g => g.name)
            if (galaxy_names.length) {
                const res = await fetch("/case/get_clusters?galaxies=" + JSON.stringify(galaxy_names))
                if (await res.status == 400) {
                    display_toast(res)
                } else {
                    let loc = await res.json()
                    cluster_list.value = loc["clusters"]
                }
            }
            loading_clusters.value = false
        }

        async function fetch_custom_tags() {
            const res = await fetch("/custom_tags/list")
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                custom_tags.value = loc
            }
        }
        fetch_custom_tags()


        async function fetch_taxonomies_case_task() {
            // No object yet (creation form) — nothing to preload.
            if (!props.object_id) return
            let url

            if (props.type_object == "case") {
                url = "/case/get_taxonomies_case/" + props.object_id
            }
            else if (props.type_object == "task") {
                url = "/case/get_taxonomies_task/" + props.object_id
            }
            else if (props.type_object == "case_template") {
                url = "/templating/get_taxonomies_case/" + props.object_id
            }
            else if (props.type_object == "task_template") {
                url = "/templating/get_taxonomies_task/" + props.object_id
            }

            const res = await fetch(url)
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                selected_tags.value = loc["tags"]
                emit('st', loc["tags"])
            }
        }
        fetch_taxonomies_case_task()

        async function fetch_galaxies_case_task() {
            if (!props.object_id) return
            let url
            if (props.type_object == "case") {
                url = "/case/get_galaxies_case/" + props.object_id
            }
            else if (props.type_object == "task") {
                url = "/case/get_galaxies_task/" + props.object_id
            }
            else if (props.type_object == "case_template") {
                url = "/templating/get_galaxies_case/" + props.object_id
            }
            else if (props.type_object == "task_template") {
                url = "/templating/get_galaxies_task/" + props.object_id
            }

            const res = await fetch(url)
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                selected_clusters.value = loc["clusters"]
                emit('sc', loc["clusters"])
                // Note: galaxy *markers* (as opposed to the clusters picked
                // inside them) aren't returned by this endpoint, so we don't
                // pre-populate selected_galaxies/emit 'sg' here, matching the
                // pre-refactor behaviour.
            }
        }
        fetch_galaxies_case_task()

        async function fetch_custom_tags_case_task() {
            if (!props.object_id) return
            let url

            if (props.type_object == "case") {
                url = "/case/get_custom_tags_case/" + props.object_id
            }
            else if (props.type_object == "task") {
                url = "/case/get_custom_tags_task/" + props.object_id
            }
            else if (props.type_object == "case_template") {
                url = "/templating/get_custom_tags_case/" + props.object_id
            }
            else if (props.type_object == "task_template") {
                url = "/templating/get_custom_tags_task/" + props.object_id
            }

            const res = await fetch(url)
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                selected_custom_tags.value = loc["custom_tags"]
                emit('sct', loc["custom_tags"])
            }
        }
        fetch_custom_tags_case_task()


        // ---- normalize backend data into the shape the picker components expect ----
        // { id, label, color?, iconClass?, iconName?, title?, disabled?, group?, raw }

        function to_tag_display(tag, group) {
            return { id: tag.name, label: tag.name, color: tag.color, title: tag.description, group: group, raw: tag }
        }
        function to_cluster_display(cluster, group) {
            return {
                id: cluster.uuid,
                label: cluster.tag,
                iconName: cluster.icon,
                title: 'Description: ' + cluster.description + (cluster.meta ? ('\nMetadata: ' + cluster.meta) : ''),
                group: group,
                raw: cluster
            }
        }

        const custom_tag_items = computed(() => custom_tags.value.map(tag => ({
            id: tag.name,
            label: tag.name,
            color: tag.color,
            iconClass: tag.icon,
            disabled: !tag.is_active,
            raw: tag
        })))
        const selected_custom_tag_ids = computed(() => selected_custom_tags.value.map(t => t.name))

        const taxonomy_items = computed(() => taxonomies.value.map(taxo => ({
            id: taxo,
            label: taxo,
            raw: taxo
        })))

        // tags_list only ever holds the (single) currently-expanded taxonomy's tags
        const tag_items = computed(() => {
            const out = []
            for (const taxo in tags_list.value) {
                for (const tag of tags_list.value[taxo]) out.push(to_tag_display(tag, taxo))
            }
            return out
        })
        const selected_tag_ids = computed(() => selected_tags.value.map(t => t.name))
        const selected_tag_display_items = computed(() => selected_tags.value.map(t => to_tag_display(t)))

        const galaxy_items = computed(() => galaxies.value.map(galaxy => ({
            id: galaxy.uuid,
            label: galaxy.name,
            iconName: galaxy.icon,
            title: galaxy.description,
            raw: galaxy
        })))
        const expanded_galaxy_ids = computed(() => selected_galaxies.value.map(g => g.uuid))

        // cluster_list can hold entries for several expanded galaxies at once
        const cluster_items = computed(() => {
            const out = []
            for (const galaxy in cluster_list.value) {
                for (const cluster of cluster_list.value[galaxy]) out.push(to_cluster_display(cluster, galaxy))
            }
            return out
        })
        const selected_cluster_ids = computed(() => selected_clusters.value.map(c => c.uuid))
        const selected_cluster_display_items = computed(() => selected_clusters.value.map(c => to_cluster_display(c)))


        // ---- search-driven auto-expand: typing/pasting a full tag jumps
        // straight to its namespace (see resolveNamespaceId in namespace_accordion.js) ----

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
            // Galaxy cluster tags always look like: misp-galaxy:<galaxy-type>="<value>"
            const m = query.match(/^misp-galaxy:([^=]+)=/i)
            if (!m) return null
            const type_query = m[1].toLowerCase()
            const galaxy = galaxies.value.find(g => (g.type || '').toLowerCase() === type_query)
            return galaxy ? galaxy.uuid : null
        }

        // When a namespace is opened, pre-fill the search bar with its prefix
        // so typing straight away narrows down within it.
        function taxo_search_prefix(ns) {
            return ns.raw + ':'
        }
        function galaxy_search_prefix(ns) {
            return 'misp-galaxy:' + (ns.raw.type || '') + '='
        }


        // ---- toggle handlers ----

        function toggle_custom_tag(item) {
            const tag = item.raw
            const idx = selected_custom_tags.value.findIndex(t => t.name === tag.name)
            if (idx > -1) {
                selected_custom_tags.value.splice(idx, 1)
                emit("delete_sct", idx)
            } else {
                selected_custom_tags.value.push(tag)
                emit("sct", tag)
            }
        }

        function toggle_taxo(ns) {
            const taxo_name = ns.raw
            if (expanded_taxo.value === taxo_name) {
                expanded_taxo.value = null
                tags_list.value = {}
            } else {
                expanded_taxo.value = taxo_name
                fetch_tags(taxo_name)
            }
        }

        function toggle_tag(item) {
            const tag = item.raw
            const idx = selected_tags.value.findIndex(t => t.name === tag.name)
            if (idx > -1) {
                selected_tags.value.splice(idx, 1)
                emit("delete_st", idx)
            } else {
                selected_tags.value.push(tag)
                emit("st", tag)
            }
        }

        function toggle_galaxy(ns) {
            const galaxy = ns.raw
            const idx = selected_galaxies.value.findIndex(g => g.uuid === galaxy.uuid)
            if (idx > -1) {
                selected_galaxies.value.splice(idx, 1)
                emit("delete_sg", idx)
            } else {
                selected_galaxies.value.push(galaxy)
                emit("sg", galaxy)
            }
            fetch_clusters()
        }

        function toggle_cluster(item) {
            const cluster = item.raw
            const idx = selected_clusters.value.findIndex(c => c.uuid === cluster.uuid)
            if (idx > -1) {
                selected_clusters.value.splice(idx, 1)
                emit("delete_sc", idx)
            } else {
                selected_clusters.value.push(cluster)
                emit("sc", cluster)
            }
        }

        return {
            expanded_taxo,
            expanded_galaxy_ids,

            custom_tag_items,
            selected_custom_tag_ids,
            taxonomy_items,
            tag_items,
            selected_tag_ids,
            selected_tag_display_items,
            galaxy_items,
            cluster_items,
            selected_cluster_ids,
            selected_cluster_display_items,

            loading_tags,
            loading_clusters,

            resolve_taxo_for_query,
            resolve_galaxy_for_query,
            taxo_search_prefix,
            galaxy_search_prefix,

            toggle_custom_tag,
            toggle_taxo,
            toggle_tag,
            toggle_galaxy,
            toggle_cluster,
        }
    },
    template: `
    <picker_pane
        title="Custom tags"
        :items="custom_tag_items"
        :selected-ids="selected_custom_tag_ids"
        empty-text="No custom tags defined."
        search-placeholder="Search custom tags..."
        @toggle="toggle_custom_tag">
    </picker_pane>
    <hr>

    <h5>Taxonomies:</h5>
    <namespace_accordion
        title="Taxonomies"
        :namespaces="taxonomy_items"
        :items="tag_items"
        :expanded-ids="expanded_taxo ? [expanded_taxo] : []"
        :selected-items="selected_tag_display_items"
        :selected-item-ids="selected_tag_ids"
        :loading-items="loading_tags"
        :resolve-namespace-id="resolve_taxo_for_query"
        :namespace-search-prefix="taxo_search_prefix"
        namespace-empty-text="No taxonomy found."
        item-empty-text="No tag in this taxonomy."
        no-selection-text="No tag selected yet."
        search-placeholder="Search taxonomies or tags..."
        @toggle-namespace="toggle_taxo"
        @toggle-item="toggle_tag">
    </namespace_accordion>
    <hr>

    <h5>Galaxies:</h5>
    <namespace_accordion
        title="Galaxies"
        :namespaces="galaxy_items"
        :items="cluster_items"
        :expanded-ids="expanded_galaxy_ids"
        :selected-items="selected_cluster_display_items"
        :selected-item-ids="selected_cluster_ids"
        :loading-items="loading_clusters"
        :resolve-namespace-id="resolve_galaxy_for_query"
        :namespace-search-prefix="galaxy_search_prefix"
        namespace-empty-text="No galaxy found."
        item-empty-text="No cluster in this galaxy."
        no-selection-text="No cluster selected yet."
        search-placeholder="Search galaxies or clusters..."
        @toggle-namespace="toggle_galaxy"
        @toggle-item="toggle_cluster">
    </namespace_accordion>
    `
}
