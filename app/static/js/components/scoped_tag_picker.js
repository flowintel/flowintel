/**
 * scoped_tag_picker.js — two-step picker: choose a namespace, then choose an
 * item scoped to it (taxonomy -> tags, galaxy -> clusters).
 *
 * Pure layout/composition around two <picker_pane>. All data fetching and
 * selection state stays owned by the caller (e.g. edition_select.js) — this
 * component just relays the two 'toggle' events under distinct names.
 */
import picker_pane from './picker_pane.js'

export default {
    name: 'ScopedTagPicker',
    delimiters: ['[[', ']]'],
    components: { picker_pane },
    props: {
        namespaceTitle: { type: String, default: 'Namespaces' },
        itemTitle: { type: String, default: 'Items' },
        namespaces: { type: Array, default: () => [] },
        items: { type: Array, default: () => [] },
        selectedNamespaceIds: { type: Array, default: () => [] },
        selectedItemIds: { type: Array, default: () => [] },
        loadingItems: { type: Boolean, default: false },
        itemsGrouped: { type: Boolean, default: true },
        namespaceEmptyText: { type: String, default: 'No namespace found.' },
        itemEmptyText: { type: String, default: 'Select a namespace on the left first.' },
    },
    emits: ['toggle-namespace', 'toggle-item'],
    template: `
    <div class="row g-2">
        <div class="col-md-5">
            <picker_pane
                :title="namespaceTitle"
                :items="namespaces"
                :selected-ids="selectedNamespaceIds"
                :empty-text="namespaceEmptyText"
                @toggle="item => $emit('toggle-namespace', item)">
            </picker_pane>
        </div>
        <div class="col-md-7">
            <picker_pane
                :title="itemTitle"
                :items="items"
                :selected-ids="selectedItemIds"
                :grouped="itemsGrouped"
                :loading="loadingItems"
                :empty-text="itemEmptyText"
                @toggle="item => $emit('toggle-item', item)">
            </picker_pane>
        </div>
    </div>
    `
}
