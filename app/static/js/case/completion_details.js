/**
 * completion_details.js — details of a case completion, shown under the progress bar of the
 * "Completion" section when it is unfolded: tasks per status (ring), deadlines of the open
 * tasks, open / closed per assignee, subtasks and tasks created / finished per week.
 * Data from /case/<id>/completion_stats, loaded when the panel is first shown and again when
 * `version` changes (a task opened / closed).
 * Styles: /static/css/case/completion_details.css
 */
const { ref, computed, watch, onMounted } = Vue

const STYLE_COLORS = { primary: '#0d6efd', secondary: '#6c757d', success: '#198754', danger: '#dc3545',
    warning: '#ffc107', info: '#0dcaf0', light: '#ced4da', dark: '#343a40' }

export default {
    name: 'completion_details',
    delimiters: ['[[', ']]'],
    props: {
        caseId: { type: Number, required: true },
        version: { type: [Number, String], default: 0 },   // change it to reload
    },
    setup(props) {
        const data = ref(null)
        const loading = ref(false)
        const failed = ref(false)

        async function load() {
            loading.value = true
            try {
                const res = await fetch(`/case/${props.caseId}/completion_stats`)
                failed.value = !res.ok
                if (res.ok) data.value = await res.json()
            } catch (e) { failed.value = true }
            loading.value = false
        }
        onMounted(load)
        watch(() => props.version, load)

        const total = computed(() => (data.value?.by_status || []).reduce((n, s) => n + s.count, 0))

        // ring: one arc per status
        const R = 42, C = 2 * Math.PI * R
        const arcs = computed(() => {
            let offset = 0
            return (data.value?.by_status || []).filter(s => s.count).map(s => {
                const len = total.value ? C * s.count / total.value : 0
                const arc = { ...s, color: STYLE_COLORS[s.style] || STYLE_COLORS.secondary, dash: `${len} ${C - len}`, offset: -offset }
                offset += len
                return arc
            })
        })

        const max_user = computed(() => Math.max(1, ...(data.value?.assignees || []).map(a => a.open + a.closed)))
        const max_week = computed(() => Math.max(1, ...(data.value?.weeks || []).flatMap(w => [w.created, w.finished])))
        const sub_pct = computed(() => {
            const s = data.value?.subtasks
            return s && s.total ? Math.round(100 * s.done / s.total) : 0
        })
        function week_label(w) { return window.dayjs ? dayjs(w).format('DD/MM') : w.slice(5) }

        return { data, loading, failed, total, arcs, R, C, max_user, max_week, sub_pct, week_label }
    },
    template: /* html */ `
    <div class="cpd">
        <div v-if="loading && !data" class="cpd-loading"><span class="lo-sk" style="width:60%"></span><span class="lo-sk lo-sk-sm" style="width:80%"></span><span class="lo-sk lo-sk-sm" style="width:40%"></span></div>
        <div v-else-if="failed && !data" class="cpd-empty">Could not load the completion details.</div>
        <div v-else-if="data && !total" class="cpd-empty">No task in this case yet.</div>
        <template v-else-if="data">
            <!-- statuses -->
            <div class="cpd-block cpd-status">
                <svg viewBox="0 0 100 100" class="cpd-ring" role="img" :aria-label="total + ' tasks by status'">
                    <circle cx="50" cy="50" :r="R" class="cpd-ring-bg"/>
                    <circle v-for="a in arcs" :key="a.id" cx="50" cy="50" :r="R" :stroke="a.color" :stroke-dasharray="a.dash" :stroke-dashoffset="a.offset"
                            class="cpd-ring-arc"><title>[[ a.name ]]: [[ a.count ]]</title></circle>
                    <text x="50" y="48" class="cpd-ring-num">[[ total ]]</text>
                    <text x="50" y="62" class="cpd-ring-label">tasks</text>
                </svg>
                <ul class="cpd-legend">
                    <li v-for="a in arcs" :key="a.id" :title="a.count + ' task' + (a.count > 1 ? 's' : '') + ' ' + a.name">
                        <span class="cpd-dot" :style="{ background: a.color }"></span>[[ a.name ]]<b>[[ a.count ]]</b>
                    </li>
                </ul>
            </div>

            <!-- deadlines + subtasks -->
            <div class="cpd-block cpd-chips">
                <span class="cpd-chip" :class="{ 'is-bad': data.overdue }" title="Open tasks past their deadline"><i class="fa-solid fa-triangle-exclamation"></i><b>[[ data.overdue ]]</b> overdue</span>
                <span class="cpd-chip" :class="{ 'is-warn': data.due_soon }" title="Open tasks due in the next 7 days"><i class="fa-solid fa-hourglass-half"></i><b>[[ data.due_soon ]]</b> due ≤ 7 days</span>
                <span class="cpd-chip" title="Open tasks without a deadline"><i class="fa-regular fa-calendar-xmark"></i><b>[[ data.no_deadline ]]</b> no deadline</span>
                <span class="cpd-chip" :class="{ 'is-warn': data.unassigned }" title="Open tasks nobody is assigned to"><i class="fa-solid fa-user-slash"></i><b>[[ data.unassigned ]]</b> unassigned</span>
                <span v-if="data.subtasks.total" class="cpd-chip cpd-chip--sub" :title="data.subtasks.done + ' of ' + data.subtasks.total + ' subtasks done'">
                    <i class="fa-solid fa-list-check"></i><span class="cpd-mini"><span :style="{ width: sub_pct + '%' }"></span></span><b>[[ data.subtasks.done ]]/[[ data.subtasks.total ]]</b> subtasks
                </span>
            </div>

            <!-- assignees -->
            <div v-if="data.assignees.length" class="cpd-block">
                <h6 class="cpd-title">By assignee</h6>
                <div v-for="a in data.assignees" :key="a.id" class="cpd-user" :title="a.name + ': ' + a.open + ' open, ' + a.closed + ' closed'">
                    <span class="cpd-user-name">[[ a.name ]]</span>
                    <span class="cpd-user-bar">
                        <span class="is-closed" :style="{ width: (100 * a.closed / max_user) + '%' }"></span><span class="is-open" :style="{ width: (100 * a.open / max_user) + '%' }"></span>
                    </span>
                    <span class="cpd-user-num">[[ a.closed ]]/[[ a.open + a.closed ]]</span>
                </div>
                <small v-if="data.more_assignees" class="cpd-more">+[[ data.more_assignees ]] more</small>
                <div class="cpd-key"><span><i class="is-closed"></i>closed</span><span><i class="is-open"></i>open</span></div>
            </div>

            <!-- weekly activity -->
            <div class="cpd-block">
                <h6 class="cpd-title">Last 8 weeks</h6>
                <div class="cpd-weeks">
                    <div v-for="w in data.weeks" :key="w.week" class="cpd-week" :title="'Week of ' + week_label(w.week) + ': ' + w.created + ' created, ' + w.finished + ' finished'">
                        <span class="cpd-week-bars">
                            <span class="is-created" :style="{ height: (100 * w.created / max_week) + '%' }"></span>
                            <span class="is-finished" :style="{ height: (100 * w.finished / max_week) + '%' }"></span>
                        </span>
                        <small>[[ week_label(w.week) ]]</small>
                    </div>
                </div>
                <div class="cpd-key"><span><i class="is-created"></i>created</span><span><i class="is-finished"></i>finished</span></div>
            </div>
        </template>
    </div>
    `,
}
