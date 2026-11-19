/**
 * tag-fit.js — v-tag-fit directive: a row of tag chips kept on ONE line, showing as many
 * chips as fit, then a "+N" button for the rest (as MISP's events index, events-index-cards.js).
 * Clicking "+N" lets the row wrap and show everything, "−" folds it back.
 *
 * Usage (on the element that directly holds the chips):
 *   <div class="tg-fit" v-tag-fit>
 *       <tag_badge ...></tag_badge> ...
 *   </div>
 *   app.directive('tag-fit', tag_fit)   or   directives: { 'tag-fit': tag_fit }
 *
 * The button is added by the directive itself; it stops the click so a row inside a link
 * (case cards) does not navigate.
 */

const MORE_CLASS = 'tg-more'

function chipsOf(el) {
    return [...el.children].filter(c => !c.classList.contains(MORE_CLASS))
}

function moreButton(el) {
    let btn = el.querySelector(':scope > .' + MORE_CLASS)
    if (!btn) {
        btn = document.createElement('button')
        btn.type = 'button'
        btn.className = MORE_CLASS
        btn.hidden = true
        btn.addEventListener('click', (e) => {
            e.preventDefault()
            e.stopPropagation()
            el.classList.toggle('is-open')
            fit(el)
        })
        el.append(btn)
    }
    return btn
}

function fit(el) {
    const btn = moreButton(el)
    const chips = chipsOf(el)
    chips.forEach(c => { c.style.display = '' })
    // keep the button last, after chips Vue may have appended
    if (el.lastElementChild !== btn) el.append(btn)

    if (el.classList.contains('is-open')) {
        btn.hidden = false
        btn.textContent = '−'
        btn.title = 'Show less'
        btn.setAttribute('aria-expanded', 'true')
        return
    }
    btn.setAttribute('aria-expanded', 'false')
    btn.hidden = true
    if (!chips.length) return

    const right = el.getBoundingClientRect().right
    const overflows = (c) => c.getBoundingClientRect().right > right + 0.5
    if (!chips.some(overflows)) return

    // show the button, then hide chips from the end until the row (with the button) fits
    btn.hidden = false
    let hidden = 0
    for (let i = chips.length - 1; i >= 0; i--) {
        btn.textContent = '+' + (hidden + 1)
        if (!chips.slice(0, i + 1).some(overflows) && btn.getBoundingClientRect().right <= right + 0.5) break
        chips[i].style.display = 'none'
        hidden++
    }
    btn.textContent = '+' + hidden
    btn.title = hidden + ' more'
    if (!hidden) btn.hidden = true
}

export default {
    mounted(el) {
        el.classList.add('tg-fit')
        const run = () => requestAnimationFrame(() => fit(el))
        el._tgFitObserver = new ResizeObserver(run)
        el._tgFitObserver.observe(el)
        // chips added / removed by Vue
        el._tgFitMutation = new MutationObserver((records) => {
            if (records.some(r => [...r.addedNodes, ...r.removedNodes].some(n => !(n.classList && n.classList.contains(MORE_CLASS))))) run()
        })
        el._tgFitMutation.observe(el, { childList: true })
        run()
    },
    updated(el) {
        requestAnimationFrame(() => fit(el))
    },
    unmounted(el) {
        el._tgFitObserver?.disconnect()
        el._tgFitMutation?.disconnect()
    },
}
