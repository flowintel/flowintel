/**
 * case_list.js — the list of cases on the case index (/case/), as a sortable table or as cards.
 *
 *   <case_list :cases="case_list.cases" :status-info="status_info" view="table"
 *              sort="last_modif" order="desc"
 *              @sort="(key) => ..." @complete="(case_loc, revive) => ..."></case_list>
 *
 * The component only renders: sorting and pagination are done by the server
 * (/case/sort_cases?filter=<key>&order=<asc|desc>), so a click on a column header emits
 * `sort` with the column key and the page fetches again.
 * tags-clickable: a click on a tag emits `tag` with { kind: 'tag' | 'cluster', value }.
 * Needs the `v-tag-fit` directive and `dayjs` (with the utc + relativeTime plugins).
 * Styles: /static/css/components/case_list.css
 */
import tag_badge from './tag-badge.js'
import tag_fit from './tag-fit.js'
import smart_render from './smart-render.js'
import loading_overlay from './loading_overlay.js'

// v-desc-clamp: the description is cut after 3 lines (CSS max-height); the fade is added only
// when the text really overflows. The markdown renders after mount, hence the observers.
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

// Icon of each default status (init_db.py); a custom status falls back to a dot.
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

// Columns the server can sort on (CaseCore.ALLOWED_SORT_COLUMNS + title).
const SORTABLE = {
    id:          'ID',
    title:       'Title',
    status_id:   'Status',
    deadline:    'Deadline',
    last_modif:  'Last modified',
}

