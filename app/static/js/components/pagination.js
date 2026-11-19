// Shared pagination control. Emits `page` with the requested page number.
const { computed } = Vue

export default {
    name: 'Pagination',
    delimiters: ['[[', ']]'],
    props: {
        currentPage: { type: Number, default: 1 },
        nbPages: { type: Number, default: 1 },
        // after a page change: 'page' scrolls smoothly to the top of the page, 'list' to the
        // element just before the pager (pages with several paginated tables), a CSS selector to
        // that element, 'none' stays put
        scroll: { type: String, default: 'page' },
    },
    emits: ['page'],
    setup(props, { emit }) {
        const root = Vue.ref(null)
        function scroll_after_change() {
            if (props.scroll === 'none') return
            const smooth = window.matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth'
            const target = props.scroll === 'page' ? null
                : props.scroll === 'list' ? root.value?.previousElementSibling
                : document.querySelector(props.scroll)
            if (target) {
                if (target.getBoundingClientRect().top < 0) target.scrollIntoView({ behavior: smooth, block: 'start' })
            } else {
                window.scrollTo({ top: 0, behavior: smooth })
            }
        }

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
                scroll_after_change()
            }
        }

        return { visible_pages, go, root }
    },
    template: `
        <nav v-if="nbPages > 1" ref="root" class="fi-pager" aria-label="Page navigation">
            <button type="button" class="fi-pager-btn fi-pager-step" :disabled="currentPage <= 1" @click="go(currentPage - 1)" aria-label="Previous page" title="Previous page">
                <i class="fa-solid fa-chevron-left"></i>
            </button>
            <template v-for="(page, index) in visible_pages" :key="index">
                <span v-if="page === '...'" class="fi-pager-gap" aria-hidden="true" title="Pages skipped">…</span>
                <button v-else type="button" class="fi-pager-btn" :class="{ 'is-active': page === currentPage }"
                        :aria-current="page === currentPage ? 'page' : null" :title="page === currentPage ? 'Current page' : 'Go to page ' + page" @click="go(page)">[[ page ]]</button>
            </template>
            <button type="button" class="fi-pager-btn fi-pager-step" :disabled="currentPage >= nbPages" @click="go(currentPage + 1)" aria-label="Next page" title="Next page">
                <i class="fa-solid fa-chevron-right"></i>
            </button>
        </nav>
    `,
}
