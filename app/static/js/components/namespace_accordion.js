/**
 * namespace_accordion.js — compact single-column namespace picker.
 *
 * All namespaces are listed in one place; clicking one expands it in place
 * to show its items right below it. Several namespaces can be expanded at
 * once (the caller decides — pass a 1-element `expandedIds` array to force
 * single-expand, like an accordion, or let it grow to allow several open at
 * the same time).
 *
 * The "selected" summary at the top is driven by an explicit `selectedItems`
 * prop (already-normalized, full objects) instead of being derived from
 * `items` — `items` only ever holds whichever namespaces are expanded, so
 * deriving the summary from it would make previously-picked items vanish
 * the moment their namespace collapses. Selection must survive collapsing.
 *
 * Props:
 *   namespaces      Array  { id, label, raw }
 *   items           Array  { id, label, color?, iconClass?, iconName?, title?,
 *                            disabled?, group, raw } — group must match the
 *                            owning namespace's `label`. Only items for
 *                            expanded namespaces need to be present.
 *   expandedIds     Array  namespace ids currently expanded
 *   selectedItems   Array  already-normalized full selection, independent of
 *                          `items`/expand state (drives the top chips row)
 *   selectedItemIds Array  ids used to check/highlight rows inside `items`
 *   loadingItems    Boolean
 *   resolveNamespaceId(query) => id|null — optional. Lets the caller parse a
 *     pasted/typed full tag string (e.g. "tlp:amber" or a MISP galaxy tag
 *     like 'misp-galaxy:agent-threat-rules="..."') and point back at which
 *     namespace it belongs to, so that namespace auto-expands as the user
 *     types/pastes instead of requiring a manual click first.
 *
 * Emits: toggle-namespace(namespace), toggle-item(item)
 */
import tag_badge from './tag-badge.js'
const { computed, ref, watch } = Vue

export default {
    name: 'NamespaceAccordion',
    delimiters: ['[[', ']]'],
    components: { tag_badge },
    props: {
        title: { type: String, default: '' },
        namespaces: { type: Array, default: () => [] },
        items: { type: Array, default: () => [] },
        expandedIds: { type: Array, default: () => [] },
        selectedItems: { type: Array, default: () => [] },
        selectedItemIds: { type: Array, default: () => [] },
        loadingItems: { type: Boolean, default: false },
        namespaceEmptyText: { type: String, default: 'No namespace found.' },
        itemEmptyText: { type: String, default: 'No item in this namespace.' },
        noSelectionText: { type: String, default: 'None selected yet.' },
        searchPlaceholder: { type: String, default: 'Search...' },
        resolveNamespaceId: { type: Function, default: null },
    },
    emits: ['toggle-namespace', 'toggle-item'],
    setup(props, { emit }) {
        const query = ref('')

        const expanded_set = computed(() => new Set(props.expandedIds))
        const selected_set = computed(() => new Set(props.selectedItemIds))

        function is_expanded(ns) {
            return expanded_set.value.has(ns.id)
        }
        function is_item_selected(item) {
            return selected_set.value.has(item.id)
        }

        const filtered_namespaces = computed(() => {
            const q = query.value.trim().toLowerCase()
            if (!q) return props.namespaces
            return props.namespaces.filter(ns =>
                is_expanded(ns) || (ns.label || '').toLowerCase().includes(q)
            )
        })

        function items_for(ns) {
            const all = props.items.filter(item => item.group === ns.label)
            const q = query.value.trim().toLowerCase()
            if (!q) return all
            return all.filter(item =>
                (item.label || '').toLowerCase().includes(q) ||
                (item.title || '').toLowerCase().includes(q)
            )
        }

        // Typing/pasting a full tag (e.g. "tlp:amber", or a galaxy tag like
        // 'misp-galaxy:agent-threat-rules="..."') auto-expands the namespace
        // it belongs to, so the match shows up without an extra click.
        watch(query, (q) => {
            if (!props.resolveNamespaceId || !q.trim()) return
            const match_id = props.resolveNamespaceId(q.trim())
            if (match_id == null || expanded_set.value.has(match_id)) return
            const ns = props.namespaces.find(n => n.id === match_id)
            if (ns) emit('toggle-namespace', ns)
        })

        return {
            query,
            is_expanded,
            is_item_selected,
            filtered_namespaces,
            items_for,
        }
    },
    template: `
    <div class="card">
        <div class="card-body p-2">
            <div v-if="selectedItems.length" class="d-flex flex-wrap gap-1 align-items-center mb-2">
                <span v-for="item in selectedItems" :key="'sel-'+item.id" class="d-inline-flex align-items-center">
                    <tag_badge :label="item.label" :color="item.color" :icon-class="item.iconClass" :icon-name="item.iconName"></tag_badge>
                    <button type="button" class="btn btn-sm btn-link text-danger p-0 ms-1" style="line-height:1;" :aria-label="'Remove ' + item.label" @click="$emit('toggle-item', item)">
                        <i class="fas fa-times"></i>
                    </button>
                </span>
            </div>
            <div v-else class="text-muted small mb-2">[[noSelectionText]]</div>

            <input v-model="query" type="text" class="form-control form-control-sm mb-1" :placeholder="searchPlaceholder">

            <div class="border rounded" style="max-height: 220px; overflow-y: auto;">
                <div v-if="!filtered_namespaces.length" class="text-muted small p-2">[[namespaceEmptyText]]</div>
                <template v-for="ns in filtered_namespaces" :key="ns.id">
                    <button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2 border-0 border-bottom small"
                            :class="{'bg-primary-subtle': is_expanded(ns)}"
                            @click="$emit('toggle-namespace', ns)">
                        <span><i class="fas me-1" :class="is_expanded(ns) ? 'fa-chevron-down' : 'fa-chevron-right'" style="font-size:0.7em;"></i>[[ns.label]]</span>
                    </button>
                    <div v-if="is_expanded(ns)" class="ps-3 pe-1 py-1 bg-body-tertiary">
                        <div v-if="loadingItems" class="text-muted small py-1">
                            <span class="spinner-border spinner-border-sm me-1"></span>Loading...
                        </div>
                        <template v-else>
                            <div v-if="!items_for(ns).length" class="text-muted small py-1">[[itemEmptyText]]</div>
                            <button v-for="item in items_for(ns)" :key="item.id" type="button"
                                    class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2 border-0 small"
                                    :class="{'bg-primary-subtle': is_item_selected(item)}"
                                    :disabled="item.disabled" :title="item.title"
                                    @click="$emit('toggle-item', item)">
                                <tag_badge :label="item.label" :color="item.color" :icon-class="item.iconClass" :icon-name="item.iconName"></tag_badge>
                                <i v-if="is_item_selected(item)" class="fas fa-check text-primary ms-2"></i>
                            </button>
                        </template>
                    </div>
                </template>
            </div>
        </div>
    </div>
    `
}
