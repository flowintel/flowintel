/**
 * tag-badge.js — one display for every tag-like thing: MISP taxonomy tags, galaxy clusters,
 * galaxies, custom tags and connector (remote) tags. Styled by static/css/tag-chips.css.
 *
 * Look copied from the MISP "Overmind" events index (EventIndexHelper::chip / ::markings):
 *   - taxonomy tag  → neutral chip, 3px left edge in the tag colour, "<small>ns</small> value"
 *                     (ns:pred="value" shows pred as the namespace, like MISP)
 *   - TLP / PAP     → marking: "<small>tlp</small> <b>red</b>" tinted with the tag colour
 *   - cluster       → violet chip with the galaxy icon and the cluster value
 *   - custom tag    → pill tinted with its own colour, its icon in that colour (not a MISP
 *                     style: Flowintel only, so it never reads as a taxonomy tag)
 *   - remote        → dashed neutral chip (connector tags with no colour)
 *
 * Props:
 *   label        String   (required) — full tag name, cluster tag, galaxy name or custom tag name
 *   color        String   — stored colour (hex)
 *   kind         String   — 'taxonomy' | 'cluster' | 'galaxy' | 'custom' | 'remote'. Guessed when
 *                           omitted: color + "ns:..." → taxonomy, color → custom, no color → cluster.
 *   iconClass    String   — ready FontAwesome class, e.g. "fa-solid fa-bug"
 *   iconName     String   — bare icon name looked up via utils.js's mapIcon() (galaxies/clusters)
 *   fallbackIcon String   — icon for a custom tag without one (default: none)
 *   title        String   — description shown in the hover card (tag-tooltip.js)
 *   meta         String   — cluster meta (JSON), listed in the hover card
 */

import { mapIcon } from '/static/js/utils.js'
import './tag-tooltip.js'

const { computed } = Vue

// Taxonomies drawn as markings (MISP: the analyst profile's marking namespaces)
const MARKING_NAMESPACES = new Set(['tlp', 'pap'])

