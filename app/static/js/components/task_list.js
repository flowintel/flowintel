/**
 * task_list.js — a list of tasks (My assignments), as a sortable table or as cards.
 * Same look and behaviour as case_list.js (it reuses its .cl-* styles), plus what a task
 * has: the case it belongs to, assignees, open subtasks.
 *
 *   <task_list :tasks="tasks" :status-info="status_info" view="cards"
 *              sort="last_modif" order="desc" :loading="loading" :can-edit="true"
 *              :group-by-case="false"
 *              @sort="(key) => ..." @complete="(task, reopen) => ..."></task_list>
 *
 * Tasks come from /my_assignment/sort_tasks?flat=true (each task has `case`, `users`,
 * `subtasks`, `nb_open_subtasks`). Sorting and pagination are done by the server: a click
 * on a column header emits `sort` with the column key.
 * Needs dayjs (utc + relativeTime). Styles: case_list.css + task_list.css.
 */
import tag_badge from './tag-badge.js'
import tag_fit from './tag-fit.js'
import smart_render from './smart-render.js'
import user_chip from './user-chip.js'
import loading_overlay from './loading_overlay.js'
import case_ref from './case_ref.js'

// description cut after a few lines, faded only when it really overflows (as in case_list)
const desc_clamp = {
    mounted(el) {
        const check = () => el.classList.toggle('is-clamped', el.scrollHeight > el.clientHeight + 1)
        el._clampRO = new ResizeObserver(check)
        el._clampRO.observe(el)
        el._clampMO = new MutationObserver(check)
        el._clampMO.observe(el, { childList: true, subtree: true, characterData: true })
        requestAnimationFrame(check)
    },
    unmounted(el) { el._clampRO?.disconnect(); el._clampMO?.disconnect() },
}

const STATUS_ICONS = {
    'Created':        'fa-solid fa-plus',
    'Ongoing':        'fa-solid fa-play',
    'Recurring':      'fa-solid fa-repeat',
    'Unavailable':    'fa-solid fa-ban',
    'Rejected':       'fa-solid fa-xmark',
    'Finished':       'fa-solid fa-flag-checkered',
    'Requested':      'fa-solid fa-inbox',
    'Approved':       'fa-solid fa-check',
    'Request Review': 'fa-solid fa-eye',
}

// Columns the server can sort on (my_assignment_core.SORT_COLUMNS)
const SORTABLE = {
    title:      'Task',
    case:       'Case',
    status_id:  'Status',
    deadline:   'Deadline',
    last_modif: 'Last modified',
}

const OPEN_SUBTASKS_SHOWN = 3

