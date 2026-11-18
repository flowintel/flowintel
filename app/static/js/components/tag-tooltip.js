/**
 * tag-tooltip.js — the hover card of every tag chip (.tg-chip / .tg-mk), replacing the
 * browser's plain title tooltip.
 *
 * A chip carries its info in data attributes (set by tag-badge.js and tagChipElement()):
 *   data-tg-kind   taxonomy | cluster | galaxy | custom | remote
 *   data-tg-name   full tag name ("misp-galaxy:threat-actor=\"APT28\"")
 *   data-tg-desc   description (optional)
 *   data-tg-meta   cluster meta, JSON (optional; Flowintel stores it JSON-encoded twice)
 *   data-tg-color  tag colour (optional)
 *   data-tg-origin task the tag comes from (optional)
 *
 * Content follows MISP's cluster popover (galaxyQuickViewNew.ctp): description, synonyms,
 * then the other meta keys, humanized; refs are left out.
 *
 * Self-installing: importing this module once registers one delegated listener per page.
 */

const SHOW_DELAY = 280
const HIDE_DELAY = 140

const KIND_LABEL = {
    taxonomy: 'Taxonomy tag',
    cluster: 'Galaxy cluster',
    galaxy: 'Galaxy',
    custom: 'Custom tag',
    remote: 'Remote tag',
}

function humanize(key) {
    const words = String(key).replace(/[-_]/g, ' ').trim()
    const s = words.charAt(0).toUpperCase() + words.slice(1)
    return s.replace(/\bId\b/g, 'ID').replace(/\bMitre\b/gi, 'MITRE').replace(/\bCfr\b/gi, 'CFR')
}

function parseMeta(raw) {
    if (!raw) return null
    let v = raw
    try {
        for (let i = 0; i < 2 && typeof v === 'string'; i++) v = JSON.parse(v)
    } catch (e) {
        return null
    }
    return v && typeof v === 'object' && !Array.isArray(v) ? v : null
}

function el(tag, cls, text) {
    const e = document.createElement(tag)
    if (cls) e.className = cls
    if (text !== undefined && text !== null) e.textContent = text
    return e
}

function build(chip) {
    const d = chip.dataset
    const kind = d.tgKind || ''
    const card = el('div', 'tg-tip')
    card.setAttribute('role', 'tooltip')
    if (d.tgColor) card.style.setProperty('--tc', d.tgColor)
    card.classList.add('is-' + (kind || 'tag'))

    const head = el('div', 'tg-tip-head')
    head.append(el('span', 'tg-tip-dot'), el('span', 'tg-tip-kind', KIND_LABEL[kind] || 'Tag'))
    card.append(head)
    card.append(el('div', 'tg-tip-name', d.tgName || chip.textContent.trim()))
    if (d.tgOrigin) card.append(el('div', 'tg-tip-origin', 'From task ' + d.tgOrigin))

    const desc = (d.tgDesc || '').trim()
    if (desc && desc !== d.tgName) card.append(el('div', 'tg-tip-desc', desc))

    const meta = parseMeta(d.tgMeta)
    if (meta) {
        // MISP order: synonyms first, then the rest; refs skipped
        const keys = Object.keys(meta).filter(k => k !== 'refs' && meta[k] !== null && meta[k] !== '')
        keys.sort((a, b) => (a === 'synonyms' ? -1 : b === 'synonyms' ? 1 : 0))
        if (keys.length) {
            const dl = el('dl', 'tg-tip-meta')
            for (const k of keys.slice(0, 8)) {
                const v = meta[k]
                const text = Array.isArray(v) ? v.join(', ') : (typeof v === 'object' ? JSON.stringify(v) : String(v))
                dl.append(el('dt', null, humanize(k)), el('dd', null, text))
            }
            if (keys.length > 8) dl.append(el('dt', null, '…'), el('dd', null, `${keys.length - 8} more`))
            card.append(dl)
        }
    }
    return card
}

function place(card, chip) {
    const r = chip.getBoundingClientRect()
    const margin = 8
    card.style.left = '0px'
    card.style.top = '0px'
    const w = card.offsetWidth, h = card.offsetHeight
    let left = Math.min(Math.max(margin, r.left), window.innerWidth - w - margin)
    let top = r.bottom + 6
    if (top + h > window.innerHeight - margin && r.top - h - 6 > margin) {
        top = r.top - h - 6
        card.classList.add('is-above')
    }
    card.style.left = left + 'px'
    card.style.top = top + 'px'
}

let current = null      // { chip, card }
let show_timer = null
let hide_timer = null

function hide() {
    clearTimeout(show_timer)
    if (current) {
        current.card.remove()
        current = null
    }
}

function schedule_hide() {
    clearTimeout(hide_timer)
    hide_timer = setTimeout(hide, HIDE_DELAY)
}

function show(chip) {
    hide()
    const card = build(chip)
    card.addEventListener('mouseenter', () => clearTimeout(hide_timer))
    card.addEventListener('mouseleave', schedule_hide)
    document.body.append(card)
    place(card, chip)
    current = { chip, card }
}

function chipOf(target) {
    return target && target.closest ? target.closest('[data-tg-kind]') : null
}

if (!window.__tgTooltipInstalled) {
    window.__tgTooltipInstalled = true

    document.addEventListener('mouseover', (e) => {
        const chip = chipOf(e.target)
        if (!chip) return
        clearTimeout(hide_timer)
        if (current && current.chip === chip) return
        clearTimeout(show_timer)
        show_timer = setTimeout(() => show(chip), SHOW_DELAY)
    })
    document.addEventListener('mouseout', (e) => {
        const chip = chipOf(e.target)
        if (!chip || chip.contains(e.relatedTarget)) return
        clearTimeout(show_timer)
        if (current) schedule_hide()
    })
    // keyboard: chips are focusable, show on focus
    document.addEventListener('focusin', (e) => { const chip = chipOf(e.target); if (chip) show(chip) })
    document.addEventListener('focusout', (e) => { if (chipOf(e.target)) schedule_hide() })
    document.addEventListener('keydown', (e) => { if (e.key === 'Escape') hide() })
    window.addEventListener('scroll', hide, true)
    window.addEventListener('resize', hide)
}

export default {}
