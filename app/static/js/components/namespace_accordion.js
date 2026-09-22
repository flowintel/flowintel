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
const { computed, ref, watch, onBeforeUnmount } = Vue

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
        namespaceSearchPrefix: { type: Function, default: null },
    },
    emits: ['toggle-namespace', 'toggle-item'],
    setup(props, { emit }) {
        const query = ref('')

        function handle_namespace_click(ns) {
            const opening = !is_expanded(ns)
            emit('toggle-namespace', ns)
            if (opening) {
                if (props.namespaceSearchPrefix) query.value = props.namespaceSearchPrefix(ns)
            } else {
                if (ns.id === auto_expanded_id) auto_expanded_id = null
                query.value = ''
            }
        }

        // Clearing the search also closes whatever's currently expanded —
        // same toggle as clicking it again, so for galaxies (where expand
        // doubles as the marker) this un-marks them too, consistent with
        // what a manual close already does.
        function clear_search() {
            const to_close = props.namespaces.filter(is_expanded)
            auto_expanded_id = null
            query.value = ''
            to_close.forEach(ns => emit('toggle-namespace', ns))
        }

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
        // it belongs to, so the match shows up without an extra click. This
        // triggers a fetch (via toggle-namespace), so it's debounced to fire
        // once after the user stops typing rather than on every keystroke.
        // Shown in the search box while a match is pending, so there's no
        // silent gap between "typed a full tag" and "namespace pops open"
        // where it just looks like nothing matched.
        const is_resolving = ref(false)
        // The namespace id the search itself opened (not a manual click) —
        // only this one auto-closes when the query stops matching it, e.g.
        // deleting the ':' in "tlp:" -> "tlp". Editing within a match
        // ("tlp:green" -> "tlp:gree") keeps it open since the ':' is still
        // there; only losing the match itself closes it, and it's checked on
        // every keystroke (not debounced) so it closes right away.
        let auto_expanded_id = null
        let debounce_timer = null
        watch(query, (q) => {
            if (debounce_timer) clearTimeout(debounce_timer)
            const trimmed = q.trim()

            if (auto_expanded_id != null && props.resolveNamespaceId) {
                const still_matches = trimmed && props.resolveNamespaceId(trimmed) === auto_expanded_id
                if (!still_matches) {
                    const ns = props.namespaces.find(n => n.id === auto_expanded_id)
                    if (ns && is_expanded(ns)) emit('toggle-namespace', ns)
                    auto_expanded_id = null
                }
            }

            // Only a candidate for a match once it has a ':' (both taxonomy
            // "tlp:" and galaxy "misp-galaxy:...=" resolution need one) — a
            // plain text search with no colon isn't trying to jump anywhere,
            // so don't spin for every keystroke of an ordinary search.
            if (!props.resolveNamespaceId || !trimmed.includes(':')) {
                is_resolving.value = false
                return
            }
            is_resolving.value = true
            debounce_timer = setTimeout(() => {
                is_resolving.value = false
                const match_id = props.resolveNamespaceId(trimmed)
                if (match_id == null || expanded_set.value.has(match_id)) return
                const ns = props.namespaces.find(n => n.id === match_id)
                if (ns) {
                    emit('toggle-namespace', ns)
                    auto_expanded_id = match_id
                }
            }, 400)
        })
        onBeforeUnmount(() => { if (debounce_timer) clearTimeout(debounce_timer) })

        // Newly-expanded namespace ids, treated as loading even before the
        // caller's own loadingItems prop update lands, so there's never a
        // rendered frame showing "no item" for a namespace whose fetch just
        // started. Cleared once the caller reports loading is done.
        const pending_ids = ref([])
        watch(() => props.expandedIds, (new_ids, old_ids) => {
            old_ids = old_ids || []
            for (const id of new_ids) {
                if (!old_ids.includes(id) && !pending_ids.value.includes(id)) pending_ids.value.push(id)
            }
            pending_ids.value = pending_ids.value.filter(id => new_ids.includes(id))
        })
        watch(() => props.loadingItems, (loading) => {
            if (!loading) pending_ids.value = []
        })
        function is_loading(ns) {
            return props.loadingItems || pending_ids.value.includes(ns.id)
        }

        return {
            query,
            is_expanded,
            is_item_selected,
            filtered_namespaces,
            items_for,
            handle_namespace_click,
            clear_search,
            is_resolving,
            is_loading,
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

            <div class="position-relative mb-1">
                <input v-model="query" type="text" class="form-control form-control-sm" :class="{'pe-4': query}" :placeholder="searchPlaceholder">
                <span v-if="is_resolving" class="spinner-border spinner-border-sm text-muted position-absolute top-50 end-0 translate-middle-y me-2" role="status" aria-label="Looking for a match..."></span>
                <button v-else-if="query" type="button" class="btn-close position-absolute top-50 end-0 translate-middle-y me-2" style="font-size:0.65rem;" aria-label="Clear search" @click="clear_search()"></button>
            </div>

            <div class="border rounded" style="max-height: 220px; overflow-y: auto;">
                <div v-if="is_resolving" class="text-muted small p-2">
                    <span class="spinner-border spinner-border-sm me-1"></span>Looking for a match...
                </div>
                <div v-else-if="!filtered_namespaces.length" class="text-muted small p-2">[[namespaceEmptyText]]</div>
                <template v-for="ns in filtered_namespaces" :key="ns.id">
                    <button type="button" class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2 border-0 border-bottom small"
                            :class="{'bg-primary-subtle': is_expanded(ns)}"
                            @click="handle_namespace_click(ns)">
                        <span><i class="fas me-1" :class="is_expanded(ns) ? 'fa-chevron-down' : 'fa-chevron-right'" style="font-size:0.7em;"></i>[[ns.label]]</span>
                    </button>
                    <div v-if="is_expanded(ns)" class="ps-3 pe-1 py-1 bg-body-tertiary">
                        <div v-if="is_loading(ns)" class="text-muted small py-1">
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