export default {
    name: 'task_list',
    delimiters: ['[[', ']]'],
    components: { tag_badge, smart_render, user_chip, loading_overlay, case_ref },
    directives: { 'tag-fit': tag_fit, 'desc-clamp': desc_clamp },
    props: {
        tasks:      { type: Array, default: () => [] },
        statusInfo: { type: Object, default: null },
        view:       { type: String, default: 'cards' },   // 'table' | 'cards'
        sort:       { type: String, default: '' },
        order:      { type: String, default: 'desc' },
        loading:    { type: Boolean, default: false },
        canEdit:    { type: Boolean, default: false },     // complete / reopen buttons
        groupByCase: { type: Boolean, default: false },    // one block per case (header + its tasks)
        currentUserId: { type: Number, default: null },    // shown first among the assignees
    },
    emits: ['sort', 'complete'],
    data() {
        return { collapsed: {} }   // case id → true when its tasks are folded (grouped view)
    },
    computed: {
        // [{ case, tasks }] in the order the cases first appear; one group of all when not grouping
        groups() {
            if (!this.groupByCase) return [{ case: null, tasks: this.tasks }]
            const by = new Map()
            for (const t of this.tasks) {
                if (!by.has(t.case_id)) by.set(t.case_id, { case: t.case, tasks: [] })
                by.get(t.case_id).tasks.push(t)
            }
            return [...by.values()]
        },
        nb_columns() { return this.groupByCase ? 8 : 9 },
        SORTABLE: () => SORTABLE,
        OPEN_SUBTASKS_SHOWN: () => OPEN_SUBTASKS_SHOWN,
    },
    methods: {
        href(t) { return `/case/${t.case_id}?task=${t.id}#task-${t.id}` },
        status(t) {
            const s = this.statusInfo?.status?.find(x => x.id === t.status_id)
            const name = s?.name || 'Unknown'
            return { name, style: s?.bootstrap_style || 'secondary', icon: STATUS_ICONS[name] || 'fa-solid fa-circle' }
        },
        tags(t) {
            return [
                ...(t.custom_tags || []).map(d => ({ kind: 'custom', d })),
                ...(t.tags || []).map(d => ({ kind: 'taxonomy', d })),
                ...(t.galaxies || []).map(d => ({ kind: 'galaxy', d })),
                ...(t.clusters || []).map(d => ({ kind: 'cluster', d })),
            ]
        },
        subtasks(t) {
            const total = (t.subtasks || []).length, open = t.nb_open_subtasks || 0, done = total - open
            return { total, open, done, pct: total ? Math.round(100 * done / total) : 0 }
        },
        toggle_group(g, e) {
            if (e && e.target.closest('a')) return   // the case title is a link
            this.collapsed[g.case.id] = !this.collapsed[g.case.id]
        },
        // fold / unfold every case of the page
        set_all_collapsed(value) {
            const next = {}
            if (value) for (const g of this.groups) next[g.case.id] = true
            this.collapsed = next
        },
        // true when every case of the page is folded (drives the "Collapse / Expand all" toggle)
        all_collapsed() {
            return this.groupByCase && this.groups.length > 0 && this.groups.every(g => this.collapsed[g.case.id])
        },
        group_late(g) { return g.tasks.filter(t => this.due(t)?.state === 'is-late').length },
        // assignees: the current user first, then a single other one; the rest as "+N"
        assignees(t) {
            const users = [...(t.users || [])]
            const me = users.findIndex(u => u.id === this.currentUserId)
            if (me > 0) users.unshift(users.splice(me, 1)[0])
            const shown = users.slice(0, 2), rest = users.slice(2)
            return { shown, rest, title: rest.map(u => u.first_name + ' ' + u.last_name).join(', ') }
        },
        open_subtasks(t) { return (t.subtasks || []).filter(s => !s.completed) },
        has_desc(t) { return !!(t.description && t.description.trim() && t.description.trim() !== '-') },
        since(d) { return d ? dayjs.utc(d).fromNow() : '' },
        full(d) { return d ? dayjs.utc(d).local().format('YYYY-MM-DD HH:mm') : '' },
        // deadline: state class + short text ("2 days late", "today", "in 3 days"...)
        due(t) {
            if (!t.deadline) return null
            const d = dayjs.utc(t.deadline)
            const days = d.startOf('day').diff(dayjs.utc().startOf('day'), 'day')
            let text, state
            if (t.completed) { text = d.local().format('YYYY-MM-DD'); state = '' }
            else if (days < -1) { text = Math.abs(days) + ' days late'; state = 'is-late' }
            else if (days === -1) { text = 'yesterday'; state = 'is-late' }
            else if (days === 0) { text = 'today'; state = d.isBefore(dayjs.utc()) ? 'is-late' : 'is-soon' }
            else if (days === 1) { text = 'tomorrow'; state = 'is-soon' }
            else if (days <= 7) { text = 'in ' + days + ' days'; state = 'is-soon' }
            else { text = d.fromNow(); state = '' }
            return { text, state, title: 'Deadline: ' + this.full(t.deadline) }
        },
        sort_icon(key) {
            if (this.sort !== key) return 'fa-sort'
            return this.order === 'asc' ? 'fa-sort-up' : 'fa-sort-down'
        },
        aria_sort(key) {
            if (this.sort !== key) return 'none'
            return this.order === 'asc' ? 'ascending' : 'descending'
        },
        // a click anywhere on a row / card opens the task, except on links, buttons and tags
        open_row(t, e) {
            if (e.target.closest('a, button, .tg-more, [data-tg-name], .ma-users')) return
            if (e.ctrlKey || e.metaKey || e.button === 1) window.open(this.href(t), '_blank')
            else window.location.href = this.href(t)
        },
    },
    template: /* html */ `
    <loading_overlay :loading="loading" :empty="!tasks.length" label="Loading tasks…">
    <template #skeleton>
    <div v-if="view === 'table'" class="cl-card">
      <table class="table cl-table">
        <thead><tr><th v-for="n in 8" :key="n"><span class="lo-sk" style="width: 60%"></span></th></tr></thead>
        <tbody>
          <tr v-for="n in 8" :key="n">
            <td><span class="lo-sk" :style="{ width: (55 + (n * 7) % 35) + '%' }"></span><span class="lo-sk lo-sk-sm" style="width: 70%"></span></td>
            <td><span class="lo-sk" style="width: 80%"></span></td>
            <td><span class="lo-sk lo-sk-pill"></span></td>
            <td><span class="lo-sk" style="width: 80%"></span></td>
            <td><span class="lo-sk" style="width: 70px"></span></td>
            <td><span class="lo-sk" style="width: 60px"></span></td>
            <td><span class="lo-sk" style="width: 70px"></span></td>
            <td><span class="lo-sk" style="width: 60px"></span></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="cl-grid">
      <article v-for="n in 4" :key="n" class="cl-tile">
        <span class="lo-sk lo-sk-sm" style="width: 30%"></span>
        <header class="cl-tile-head"><span class="lo-sk" :style="{ width: (35 + (n * 11) % 30) + '%' }"></span><span class="lo-sk lo-sk-pill cl-tile-status"></span></header>
        <div class="cl-tile-meta"><span class="lo-sk" style="width: 90px"></span><span class="lo-sk" style="width: 110px"></span><span class="lo-sk" style="width: 80px"></span></div>
        <div class="cl-tile-meta"><span class="lo-sk lo-sk-pill" v-for="t in 3" :key="t"></span></div>
        <div><span class="lo-sk lo-sk-sm" style="width: 90%"></span><span class="lo-sk lo-sk-sm" style="width: 65%"></span></div>
      </article>
    </div>
    </template>

    <!-- ───── table ───── -->
    <div v-if="view === 'table'" class="cl-card">
      <div class="table-responsive">
        <table class="table cl-table ma-table">
          <thead>
            <tr>
              <th v-for="key in (groupByCase ? ['title', 'status_id'] : ['title', 'case', 'status_id'])" :key="key" :class="'ma-col-' + key" :aria-sort="aria_sort(key)">
                <button type="button" class="cl-sort" :class="{ 'is-active': sort === key }" @click="$emit('sort', key)" :title="'Sort by ' + SORTABLE[key].toLowerCase()">
                  [[ SORTABLE[key] ]]<i :class="['fa-solid', sort_icon(key)]"></i>
                </button>
              </th>
              <th class="ma-col-tags">Tags</th>
              <th class="ma-col-subtasks cl-hide-md">Subtasks</th>
              <th class="ma-col-users cl-hide-md">Assignees</th>
              <th v-for="key in ['deadline', 'last_modif']" :key="key" :class="'ma-col-' + key" :aria-sort="aria_sort(key)">
                <button type="button" class="cl-sort" :class="{ 'is-active': sort === key }" @click="$emit('sort', key)" :title="'Sort by ' + SORTABLE[key].toLowerCase()">
                  [[ SORTABLE[key] ]]<i :class="['fa-solid', sort_icon(key)]"></i>
                </button>
              </th>
              <th class="cl-col-actions"><span class="visually-hidden">Actions</span></th>
            </tr>
          </thead>
          <tbody v-for="g in groups" :key="g.case ? g.case.id : 'all'">
            <tr v-if="groupByCase" class="ma-group-row" :class="{ 'is-collapsed': collapsed[g.case.id] }" @click="toggle_group(g, $event)">
              <td :colspan="nb_columns">
                <button type="button" class="ma-group-toggle" :aria-expanded="!collapsed[g.case.id]"
                  :title="collapsed[g.case.id] ? 'Show the tasks of this case' : 'Hide the tasks of this case'" @click.stop="toggle_group(g)">
                  <i class="fa-solid fa-chevron-down"></i>
                </button>
                <a :href="'/case/' + g.case.id" class="ma-group-head" :title="'Open the case: ' + g.case.title">
                  <i class="fa-solid fa-briefcase"></i><span class="cl-id">#[[ g.case.id ]]</span><span class="ma-group-title">[[ g.case.title ]]</span>
                  <i v-if="g.case.privileged_case" class="fa-solid fa-user-shield cl-priv" title="Privileged case"></i>
                  <i v-if="g.case.is_private" class="fa-solid fa-lock ma-private" title="Private case"></i>
                </a>
                <span class="ma-group-count">[[ g.tasks.length ]] [[ g.tasks.length === 1 ? 'task' : 'tasks' ]]<b v-if="group_late(g)" class="ma-group-late">· [[ group_late(g) ]] late</b></span>
              </td>
            </tr>
            <tr v-for="t in (groupByCase && collapsed[g.case.id] ? [] : g.tasks)" :key="t.id" class="cl-row" @click="open_row(t, $event)">
              <td class="ma-col-title">
                <a :href="href(t)" class="cl-title" :title="'Open the task: ' + t.title">[[ t.title ]]</a>
                <div v-if="has_desc(t)" v-desc-clamp class="cl-desc cl-desc--row" title="Description — click to open the task">
                  <smart_render :code="t.description" language="markdown" bare></smart_render>
                </div>
              </td>
              <td v-if="!groupByCase" class="ma-col-case">
                <case_ref :item="t.case" mode="id"></case_ref>
              </td>
              <td class="ma-col-status_id">
                <span :class="'cl-status cl-status--' + status(t).style" :title="'Status: ' + status(t).name"><i :class="status(t).icon"></i>[[ status(t).name ]]</span>
              </td>
              <td class="ma-col-tags">
                <div v-if="tags(t).length" v-tag-fit class="cl-tags" title="Tags, taxonomies and galaxies — hover a tag for details">
                  <template v-for="g in tags(t)">
                    <tag_badge v-if="g.kind === 'custom'" kind="custom" :label="g.d.name" :color="g.d.color" :icon-class="g.d.icon"></tag_badge>
                    <tag_badge v-else-if="g.kind === 'taxonomy'" kind="taxonomy" :label="g.d.name" :color="g.d.color" :title="g.d.description || g.d.name"></tag_badge>
                    <tag_badge v-else-if="g.kind === 'galaxy'" kind="galaxy" :label="g.d.name" :icon-name="g.d.icon" :title="g.d.description || g.d.name"></tag_badge>
                    <tag_badge v-else kind="cluster" :label="g.d.tag" :icon-name="g.d.icon" :title="g.d.description || g.d.tag" :meta="g.d.meta || ''"></tag_badge>
                  </template>
                </div>
                <span v-else class="cl-none" title="No tag on this task">—</span>
              </td>
              <td class="ma-col-subtasks cl-hide-md">
                <div v-if="subtasks(t).total" class="cl-progress" :title="subtasks(t).done + ' of ' + subtasks(t).total + ' subtasks done'">
                  <div class="cl-bar"><span :style="{ width: subtasks(t).pct + '%' }"></span></div>
                  <small>[[ subtasks(t).done ]]/[[ subtasks(t).total ]]</small>
                </div>
                <span v-else class="cl-none" title="No subtask">—</span>
              </td>
              <td class="ma-col-users cl-hide-md">
                <div v-if="t.users && t.users.length" class="ma-users">
                  <user_chip v-for="u in assignees(t).shown" :key="u.id" :user="u" size="sm"></user_chip>
                  <span v-if="assignees(t).rest.length" class="cl-more-orgs" :title="'Also assigned: ' + assignees(t).title">+[[ assignees(t).rest.length ]]</span>
                </div>
                <span v-else class="cl-none">—</span>
              </td>
              <td class="ma-col-deadline">
                <span v-if="due(t)" :class="['cl-deadline', due(t).state]" :title="due(t).title"><i class="fa-solid fa-hourglass-half"></i>[[ due(t).text ]]</span>
                <span v-else class="cl-none" title="No deadline">—</span>
              </td>
              <td class="ma-col-last_modif"><span :title="'Last modified: ' + full(t.last_modif)">[[ since(t.last_modif) ]]</span></td>
              <td class="cl-col-actions">
                <div class="cl-actions">
                  <template v-if="canEdit">
                    <button v-if="t.completed" type="button" class="btn btn-sm btn-outline-secondary" title="Reopen the task" @click="$emit('complete', t, true)"><i class="fa-solid fa-rotate-left"></i></button>
                    <button v-else type="button" class="btn btn-sm btn-outline-success" title="Complete the task" @click="$emit('complete', t, false)"><i class="fa-solid fa-check"></i></button>
                  </template>
                  <a class="btn btn-sm btn-outline-primary" :href="href(t)" title="Open the task in its case"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ───── cards ───── -->
    <div v-else class="ma-groups">
    <section v-for="g in groups" :key="g.case ? g.case.id : 'all'" :class="{ 'ma-group': groupByCase }">
      <header v-if="groupByCase" class="ma-group-bar" :class="{ 'is-collapsed': collapsed[g.case.id] }" @click="toggle_group(g, $event)">
        <button type="button" class="ma-group-toggle" :aria-expanded="!collapsed[g.case.id]"
          :title="collapsed[g.case.id] ? 'Show the tasks of this case' : 'Hide the tasks of this case'" @click.stop="toggle_group(g)">
          <i class="fa-solid fa-chevron-down"></i>
        </button>
        <a :href="'/case/' + g.case.id" class="ma-group-head" :title="'Open the case: ' + g.case.title">
          <i class="fa-solid fa-briefcase"></i><span class="cl-id">#[[ g.case.id ]]</span><span class="ma-group-title">[[ g.case.title ]]</span>
          <i v-if="g.case.privileged_case" class="fa-solid fa-user-shield cl-priv" title="Privileged case"></i>
          <i v-if="g.case.is_private" class="fa-solid fa-lock ma-private" title="Private case"></i>
        </a>
        <span class="ma-group-count">[[ g.tasks.length ]] [[ g.tasks.length === 1 ? 'task' : 'tasks' ]]<b v-if="group_late(g)" class="ma-group-late">· [[ group_late(g) ]] late</b></span>
      </header>
    <div v-if="!(groupByCase && collapsed[g.case.id])" class="cl-grid">
      <article v-for="t in g.tasks" :key="t.id" class="cl-tile ma-tile" @click="open_row(t, $event)">
        <case_ref v-if="!groupByCase" :item="t.case" mode="id" class="ma-tile-case"></case_ref>
        <header class="cl-tile-head">
          <a :href="href(t)" class="cl-title cl-tile-title" :title="'Open the task: ' + t.title">[[ t.title ]]</a>
          <span :class="'cl-status cl-tile-status cl-status--' + status(t).style" :title="'Status: ' + status(t).name"><i :class="status(t).icon"></i>[[ status(t).name ]]</span>
        </header>

        <div class="cl-tile-meta">
          <span v-if="due(t)" :class="['cl-deadline', due(t).state]" :title="due(t).title"><i class="fa-solid fa-hourglass-half"></i>[[ due(t).text ]]</span>
          <span v-else title="No deadline"><i class="fa-regular fa-calendar-xmark"></i>No deadline</span>
          <span :title="'Last modified: ' + full(t.last_modif)"><i class="fa-solid fa-clock-rotate-left"></i>[[ since(t.last_modif) ]]</span>
          <span v-if="subtasks(t).total" class="cl-progress" :title="subtasks(t).done + ' of ' + subtasks(t).total + ' subtasks done'">
            <i class="fa-solid fa-list-ul"></i><span class="cl-bar"><span :style="{ width: subtasks(t).pct + '%' }"></span></span><small>[[ subtasks(t).done ]]/[[ subtasks(t).total ]]</small>
          </span>
          <span v-if="t.time_required" title="Time required"><i class="fa-solid fa-stopwatch"></i>[[ t.time_required ]]</span>
          <span v-if="t.nb_notes" title="Notes"><i class="fa-solid fa-note-sticky"></i>[[ t.nb_notes ]]</span>
        </div>

        <div v-if="tags(t).length" v-tag-fit class="cl-tags" title="Tags, taxonomies and galaxies — hover a tag for details">
          <template v-for="g in tags(t)">
            <tag_badge v-if="g.kind === 'custom'" kind="custom" :label="g.d.name" :color="g.d.color" :icon-class="g.d.icon"></tag_badge>
            <tag_badge v-else-if="g.kind === 'taxonomy'" kind="taxonomy" :label="g.d.name" :color="g.d.color" :title="g.d.description || g.d.name"></tag_badge>
            <tag_badge v-else-if="g.kind === 'galaxy'" kind="galaxy" :label="g.d.name" :icon-name="g.d.icon" :title="g.d.description || g.d.name"></tag_badge>
            <tag_badge v-else kind="cluster" :label="g.d.tag" :icon-name="g.d.icon" :title="g.d.description || g.d.tag" :meta="g.d.meta || ''"></tag_badge>
          </template>
        </div>

        <div v-if="has_desc(t)" v-desc-clamp class="cl-desc" title="Description — click to open the task">
          <smart_render :code="t.description" language="markdown" bare></smart_render>
        </div>

        <ul v-if="open_subtasks(t).length" class="ma-subtasks" title="Open subtasks">
          <li v-for="s in open_subtasks(t).slice(0, OPEN_SUBTASKS_SHOWN)" :key="s.id"><i class="fa-regular fa-square"></i><span class="ma-subtask-text">[[ s.description ]]</span></li>
          <li v-if="open_subtasks(t).length > OPEN_SUBTASKS_SHOWN" class="ma-subtasks-more">+[[ open_subtasks(t).length - OPEN_SUBTASKS_SHOWN ]] more open</li>
        </ul>

        <footer class="cl-tile-foot">
          <div class="ma-users">
            <template v-if="t.users && t.users.length">
              <user_chip v-for="u in assignees(t).shown" :key="u.id" :user="u" size="sm"></user_chip>
              <span v-if="assignees(t).rest.length" class="cl-more-orgs" :title="'Also assigned: ' + assignees(t).title">+[[ assignees(t).rest.length ]]</span>
            </template>
            <span v-else class="cl-none">No one assigned</span>
          </div>
          <div class="cl-actions">
            <template v-if="canEdit">
              <button v-if="t.completed" type="button" class="btn btn-sm btn-outline-secondary" title="Reopen the task" @click="$emit('complete', t, true)"><i class="fa-solid fa-rotate-left"></i></button>
              <button v-else type="button" class="btn btn-sm btn-outline-success" title="Complete the task" @click="$emit('complete', t, false)"><i class="fa-solid fa-check"></i></button>
            </template>
            <a class="btn btn-sm btn-outline-primary" :href="href(t)" title="Open the task in its case"><i class="fa-solid fa-arrow-up-right-from-square"></i></a>
          </div>
        </footer>
      </article>
    </div>
    </section>
    </div>
    </loading_overlay>
    `,
}
