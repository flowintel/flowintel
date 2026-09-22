import { display_toast } from '../toaster.js'
import picker_pane from '/static/js/components/picker_pane.js'
import scoped_tag_picker from '/static/js/components/scoped_tag_picker.js'
const { ref, computed } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: { type_object: String, object_id: Number },
    emits: ['st', 'sc', 'sct', 'sg', "delete_st", "delete_sc", "delete_sg", "delete_sct"],
    components: { picker_pane, scoped_tag_picker },
    setup(props, { emit }) {
        const taxonomies = ref([])
        const galaxies = ref([])
        const tags_list = ref({})
        const cluster_list = ref({})
        const custom_tags = ref([])

        const selected_taxo = ref([])
        const selected_tags = ref([])
        const selected_galaxies = ref([])
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

        async function fetch_tags(s_taxo) {
            loading_tags.value = true
            tags_list.value = {}
            const res = await fetch("/case/get_tags?taxonomies=" + JSON.stringify(s_taxo))
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                tags_list.value = loc["tags"]
            }
            loading_tags.value = false
        }

        async function fetch_cluster(s_galaxies) {
            loading_clusters.value = true
            cluster_list.value = {}
            const res = await fetch("/case/get_clusters?galaxies=" + JSON.stringify(s_galaxies))
            if (await res.status == 400) {
                display_toast(res)
            } else {
                let loc = await res.json()
                cluster_list.value = loc["clusters"]
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
                selected_taxo.value = loc["taxonomies"]

                emit('st', loc["tags"])
            }

            if (selected_taxo.value.length > 0) {
                fetch_tags([...selected_taxo.value])
            }
        }
        fetch_taxonomies_case_task()

        async function fetch_galaxies_case_task() {
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
                selected_galaxies.value = loc["galaxies"]
                emit('sc', loc["clusters"])
                emit('sg', loc["galaxies"])
            }
            if (selected_galaxies.value.length > 0) {
                fetch_cluster(selected_galaxies.value.map(g => g.name))
            }
        }
        fetch_galaxies_case_task()

        async function fetch_custom_tags_case_task() {
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


        // ---- normalize backend data into the shape <picker_pane> expects ----
        // { id, label, color?, iconClass?, iconName?, title?, disabled?, group?, raw }

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

        const tag_items = computed(() => {
            const out = []
            for (const taxo in tags_list.value) {
                for (const tag of tags_list.value[taxo]) {
                    out.push({
                        id: tag.name,
                        label: tag.name,
                        color: tag.color,
                        title: tag.description,
                        group: taxo,
                        raw: tag
                    })
                }
            }
            return out
        })
        const selected_tag_ids = computed(() => selected_tags.value.map(t => t.name))

        const galaxy_items = computed(() => galaxies.value.map(galaxy => ({
            id: galaxy.uuid,
            label: galaxy.name,
            iconName: galaxy.icon,
            title: galaxy.description,
            raw: galaxy
        })))
        const selected_galaxy_ids = computed(() => selected_galaxies.value.map(g => g.uuid))

        const cluster_items = computed(() => {
            const out = []
            for (const galaxy in cluster_list.value) {
                for (const cluster of cluster_list.value[galaxy]) {
                    out.push({
                        id: cluster.uuid,
                        label: cluster.tag,
                        iconName: cluster.icon,
                        title: 'Description: ' + cluster.description + (cluster.meta ? ('\nMetadata: ' + cluster.meta) : ''),
                        group: galaxy,
                        raw: cluster
                    })
                }
            }
            return out
        })
        const selected_cluster_ids = computed(() => selected_clusters.value.map(c => c.uuid))


        // ---- toggle handlers: click an item to add it, click it again (in the
        // list or on its selected-summary badge) to remove it ----

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

        function toggle_taxo(item) {
            const taxo_name = item.raw
            const idx = selected_taxo.value.indexOf(taxo_name)
            if (idx > -1) {
                selected_taxo.value.splice(idx, 1)
            } else {
                selected_taxo.value.push(taxo_name)
            }
            fetch_tags([...selected_taxo.value])
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

        function toggle_galaxy(item) {
            const galaxy = item.raw
            const idx = selected_galaxies.value.findIndex(g => g.uuid === galaxy.uuid)
            if (idx > -1) {
                selected_galaxies.value.splice(idx, 1)
                emit("delete_sg", idx)
            } else {
                selected_galaxies.value.push(galaxy)
                emit("sg", galaxy)
            }
            fetch_cluster(selected_galaxies.value.map(g => g.name))
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
            selected_taxo,

            custom_tag_items,
            selected_custom_tag_ids,
            taxonomy_items,
            tag_items,
            selected_tag_ids,
            galaxy_items,
            selected_galaxy_ids,
            cluster_items,
            selected_cluster_ids,

            loading_tags,
            loading_clusters,

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
    <scoped_tag_picker
        namespace-title="Taxonomies"
        item-title="Tags"
        :namespaces="taxonomy_items"
        :items="tag_items"
        :selected-namespace-ids="selected_taxo"
        :selected-item-ids="selected_tag_ids"
        :loading-items="loading_tags"
        namespace-empty-text="No taxonomy found."
        item-empty-text="Select a taxonomy on the left."
        @toggle-namespace="toggle_taxo"
        @toggle-item="toggle_tag">
    </scoped_tag_picker>
    <hr>

    <h5>Galaxies:</h5>
    <scoped_tag_picker
        namespace-title="Galaxies"
        item-title="Clusters"
        :namespaces="galaxy_items"
        :items="cluster_items"
        :selected-namespace-ids="selected_galaxy_ids"
        :selected-item-ids="selected_cluster_ids"
        :loading-items="loading_clusters"
        namespace-empty-text="No galaxy found."
        item-empty-text="Select a galaxy on the left."
        @toggle-namespace="toggle_galaxy"
        @toggle-item="toggle_cluster">
    </scoped_tag_picker>
    `
}
