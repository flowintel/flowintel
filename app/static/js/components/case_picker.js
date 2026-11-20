/**
 * case_picker.js — Pick one or more cases to link, in the same style as user-picker.js and
 * connector_picker.js: chosen cases are chips (#id + title, with ×); the list shows the
 * status, ticket, owner organisation and flags of each case.
 *
 * Search (server side, /case/<caseId>/link_candidates?q=…, debounced):
 *   "#123" or "123"  that case first          title / ticket / UUID  substring match
 *   nothing typed    suggestions: cases sharing tags with this case, then recently modified
 * The case itself and the cases already linked are never offered.
 * Type, ↑ ↓ to move, Enter to pick, Backspace removes the last chip, Esc closes.
 *
 * Props:
 *   caseId      Number — the case the links are added to
 *   modelValue  Array  — the chosen cases (objects: {id, title, …}) (v-model)
 *   statuses    Array  — status_info.status, for the status badge
 *
 * Styles: /static/css/components/case_picker.css
 */
const { ref, computed, watch, nextTick, onMounted, onBeforeUnmount } = Vue

export default {
    name: 'CasePicker',
    delimiters: ['[[', ']]'],
    props: {
        caseId: { type: Number, required: true },
        modelValue: { type: Array, default: () => [] },
        statuses: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Search a case: #id, title, ticket…' },
        autofocus: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const root = ref(null), box = ref(null), input = ref(null), menu = ref(null)
        const query = ref('')
        const open = ref(false)
        const active = ref(0)
        const loading = ref(false)
        const sections = ref([])          // [{ label, items }]
        const pos = ref({ top: 0, left: 0, width: 0 })
        let timer = null, seq = 0

        const chosen_ids = computed(() => new Set(props.modelValue.map(c => c.id)))
        // sections without the chosen cases, plus a flat list for the keyboard
        const shown = computed(() => {
            let idx = 0
            return sections.value
                .map(s => ({ label: s.label, items: s.items.filter(c => !chosen_ids.value.has(c.id)).map(c => ({ c, idx: idx++ })) }))
                .filter(s => s.items.length)
        })
        const flat = computed(() => shown.value.flatMap(s => s.items.map(i => i.c)))

        async function load() {
            const my = ++seq
            loading.value = true
            try {
                const res = await fetch(`/case/${props.caseId}/link_candidates?q=${encodeURIComponent(query.value.trim())}`)
                const d = res.ok ? await res.json() : {}
                if (my !== seq) return
                sections.value = d.results ? [{ label: '', items: d.results }]
                    : [{ label: 'Suggested · tags in common', items: d.suggested || [] }, { label: 'Recently modified', items: d.recent || [] }]
                active.value = 0
            } catch (e) {
                if (my === seq) sections.value = []
            } finally {
                if (my === seq) { loading.value = false; nextTick(place) }
            }
        }
        watch(query, () => { clearTimeout(timer); timer = setTimeout(load, 200) })
        watch(open, v => { if (v) { if (!sections.value.length) load(); nextTick(place) } })

        function status(c) { return props.statuses.find(s => s.id === c.status_id) }
        function since(d) { return d && window.dayjs ? dayjs.utc(d).fromNow() : '' }

        function pick(c) {
            if (!c) return
            emit('update:modelValue', [...props.modelValue, c])
            query.value = ''
            active.value = 0
            nextTick(() => { input.value && input.value.focus(); place() })
        }
        function remove(id) { emit('update:modelValue', props.modelValue.filter(c => c.id !== id)); nextTick(place) }

        function on_key(e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); open.value = true; active.value = Math.min(active.value + 1, flat.value.length - 1) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); active.value = Math.max(active.value - 1, 0) }
            else if (e.key === 'Enter') { e.preventDefault(); if (open.value) pick(flat.value[active.value]) }
            else if (e.key === 'Escape') { if (open.value) { e.stopPropagation(); open.value = false } }
            else if (e.key === 'Backspace' && !query.value && props.modelValue.length) remove(props.modelValue[props.modelValue.length - 1].id)
        }

        // the menu is teleported to <body> so a modal never cuts it
        function place() {
            const r = box.value && box.value.getBoundingClientRect()
            if (!r) return
            const h = (menu.value && menu.value.offsetHeight) || 320
            const below = r.bottom + 4 + h <= window.innerHeight || r.top < h + 4
            pos.value = { left: r.left, width: r.width, top: below ? r.bottom + 4 : r.top - h - 4 }
        }
        function on_move() { if (open.value) place() }
        function on_doc_click(e) {
            if (root.value && !root.value.contains(e.target) && !(menu.value && menu.value.contains(e.target))) open.value = false
        }
        onMounted(() => {
            document.addEventListener('mousedown', on_doc_click)
            window.addEventListener('scroll', on_move, true)
            window.addEventListener('resize', on_move)
            if (props.autofocus) nextTick(focus_input)
        })
        onBeforeUnmount(() => {
            clearTimeout(timer)
            document.removeEventListener('mousedown', on_doc_click)
            window.removeEventListener('scroll', on_move, true)
            window.removeEventListener('resize', on_move)
        })
        function focus_input() { open.value = true; input.value && input.value.focus() }

        return { root, box, input, menu, query, open, active, loading, shown, flat, pos, status, since, pick, remove, on_key, focus_input }
    },
    template: /* html */ `
    <div ref="root" :class="['upick', 'kpick', { 'upick--open': open }]">
        <div ref="box" class="upick-box" @click="focus_input">
            <span v-for="c in modelValue" :key="c.id" class="kchip" :title="'#' + c.id + ' ' + c.title">
                <span class="kchip-id">#[[ c.id ]]</span><span class="kchip-title">[[ c.title ]]</span>
                <button type="button" class="kchip-x" @click.stop="remove(c.id)" :aria-label="'Remove case #' + c.id" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            </span>
            <input ref="input" class="upick-input" v-model="query" :placeholder="modelValue.length ? 'Add another case…' : placeholder"
                   @focus="open = true" @input="open = true" @keydown="on_key"
                   role="combobox" :aria-expanded="open" aria-autocomplete="list" aria-label="Search a case to link">
            <i v-if="loading" class="fa-solid fa-circle-notch fa-spin upick-caret"></i>
            <i v-else class="fa-solid fa-magnifying-glass upick-caret"></i>
        </div>
        <teleport to="body">
        <ul v-if="open" ref="menu" class="upick-menu kpick-menu" role="listbox"
            :style="{ top: pos.top + 'px', left: pos.left + 'px', width: pos.width + 'px' }">
            <li v-if="!flat.length" class="upick-none">
                <template v-if="loading">Searching…</template>
                <template v-else-if="query">No case matches “[[ query ]]” <small>(already linked cases are hidden)</small></template>
                <template v-else>Type a case number, a title or a ticket id</template>
            </li>
            <template v-for="s in shown" :key="s.label">
                <li v-if="s.label" class="kpick-group" role="presentation">[[ s.label ]]</li>
                <li v-for="o in s.items" :key="o.c.id" :class="['kpick-option', { 'is-active': o.idx === active, 'is-done': o.c.completed }]"
                    role="option" :aria-selected="o.idx === active" @mousedown.prevent="pick(o.c)" @mouseenter="active = o.idx">
                    <span class="kpick-id">#[[ o.c.id ]]</span>
                    <span class="kpick-main">
                        <span class="kpick-title">[[ o.c.title ]]
                            <i v-if="o.c.is_private" class="fa-solid fa-lock kpick-flag" title="Private case"></i>
                            <i v-if="o.c.privileged" class="fa-solid fa-user-shield kpick-flag kpick-priv" title="Privileged case"></i>
                        </span>
                        <span class="kpick-sub">
                            <span v-if="o.c.ticket_id"><i class="fa-solid fa-ticket"></i>[[ o.c.ticket_id ]]</span>
                            <span v-if="o.c.owner_org"><i class="fa-solid fa-building"></i>[[ o.c.owner_org ]]</span>
                            <span v-if="o.c.last_modif"><i class="fa-solid fa-clock-rotate-left"></i>[[ since(o.c.last_modif) ]]</span>
                            <span v-if="o.c.reason && o.c.reason !== 'recently modified'" class="kpick-reason"><i class="fa-solid fa-tags"></i>[[ o.c.reason ]]</span>
                        </span>
                    </span>
                    <span v-if="o.c.completed" class="kpick-status kpick-status--done">Finished</span>
                    <span v-else-if="status(o.c)" :class="'kpick-status text-bg-' + status(o.c).bootstrap_style">[[ status(o.c).name ]]</span>
                </li>
            </template>
            <li class="kpick-hint" role="presentation"><kbd>↑</kbd><kbd>↓</kbd> move · <kbd>Enter</kbd> add · <kbd>#12</kbd> case number</li>
        </ul>
        </teleport>
    </div>
    `
}