// MISP EventCardTool::tagParts. The chip also shows the taxonomy (root) in front of the predicate.
function tagParts(name) {
    const n = (name || '').trim()
    let m = /^([^:="]+):([^=]+)="(.*)"$/s.exec(n)
    if (m) return { namespace: m[2], value: m[3], root: m[1] }
    m = /^([^:]+):(.+)$/s.exec(n)
    if (m) return { namespace: m[1], value: m[2], root: m[1] }
    return { namespace: null, value: n, root: null }
}

// Saturation (0-100) of a #rrggbb colour: below 15 the marking is drawn "clear" (e.g. tlp:clear)
function saturation(hex) {
    const m = /^#?([0-9a-f]{6})$/i.exec(hex || '')
    if (!m) return 0
    const n = parseInt(m[1], 16)
    const r = (n >> 16 & 255) / 255, g = (n >> 8 & 255) / 255, b = (n & 255) / 255
    const max = Math.max(r, g, b), min = Math.min(r, g, b), d = max - min
    if (d === 0) return 0
    const l = (max + min) / 2
    return Math.round(d / (1 - Math.abs(2 * l - 1)) * 100)
}

const VALID_COLOUR = /^#[0-9a-f]{3,8}$/i

/** True for a TLP / PAP tag drawn as a marking (used to pull them out of tag lists). */
export function isMarking(name, color) {
    return MARKING_NAMESPACES.has((tagParts(name).root || '').toLowerCase()) && VALID_COLOUR.test(color || '')
}

/**
 * Same compact chip as the component, as a DOM element, for pages that build their
 * markup without Vue (calendar popups, jQuery). Takes the component's props.
 */
export function tagChipElement({ label, color = '', kind = '', iconClass = '', iconName = '', title = '', meta = '' }) {
    const k = kind || (!color ? 'cluster' : (label.includes(':') ? 'taxonomy' : 'custom'))
    const plain = k === 'custom' || k === 'galaxy'
    const p = plain ? { namespace: null, value: label, root: null } : tagParts(label)
    const el = document.createElement('span')
    el.tabIndex = 0
    el.setAttribute('aria-label', label)
    el.dataset.tgKind = k
    el.dataset.tgName = label
    if (title && title !== label) el.dataset.tgDesc = title
    if (meta) el.dataset.tgMeta = meta
    if (VALID_COLOUR.test(color)) el.dataset.tgColor = color
    if (k === 'taxonomy' && MARKING_NAMESPACES.has((p.root || '').toLowerCase()) && VALID_COLOUR.test(color)) {
        el.className = 'tg-mk'
        if (saturation(color) < 15) el.classList.add('is-clear')
        else el.style.setProperty('--c', color)
        const v = (p.value || '').toLowerCase(), plus = v.indexOf('+')
        el.append(Object.assign(document.createElement('small'), { textContent: p.namespace }),
                  Object.assign(document.createElement('b'), { textContent: plus === -1 ? v : v.slice(0, plus) + '⁺' }))
        return el
    }
    el.className = 'tg-chip ' + (k === 'cluster' || k === 'galaxy' ? 'is-gx' : k === 'remote' ? 'is-remote' : k === 'custom' ? 'is-custom' : 'is-tag')
    if ((k === 'taxonomy' || k === 'custom') && VALID_COLOUR.test(color)) el.style.setProperty('--tc', color)
    if (!iconClass && iconName) {
        const ic = document.createElement('span'); ic.className = 'tg-icon'; ic.innerHTML = mapIcon(iconName) || ''; el.append(ic)
    } else {
        const cls = iconClass || (k === 'cluster' || k === 'galaxy' ? 'fas fa-circle-dot' : '')
        if (cls) { const i = document.createElement('i'); i.className = cls; el.append(i) }
    }
    const text = document.createElement('span')
    if (k === 'cluster') { p.root = p.namespace }
    if (p.namespace) {
        const small = document.createElement('small')
        if (p.root) small.append(Object.assign(document.createElement('b'), { className: 'tg-tx', textContent: p.root }))
        if (p.root && p.root !== p.namespace) small.append(Object.assign(document.createElement('i'), { className: 'tg-sep', textContent: '›' }), p.namespace)
        text.append(small, ' ')
    }
    text.append(p.value)
    el.append(text)
    return el
}

export default {
    name: 'TagBadge',

    props: {
        label:        { type: String, required: true },
        color:        { type: String, default: '' },
        kind:         { type: String, default: '' },
        iconClass:    { type: String, default: '' },
        iconName:     { type: String, default: '' },
        fallbackIcon: { type: String, default: '' },
        title:        { type: String, default: '' },
        meta:         { type: String, default: '' },
    },

    template: `
        <span v-if="is_marking" class="tg-mk" :class="{'is-clear': marking_clear}" :style="marking_clear ? null : {'--c': color}" v-bind="tip_attrs"><small>{{ parts.namespace }}</small><b>{{ marking_value }}</b></span>
        <span v-else class="tg-chip" :class="chip_class" :style="chip_style" v-bind="tip_attrs">
            <span v-if="icon_html" class="tg-icon" v-html="icon_html"></span>
            <i v-else-if="icon_class" :class="icon_class"></i>
            <span><small v-if="parts.namespace"><b v-if="parts.root" class="tg-tx">{{ parts.root }}</b><template v-if="parts.root && parts.root !== parts.namespace"><i class="tg-sep">›</i>{{ parts.namespace }}</template></small>{{ parts.namespace ? ' ' + parts.value : parts.value }}</span>
        </span>
    `,

    setup(props) {
        const resolved_kind = computed(() => {
            if (props.kind) return props.kind
            if (!props.color) return 'cluster'
            return props.label.includes(':') ? 'taxonomy' : 'custom'
        })

        const parts = computed(() => {
            const k = resolved_kind.value
            if (k === 'custom' || k === 'galaxy') return { namespace: null, value: props.label, root: null }
            const p = tagParts(props.label)
            // clusters: the galaxy type in front ("misp-galaxy:threat-actor=…" → threat-actor)
            if (k === 'cluster') return { namespace: p.namespace, value: p.value, root: p.namespace }
            return p
        })

        const is_marking = computed(() =>
            resolved_kind.value === 'taxonomy' && MARKING_NAMESPACES.has((parts.value.root || '').toLowerCase())
            && VALID_COLOUR.test(props.color || ''))
        const marking_clear = computed(() => saturation(props.color) < 15)
        // amber+strict reads as amber⁺
        const marking_value = computed(() => {
            const v = (parts.value.value || '').toLowerCase()
            const plus = v.indexOf('+')
            return plus === -1 ? v : v.slice(0, plus) + '⁺'
        })

        const chip_class = computed(() => {
            const k = resolved_kind.value
            return {
                'is-gx': k === 'cluster' || k === 'galaxy',
                'is-tag': k === 'taxonomy',
                'is-custom': k === 'custom',
                'is-remote': k === 'remote',
            }
        })
        const chip_style = computed(() =>
            (chip_class.value['is-tag'] || chip_class.value['is-custom']) && VALID_COLOUR.test(props.color || '') ? { '--tc': props.color } : null)

        const icon_html = computed(() => (!props.iconClass && props.iconName ? mapIcon(props.iconName) : '') || '')
        const icon_class = computed(() => {
            if (props.iconClass) return props.iconClass
            if (props.iconName) return ''
            const k = resolved_kind.value
            if (k === 'cluster' || k === 'galaxy') return 'fas fa-circle-dot'
            if (k === 'custom') return props.fallbackIcon
            return ''
        })

        // hover card (tag-tooltip.js) reads these
        const tip_attrs = computed(() => ({
            tabindex: 0,
            'aria-label': props.label,
            'data-tg-kind': resolved_kind.value,
            'data-tg-name': props.label,
            'data-tg-desc': props.title && props.title !== props.label ? props.title : null,
            'data-tg-meta': props.meta || null,
            'data-tg-color': VALID_COLOUR.test(props.color || '') ? props.color : null,
        }))

        return { tip_attrs, parts, is_marking, marking_clear, marking_value, chip_class, chip_style, icon_html, icon_class }
    }
}
