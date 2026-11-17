/**
 * org-picker.js — Pick one or more organisations, the same way user-picker.js picks users:
 * the chosen organisations are pills (same style as on the admin pages, with ×), and the
 * list shows each organisation's icon, name and description. Type to search, arrows +
 * Enter to pick, Backspace removes the last.
 *
 * Props:
 *   orgs         Array   — Org.to_json() dicts ({id, name, description})
 *   modelValue   Array   — ids of the chosen organisations (v-model)
 *   exclude      Array   — ids not offered (e.g. organisations already in the case)
 *   placeholder  String
 *   multiple     Boolean — several organisations (default true); false = one, replaced on pick
 *   disabled     Boolean
 *
 * Usage:
 *   <org_picker v-model="to_add" :orgs="orgs" :exclude="cases_info.orgs_in_case.map(o => o.id)"></org_picker>
 *   <org_picker v-model="new_owner" :orgs="candidates" :multiple="false"></org_picker>
 */
const { ref, computed, nextTick, onMounted, onBeforeUnmount } = Vue

export default {
    name: 'OrgPicker',
    delimiters: ['[[', ']]'],
    props: {
        orgs: { type: Array, default: () => [] },
        modelValue: { type: Array, default: () => [] },
        exclude: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Pick organisations…' },
        multiple: { type: Boolean, default: true },
        disabled: { type: Boolean, default: false },
    },
    emits: ['update:modelValue'],
    setup(props, { emit }) {
        const root = ref(null)
        const input = ref(null)
        const query = ref('')
        const open = ref(false)
        const active = ref(0)

        const by_id = computed(() => new Map(props.orgs.map(o => [Number(o.id), o])))
        const chosen = computed(() => props.modelValue.map(id => by_id.value.get(Number(id))).filter(Boolean))

        const options = computed(() => {
            const taken = new Set([...props.modelValue, ...props.exclude].map(Number))
            const q = query.value.trim().toLowerCase()
            return props.orgs
                .filter(o => !taken.has(Number(o.id)))
                .filter(o => !q || [o.name, o.description].some(v => (v || '').toLowerCase().includes(q)))
                .sort((a, b) => (a.name || '').localeCompare(b.name || ''))
        })

        function pick(o) {
            if (!o) return
            emit('update:modelValue', props.multiple ? [...props.modelValue, o.id] : [o.id])
            query.value = ''
            active.value = 0
            if (!props.multiple) open.value = false
            nextTick(() => input.value && input.value.focus())
        }

        function remove(id) {
            emit('update:modelValue', props.modelValue.filter(x => Number(x) !== Number(id)))
        }

        function on_key(e) {
            if (e.key === 'ArrowDown') { e.preventDefault(); open.value = true; active.value = Math.min(active.value + 1, options.value.length - 1) }
            else if (e.key === 'ArrowUp') { e.preventDefault(); active.value = Math.max(active.value - 1, 0) }
            else if (e.key === 'Enter') { e.preventDefault(); if (open.value) pick(options.value[active.value]) }
            else if (e.key === 'Escape') { open.value = false }
            else if (e.key === 'Backspace' && !query.value && props.modelValue.length) { remove(props.modelValue[props.modelValue.length - 1]) }
        }

        function on_doc_click(e) { if (root.value && !root.value.contains(e.target)) open.value = false }
        onMounted(() => document.addEventListener('mousedown', on_doc_click))
        onBeforeUnmount(() => document.removeEventListener('mousedown', on_doc_click))

        function focus_input() { if (!props.disabled) { open.value = true; input.value && input.value.focus() } }

        return { root, input, query, open, active, chosen, options, pick, remove, on_key, focus_input }
    },
    template: `
    <div ref="root" :class="['upick', 'opick', { 'upick--open': open, 'upick--disabled': disabled }]">
        <div class="upick-box" @click="focus_input">
            <span v-for="o in chosen" :key="o.id" class="uchip-org opick-chip" :title="o.description || o.name">
                <i class="fa-solid fa-building"></i>[[ o.name ]]
                <button type="button" class="uchip-remove" @click.stop="remove(o.id)" :aria-label="'Remove ' + o.name" title="Remove"><i class="fa-solid fa-xmark"></i></button>
            </span>
            <input ref="input" class="upick-input" v-model="query" :placeholder="chosen.length ? '' : placeholder" :disabled="disabled"
                   @focus="open = true" @input="open = true; active = 0" @keydown="on_key"
                   role="combobox" :aria-expanded="open" aria-autocomplete="list">
            <i class="fa-solid fa-chevron-down upick-caret"></i>
        </div>
        <ul v-if="open" class="upick-menu" role="listbox">
            <li v-if="!options.length" class="upick-none">[[ query ? 'No organisation matches “' + query + '”' : 'No other organisation to pick' ]]</li>
            <li v-for="(o, i) in options" :key="o.id" :class="['upick-option', { 'is-active': i === active }]" role="option" :aria-selected="i === active"
                @mousedown.prevent="pick(o)" @mouseenter="active = i">
                <span class="opick-icon"><i class="fa-solid fa-building"></i></span>
                <span class="upick-text">
                    <span class="upick-name">[[ o.name ]]</span>
                    <span class="upick-sub">[[ o.description || 'No description' ]]</span>
                </span>
            </li>
        </ul>
    </div>
    `
}
