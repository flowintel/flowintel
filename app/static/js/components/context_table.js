import Pagination from './pagination.js'

/**
 * context_table.js — Table with expandable rows, shared by the Context pages
 * (custom tags, taxonomies, galaxies).
 *
 * Clicking a row (or pressing Enter on it) opens a detail row underneath that spans
 * the whole table. Only one row is open at a time.
 *
 * Props:
 *   columns      Array    [{ key, label, class?, width?, sortable?, sortKey? }] — header + cell
 *                         layout. sortable columns get a clickable header; sortKey is the
 *                         field sent in the sort event (defaults to key)
 *   rows         Array    rows to display
 *   rowKey       String   unique key of a row (default: "id")
 *   loading      Boolean  show a spinner instead of the rows
 *   emptyText    String   text shown when there are no rows
 *   currentPage  Number   current page (pagination is hidden when nbPages <= 1)
 *   nbPages      Number   total number of pages
 *   sortKey      String   field the rows are currently sorted on
 *   sortOrder    String   "asc" or "desc"
 *
 * Events:
 *   row-open(row)   a row has just been opened (fetch its details here)
 *   page(n)         the user asked for page n
 *   sort(key, order) the user clicked a sortable header (asc first, then desc)
 *
 * Slots:
 *   cell-<key>  { row }   custom rendering of a cell (default: row[key])
 *   detail      { row }   content of the opened row
 *
 * Interactive elements inside cells (switches, buttons) should use @click.stop so
 * they don't toggle the row.
 */

const { ref, watch } = Vue

export default {
    name: 'ContextTable',
    components: { Pagination },
    delimiters: ['[[', ']]'],

    props: {
        columns:     { type: Array, required: true },
        rows:        { type: Array, default: () => [] },
        rowKey:      { type: String, default: 'id' },
        loading:     { type: Boolean, default: false },
        emptyText:   { type: String, default: 'Nothing to display' },
        currentPage: { type: Number, default: 1 },
        nbPages:     { type: Number, default: 1 },
        sortKey:     { type: String, default: '' },
        sortOrder:   { type: String, default: 'asc' },
    },

    emits: ['row-open', 'page', 'sort'],

    template: `
        <div class="ctx-table-wrap">
            <table class="ctx-table">
                <thead>
                    <tr>
                        <th class="ctx-col-toggle" aria-hidden="true"></th>
                        <th v-for="col in columns" :key="col.key" :class="col.class" :style="col.width ? {width: col.width} : null"
                            :aria-sort="col.sortable && is_sorted(col) ? (sortOrder === 'desc' ? 'descending' : 'ascending') : null">
                            <button v-if="col.sortable" type="button" class="ctx-sort" :class="{'is-sorted': is_sorted(col)}"
                                    @click="sort_by(col)" :title="'Sort by ' + col.label.toLowerCase()">
                                [[ col.label ]]
                                <i :class="sort_icon(col)"></i>
                            </button>
                            <template v-else>[[ col.label ]]</template>
                        </th>
                    </tr>
                </thead>
                <tbody v-if="loading">
                    <tr><td :colspan="columns.length + 1" class="ctx-table-state">
                        <div class="spinner-border spinner-border-sm text-primary me-2" role="status"></div>Loading...
                    </td></tr>
                </tbody>
                <tbody v-else-if="!rows || !rows.length">
                    <tr><td :colspan="columns.length + 1" class="ctx-table-state">
                        <i class="fa-solid fa-inbox me-2"></i>[[ emptyText ]]
                    </td></tr>
                </tbody>
                <tbody v-else>
                    <template v-for="row in rows" :key="row[rowKey]">
                        <tr class="ctx-row" :class="{'is-open': open_key === row[rowKey]}"
                            tabindex="0" :aria-expanded="open_key === row[rowKey]"
                            @click="toggle(row)" @keydown.enter.prevent="toggle(row)">
                            <td class="ctx-col-toggle"><i class="fa-solid fa-angle-right"></i></td>
                            <td v-for="col in columns" :key="col.key" :class="col.class">
                                <slot :name="'cell-' + col.key" :row="row">[[ row[col.key] ]]</slot>
                            </td>
                        </tr>
                        <tr v-if="open_key === row[rowKey]" class="ctx-detail-row">
                            <td :colspan="columns.length + 1">
                                <div class="ctx-detail">
                                    <slot name="detail" :row="row"></slot>
                                </div>
                            </td>
                        </tr>
                    </template>
                </tbody>
            </table>

            <div v-if="nbPages > 1" class="ctx-pagination">
                <span class="ctx-pagination-info">Page [[ currentPage ]] of [[ nbPages ]]</span>
                <Pagination :current-page="currentPage" :nb-pages="nbPages" @page="$emit('page', $event)" />
            </div>
        </div>
    `,

    setup(props, { emit }) {
        const open_key = ref(null)

        function toggle(row) {
            const key = row[props.rowKey]
            if (open_key.value === key) {
                open_key.value = null
            } else {
                open_key.value = key
                emit('row-open', row)
            }
        }

        function col_sort_key(col) {
            return col.sortKey || col.key
        }

        function is_sorted(col) {
            return props.sortKey === col_sort_key(col)
        }

        function sort_by(col) {
            const order = is_sorted(col) && props.sortOrder === 'asc' ? 'desc' : 'asc'
            emit('sort', col_sort_key(col), order)
        }

        function sort_icon(col) {
            if (!is_sorted(col)) return 'fa-solid fa-sort'
            return props.sortOrder === 'desc' ? 'fa-solid fa-sort-down' : 'fa-solid fa-sort-up'
        }

        // A new page or a new search closes the opened row
        watch(() => props.rows, () => { open_key.value = null })

        return { open_key, toggle, is_sorted, sort_by, sort_icon }
    }
}
