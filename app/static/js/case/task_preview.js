/**
 * task_preview.js — the case calendar's hover card (case_calendar.js, .ccal-preview), for one task,
 * shown outside the calendar: hovering a task badge in the tags panel (tags_edition.js).
 *
 * Data: the case calendar items (GET /case/<cid>/calendar), the task's own entry ("Task created" /
 * "Task finished", else its deadline), picked as the calendar's "See in the calendar" does.
 *
 *   <task_preview :item="item" :pos="{x, y}"></task_preview>
 *   load_task_item(case_id, task_id) → Promise<item|null>   (calendar items cached per case)
 */

import { KINDS, period_info, format_when } from './case_calendar.js'

const kind_info = (key) => KINDS.find(k => k.key === key) || KINDS[KINDS.length - 1]

const cache = new Map()     // case id → Promise<items>

function calendar_items(case_id) {
    if (!cache.has(case_id)) {
        cache.set(case_id, fetch('/case/' + case_id + '/calendar')
            .then(r => r.ok ? r.json() : {})
            .then(d => d.items || [])
            .catch(() => []))
    }
    return cache.get(case_id)
}

export async function load_task_item(case_id, task_id) {
    const items = await calendar_items(case_id)
    const rank = it => ({ task: 0, deadline: 1 })[it.kind] ?? 2
    return items
        .filter(it => it.target && it.target.task === task_id)
        .sort((a, b) => rank(a) - rank(b) || (a.start < b.start ? 1 : -1))[0] || null
}

/** Forget the cached calendar of a case (after its tasks changed). */
export function reset_task_items(case_id) {
    cache.delete(case_id)
}

export default {
    name: 'TaskPreview',
    delimiters: ['[[', ']]'],
    props: {
        item: { type: Object, required: true },
        pos:  { type: Object, default: () => ({ x: 0, y: 0 }) },
    },
    setup() {
        const item_label = (it) => it.label || kind_info(it.kind).label
        return { kind_info, item_label, period_info, format_when }
    },
    template: `
        <div class="ccal-preview" :style="{ left: pos.x + 'px', top: pos.y + 'px', '--ccal-c': kind_info(item.kind).color }">
            <div class="ccal-preview-head">
                <span class="ccal-preview-kind"><i :class="kind_info(item.kind).icon"></i> [[ item_label(item) ]]</span>
                <span v-if="item.status" :class="'badge rounded-pill text-bg-' + (item.status.style || 'secondary')">[[ item.status.name ]]</span>
            </div>
            <div class="ccal-preview-title">[[ item.title ]]</div>
            <div class="ccal-preview-when"><i class="fa-regular fa-clock me-1"></i>[[ format_when(item) ]]</div>
            <div v-if="period_info(item)" :class="['ccal-period', 'ccal-period-' + period_info(item).state]">
                <div class="ccal-period-ends"><span>[[ period_info(item).from ]]</span><span>[[ period_info(item).to_label ]] · [[ period_info(item).to ]]</span></div>
                <div class="ccal-period-track"><div v-if="period_info(item).percent !== null" class="ccal-period-fill" :style="{ width: period_info(item).percent + '%' }"></div></div>
                <div class="ccal-period-status">
                    <span>[[ period_info(item).status ]]</span>
                    <span v-if="period_info(item).time_required" class="ccal-period-req"><i class="fa-solid fa-stopwatch me-1"></i>[[ period_info(item).time_required ]]</span>
                </div>
            </div>
            <dl v-if="item.meta && item.meta.length" class="ccal-preview-meta">
                <template v-for="m in item.meta.slice(0, 5)" :key="m[0]">
                    <dt>[[ m[0] ]]</dt><dd>[[ m[1] ]]</dd>
                </template>
            </dl>
            <div v-if="item.body" class="ccal-preview-body">[[ item.body ]]</div>
            <div class="ccal-preview-hint">Click to open the task</div>
        </div>
    `,
}
