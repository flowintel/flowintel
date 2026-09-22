/**
 * picker_pane.js — generic searchable "pick from a list" card
 *
 * Renders a Bootstrap card with a search box and a scrollable list of clickable
 * items (rendered via <tag_badge>), plus a summary row of currently selected
 * items with a small "x" to remove them without hunting through the list.
 *
 * Items must already be normalized by the caller to:
 *   { id, label, color?, iconClass?, iconName?, title?, disabled?, group?, raw }
 * `id` is whatever the caller uses to test membership in its own selected-state
 * array (tag name, cluster uuid, ...). `raw` is passed back untouched on toggle
 * so the caller can plug it into its existing add/remove logic.
 *
 * This component owns no selection state itself — it's a controlled component:
 * the caller passes `items` + `selectedIds` and reacts to `toggle`.
 */
import tag_badge from './tag-badge.js'
const { computed, ref } = Vue

export default {
    name: 'PickerPane',
    delimiters: ['[[', ']]'],
    components: { tag_badge },
    props: {
        title: { type: String, default: '' },
        items: { type: Array, default: () => [] },
        selectedIds: { type: Array, default: () => [] },
        grouped: { type: Boolean, default: false },
        searchable: { type: Boolean, default: true },
        loading: { type: Boolean, default: false },
        emptyText: { type: String, default: 'No items.' },
        searchPlaceholder: { type: String, default: 'Search...' },
    },
    emits: ['toggle'],
    setup(props) {
        const query = ref('')

        const selected_set = computed(() => new Set(props.selectedIds))

        function is_selected(item) {
            return selected_set.value.has(item.id)
        }

        const filtered = computed(() => {
            const q = query.value.trim().toLowerCase()
            if (!q) return props.items
            return props.items.filter(item =>
                (item.label || '').toLowerCase().includes(q) ||
                (item.title || '').toLowerCase().includes(q)
            )
        })

        const selected_items = computed(() =>
            props.items.filter(item => selected_set.value.has(item.id))
        )

        const grouped_filtered = computed(() => {
            const order = []
            const groups = {}
            for (const item of filtered.value) {
                const key = item.group || ''
                if (!groups[key]) {
                    groups[key] = []
                    order.push(key)
                }
                groups[key].push(item)
            }
            return order.map(key => ({ name: key, items: groups[key] }))
        })

        return {
            query,
            is_selected,
            filtered,
            selected_items,
            grouped_filtered,
        }
    },
    template: `
    <div class="card h-100">
        <div class="card-header d-flex justify-content-between align-items-center py-2">
            <span class="fw-semibold">
                [[title]]
                <span class="badge bg-secondary ms-1">[[filtered.length]]</span>
                <span v-if="selectedIds.length" class="badge bg-primary ms-1">[[selectedIds.length]] selected</span>
            </span>
        </div>
        <div class="card-body p-2">
            <div v-if="selected_items.length" class="d-flex flex-wrap gap-2 align-items-center mb-2 pb-2 border-bottom">
                <span v-for="item in selected_items" :key="'sel-'+item.id" class="d-inline-flex align-items-center gap-1">
                    <tag_badge :label="item.label" :color="item.color" :icon-class="item.iconClass" :icon-name="item.iconName"></tag_badge>
                    <button type="button" class="btn btn-sm btn-outline-danger py-0 px-1" :aria-label="'Remove ' + item.label" @click="$emit('toggle', item)">
                        <i class="fas fa-times"></i>
                    </button>
                </span>
            </div>

            <input v-if="searchable" v-model="query" type="text" class="form-control form-control-sm mb-2" :placeholder="searchPlaceholder">

            <div v-if="loading" class="text-center py-3 text-muted">
                <span class="spinner-border spinner-border-sm me-2"></span>Loading...
            </div>
            <div v-else style="max-height: 300px; overflow-y: auto;">
                <div v-if="!filtered.length" class="text-muted small p-2">[[emptyText]]</div>

                <template v-if="grouped">
                    <div v-for="group in grouped_filtered" :key="group.name || '_'" class="mb-1">
                        <div v-if="group.name" class="text-muted small fw-semibold px-1 pt-2">[[group.name]]</div>
                        <div class="list-group list-group-flush">
                            <button v-for="item in group.items" :key="item.id" type="button"
                                    class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2"
                                    :class="{'bg-primary-subtle': is_selected(item)}"
                                    :disabled="item.disabled" :title="item.title"
                                    @click="$emit('toggle', item)">
                                <tag_badge :label="item.label" :color="item.color" :icon-class="item.iconClass" :icon-name="item.iconName"></tag_badge>
                                <i v-if="is_selected(item)" class="fas fa-check text-primary ms-2"></i>
                            </button>
                        </div>
                    </div>
                </template>
                <template v-else>
                    <div class="list-group list-group-flush">
                        <button v-for="item in filtered" :key="item.id" type="button"
                                class="list-group-item list-group-item-action d-flex justify-content-between align-items-center py-1 px-2"
                                :class="{'bg-primary-subtle': is_selected(item)}"
                                :disabled="item.disabled" :title="item.title"
                                @click="$emit('toggle', item)">
                            <tag_badge :label="item.label" :color="item.color" :icon-class="item.iconClass" :icon-name="item.iconName"></tag_badge>
                            <i v-if="is_selected(item)" class="fas fa-check text-primary ms-2"></i>
                        </button>
                    </div>
                </template>
            </div>
        </div>
    </div>
    `
}
