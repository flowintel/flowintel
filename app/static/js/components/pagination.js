// Shared pagination control. Emits `page` with the requested page number.
const { computed } = Vue

export default {
    name: 'Pagination',
    delimiters: ['[[', ']]'],
    props: {
        currentPage: { type: Number, default: 1 },
        nbPages: { type: Number, default: 1 },
    },
    emits: ['page'],
    setup(props, { emit }) {
        const visible_pages = computed(() => {
            const total = props.nbPages
            const current = props.currentPage
            if (total <= 7) return Array.from({ length: total }, (_, i) => i + 1)
            if (current <= 4) return [1, 2, 3, 4, 5, '...', total]
            if (current >= total - 3) return [1, '...', total - 4, total - 3, total - 2, total - 1, total]
            return [1, '...', current - 1, current, current + 1, '...', total]
        })

        function go(page) {
            if (Number.isInteger(page) && page >= 1 && page <= props.nbPages && page !== props.currentPage) {
                emit('page', page)
            }
        }

        return { visible_pages, go }
    },
    template: `
        <nav v-if="nbPages > 1" aria-label="Page navigation">
            <ul class="pagination pagination-sm justify-content-center flex-wrap mb-0">
                <li class="page-item" :class="{disabled: currentPage <= 1}">
                    <button type="button" class="page-link" :disabled="currentPage <= 1" @click="go(currentPage - 1)" aria-label="Previous page">Previous</button>
                </li>
                <li v-for="(page, index) in visible_pages" :key="index" class="page-item" :class="{active: page === currentPage, disabled: page === '...'}">
                    <button v-if="page !== '...'" type="button" class="page-link" :aria-current="page === currentPage ? 'page' : null" @click="go(page)">[[ page ]]</button>
                    <span v-else class="page-link">...</span>
                </li>
                <li class="page-item" :class="{disabled: currentPage >= nbPages}">
                    <button type="button" class="page-link" :disabled="currentPage >= nbPages" @click="go(currentPage + 1)" aria-label="Next page">Next</button>
                </li>
            </ul>
        </nav>
    `,
}
