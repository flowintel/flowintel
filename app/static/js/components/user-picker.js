/**
 * user-picker.js — Pick one or more users, shown the same way as user-chip.js:
 * the chosen users are chips (with ×), and the list shows each user's avatar, name,
 * nickname and email. Type to search, arrows + Enter to pick, Backspace removes the last.
 *
 * Props:
 *   users        Array   — User.to_json() dicts to choose from
 *   modelValue   Array   — ids of the chosen users (v-model)
 *   exclude      Array   — ids not offered (e.g. users already assigned)
 *   placeholder  String
 *   multiple     Boolean — several users (default true)
 *   disabled     Boolean
 *
 * Usage:
 *   <user_picker v-model="chosen" :users="users_in_case.users_list" :exclude="task.users.map(u => u.id)"></user_picker>
 */
import user_chip from './user-chip.js'
const { ref, computed, nextTick, onMounted, onBeforeUnmount } = Vue

export default {
    name: 'UserPicker',
    delimiters: ['[[', ']]'],
    components: { user_chip },
    props: {
        users: { type: Array, default: () => [] },
        modelValue: { type: Array, default: () => [] },
        exclude: { type: Array, default: () => [] },
        placeholder: { type: String, default: 'Pick users…' },
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
        const me = window.FI_CURRENT_USER_ID != null ? Number(window.FI_CURRENT_USER_ID) : null

        const by_id = computed(() => new Map(props.users.map(u => [Number(u.id), u])))
        const chosen = computed(() => props.modelValue.map(id => by_id.value.get(Number(id))).filter(Boolean))

        function name_of(u) { return [u.first_name, u.last_name].filter(Boolean).join(' ') || u.nickname || u.email || `User #${u.id}` }

        // Users still offered: not chosen, not excluded, matching the search; the signed-in user first
        const options = computed(() => {
            const taken = new Set([...props.modelValue, ...props.exclude].map(Number))
            const q = query.value.trim().toLowerCase()
            return props.users
                .filter(u => !taken.has(Number(u.id)))
                .filter(u => !q || [name_of(u), u.nickname, u.email].some(v => (v || '').toLowerCase().includes(q)))
                .sort((a, b) => (Number(b.id) === me) - (Number(a.id) === me) || name_of(a).localeCompare(name_of(b)))
        })

        function pick(u) {
            if (!u) return
            const ids = props.multiple ? [...props.modelValue, u.id] : [u.id]
            emit('update:modelValue', ids)
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

        return { root, input, query, open, active, chosen, options, me, name_of, pick, remove, on_key, focus_input }
    },
    template: `
    <div ref="root" :class="['upick', { 'upick--open': open, 'upick--disabled': disabled }]">
        <div class="upick-box" @click="focus_input">
            <user_chip v-for="u in chosen" :key="u.id" :user="u" size="sm" removable no-card @remove="remove(u.id)"></user_chip>
            <input ref="input" class="upick-input" v-model="query" :placeholder="chosen.length ? '' : placeholder" :disabled="disabled"
                   @focus="open = true" @input="open = true; active = 0" @keydown="on_key"
                   role="combobox" :aria-expanded="open" aria-autocomplete="list">
            <i class="fa-solid fa-chevron-down upick-caret"></i>
        </div>
        <ul v-if="open" class="upick-menu" role="listbox">
            <li v-if="!options.length" class="upick-none">[[ query ? 'No user matches “' + query + '”' : 'Everyone is already picked' ]]</li>
            <li v-for="(u, i) in options" :key="u.id" :class="['upick-option', { 'is-active': i === active }]" role="option" :aria-selected="i === active"
                @mousedown.prevent="pick(u)" @mouseenter="active = i">
                <user_chip :user="u" variant="avatar" no-card no-you></user_chip>
                <span class="upick-text">
                    <span class="upick-name">[[ name_of(u) ]] <span v-if="Number(u.id) === me" class="uchip-me">you</span></span>
                    <span class="upick-sub">[[ u.email ]]<template v-if="u.nickname"> · @[[ u.nickname ]]</template></span>
                </span>
            </li>
        </ul>
    </div>
    `
}