export default {
    name: 'case_list',
    delimiters: ['[[', ']]'],
    components: { tag_badge, smart_render, loading_overlay },
    directives: { 'tag-fit': tag_fit, 'desc-clamp': desc_clamp },
    props: {
        cases:      { type: Array, default: () => [] },
        statusInfo: { type: Object, default: null },
        view:       { type: String, default: 'table' },   // 'table' | 'cards'
        sort:       { type: String, default: 'last_modif' },
        order:      { type: String, default: 'desc' },
        loading:    { type: Boolean, default: false },
        tagsClickable: { type: Boolean, default: false },   // a click on a tag emits `tag` (the index adds it to its filter)
    },
    emits: ['sort', 'complete', 'tag'],
    data() {
        return {}
    },
    methods: {
        status(c) {
            const s = this.statusInfo?.status?.find(x => x.id === c.status_id)
            const name = s?.name || 'Unknown'
            return { name, style: s?.bootstrap_style || 'secondary', icon: STATUS_ICONS[name] || 'fa-solid fa-circle' }
        },
        tags(c) {
            return [
                ...(c.custom_tags || []).map(d => ({ kind: 'custom', d })),
                ...(c.tags || []).map(d => ({ kind: 'taxonomy', d })),
                ...(c.clusters || []).map(d => ({ kind: 'cluster', d })),
            ]
        },
        tasks(c) {
            const done = c.closed_tasks || 0, total = done + (c.open_tasks || 0)
            return { done, total, pct: total ? Math.round(100 * done / total) : 0 }
        },
        other_orgs(c) {
            return (c.orgs_in_case || []).filter(o => o.name !== c.owner_org_name)
        },
        has_desc(c) { return !!(c.description && c.description.trim() && c.description.trim() !== '-') },
        since(d) { return d ? dayjs.utc(d).fromNow() : '' },
        full(d) { return d ? dayjs.utc(d).local().format('YYYY-MM-DD HH:mm') : '' },
        deadline_state(c) {
            if (!c.deadline) return ''
            const days = dayjs.utc(c.deadline).diff(dayjs.utc(), 'day', true)
            if (days < 0) return 'is-late'
            if (days <= 7) return 'is-soon'
            return ''
        },
        can_act(c) {
            const p = c.current_user_permission || {}
            return !p.read_only && (c.present_in_case || p.admin)
        },
        can_complete(c) {
            const p = c.current_user_permission || {}
            return !c.privileged_case || p.admin || p.case_admin
        },
        sort_icon(key) {
            if (this.sort !== key) return 'fa-sort'
            return this.order === 'asc' ? 'fa-sort-up' : 'fa-sort-down'
        },
        aria_sort(key) {
            if (this.sort !== key) return 'none'
            return this.order === 'asc' ? 'ascending' : 'descending'
        },
        // `tag` payload: { kind: 'tag' | 'cluster', value } — the value the tag filter uses
        tag_click(t, e) {
            if (!this.tagsClickable) return
            e.preventDefault(); e.stopPropagation()
            this.$emit('tag', t.kind === 'cluster' ? { kind: 'cluster', value: t.d.tag } : { kind: 'tag', value: t.d.name })
        },
        // A click anywhere on a row opens the case, except on links, buttons and the tag "+N".
        open_row(c, e) {
            if (e.target.closest('a, button, .tg-more, [data-tg-name]')) return
            if (e.ctrlKey || e.metaKey || e.button === 1) window.open(`/case/${c.id}`, '_blank')
            else window.location.href = `/case/${c.id}`
        },
    },
    computed: {
        SORTABLE: () => SORTABLE,
    },
    template: /* html */ `
    <loading_overlay :loading="loading" :empty="!cases.length" label="Loading cases…">
    <!-- first load: skeleton of the list, in the current view -->
    <template #skeleton>
    <div v-if="view === 'table'" class="cl-card">
      <table class="table cl-table">
        <thead><tr><th v-for="n in 8" :key="n"><span class="lo-sk" style="width: 60%"></span></th></tr></thead>
        <tbody>
          <tr v-for="n in 8" :key="n">
            <td><span class="lo-sk" style="width: 28px"></span></td>
            <td><span class="lo-sk" :style="{ width: (55 + (n * 7) % 35) + '%' }"></span><span class="lo-sk lo-sk-sm" style="width: 30%"></span></td>
            <td><span class="lo-sk lo-sk-pill"></span></td>
            <td><span class="lo-sk" style="width: 80%"></span></td>
            <td><span class="lo-sk" style="width: 70px"></span></td>
            <td><span class="lo-sk" style="width: 70px"></span></td>
            <td><span class="lo-sk" style="width: 60px"></span></td>
            <td><span class="lo-sk" style="width: 60px"></span></td>
          </tr>
        </tbody>
      </table>
    </div>
    <div v-else class="cl-grid lo-skeleton">
      <article v-for="n in 4" :key="n" class="cl-tile">
        <header class="cl-tile-head"><span class="lo-sk" style="width: 34px"></span><span class="lo-sk" :style="{ width: (35 + (n * 11) % 30) + '%' }"></span><span class="lo-sk lo-sk-pill cl-tile-status"></span></header>
        <div class="cl-tile-meta"><span class="lo-sk" style="width: 90px"></span><span class="lo-sk" style="width: 110px"></span><span class="lo-sk" style="width: 80px"></span></div>
        <div class="cl-tile-meta"><span class="lo-sk lo-sk-pill" v-for="t in 4" :key="t"></span></div>
        <div><span class="lo-sk lo-sk-sm" style="width: 90%"></span><span class="lo-sk lo-sk-sm" style="width: 65%"></span></div>
        <footer class="cl-tile-foot"><span class="lo-sk" style="width: 180px"></span></footer>
      </article>
    </div>

    </template>

    <!-- ───── table ───── -->
    <div v-if="view === 'table'" class="cl-card">
      <div class="table-responsive">
        <table class="table cl-table">
          <thead>
            <tr>
              <th v-for="key in ['id', 'title', 'status_id']" :key="key" :class="'cl-col-' + key" :aria-sort="aria_sort(key)">
                <button type="button" class="cl-sort" :class="{ 'is-active': sort === key }" @click="$emit('sort', key)"
                        :title="'Sort by ' + SORTABLE[key].toLowerCase()">
                  [[ SORTABLE[key] ]]<i :class="['fa-solid', sort_icon(key)]"></i>
                </button>
              </th>
              <th class="cl-col-tags">Tags</th>
              <th class="cl-col-tasks">Tasks</th>
              <th class="cl-col-orgs cl-hide-md">Organisations</th>
              <th v-for="key in ['deadline', 'last_modif']" :key="key" :class="['cl-col-' + key, key === 'deadline' ? 'cl-hide-md' : '']" :aria-sort="aria_sort(key)">
                <button type="button" class="cl-sort" :class="{ 'is-active': sort === key }" @click="$emit('sort', key)"
                        :title="key === 'deadline' ? 'Sort by deadline (cases without a deadline are hidden)' : 'Sort by ' + SORTABLE[key].toLowerCase()">
                  [[ SORTABLE[key] ]]<i :class="['fa-solid', sort_icon(key)]"></i>
                </button>
              </th>
              <th class="cl-col-actions"><span class="visually-hidden">Actions</span></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="c in cases" :key="c.id" class="cl-row" @click="open_row(c, $event)">
              <td class="cl-col-id"><span class="cl-id" :title="'Case ID ' + c.id">#[[ c.id ]]</span></td>
              <td class="cl-col-title">
                <a :href="'/case/' + c.id" class="cl-title" :title="'Open the case: ' + c.title">[[ c.title ]]</a>
                <div class="cl-sub">
                  <span v-if="c.is_private" class="cl-vis cl-vis--private" title="Private case: only the organisations in the case can see it"><i class="fa-solid fa-lock"></i>Private</span>
                  <span v-else class="cl-vis" title="Public case: visible to every organisation on this instance"><i class="fa-solid fa-globe"></i>Public</span>
                  <span v-if="c.privileged_case" class="cl-priv" title="Privileged case: restricted actions, only an Admin or Case Admin can complete it"><i class="fa-solid fa-user-shield"></i>Privileged</span>
                  <span v-if="c.ticket_id" title="Ticket ID"><i class="fa-solid fa-ticket"></i>[[ c.ticket_id ]]</span>
                  <span v-if="c.has_misp_event" title="Linked to a MISP event">
                    <img v-if="c.misp_icon" :src="'/static/icons/' + c.misp_icon" alt="">MISP
                  </span>
                </div>
                <div v-if="has_desc(c)" v-desc-clamp class="cl-desc cl-desc--row" title="Description — click to open the case and read it all">
                  <smart_render :code="c.description" language="markdown" bare></smart_render>
                </div>
              </td>
              <td class="cl-col-status">
                <span :class="'cl-status cl-status--' + status(c).style" :title="'Status: ' + status(c).name"><i :class="status(c).icon"></i>[[ status(c).name ]]</span>
              </td>
              <td class="cl-col-tags">
                <div v-tag-fit class="cl-tags" title="Tags, taxonomies and galaxies — hover a tag for details">
                  <template v-for="t in tags(c)">
                    <tag_badge v-if="t.kind === 'custom'" :class="{ 'cl-tag-click': tagsClickable }" @click="tag_click(t, $event)" kind="custom" :label="t.d.name" :color="t.d.color" :icon-class="t.d.icon"></tag_badge>
                    <tag_badge v-else-if="t.kind === 'taxonomy'" :class="{ 'cl-tag-click': tagsClickable }" @click="tag_click(t, $event)" kind="taxonomy" :label="t.d.name" :color="t.d.color" :title="t.d.description || t.d.name"></tag_badge>
                    <tag_badge v-else :class="{ 'cl-tag-click': tagsClickable }" @click="tag_click(t, $event)" kind="cluster" :label="t.d.tag" :icon-name="t.d.icon" :title="t.d.description || t.d.tag" :meta="t.d.meta || ''"></tag_badge>
                  </template>
                </div>
                <span v-if="!tags(c).length" class="cl-none" title="No tag, taxonomy or galaxy on this case">—</span>
              </td>
              <td class="cl-col-tasks">
                <div v-if="tasks(c).total" class="cl-progress" :title="tasks(c).done + ' of ' + tasks(c).total + ' tasks closed'">
                  <div class="cl-bar"><span :style="{ width: tasks(c).pct + '%' }"></span></div>
                  <small>[[ tasks(c).done ]]/[[ tasks(c).total ]]</small>
                </div>
                <span v-else class="cl-none" title="This case has no task yet">No task</span>
              </td>
              <td class="cl-col-orgs cl-hide-md">
                <span class="cl-org" :title="'Owner organisation: ' + c.owner_org_name"><i class="fa-solid fa-building"></i>[[ c.owner_org_name ]]</span>
                <span v-if="other_orgs(c).length" class="cl-more-orgs" :title="'Also in the case: ' + other_orgs(c).map(o => o.name).join(', ')">+[[ other_orgs(c).length ]]</span>
              </td>
              <td class="cl-col-deadline cl-hide-md">
                <span v-if="c.deadline" :class="['cl-deadline', deadline_state(c)]" :title="'Deadline: ' + full(c.deadline) + (deadline_state(c) === 'is-late' ? ' (overdue)' : deadline_state(c) === 'is-soon' ? ' (less than 7 days)' : '')">
                  <i class="fa-solid fa-hourglass-half"></i>[[ since(c.deadline) ]]
                </span>
                <span v-else class="cl-none" title="No deadline">—</span>
              </td>
              <td class="cl-col-last_modif"><span :title="'Last modified: ' + full(c.last_modif)">[[ since(c.last_modif) ]]</span></td>
              <td class="cl-col-actions">
                <div v-if="can_act(c)" class="cl-actions">
                  <button v-if="c.completed" type="button" class="btn btn-sm btn-outline-secondary" title="Revive the case" @click="$emit('complete', c, true)">
                    <i class="fa-solid fa-rotate-left"></i>
                  </button>
                  <span v-else :title="can_complete(c) ? 'Complete the case' : 'A privileged case can only be completed by an Admin or Case Admin'">
                    <button type="button" class="btn btn-sm btn-outline-success" :disabled="!can_complete(c)" @click="$emit('complete', c, false)">
                      <i class="fa-solid fa-check"></i>
                    </button>
                  </span>
                  <a class="btn btn-sm btn-outline-primary" :href="'/case/edit/' + c.id" title="Edit the case"><i class="fa-solid fa-pen-to-square"></i></a>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- ───── cards: one per row, everything read left to right ───── -->
    <div v-else class="cl-grid">
      <article v-for="c in cases" :key="c.id" class="cl-tile" @click="open_row(c, $event)">
        <header class="cl-tile-head">
          <span class="cl-id" :title="'Case ID ' + c.id">#[[ c.id ]]</span>
          <a :href="'/case/' + c.id" class="cl-title cl-tile-title" :title="'Open the case: ' + c.title">[[ c.title ]]</a>
          <span class="cl-tile-icons">
            <i v-if="c.is_private" class="fa-solid fa-lock" title="Private case: only the organisations in the case can see it"></i>
            <i v-else class="fa-solid fa-globe" title="Public case: visible to every organisation on this instance"></i>
            <i v-if="c.privileged_case" class="fa-solid fa-user-shield cl-priv" title="Privileged case: restricted actions, only an Admin or Case Admin can complete it"></i>
            <img v-if="c.has_misp_event && c.misp_icon" :src="'/static/icons/' + c.misp_icon" title="Linked to a MISP event" alt="MISP">
          </span>
          <span :class="'cl-status cl-tile-status cl-status--' + status(c).style" :title="'Status: ' + status(c).name"><i :class="status(c).icon"></i>[[ status(c).name ]]</span>
        </header>

        <div class="cl-tile-meta">
          <span :title="'Last modified: ' + full(c.last_modif)"><i class="fa-solid fa-clock-rotate-left"></i>[[ since(c.last_modif) ]]</span>
          <span :title="'Owner organisation: ' + c.owner_org_name"><i class="fa-solid fa-building"></i>[[ c.owner_org_name ]]<b v-if="other_orgs(c).length" class="cl-more-orgs" :title="'Also in the case: ' + other_orgs(c).map(o => o.name).join(', ')">+[[ other_orgs(c).length ]]</b></span>
          <span v-if="c.ticket_id" title="Ticket ID"><i class="fa-solid fa-ticket"></i>[[ c.ticket_id ]]</span>
          <span v-if="c.deadline" :class="['cl-deadline', deadline_state(c)]" :title="'Deadline: ' + full(c.deadline) + (deadline_state(c) === 'is-late' ? ' (overdue)' : deadline_state(c) === 'is-soon' ? ' (less than 7 days)' : '')"><i class="fa-solid fa-hourglass-half"></i>[[ since(c.deadline) ]]</span>
          <span v-if="tasks(c).total" class="cl-progress" :title="tasks(c).done + ' of ' + tasks(c).total + ' tasks closed'">
            <i class="fa-solid fa-list-check"></i><span class="cl-bar"><span :style="{ width: tasks(c).pct + '%' }"></span></span><small>[[ tasks(c).done ]]/[[ tasks(c).total ]]</small>
          </span>
          <span v-else title="This case has no task yet"><i class="fa-solid fa-list-check"></i>No task</span>
        </div>

        <div v-if="tags(c).length" v-tag-fit class="cl-tags" title="Tags, taxonomies and galaxies — hover a tag for details">
          <template v-for="t in tags(c)">
            <tag_badge v-if="t.kind === 'custom'" :class="{ 'cl-tag-click': tagsClickable }" @click="tag_click(t, $event)" kind="custom" :label="t.d.name" :color="t.d.color" :icon-class="t.d.icon"></tag_badge>
            <tag_badge v-else-if="t.kind === 'taxonomy'" :class="{ 'cl-tag-click': tagsClickable }" @click="tag_click(t, $event)" kind="taxonomy" :label="t.d.name" :color="t.d.color" :title="t.d.description || t.d.name"></tag_badge>
            <tag_badge v-else :class="{ 'cl-tag-click': tagsClickable }" @click="tag_click(t, $event)" kind="cluster" :label="t.d.tag" :icon-name="t.d.icon" :title="t.d.description || t.d.tag" :meta="t.d.meta || ''"></tag_badge>
          </template>
        </div>

        <div v-if="has_desc(c)" v-desc-clamp class="cl-desc" title="Description — click to open the case and read it all">
          <smart_render :code="c.description" language="markdown" bare></smart_render>
        </div>

        <footer class="cl-tile-foot">
          <div class="cl-counts">
            <span title="Files attached to the case"><i class="fa-solid fa-file-lines"></i>[[ (c.files || []).length ]]</span>
            <span title="MISP objects in the case"><i class="misp-icon misp-icon-object misp-simple"></i>[[ c.nb_objects || 0 ]]</span>
            <span title="Standalone MISP attributes (not in an object)"><i class="misp-icon misp-icon-attribute misp-simple"></i>[[ c.nb_standalone_attrs || 0 ]]</span>
            <span title="Cases linked to this one"><i class="fa-solid fa-link"></i>[[ (c.link_to || []).length ]]</span>
            <span title="Connectors (MISP, AIL…) linked to the case"><i class="fa-solid fa-plug"></i>[[ (c.connectors || []).length ]]</span>
          </div>
          <div v-if="can_act(c)" class="cl-actions">
            <button v-if="c.completed" type="button" class="btn btn-sm btn-outline-secondary" title="Revive the case" @click="$emit('complete', c, true)">
              <i class="fa-solid fa-rotate-left"></i>
            </button>
            <span v-else :title="can_complete(c) ? 'Complete the case' : 'A privileged case can only be completed by an Admin or Case Admin'">
              <button type="button" class="btn btn-sm btn-outline-success" :disabled="!can_complete(c)" @click="$emit('complete', c, false)">
                <i class="fa-solid fa-check"></i>
              </button>
            </span>
            <a class="btn btn-sm btn-outline-primary" :href="'/case/edit/' + c.id" title="Edit the case"><i class="fa-solid fa-pen-to-square"></i></a>
          </div>
        </footer>
      </article>
    </div>
    </loading_overlay>
    `,
}
