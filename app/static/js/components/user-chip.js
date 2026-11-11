/**
 * user-chip.js — One way to show a user everywhere: initials avatar + name, and a card
 * with useful details when the mouse (or keyboard focus) stays on it.
 *
 * The avatar colour comes from the user id, so a person keeps the same colour on every
 * page. The card is loaded on first hover from /account/user_card/<id> (only what the
 * viewer is allowed to see), then cached for the whole page.
 *
 * Props:
 *   user       Object  — a User.to_json() dict ({id, first_name, last_name, nickname, email})
 *   userId     Number  — when only an id and a name are known (e.g. history, alerting)
 *   name       String  — display name when there is no user object
 *   email      String  — idem
 *   variant    String  — 'chip' (pill, default), 'inline' (avatar + text, for tables and
 *                        lists) or 'avatar' (avatar only, e.g. stacked assignees)
 *   size       String  — 'sm' or 'md' (default)
 *   removable  Boolean — shows a small × that emits `remove`
 *   noCard     Boolean — no hover card
 *   noYou      Boolean — do not add "you" when the chip is the signed-in user
 *
 * Usage:
 *   <user_chip :user="user"></user_chip>
 *   <user_chip :user-id="entry.user_id" :name="entry.user_name" variant="inline"></user_chip>
 *   <user_chip :user="u" removable @remove="remove_user(u)"></user_chip>
 */
const { ref, computed, onBeforeUnmount, nextTick } = Vue

// Colours that sit well with the Flowintel blue and stay readable with white initials
const PALETTE = ['#1f3763', '#2f6fb0', '#0f7b6c', '#6f42c1', '#b2456e', '#c25b12', '#4d7a1f', '#5a6b7c', '#8a5a00', '#1d6a96']

// Cards already loaded on this page, by user id (a promise, so concurrent hovers share it)
const card_cache = new Map()
// One card open at a time on the page
let close_open_card = null

function load_card(id) {
    if (!card_cache.has(id)) {
        card_cache.set(id, fetch(`/account/user_card/${id}`)
            .then(r => r.ok ? r.json() : null)
            .catch(() => null))
    }
    return card_cache.get(id)
}

