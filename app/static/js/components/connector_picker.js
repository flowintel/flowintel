/**
 * connector_picker.js — Pick one or more connector instances, in the same style as
 * user-picker.js: the chosen instances are chips (icon + name, with ×), the list is grouped
 * by connector type and shows each instance's icon, name and URL. Type to search, arrows +
 * Enter to pick, Backspace removes the last.
 *
 * Props:
 *   instances   Object — { "<connector type>": [instance.to_json(), …] } (from /case/get_connectors)
 *   icons       Object — { "<connector type>": "<icon file uuid>" } (optional)
 *   modelValue  Array  — ids of the chosen instances (v-model)
 *   exclude     Array  — ids not offered (instances already linked)
 *   placeholder String
 *
 * Styles: /static/css/components/connectors.css
 */
const { ref, computed, nextTick, watch, onMounted, onBeforeUnmount } = Vue

export default {
    name: 'ConnectorPicker',
    delimiters: ['[[', ']]'],
    props: {
        instances: { type: Object, default: () => ({}) },
        icons: { type: Object, default: () => ({}) },
        modelValue: { type: Array, default: () => [] },
        exclude: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Pick connector instances…' },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const root = ref(null)
        const input = ref(null)
        const query = ref('')
        const open = ref(false)
        const active = ref(0)
        const box = ref(null)
        const menu = ref(null)
        const pos = ref({ top: 0, left: 0, width: 0 })

        // flat list: every instance with its connector type
        const all = computed(() => Object.entries(props.instances || {})
            .flatMap(([type, list]) => (list || []).filter(Boolean).map(i => ({ ...i, type }))))
        const by_id = computed(() => new Map(all.value.map(i => [String(i.id), i])))
        const chosen = computed(() => props.modelValue.map(id => by_id.value.get(String(id))).filter(Boolean))

        const options = computed(() => {
            const taken = new Set([...props.modelValue, ...props.exclude].map(String))
            const q = query.value.trim().toLowerCase()
            return all.value
                .filter(i => !taken.has(String(i.id)))
                .filter(i => !q || [i.name, i.type, i.url].some(v => (v || '').toLowerCase().includes(q)))
        })
        // options grouped by type, keeping a flat index for the keyboard
        const groups = computed(() => {
            const out = []
            options.value.forEach((i, idx) => {
                let g = out[out.length - 1]
                if (!g || g.type !== i.type) out.push(g = { type: i.type, items: [] })
                g.items.push({ inst: i, idx })
            })
            return out
        })

        function icon(type) { return props.icons && props.icons[type] ? '/static/icons/' + props.icons[type] : null }
        function host(url) { try { return new URL(url).host } catch (e) { return url || '' } }

        function pick(i) {
            if (!i) return
            emit('update:modelValue', [...props.modelValue, i.id])
            query.value = ''
            active.value = 0
            nextTick(() => input.value && input.value.focus())
        }
        function remove(id) { emit('update:modelValue', props.modelValue.filter(x => String(x) !== String(id))) }

        function on_key(e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); open.value = true; active.value = Math.min(active.value + 1, options.value.length - 1) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); active.value = Math.max(active.value - 1, 0) }
            else if (e.key === 'Enter') { e.preventDefault(); if (open.value) pick(options.value[active.value]) }
            else if (e.key === 'Escape') { open.value = false }
            else if (e.key === 'Backspace' && !query.value && props.modelValue.length) remove(props.modelValue[props.modelValue.length - 1])
        }
        // the menu is teleported to <body> (a scrolling modal would cut it): keep it under the box
        function place() {
            const r = box.value && box.value.getBoundingClientRect()
            if (!r) return
            const h = (menu.value && menu.value.offsetHeight) || 280
            const below = r.bottom + 4 + h <= window.innerHeight || r.top < h + 4
            pos.value = { left: r.left, width: r.width, top: below ? r.bottom + 4 : r.top - h - 4 }
        }
        watch(open, v => { if (v) nextTick(place) })
        watch(() => props.modelValue.length, () => { if (open.value) nextTick(place) })
        function on_move() { if (open.value) place() }
        function on_doc_click(e) {
            if (root.value && !root.value.contains(e.target) && !(menu.value && menu.value.contains(e.target))) open.value = false
        }
        onMounted(() => {
            document.addEventListener('mousedown', on_doc_click)
            window.addEventListener('scroll', on_move, true)
            window.addEventListener('resize', on_move)
        })
        onBeforeUnmount(() => {
            document.removeEventListener('mousedown', on_doc_click)
            window.removeEventListener('scroll', on_move, true)
            window.removeEventListener('resize', on_move)
        })
        function focus_input() { open.value = true; input.value && input.value.focus() }

        return { root, input, box, menu, pos, query, open, active, chosen, options, groups, icon, host, pick, remove, on_key, focus_input }
    },
    template: `
    <div ref="root" :class="['upick', 'cpick', { 'upick--open': open }]">
        <div ref="box" class="upick-box" @click="focus_input">
            <span v-for="i in chosen" :key="i.id" class="cchip cchip--sm" :title="i.type + ' — ' + (i.url || '')">
                <img v-if="icon(i.type)" :src="icon(i.type)" alt="" class="cchip-icon"><i v-else class="fa-solid fa-plug cchip-icon"></i>
                <span class="cchip-name">[[ i.name ]]</span>
                <button type="button" class="cchip-x" @click.stop="remove(i.id)" :aria-label="'Remove ' + i.name" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            </span>
            <input ref="input" class="upick-input" v-model="query" :placeholder="chosen.length ? '' : placeholder"
                   @input="open = true; active = 0" @keydown="on_key"
                   role="combobox" :aria-expanded="open" aria-autocomplete="list">
            <i class="fa-solid fa-chevron-down upick-caret"></i>
        </div>
        <teleport to="body">
        <ul v-if="open" ref="menu" class="upick-menu cpick-menu" role="listbox"
            :style="{ top: pos.top + 'px', left: pos.left + 'px', width: pos.width + 'px' }">
            <li v-if="!options.length" class="upick-none">[[ query ? 'No instance matches “' + query + '”' : 'Every instance is already linked' ]]</li>
            <template v-for="g in groups" :key="g.type">
                <li class="cpick-group" role="presentation">[[ g.type ]]</li>
                <li v-for="o in g.items" :key="o.inst.id" :class="['upick-option', { 'is-active': o.idx === active }]" role="option" :aria-selected="o.idx === active"
                    @mousedown.prevent="pick(o.inst)" @mouseenter="active = o.idx">
                    <span class="cpick-icon"><img v-if="icon(o.inst.type)" :src="icon(o.inst.type)" alt=""><i v-else class="fa-solid fa-plug"></i></span>
                    <span class="upick-text">
                        <span class="upick-name">[[ o.inst.name ]]</span>
                        <span class="upick-sub">[[ host(o.inst.url) ]]<template v-if="o.inst.description"> · [[ o.inst.description ]]</template></span>
                    </span>
                </li>
            </template>
        </ul>
        </teleport>
    </div>
    `
}
