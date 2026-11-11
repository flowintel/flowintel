/**
 * case-links.js — The linked cases of a case: small cards (status, title, progress,
 * deadline), two at a time; ← → page through them, so a long list never pushes the page
 * down. A click anywhere on a card opens the linked case.
 *
 * Props:
 *   links       Array   — Case.to_link_json() of the linked cases
 *   statuses    Array   — status_info.status ({id, name, bootstrap_style}), for the badge
 *   removable   Boolean — show the "remove the link" button
 * Emits:
 *   remove(link)
 */
const { ref, computed, watch } = Vue

const PER_PAGE = 2

export default {
    name: 'CaseLinks',
    delimiters: ['[[', ']]'],
    props: {
        links: { type: Array, default: () => [] },
        statuses: { type: Array, default: () => [] },
        removable: { type: Boolean, default: false },
    },
    emits: ['remove'],
    setup(props) {
        const page = ref(0)
        const pages = computed(() => Math.max(1, Math.ceil(props.links.length / PER_PAGE)))
        const shown = computed(() => props.links.slice(page.value * PER_PAGE, page.value * PER_PAGE + PER_PAGE))
        const range = computed(() => {
            const from = page.value * PER_PAGE + 1
            return `${from}–${Math.min(from + PER_PAGE - 1, props.links.length)} / ${props.links.length}`
        })
        // a removed link can leave the last page empty
        watch(() => props.links.length, () => { if (page.value > pages.value - 1) page.value = pages.value - 1 })

        function go(link) { window.location.href = '/case/' + link.id }
        function status_of(l) { return props.statuses.find(s => s.id === l.status_id) || null }
        function progress(l) { return l.tasks_total ? Math.round(l.tasks_closed / l.tasks_total * 100) : 0 }
        function day(d) {
            if (!d) return ''
            const x = window.dayjs ? window.dayjs.utc(d) : null
            return x && x.isValid() ? x.format('YYYY-MM-DD') : String(d).slice(0, 10)
        }
        function overdue(l) { return !!l.deadline && !l.completed && !!window.dayjs && window.dayjs.utc(l.deadline).isBefore(window.dayjs()) }

        return { page, pages, shown, range, go, status_of, progress, day, overdue }
    },
    template: `
    <div class="clk">
        <div v-if="!links.length" class="text-muted small fst-italic">No linked case.</div>
        <div v-else class="clk-carousel">
            <button v-if="pages > 1" type="button" class="clk-arrow" :disabled="page === 0" @click="page--" aria-label="Previous linked cases">
                <i class="fa-solid fa-chevron-left"></i>
            </button>
            <div class="clk-cards">
                <!-- the whole card leads to the linked case -->
                <article v-for="l in shown" :key="l.id" :class="['clc', { 'is-done': l.completed, 'is-overdue': overdue(l) }]"
                         role="link" tabindex="0" :title="'Open: ' + l.title" @click="go(l)" @keydown.enter="go(l)">
                    <span class="clc-icon"><i :class="l.completed ? 'fa-solid fa-circle-check' : 'fa-solid fa-briefcase'"></i></span>
                    <div class="clc-body">
                        <div class="clc-sub">
                            <span>#[[ l.id ]]</span>
                            <span v-if="status_of(l)" :class="'badge rounded-pill text-bg-' + (status_of(l).bootstrap_style || 'secondary')">[[ status_of(l).name ]]</span>
                            <i v-if="l.is_private" class="fa-solid fa-lock" title="Private case"></i>
                        </div>
                        <div class="clc-title">[[ l.title ]]</div>
                        <div class="clc-facts">
                            <span v-if="l.tasks_total" class="clc-progress" :title="l.tasks_closed + ' / ' + l.tasks_total + ' tasks done'">
                                <span class="clc-bar"><span :style="{ width: progress(l) + '%' }"></span></span>[[ l.tasks_closed ]]/[[ l.tasks_total ]]
                            </span>
                            <span v-else>No task</span>
                            <span v-if="l.deadline" :class="['clc-due', { 'is-late': overdue(l) }]" :title="'Deadline: ' + day(l.deadline)">
                                <i :class="overdue(l) ? 'fa-solid fa-triangle-exclamation' : 'fa-regular fa-calendar'"></i>[[ day(l.deadline) ]]
                            </span>
                        </div>
                    </div>
                    <button v-if="removable" type="button" class="clc-remove" @click.stop="$emit('remove', l)" title="Remove the link to this case" aria-label="Remove the link">
                        <i class="fa-solid fa-link-slash"></i>
                    </button>
                </article>
            </div>
            <button v-if="pages > 1" type="button" class="clk-arrow" :disabled="page >= pages - 1" @click="page++" aria-label="Next linked cases">
                <i class="fa-solid fa-chevron-right"></i>
            </button>
        </div>
        <div v-if="pages > 1" class="clk-pager">
            <span v-for="i in pages" :key="i" :class="['clk-dot', { 'is-active': i - 1 === page }]" @click="page = i - 1" :title="'Page ' + i"></span>
            <span class="clk-range">[[ range ]]</span>
        </div>
    </div>
    `
}