export default {
    name: 'UserChip',
    inheritAttrs: false,
    delimiters: ['[[', ']]'],
    props: {
        user: { type: Object, default: null },
        userId: { type: [Number, String], default: null },
        name: { type: String, default: '' },
        email: { type: String, default: '' },
        variant: { type: String, default: 'chip' },
        size: { type: String, default: 'md' },
        removable: { type: Boolean, default: false },
        noCard: { type: Boolean, default: false },
        noYou: { type: Boolean, default: false },
    },
    emits: ['remove'],
    setup(props) {
        const root = ref(null)
        const open = ref(false)
        const card = ref(null)        // loaded details | null
        const loading = ref(false)
        const pos = ref({ top: 0, left: 0, above: false })
        const copied = ref(false)
        let show_timer = null
        let hide_timer = null

        const id = computed(() => {
            const v = props.user ? props.user.id : props.userId
            return v === null || v === undefined || v === '' ? null : Number(v)
        })

        const full_name = computed(() => {
            const u = props.user
            if (u) {
                const n = [u.first_name, u.last_name].filter(Boolean).join(' ').trim()
                return n || u.nickname || u.email || (id.value ? `User #${id.value}` : 'Unknown user')
            }
            return props.name || props.email || (id.value ? `User #${id.value}` : 'Unknown user')
        })

        const initials = computed(() => {
            const parts = full_name.value.replace(/@.*/, '').split(/[\s._-]+/).filter(Boolean)
            if (!parts.length) return '?'
            return ((parts[0][0] || '') + (parts.length > 1 ? parts[parts.length - 1][0] : '')).toUpperCase()
        })

        const color = computed(() => {
            const key = id.value !== null ? String(id.value) : full_name.value
            let h = 0
            for (const c of key) h = (h * 31 + c.charCodeAt(0)) >>> 0
            return PALETTE[h % PALETTE.length]
        })

        // The signed-in user (base.html sets FI_CURRENT_USER_ID)
        const is_me = computed(() => id.value !== null && window.FI_CURRENT_USER_ID != null && id.value === Number(window.FI_CURRENT_USER_ID))

        const has_card = computed(() => !props.noCard && id.value !== null)

        function place() {
            const el = root.value
            if (!el) return
            const r = el.getBoundingClientRect()
            const width = 280
            const left = Math.max(8, Math.min(r.left, window.innerWidth - width - 8))
            const above = r.bottom + 230 > window.innerHeight && r.top > 230
            pos.value = { left, top: above ? r.top - 8 : r.bottom + 8, above }
        }

        async function show() {
            if (!has_card.value) return
            clearTimeout(hide_timer)
            clearTimeout(show_timer)
            show_timer = setTimeout(async () => {
                if (close_open_card && close_open_card !== hide_now) close_open_card()
                close_open_card = hide_now
                place()
                open.value = true
                if (!card.value) {
                    loading.value = true
                    card.value = await load_card(id.value)
                    loading.value = false
                    await nextTick()
                    place()
                }
            }, 300)
        }

        function hide() {
            clearTimeout(show_timer)
            hide_timer = setTimeout(hide_now, 150)
        }

        function hide_now() {
            clearTimeout(show_timer)
            clearTimeout(hide_timer)
            open.value = false
            if (close_open_card === hide_now) close_open_card = null
        }

        async function copy_email() {
            const mail = (card.value && card.value.email) || (props.user && props.user.email) || props.email
            if (!mail) return
            try {
                await navigator.clipboard.writeText(mail)
                copied.value = true
                setTimeout(() => { copied.value = false }, 1200)
            } catch (e) {}
        }

        function on_key(e) {
            if (e.key === 'Escape') hide_now()
        }

        onBeforeUnmount(() => { clearTimeout(show_timer); clearTimeout(hide_timer); if (close_open_card === hide_now) close_open_card = null })

        return { is_me, root, open, card, loading, pos, copied, full_name, initials, color, has_card, show, hide, hide_now, copy_email, on_key }
    },
    template: `
    <span ref="root" v-bind="$attrs" :class="['uchip', 'uchip--' + variant, 'uchip--' + size, { 'uchip--hover': has_card }]"
          :tabindex="has_card ? 0 : null" :aria-label="is_me ? full_name + ' (you)' : full_name"
          :title="has_card ? null : full_name"
          @mouseenter="show" @mouseleave="hide" @focus="show" @blur="hide" @keydown="on_key">
        <span :class="['uchip-avatar', { 'uchip-avatar--me': is_me && !noYou }]" :style="{ background: color }" aria-hidden="true">[[ initials ]]</span>
        <span v-if="variant !== 'avatar'" class="uchip-name">[[ full_name ]]</span>
        <span v-if="is_me && !noYou && variant !== 'avatar'" class="uchip-me">you</span>
        <button v-if="removable" type="button" class="uchip-remove" @click.stop="$emit('remove')" :aria-label="'Remove ' + full_name" title="Remove">
            <i class="fa-solid fa-xmark"></i>
        </button>
    </span>
    <teleport to="body">
        <div v-if="open" :class="['uchip-card', { 'uchip-card--above': pos.above }]" :style="{ top: pos.top + 'px', left: pos.left + 'px' }"
             role="dialog" :aria-label="full_name" @mouseenter="show" @mouseleave="hide">
            <div class="uchip-card-head">
                <span class="uchip-avatar uchip-avatar--lg" :style="{ background: color }" aria-hidden="true">[[ initials ]]</span>
                <div class="uchip-card-titles">
                    <div class="uchip-card-name">[[ full_name ]] <span v-if="card && card.is_me" class="uchip-me">you</span></div>
                    <div v-if="card && card.nickname" class="uchip-card-nick">@[[ card.nickname ]]</div>
                </div>
            </div>
            <div v-if="loading" class="uchip-card-loading"><span class="spinner-border spinner-border-sm me-2"></span>Loading…</div>
            <template v-else-if="card">
                <div v-if="card.email" class="uchip-card-row">
                    <i class="fa-solid fa-envelope fa-fw"></i>
                    <a :href="'mailto:' + card.email" class="text-truncate">[[ card.email ]]</a>
                    <button type="button" class="uchip-copy" @click="copy_email" :title="copied ? 'Copied' : 'Copy the email'">
                        <i :class="['fa-solid', copied ? 'fa-check' : 'fa-copy']"></i>
                    </button>
                </div>
                <div v-if="card.org" class="uchip-card-row"><i class="fa-solid fa-building fa-fw"></i><span>[[ card.org.name ]]</span></div>
                <div v-if="card.role" class="uchip-card-row">
                    <i class="fa-solid fa-user-shield fa-fw"></i>
                    <span v-if="card.role_admin" class="uchip-admin" title="Full access to the instance"><i class="fa-solid fa-shield-halved"></i>[[ card.role ]]</span>
                    <span v-else>[[ card.role ]]</span>
                </div>
                <div class="uchip-card-stats">
                    <span title="Open tasks assigned to this user, in the cases you can see"><b>[[ card.open_tasks ]]</b> open [[ card.open_tasks === 1 ? 'task' : 'tasks' ]]</span>
                    <span v-if="card.member_since" title="Account created">since [[ card.member_since ]]</span>
                </div>
                <div v-if="card.last_login !== undefined" class="uchip-card-admin">
                    <span><i class="fa-solid fa-right-to-bracket fa-fw"></i>Last login: [[ card.last_login || 'never' ]]</span>
                    <span v-if="card.auth_provider" class="uchip-auth">[[ card.auth_provider ]]</span>
                </div>
            </template>
            <div v-else class="uchip-card-row text-muted small">No more details available.</div>
        </div>
    </teleport>
    `
}
