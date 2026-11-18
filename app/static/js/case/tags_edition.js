import { display_toast } from '../toaster.js'
import edition_select from '../components/misp_tag_editor.js'
import { getTextColor, mapIcon } from '/static/js/utils.js'
import tag_badge, { isMarking } from '/static/js/components/tag-badge.js'
import task_preview, { load_task_item } from './task_preview.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
const { ref, computed } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: {
        current_case: Object,
        type_object: String,
        can_edit: {
            type: Boolean,
            default: true
        }
    },
    components: {
        tag_badge,
        task_preview,
        edition_select
    },
    directives: { decorate: { mounted: (el, b) => b.value?.(el), updated: (el, b) => b.value?.(el) } },
    emits: ['open-task'],
    setup(props, { emit }) {
        const selected_tags = ref([])
        const selected_clusters = ref([])
        const selected_custom_tags = ref([])

        // Compact (MISP events index) or context (MISP event context) look, remembered per browser
        const TAG_VIEW_KEY = 'flowintel_case_tag_view'
        let saved_view = 'compact'
        try { saved_view = localStorage.getItem(TAG_VIEW_KEY) || 'compact' } catch (e) {}
        const tag_view = ref(saved_view === 'context' ? 'context' : 'compact')
        // Context view: drawn by MISP's own client renderer (static/js/misp-tag-chips.js,
        // copied from MISP webroot/js/tag-chips.js), so it is exactly MISP's event context.
        const icon_class = (name) => ((mapIcon(name) || '').match(/class="([^"]+)"/) || [])[1] || null
        // TLP / PAP go to the case meta strip (case_view.html); the panel lists the other tags
        // (only for a case: a case template has no meta strip, it keeps them here)
        const plain_tags = computed(() => (props.current_case.tags || []).filter(t => props.type_object !== 'case' || !isMarking(t.name, t.color)))
        const has_markings = computed(() => (props.current_case.tags || []).length > plain_tags.value.length)
        // The case's tasks add their tags to the context view, each chip prefixed by an origin badge
        // "#<task id>" (hover: the task's calendar card, click: opens it), coloured per task (MISP extension_origin.ctp:
        // ExtensionEventColour, hue 25 + i * 137).
        const task_tags = ref([])
        // Context view filter: every tag, only the case's own, or only the tasks'
        const ORIGIN_KEY = 'flowintel_case_tag_origin'
        let saved_origin = 'all'
        try { saved_origin = localStorage.getItem(ORIGIN_KEY) || 'all' } catch (e) {}
        const origin_filter = ref(['all', 'case', 'tasks'].includes(saved_origin) ? saved_origin : 'all')
        function set_origin_filter(v) {
            origin_filter.value = v
            try { localStorage.setItem(ORIGIN_KEY, v) } catch (e) {}
        }
        async function fetch_task_tags() {
            if (props.type_object !== 'case' || !props.current_case?.id) return
            try {
                const res = await fetch('/case/' + props.current_case.id + '/tasks_tags')
                if (res.ok) task_tags.value = (await res.json()).tasks || []
            } catch (e) {}
        }
        if (tag_view.value === 'context') fetch_task_tags()
        const origin_hue = (i) => (25 + i * 137) % 360

        // Every chip gets a synthetic id (data-tag-id) so the rendered DOM can be matched back to
        // its tag: hover card data + origin badge (decorate_misp_chips below).
        let chip_seq = 0
        const chip_info = new Map()
        function entry(kind, data, origins) {
            const id = ++chip_seq
            chip_info.set(id, { kind, data, origins })
            return id
        }
        // One row per tag: a tag on the case and / or on several tasks is shown once, MISP's chip on
        // the left, where it is set on the right ("Case", then one "#id" badge per task). Rows are
        // sorted by taxonomy / galaxy, a thin line between two of them.
        function section_rows(kind, own) {
            const key = (d) => (kind === 'clusters' ? d.tag : d.name) || ''
            const rows = new Map()
            for (const d of own) rows.set(key(d), { d, own: true, origins: [] })
            task_tags.value.forEach((task, i) => {
                let list = task[kind] || []
                if (kind === 'tags') list = list.filter(t => !isMarking(t.name, t.color))
                for (const d of list) {
                    if (!rows.has(key(d))) rows.set(key(d), { d, own: false, origins: [] })
                    rows.get(key(d)).origins.push({ id: task.id, title: task.title, completed: task.completed, hue: origin_hue(i) })
                }
            })
            const kind_of = { tags: 'taxonomy', clusters: 'cluster', custom_tags: 'custom' }[kind]
            const keep = ([, r]) => origin_filter.value === 'all' || (origin_filter.value === 'case' ? r.own : r.origins.length > 0)
            const out = [...rows.entries()].filter(keep).map(([k, r]) => {
                const d = r.d
                const id = entry(kind_of, d, r.origins)
                let html = '', group = '', label = ''
                if (!window.TagChips) html = ''
                else if (kind === 'clusters') {
                    group = (d.galaxy || '').toLowerCase()
                    label = d.galaxy || ''
                    
                    html = TagChips.cluster({ tag_id: id, value: d.name, galaxy: d.galaxy, iconClass: icon_class(d.icon), description: d.description }, {})
                } else {
                    group = kind === 'tags' ? (d.name.split(':')[0] || '').toLowerCase() : ''
                    label = kind === 'tags' && d.name.includes(':') ? d.name.split(':')[0] : ''
                    html = TagChips.chip({ id, name: d.name, colour: d.color }, { searchUrl: '' })
                }
                return { key: k, html, group, label, own: r.own, origins: r.origins }
            })
            out.sort((a, b) => a.group.localeCompare(b.group) || a.key.localeCompare(b.key, undefined, { numeric: true }))
            // families: rows of one taxonomy / galaxy, kept together in one block
            const families = []
            for (const r of out) {
                const last = families[families.length - 1]
                if (last && last.group === r.group) last.rows.push(r)
                else families.push({ group: r.group, label: r.label, rows: [r] })
            }
            // a big family (or the only one of the section) spans the whole width, its tags
            // spread over the columns inside the block
            for (const f of families) f.wide = f.rows.length >= 6 || (families.length === 1 && f.rows.length > 1)
            families.count = out.length
            return families
        }
        const rows_tags = computed(() => section_rows('tags', plain_tags.value))
        const rows_clusters = computed(() => section_rows('clusters', props.current_case.clusters || []))
        const rows_custom = computed(() => section_rows('custom_tags', props.current_case.custom_tags || []))
        const has_linked = (kind) => task_tags.value.some(t => (t[kind] || []).length)

        // Hover a task badge: the case calendar's preview card of that task (task_preview.js)
        const task_card = ref(null)       // { item, pos }
        let task_card_timer = null
        function show_task_card(o, e) {
            clearTimeout(task_card_timer)
            const x0 = e.clientX, y0 = e.clientY
            task_card_timer = setTimeout(async () => {
                const item = await load_task_item(props.current_case.id, o.id)
                if (!item) return
                const w = 320, margin = 14
                let x = x0 + margin, y = y0 + margin
                if (x + w > window.innerWidth - 8) x = x0 - w - margin
                if (y + 260 > window.innerHeight) y = Math.max(8, y0 - 260 - margin)
                task_card.value = { item, pos: { x, y } }
            }, 180)
        }
        function hide_task_card() {
            clearTimeout(task_card_timer)
            task_card.value = null
        }
        function open_task(o) {
            hide_task_card()
            emit('open-task', o)
        }
        function focus_task_card(o, e) {
            const r = e.target.getBoundingClientRect()
            show_task_card(o, { clientX: r.left, clientY: r.bottom })
        }
        // After each render of a MISP chip: hover card attributes
        function decorate_misp_chips(root) {
            if (!root) return
            for (const chip of root.querySelectorAll('.hg-chip[data-tag-id]')) {
                if (chip.dataset.tgKind) continue
                const info = chip_info.get(parseInt(chip.dataset.tagId, 10))
                if (!info) continue
                const d = info.data
                chip.removeAttribute('title')
                chip.dataset.tgKind = info.kind
                chip.dataset.tgName = info.kind === 'cluster' ? d.tag : d.name
                if (d.description) chip.dataset.tgDesc = d.description
                if (d.meta) chip.dataset.tgMeta = d.meta
                if (d.color) chip.dataset.tgColor = d.color
                if (info.origins.length) chip.dataset.tgOrigin = info.origins.map(o => '#' + o.id).join(', ')
            }
        }

        function toggle_tag_view() {
            tag_view.value = tag_view.value === 'context' ? 'compact' : 'context'
            if (tag_view.value === 'context') fetch_task_tags()
            try { localStorage.setItem(TAG_VIEW_KEY, tag_view.value) } catch (e) {}
        }

        async function change_tags() {
            let tags_select = []
            let clusters_select = []
            let custom_select = []
            $.each(selected_clusters.value, function (i, v) {
                clusters_select.push(v.uuid)
            });
            $.each(selected_tags.value, function (i, v) {
                tags_select.push(v.name)
            });
            $.each(selected_custom_tags.value, function (i, v) {
                custom_select.push(v.name)
            });

            let url

            if (props.type_object == 'case')
                url = '/case/edit_tags/'
            else if (props.type_object == 'case_template')
                url = '/templating/case/edit_tags/'
            url += props.current_case.id

            const res_msg = await fetch(
                url, {
                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                method: "POST",
                body: JSON.stringify({
                    "tags_select": tags_select,
                    "clusters_select": clusters_select,
                    "custom_select": custom_select
                })
            }
            )

            if (await res_msg.status == 200) {
                props.current_case.tags = selected_tags.value
                props.current_case.clusters = selected_clusters.value
                props.current_case.custom_tags = selected_custom_tags.value
                if (props.type_object == 'case') {
                    touchCaseLastModif({ case: props.current_case })
                }

                var myModalEl = document.getElementById('ModalEditTags');
                var modal = bootstrap.Modal.getInstance(myModalEl)
                modal.hide();
            }
            await display_toast(res_msg)
        }


        return {
            getTextColor,
            mapIcon,
            selected_tags,
            selected_clusters,
            selected_custom_tags,
            tag_view,
            toggle_tag_view,
            origin_filter,
            set_origin_filter,
            rows_tags,
            rows_clusters,
            rows_custom,
            open_task,
            show_task_card,
            hide_task_card,
            focus_task_card,
            has_linked,
            decorate_misp_chips,
            task_card,
            plain_tags,
            has_markings,
            change_tags
        }
    },
    template: `
    <div class="case-tags-style">
        <div class="tg-panel-head">
            <h6 class="section-title mb-0">
                <i class="misp-icon misp-icon-galaxy misp-simple me-1" style="font-size:1.25em;"></i><template v-if="type_object !== 'case'">Tags, taxonomies and galaxies</template><template v-else-if="tag_view === 'context'">Tags in this case and its tasks</template><template v-else>Tags in this case</template>
            </h6>
            <div class="tg-panel-head-mid">
                <div v-if="tag_view === 'context' && type_object === 'case'" class="tg-origin-filter btn-group btn-group-sm" role="group" aria-label="Show tags set on">
                    <button v-for="o in [['all', 'All'], ['case', 'Case'], ['tasks', 'Tasks']]" :key="o[0]" type="button"
                            class="btn btn-outline-secondary" :class="{active: origin_filter === o[0]}" :aria-pressed="origin_filter === o[0]"
                            @click="set_origin_filter(o[0])">[[ o[1] ]]</button>
                </div>
            </div>
            <div class="tg-panel-head-actions">
                <button type="button" class="btn btn-outline-secondary btn-sm" @click="toggle_tag_view"
                        :title="tag_view === 'context' ? 'Compact view' : 'Context view'" :aria-pressed="tag_view === 'context'">
                    <i class="fa-solid fa-sm" :class="tag_view === 'context' ? 'fa-grip-lines' : 'fa-layer-group'"></i>
                </button>
                <button v-if="can_edit" type="button" class="btn btn-outline-primary btn-sm" data-bs-toggle="modal" data-bs-target="#ModalEditTags">
                    <i class="fa-solid fa-pen fa-sm"></i>
                </button>
            </div>
        </div>
        <hr class="fading-line-2 mt-2 mb-2">
        <div class="tg-sections" :class="{'is-context': tag_view === 'context'}">
            <section v-if="tag_view === 'context' ? rows_tags.count : plain_tags.length" class="tg-section">
                <h6 class="tg-section-title"><i class="misp-icon misp-icon-taxonomy misp-simple"></i>Taxonomies <small>[[ tag_view === 'context' ? rows_tags.count : plain_tags.length ]]</small></h6>
                <div v-if="tag_view === 'compact'" class="tg-row">
                    <tag_badge v-for="t in plain_tags" :key="t.id" kind="taxonomy" :label="t.name" :color="t.color" :title="t.description || t.name"></tag_badge>
                </div>
                <div v-else class="tg-ctx">
                    <div v-for="fam in rows_tags" :key="fam.group" class="tg-ctx-fam" :class="{'is-single': fam.rows.length === 1, 'is-wide': fam.wide}">
                    <div v-if="fam.label && fam.rows.length > 1" class="tg-ctx-fam-head">[[ fam.label ]] <small>[[ fam.rows.length ]]</small></div>
                    <div v-for="r in fam.rows" :key="r.key" class="tg-ctx-row">
                        <div class="tg-ctx-chip" v-decorate="decorate_misp_chips" v-html="r.html"></div>
                        <div class="tg-ctx-from">
                            <span v-if="r.own" class="tg-from-case" title="Set on the case">Case</span>
                            <button v-for="o in r.origins" :key="o.id" type="button" class="badge tg-origin" :style="{'--o-h': o.hue}"
                                    :aria-label="'Task #' + o.id + ': ' + o.title + ' (open it)'"
                                    @click.stop.prevent="open_task(o)" @mouseenter="show_task_card(o, $event)" @mouseleave="hide_task_card"
                                    @focus="focus_task_card(o, $event)" @blur="hide_task_card"><i class="fa-solid fa-list-check"></i><span>#[[ o.id ]]</span></button>
                        </div>
                    </div>
                    </div>
                </div>
            </section>
            <section v-if="tag_view === 'context' ? rows_clusters.count : (current_case.clusters || []).length" class="tg-section">
                <h6 class="tg-section-title"><i class="misp-icon misp-icon-galaxy misp-simple"></i>Galaxies <small>[[ tag_view === 'context' ? rows_clusters.count : (current_case.clusters || []).length ]]</small></h6>
                <div v-if="tag_view === 'compact'" class="tg-row">
                    <tag_badge v-for="c in current_case.clusters" :key="c.id" kind="cluster" :label="c.tag" :icon-name="c.icon" :title="c.description || c.tag" :meta="c.meta || ''"></tag_badge>
                </div>
                <div v-else class="tg-ctx">
                    <div v-for="fam in rows_clusters" :key="fam.group" class="tg-ctx-fam" :class="{'is-single': fam.rows.length === 1, 'is-wide': fam.wide}">
                    <div v-if="fam.label && fam.rows.length > 1" class="tg-ctx-fam-head">[[ fam.label ]] <small>[[ fam.rows.length ]]</small></div>
                    <div v-for="r in fam.rows" :key="r.key" class="tg-ctx-row">
                        <div class="tg-ctx-chip" v-decorate="decorate_misp_chips" v-html="r.html"></div>
                        <div class="tg-ctx-from">
                            <span v-if="r.own" class="tg-from-case" title="Set on the case">Case</span>
                            <button v-for="o in r.origins" :key="o.id" type="button" class="badge tg-origin" :style="{'--o-h': o.hue}"
                                    :aria-label="'Task #' + o.id + ': ' + o.title + ' (open it)'"
                                    @click.stop.prevent="open_task(o)" @mouseenter="show_task_card(o, $event)" @mouseleave="hide_task_card"
                                    @focus="focus_task_card(o, $event)" @blur="hide_task_card"><i class="fa-solid fa-list-check"></i><span>#[[ o.id ]]</span></button>
                        </div>
                    </div>
                    </div>
                </div>
            </section>
            <section v-if="tag_view === 'context' ? rows_custom.count : (current_case.custom_tags || []).length" class="tg-section">
                <h6 class="tg-section-title"><i class="fa-solid fa-tags"></i>Custom tags <small>[[ tag_view === 'context' ? rows_custom.count : (current_case.custom_tags || []).length ]]</small></h6>
                <div v-if="tag_view === 'compact'" class="tg-row">
                    <tag_badge v-for="t in current_case.custom_tags" :key="t.id" kind="custom" :label="t.name" :color="t.color" :icon-class="t.icon"></tag_badge>
                </div>
                <div v-else class="tg-ctx">
                    <div v-for="fam in rows_custom" :key="fam.group" class="tg-ctx-fam" :class="{'is-single': fam.rows.length === 1, 'is-wide': fam.wide}">
                    <div v-if="fam.label && fam.rows.length > 1" class="tg-ctx-fam-head">[[ fam.label ]] <small>[[ fam.rows.length ]]</small></div>
                    <div v-for="r in fam.rows" :key="r.key" class="tg-ctx-row">
                        <div class="tg-ctx-chip" v-decorate="decorate_misp_chips" v-html="r.html"></div>
                        <div class="tg-ctx-from">
                            <span v-if="r.own" class="tg-from-case" title="Set on the case">Case</span>
                            <button v-for="o in r.origins" :key="o.id" type="button" class="badge tg-origin" :style="{'--o-h': o.hue}"
                                    :aria-label="'Task #' + o.id + ': ' + o.title + ' (open it)'"
                                    @click.stop.prevent="open_task(o)" @mouseenter="show_task_card(o, $event)" @mouseleave="hide_task_card"
                                    @focus="focus_task_card(o, $event)" @blur="hide_task_card"><i class="fa-solid fa-list-check"></i><span>#[[ o.id ]]</span></button>
                        </div>
                    </div>
                    </div>
                </div>
            </section>
            <task_preview v-if="task_card" :item="task_card.item" :pos="task_card.pos"></task_preview>
            <p v-if="tag_view === 'context' ? !(rows_tags.count || rows_clusters.count || rows_custom.count) : !plain_tags.length && !(current_case.clusters || []).length && !(current_case.custom_tags || []).length" class="tg-empty">
                <template v-if="tag_view === 'context' && origin_filter === 'case'">No tags set on the case itself</template>
                <template v-else-if="tag_view === 'context' && origin_filter === 'tasks'">No tags set on its tasks</template>
                <template v-else>No tags</template><template v-if="has_markings"> (TLP / PAP shown at the top of the case)</template>
            </p>
        </div>
    </div>
    

    <!-- Modal -->
    <div v-if="can_edit" class="modal fade" id="ModalEditTags" tabindex="-1" aria-labelledby="ModalEditTags" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="exampleModalLabel">Edit tags, taxonomies and galaxies</h1>
                    <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
                    <edition_select 
                        :type_object="type_object"
                        :object_id="current_case.id"
                        @st="(msg) => selected_tags=selected_tags.concat(msg)"
                        @sc="(msg) => selected_clusters=selected_clusters.concat(msg)"
                        @sct="(msg) => selected_custom_tags=selected_custom_tags.concat(msg)"
                        @delete_st="(msg) => selected_tags.splice(msg, 1)"
                        @delete_sc="(msg) => selected_clusters.splice(msg, 1)"
                        @delete_sct="(msg) => selected_custom_tags.splice(msg, 1)"
                    >
                    </edition_select>
                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                    <button type="button" class="btn btn-primary" @click="change_tags()">Save changes</button>
                </div>
            </div>
        </div>
    </div>
    `
}
