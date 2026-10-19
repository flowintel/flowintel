/**
 * themes/christmas.js — Decorations of the "Christmas" theme (css/themes/christmas.css),
 * ported from Rulezet.
 *
 * Present only while <html data-theme-pref="christmas">, added and removed live when the
 * theme is switched (user_settings.js sets the attribute); nothing at all for other themes.
 *   - a twinkling garland under the top bar, changing pattern now and then
 *   - a Santa hat on the "I" of FLOWINTEL
 *   - red Christmas baubles hanging from a fir branch at the bottom of the sidebar
 *   - snow that comes and goes (can be turned off from the menu, per browser)
 *   - discreet stars and shooting stars in the night sky (the theme is dark)
 *   - a snowy landscape band above the footer: fir trees, snow piles, a campfire and a
 *     snowman on his bike, who does something different on each pass (crashes into a
 *     fir tree, melts in front of the fire, jumps a snow pile, flies...)
 *   - a tree button bottom right opening the Christmas menu: snow, garland, shooting
 *     star, the snowman on / off and every scenario to play right away
 */
(function () {
    const html = document.documentElement
    const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const COLORS = ['red', 'gold', 'green', 'blue', 'pink']
    const LIGHT_COLORS = new Set(['gold', 'blue', 'pink'])    // the "light" bulbs, vs red and green
    // Garland patterns, one at a time, each kept for a while (christmas.css)
    const GARLAND_PATTERNS = ['twinkle', 'wave', 'tones', 'alternate', 'breathe']
    const PATTERN_NAMES = { twinkle: 'Twinkle', wave: 'Wave', tones: 'Light and dark', alternate: 'Every other bulb', breathe: 'Breathing' }
    const SPACING = 46          // px between two bulbs (one scallop of the wire)
    let garlandTimer = null, weatherTimer = null, shootingTimer = null, resizeTimer = null
    let stopRider = () => {}
    let garlandPattern = 'twinkle'
    let mounted = false

    const wanted = () => html.getAttribute('data-theme-pref') === 'christmas'

    // ── Garland ───────────────────────────────────────────────────────

    function garland(nav) {
        const width = nav.clientWidth
        const count = Math.max(4, Math.floor(width / SPACING))
        const step = width / count
        let d = ''
        for (let i = 0; i < count; i++) {
            const x0 = i * step, x1 = x0 + step
            d += `${i ? '' : `M${x0},2 `}Q${x0 + step / 2},20 ${x1},2 `
        }
        const el = document.createElement('div')
        el.className = 'xmas-garland'
        el.setAttribute('aria-hidden', 'true')
        el.innerHTML = `<svg class="xmas-garland__wire" viewBox="0 0 ${width} 26" preserveAspectRatio="none"><path d="${d}"/></svg>`
        for (let i = 0; i < count; i++) {
            const b = document.createElement('span')
            const color = COLORS[i % COLORS.length]
            b.className = `xmas-bulb xmas-bulb--${color}`
            b.dataset.tone = LIGHT_COLORS.has(color) ? 'light' : 'dark'
            b.style.left = `${i * step + step / 2}px`
            b.style.setProperty('--i', i)                               // position, for the wave
            b.style.setProperty('--r', `${((i * 7) % 11) * 0.22}s`)     // scattered, for the twinkle
            el.appendChild(b)
        }
        el.dataset.pattern = garlandPattern
        return el
    }

    function setGarlandPattern(pattern) {
        garlandPattern = pattern
        document.querySelectorAll('.xmas-garland').forEach(g => { g.dataset.pattern = pattern })
        document.querySelectorAll('.xmas-garland-switch').forEach(b => setLabel(b, `Garland: ${PATTERN_NAMES[pattern]}`))
    }

    function scheduleGarland() {
        clearTimeout(garlandTimer)
        garlandTimer = setTimeout(cycleGarland, (45 + Math.random() * 30) * 1000)
    }

    // A new pattern every 45–75 s, never the same one twice in a row
    function cycleGarland() {
        const next = GARLAND_PATTERNS.filter(p => p !== garlandPattern)
        setGarlandPattern(next[Math.floor(Math.random() * next.length)])
        scheduleGarland()
    }

    // An item of the Christmas menu (bottom right, see christmas.css .xmas-menu)
    function menuItem(icon, label, extraClass = '') {
        const btn = document.createElement('button')
        btn.type = 'button'
        btn.className = `xmas-menu__item ${extraClass}`.trim()
        btn.innerHTML = `<i class="fa-solid ${icon} fa-fw"></i><span class="xmas-menu__label"></span>`
        setLabel(btn, label)
        return btn
    }

    function setLabel(btn, label) {
        btn.querySelector('.xmas-menu__label').textContent = label
        btn.title = label
    }

    // Menu item: the next garland pattern, now
    function garlandSwitch() {
        const btn = menuItem('fa-lightbulb', 'Garland', 'xmas-garland-switch')
        btn.addEventListener('click', () => {
            const i = GARLAND_PATTERNS.indexOf(garlandPattern)
            setGarlandPattern(GARLAND_PATTERNS[(i + 1) % GARLAND_PATTERNS.length])
            scheduleGarland()
        })
        return btn
    }

    // ── Santa hat ─────────────────────────────────────────────────────

    function hat() {
        const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg')
        svg.setAttribute('class', 'xmas-hat')
        svg.setAttribute('viewBox', '0 0 64 56')
        svg.setAttribute('aria-hidden', 'true')
        svg.innerHTML =
            '<path d="M8 44 C14 20 30 6 46 8 C54 9 58 16 56 24 L50 22 C44 18 36 24 32 44 Z" fill="#d62828"/>' +
            '<rect x="2" y="40" width="40" height="11" rx="5.5" fill="#fff"/>' +
            '<circle cx="54" cy="26" r="7" fill="#fff"/>'
        return svg
    }

    // ── Red baubles in the sidebar ────────────────────────────────────
    // A fir branch across the bottom of the sidebar with red baubles hanging on
    // strings of different lengths, each swinging from its hook (christmas.css).

    function baubles() {
        const W = 208, H = 150
        let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMax meet" xmlns="http://www.w3.org/2000/svg">`
        svg += '<defs><radialGradient id="xmas-bauble-shine" cx=".35" cy=".35" r=".7">' +
            '<stop offset="0" stop-color="#ff8a8a"/><stop offset=".45" stop-color="#d62828"/><stop offset="1" stop-color="#8e1414"/>' +
            '</radialGradient></defs>'
        // hooks along the branch: x, string length, radius, swing delay
        const hooks = [[28, 28, 11, -0.4], [70, 46, 14, -1.9], [112, 20, 10, -1.1], [150, 38, 13, -2.6], [186, 24, 10, -0.8]]
        const branchY = x => 52 + Math.sin(x / W * Math.PI) * 10
        hooks.forEach(([x, len, r, delay]) => {
            const top = branchY(x), cy = top + len + r
            svg += `<g class="xmas-bauble" style="transform-origin:${x}px ${top}px;animation-delay:${delay}s">` +
                `<line x1="${x}" y1="${top}" x2="${x}" y2="${cy - r - 3}" stroke="#d9dee8" stroke-width="1"/>` +
                `<rect x="${x - 3.5}" y="${cy - r - 4}" width="7" height="5" rx="1" fill="#e2b33c"/>` +
                `<circle cx="${x}" cy="${cy}" r="${r}" fill="url(#xmas-bauble-shine)"/>` +
                `<ellipse cx="${x - r * 0.35}" cy="${cy - r * 0.4}" rx="${r * 0.28}" ry="${r * 0.16}" fill="#fff" opacity=".55" transform="rotate(-35 ${x - r * 0.35} ${cy - r * 0.4})"/>` +
                '</g>'
        })
        // the fir branch, drawn last so the hooks hide behind it
        let needles = ''
        for (let x = 0; x <= W; x += 6) {
            const y = branchY(x)
            needles += `M${x},${y} l-5,-7 M${x},${y} l5,-7 M${x},${y} l-5,7 M${x},${y} l5,7 `
        }
        svg += `<path d="${needles}" stroke="#2f6b3f" stroke-width="2" stroke-linecap="round"/>`
        svg += `<path d="M0,${branchY(0)} Q${W / 2},${branchY(W / 2) + 10} ${W},${branchY(W)}" stroke="#5a3d2b" stroke-width="2.5" fill="none"/>`
        svg += '</svg>'
        const el = document.createElement('div')
        el.className = 'xmas-baubles'
        el.setAttribute('aria-hidden', 'true')
        el.innerHTML = svg
        return el
    }

    // The hat sits on the "I" of FLOWINTEL in the logo image: the I is at 54% of the
    // logo's width and its top at 77% of its height (static/image/flowintel.png).
    // Placed from the image's real size, so it follows the smaller logo when the
    // sidebar is collapsed.
    const HAT_ON = { x: 0.541, y: 0.768 }
    let hatObserver = null

    function placeHat(logo) {
        const img = logo.querySelector('img')
        if (!img) return
        logo.classList.add('xmas-logo')
        const el = hat()
        logo.appendChild(el)
        const place = () => {
            const w = el.clientWidth, h = el.clientHeight
            // the middle of the brim (x 22 of 64) over the I, the brim just on its top
            el.style.left = `${img.offsetLeft + img.offsetWidth * HAT_ON.x - w * 0.34}px`
            el.style.top = `${img.offsetTop + img.offsetHeight * HAT_ON.y - h * 0.86}px`
        }
        place()
        img.addEventListener('load', place)
        if (window.ResizeObserver) { hatObserver = new ResizeObserver(place); hatObserver.observe(img) }
    }

    // ── Snow ──────────────────────────────────────────────────────────

    function snow() {
        const el = document.createElement('div')
        el.className = 'xmas-snow'
        el.setAttribute('aria-hidden', 'true')
        const n = window.innerWidth < 768 ? 14 : 28
        for (let i = 0; i < n; i++) {
            const f = document.createElement('span')
            f.className = 'xmas-flake'
            f.textContent = Math.random() < 0.5 ? '❄' : '•'
            f.style.left = `${Math.random() * 100}%`
            f.style.fontSize = `${8 + Math.random() * 10}px`
            f.style.opacity = (0.35 + Math.random() * 0.45).toFixed(2)
            const fall = 9 + Math.random() * 10, sway = 2 + Math.random() * 3
            f.style.animationDuration = `${fall}s, ${sway}s`
            f.style.animationDelay = `${-Math.random() * fall}s, ${-Math.random() * sway}s`
            el.appendChild(f)
        }
        return el
    }

    // Snow that starts and stops naturally: stopping lets each flake finish its fall,
    // starting sends them again from the top one after the other.
    const rangeMs = (min, max) => (min + Math.random() * (max - min)) * 1000
    const SNOW_OFF_KEY = 'fi-xmas-snow-off'
    const snowOff = () => { try { return localStorage.getItem(SNOW_OFF_KEY) === '1' } catch { return false } }

    function stopFalling(snowEl, onDone) {
        let falling = 0
        Array.from(snowEl.children).forEach(f => {
            if (f._onFallEnd) f.removeEventListener('animationiteration', f._onFallEnd)
            if (f.classList.contains('xmas-flake--done') || f.classList.contains('xmas-flake--off')) {
                f.classList.add('xmas-flake--done')
                return
            }
            falling++
            f._onFallEnd = e => {
                if (e.animationName !== 'xmas-fall') return      // ignore the sway loop
                f.removeEventListener('animationiteration', f._onFallEnd)
                f._onFallEnd = null
                f.classList.add('xmas-flake--done')
                if (--falling === 0 && onDone) onDone()
            }
            f.addEventListener('animationiteration', f._onFallEnd)
        })
        if (falling === 0 && onDone) onDone()
    }

    function startFalling(snowEl, intensity) {
        const flakes = Array.from(snowEl.children)
        const visible = Math.round(flakes.length * intensity)
        flakes.forEach((f, i) => {
            if (f._onFallEnd) { f.removeEventListener('animationiteration', f._onFallEnd); f._onFallEnd = null }
            const [fall, sway] = f.style.animationDuration.split(',').map(parseFloat)
            // restart from the top: drop the animation, reflow, put it back with a positive delay
            f.style.animationName = 'none'
            void f.offsetWidth
            f.style.animationName = ''
            f.style.animationDelay = `${(Math.random() * fall * 0.8).toFixed(2)}s, ${(-Math.random() * sway).toFixed(2)}s`
            f.classList.toggle('xmas-flake--off', i >= visible)
            f.classList.remove('xmas-flake--done')
        })
    }

    // Weather: snowfalls of varying intensity (40–100% of the flakes), then calm spells
    function weather(snowEl) {
        const snowfall = () => {
            if (snowOff()) return
            startFalling(snowEl, 0.4 + Math.random() * 0.6)
            weatherTimer = setTimeout(calm, rangeMs(45, 90))
        }
        const calm = () => {
            stopFalling(snowEl, () => { if (!snowOff()) weatherTimer = setTimeout(snowfall, rangeMs(25, 50)) })
        }
        snowEl._resume = () => { clearTimeout(weatherTimer); snowfall() }
        snowEl._halt = () => { clearTimeout(weatherTimer); stopFalling(snowEl) }
        if (snowOff()) Array.from(snowEl.children).forEach(f => f.classList.add('xmas-flake--done'))
        else weatherTimer = setTimeout(calm, rangeMs(45, 90))    // the page loads with snow already falling
    }

    // Menu item to turn the snow off (remembered in this browser only)
    function snowSwitch(snowEl) {
        const btn = menuItem('fa-snowflake', 'Snow')
        const update = () => {
            const off = snowOff()
            btn.classList.toggle('is-off', off)
            setLabel(btn, off ? 'Turn the snow back on' : 'Turn the snow off')
            btn.setAttribute('aria-pressed', String(off))
        }
        btn.addEventListener('click', () => {
            const turnOff = !snowOff()
            try { localStorage.setItem(SNOW_OFF_KEY, turnOff ? '1' : '0') } catch { /* storage unavailable */ }
            if (turnOff) snowEl._halt(); else snowEl._resume()
            update()
        })
        update()
        return btn
    }

    // ── Night sky ─────────────────────────────────────────────────────

    // Discreet stars behind the page (christmas.css), at the top of the screen
    function stars() {
        const el = document.createElement('div')
        el.className = 'xmas-stars'
        el.setAttribute('aria-hidden', 'true')
        const n = window.innerWidth < 768 ? 18 : 40
        for (let i = 0; i < n; i++) {
            const st = document.createElement('span')
            st.className = 'xmas-star'
            st.style.left = `${Math.random() * 100}%`
            st.style.top = `${8 + Math.random() * 90}%`
            const size = Math.random() < 0.8 ? 1.5 : 2.5
            st.style.width = st.style.height = `${size}px`
            st.style.animationDuration = `${3 + Math.random() * 4}s`
            st.style.animationDelay = `${-Math.random() * 6}s`
            el.appendChild(st)
        }
        return el
    }

    function spawnShootingStar() {
        const sky = document.querySelector('.xmas-stars')
        if (!sky) return
        const s = document.createElement('span')
        s.className = 'xmas-shooting-star'
        s.style.left = `${10 + Math.random() * 60}%`
        s.style.top = `${4 + Math.random() * 30}%`
        s.addEventListener('animationend', () => s.remove())
        sky.appendChild(s)
    }

    // Every 10–25 s a shooting star crosses the sky
    function shootingStar() {
        if (!document.hidden) spawnShootingStar()
        shootingTimer = setTimeout(shootingStar, (10 + Math.random() * 15) * 1000)
    }

    // Menu item: a shooting star right now
    function shootingStarSwitch() {
        const btn = menuItem('fa-star', 'Make a wish — a shooting star')
        btn.addEventListener('click', spawnShootingStar)
        return btn
    }

    // ── Landscape ─────────────────────────────────────────────────────
    // Two rows of snowy hills with fir trees, snow piles and a campfire, at night.
    // Seeded, so it is the same on every page. The snowman rides on the snow line.

    const LAND = {
        farHills: '#16223a', farTree: '#101a2d', farSnow: 'rgba(220,232,250,.3)',
        nearHills: '#121b2f', nearTree: '#0b1324', nearSnow: 'rgba(235,242,255,.5)',
        ground: '#dfe7f5', groundOpacity: '.22', pile: '#d5def0', pileShade: '#8e9fbb', stars: 60,
    }

    // The band is W x H; SKY more units of night sky above the hills leave room for
    // what happens up there (the flying bike, shooting stars...)
    const W = 1440, H = 240, SKY = 200

    const hillY = (base, amp, waves, x) =>
        base - amp * (Math.sin(x / W * Math.PI * waves) * 0.6 + Math.sin(x / W * Math.PI * waves * 2.3 + 1) * 0.4)

    function hills(base, amp, waves) {
        let d = `M0,${H} L0,${base}`
        for (let x = 0; x <= W; x += 40) d += ` L${x},${hillY(base, amp, waves, x).toFixed(1)}`
        return d + ` L${W},${H} Z`
    }

    // The snow line the snowman rides on (flat beyond both edges)
    const groundY = x => hillY(226, 6, 4, Math.min(W, Math.max(0, x)))

    function tree(x, ground, h, color, snowColor) {
        const w = h * 0.62
        let path = '', caps = ''
        for (let t = 0; t < 3; t++) {               // three tiers of branches
            const top = ground - h + t * h * 0.24
            const bottom = top + h * 0.42
            const half = w * (0.55 + t * 0.22) / 2
            path += `M${x},${top} L${x - half},${bottom} L${x + half},${bottom} Z `
            caps += `M${x},${top} L${x - half * 0.45},${top + h * 0.12} L${x + half * 0.45},${top + h * 0.12} Z `
        }
        path += `M${x - w * 0.06},${ground - h * 0.1} h${w * 0.12} v${h * 0.12} h${-w * 0.12} Z`
        return `<path d="${path}" fill="${color}"/><path d="${caps}" fill="${snowColor}"/>`
    }

    // A rounded heap of snow, sometimes with a few snowballs on top
    function snowPile(x, y, w, c, balls) {
        const h = w * 0.38
        let g = `<path d="M${x - w / 2},${y} C${x - w * 0.35},${y - h} ${x + w * 0.3},${y - h * 1.1} ${x + w / 2},${y} Z" fill="${c.pile}"/>`
        g += `<path d="M${x - w * 0.1},${y} C${x + w * 0.05},${y - h * 0.55} ${x + w * 0.3},${y - h * 0.6} ${x + w / 2},${y} Z" fill="${c.pileShade}" opacity=".45"/>`
        if (balls) {
            g += `<circle cx="${x - w * 0.12}" cy="${y - h * 0.82}" r="${w * 0.09}" fill="${c.pile}" stroke="${c.pileShade}" stroke-width=".8"/>`
            g += `<circle cx="${x + w * 0.08}" cy="${y - h * 0.86}" r="${w * 0.08}" fill="${c.pile}" stroke="${c.pileShade}" stroke-width=".8"/>`
            g += `<circle cx="${x - w * 0.02}" cy="${y - h * 1.08}" r="${w * 0.075}" fill="${c.pile}" stroke="${c.pileShade}" stroke-width=".8"/>`
        }
        return g
    }

    // A small campfire: flickering flames, a warm glow on the snow, rising smoke
    function campfire(x, y) {
        let g = `<g class="xmas-camp" transform="translate(${x},${y}) scale(1.3)">`
        g += '<ellipse class="xmas-camp__glow" cx="0" cy="-2" rx="34" ry="12" fill="url(#xmas-camp-glow)"/>'
        for (let i = 0; i < 4; i++) {
            g += `<circle class="xmas-camp__smoke" style="animation-delay:${-i * 1.6}s" cx="0" cy="-12" r="3.5" fill="url(#xmas-camp-smoke)"/>`
        }
        g += '<rect x="-9" y="-3" width="18" height="3" rx="1.5" fill="#3a2a1f" transform="rotate(14)"/>'
        g += '<rect x="-9" y="-3" width="18" height="3" rx="1.5" fill="#3a2a1f" transform="rotate(-14)"/>'
        g += '<path class="xmas-camp__flame" d="M0,-16 C5,-9 6,-4 0,-2 C-6,-4 -5,-9 0,-16 Z" fill="#ff7a1f"/>'
        g += '<path class="xmas-camp__flame xmas-camp__flame--in" d="M0,-11 C3,-7 3,-4 0,-2.5 C-3,-4 -3,-7 0,-11 Z" fill="#ffd166"/>'
        return g + '</g>'
    }

    // The fir tree he rides into: shaken by the rider loop (tree-shake + falling snow)
    function crashTree(x, ground, c) {
        const h = 66
        let g = `<g class="xmas-crash-tree">${tree(x, ground, h, c.nearTree, c.nearSnow)}</g>`
        for (let i = 0; i < 5; i++) {
            const sx = x - 12 + i * 6, sy = ground - h + 10 + (i % 2) * 12
            g += `<circle class="xmas-crash-snow" data-y="${sy}" cx="${sx}" cy="${sy}" r="${1.8 + (i % 3) * 0.6}" fill="${c.pile}" opacity="0"/>`
        }
        return g
    }

    // A snowman on a bike, drawn around (0,0) = the ground between the wheels, facing
    // right. Parts moved by the rider loop: the whole rider (position, slope, direction),
    // the tumble (falling over backwards), the wheels' spokes, the snowman (melting),
    // his hat, the puddle, the drops and the dizzy stars.
    function snowmanOnBike() {
        // a wheel, and its jet (lit when the bike flies, the wheel then lies flat as a propeller)
        const wheel = cx => {
            let w = `<path class="xmas-rider__jet" data-cx="${cx}" opacity="0" d="M${cx - 3.5},-6 L${cx + 3.5},-6 L${cx},8 Z" fill="#ff9a3c"/>`
            w += `<g class="xmas-rider__wheel" data-cx="${cx}" transform="translate(${cx},-8)"><circle r="7.5" fill="none" stroke="#2b2b2b" stroke-width="1.8"/><g class="xmas-rider__spokes">`
            for (let a = 0; a < 180; a += 45) w += `<line x1="0" y1="-7" x2="0" y2="7" stroke="#8a8a8a" stroke-width=".7" transform="rotate(${a})"/>`
            return w + '</g></g>'
        }
        let g = '<g class="xmas-rider">'
        g += '<ellipse class="xmas-rider__puddle" cx="0" cy="0" rx="0" ry="2.6" fill="#bcd7f5" opacity="0"/>'
        g += '<g class="xmas-rider__tumble">'
        g += wheel(-12) + wheel(12)
        // frame, seat and handlebar
        g += '<path d="M-12,-8 L-2,-8 L6,-19 L-5,-19 Z M-2,-8 L-6,-22 M6,-19 L12,-8 M6,-19 L8,-25" fill="none" stroke="#c62828" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
        g += '<path d="M-9,-23 h6" stroke="#2b2b2b" stroke-width="2.2" stroke-linecap="round"/>'
        g += '<path d="M6,-25 h5" stroke="#2b2b2b" stroke-width="2" stroke-linecap="round"/>'
        // the snowman himself (melts down onto the seat)
        g += '<g class="xmas-rider__snowman">'
        g += '<circle cx="-4" cy="-30" r="8" fill="#ffffff" stroke="#c5d3e6" stroke-width="1"/>'
        g += '<path d="M-2,-25 L1,-12 M-4,-25 L-3,-11" stroke="#5a3d2b" stroke-width="1.6" stroke-linecap="round"/>'
        g += '<circle cx="-1" cy="-43" r="6" fill="#ffffff" stroke="#c5d3e6" stroke-width="1"/>'
        g += '<path d="M0,-33 L9,-26" stroke="#5a3d2b" stroke-width="1.4" stroke-linecap="round"/>'
        g += '<circle cx="-1" cy="-32" r=".9" fill="#2b2b2b"/><circle cx="-0.5" cy="-28" r=".9" fill="#2b2b2b"/>'
        g += '<circle cx="0.5" cy="-45" r=".8" fill="#2b2b2b"/><circle cx="3" cy="-44.5" r=".8" fill="#2b2b2b"/>'
        g += '<path d="M4,-43 L10,-42 L4,-41.4 Z" fill="#f47c20"/>'
        g += '<rect x="-6" y="-38.5" width="10" height="3" rx="1.2" fill="#c62828"/>'
        g += '<path class="xmas-rider__scarf" d="M-6,-37.5 L-15,-36 L-14.5,-33.5 L-6,-35.5 Z" fill="#c62828"/>'
        // a snowball splat on his face
        g += '<path class="xmas-rider__splat" opacity="0" d="M1,-48 l2,2 l2,-1 l0,3 l3,1 l-2,2 l2,3 l-3,0 l-1,3 l-2,-2 l-3,2 l0,-3 l-3,-1 l2,-2 l-2,-3 l3,0 Z" fill="#ffffff" stroke="#c5d3e6" stroke-width=".5"/>'
        g += '</g>'
        // top hat, sinks with the snowman when he melts
        g += '<g class="xmas-rider__hat">'
        g += '<rect x="-7" y="-49.5" width="12" height="1.8" rx=".8" fill="#2b2b2b"/>'
        g += '<rect x="-4.5" y="-57" width="7" height="7.8" rx="1" fill="#2b2b2b"/>'
        g += '<rect x="-4.5" y="-52.5" width="7" height="1.4" fill="#c62828"/>'
        g += '</g>'
        g += '</g>'
        // snow sprayed behind the rear wheel when he skids
        for (let i = 0; i < 5; i++) g += `<circle class="xmas-rider__spray" data-i="${i}" cx="-20" cy="-2" r="${1.4 + (i % 2)}" fill="#e9eef7" opacity="0"/>`
        // Zzz while he naps
        g += '<g class="xmas-rider__zzz" opacity="0" font-family="sans-serif" font-weight="700" fill="#cfe0ff">' +
            '<text x="6" y="-52" font-size="7">z</text><text x="11" y="-60" font-size="9">z</text><text x="17" y="-70" font-size="11">Z</text></g>'
        // drops running down while he melts
        for (let i = 0; i < 3; i++) g += `<circle class="xmas-rider__drop" cx="${-6 + i * 4}" cy="-20" r="1.2" fill="#bcd7f5" opacity="0"/>`
        // dizzy stars over his head while he lies in the snow after the crash
        g += '<g class="xmas-rider__dizzy" opacity="0"><g transform="translate(-54,-46)"><g class="xmas-rider__dizzy-spin">'
        for (let i = 0; i < 3; i++) {
            g += `<path transform="rotate(${i * 120}) translate(7,0)" d="M0,-2.6 L.8,-.8 L2.6,-.8 L1.2,.4 L1.7,2.3 L0,1.2 L-1.7,2.3 L-1.2,.4 L-2.6,-.8 L-.8,-.8 Z" fill="#ffc93c"/>`
        }
        g += '</g></g></g>'
        return g + '</g>'
    }

    // David, whose bike the snowman borrowed: drawn around (0,0) = his feet, facing
    // right. The rider loop moves his legs, arms and back (running, out of breath, walking).
    function david() {
        // a sleeve and a hand, hanging from the shoulder (rotated by the rider loop)
        const arm = (sleeve, x) => `<g class="xmas-david__arm" data-x="${x}">` +
            `<line x1="${x}" y1="-38" x2="${x}" y2="-25" stroke="${sleeve}" stroke-width="3.4" stroke-linecap="round"/>` +
            `<circle cx="${x}" cy="-23.5" r="2" fill="#f2c9a0"/></g>`
        let g = '<g class="xmas-david" style="display:none">'
        g += '<line class="xmas-david__leg" x1="0" y1="-22" x2="0" y2="0" stroke="#2b2f3a" stroke-width="3.2" stroke-linecap="round"/>'
        g += '<line class="xmas-david__leg" x1="0" y1="-22" x2="0" y2="0" stroke="#3a4050" stroke-width="3.2" stroke-linecap="round"/>'
        g += '<g class="xmas-david__body">'
        g += arm('#1b4470', -1.5)                                                                     // back arm
        g += '<rect x="-5.5" y="-41" width="11" height="20" rx="3.5" fill="#2f6fb0"/>'                 // blue jacket
        g += '<rect x="-5.5" y="-42" width="11" height="3.2" rx="1.4" fill="#2e8b57"/>'                // green scarf
        g += '<circle cx="0" cy="-48" r="6" fill="#f2c9a0"/>'                                         // head
        g += '<circle cx="2.8" cy="-49" r=".8" fill="#2b2b2b"/><path d="M1.5,-45.5 q1.5,1 3,0" stroke="#2b2b2b" stroke-width=".7" fill="none"/>'
        g += '<path d="M-6.2,-49 Q0,-60 6.2,-49 Z" fill="#c62828"/><circle cx="0" cy="-57" r="2" fill="#ffffff"/>'   // beanie
        g += arm('#173a63', 1.5)                                                                      // front arm, over the jacket
        g += '</g></g>'
        return g
    }

    // The snowman's head on its own (wish scenario), drawn around (0,0) = its middle, facing right
    function looseHead() {
        return '<g class="xmas-loose-head" style="display:none"><g class="xmas-loose-head__spin">' +
            '<circle r="6" fill="#ffffff" stroke="#c5d3e6" stroke-width="1"/>' +
            '<circle cx="1.5" cy="-2" r=".8" fill="#2b2b2b"/><circle cx="4" cy="-1.5" r=".8" fill="#2b2b2b"/>' +
            '<path d="M5,0 L11,1 L5,1.6 Z" fill="#f47c20"/>' +
            '<rect x="-6" y="-6.5" width="12" height="1.8" rx=".8" fill="#2b2b2b"/>' +
            '<rect x="-3.5" y="-14" width="7" height="7.8" rx="1" fill="#2b2b2b"/>' +
            '<rect x="-3.5" y="-9.5" width="7" height="1.4" fill="#c62828"/>' +
            '</g><g class="xmas-loose-head__dizzy" opacity="0">' +
            [0, 120, 240].map(a => `<circle transform="rotate(${a}) translate(9,0)" r="1.6" fill="#ffc93c"/>`).join('') +
            '</g></g>'
    }

    // A speech bubble (text and size set by the rider loop)
    function bubble(who) {
        return `<g class="xmas-bubble xmas-bubble--${who}" opacity="0"><path class="xmas-bubble__box" fill="#ffffff" stroke="#c5d3e6" stroke-width="1"/>` +
            '<text class="xmas-bubble__text" font-size="11" font-weight="600" fill="#1d2433" text-anchor="middle"></text></g>'
    }

    function landscape() {
        const c = LAND
        let seed = 7
        const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)

        let svg = `<svg viewBox="0 ${-SKY} ${W} ${H + SKY}" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">`
        svg += '<defs>' +
            '<radialGradient id="xmas-camp-glow"><stop offset="0" stop-color="#ff9a3c" stop-opacity="1"/><stop offset="1" stop-color="#ff9a3c" stop-opacity="0"/></radialGradient>' +
            '<radialGradient id="xmas-camp-smoke"><stop offset="0" stop-color="#aab4c4" stop-opacity=".9"/><stop offset="1" stop-color="#aab4c4" stop-opacity="0"/></radialGradient>' +
            '</defs>'
        for (let i = 0; i < c.stars; i++) {                                // stars in the sky
            const big = rand() < 0.2
            svg += `<circle class="xmas-sky-star" style="animation-delay:${(-rand() * 5).toFixed(2)}s" ` +
                   `cx="${(rand() * W).toFixed(0)}" cy="${(-SKY + 8 + rand() * (SKY + 95)).toFixed(0)}" r="${big ? 1.4 : 0.8}" fill="#fff"/>`
        }
        svg += `<path d="${hills(150, 26, 3)}" fill="${c.farHills}"/>`          // far hills
        for (let i = 0; i < 26; i++) {                                     // far trees
            const x = rand() * W, h = 26 + rand() * 18
            svg += tree(x, 150 + rand() * 10, h, c.farTree, c.farSnow)
        }
        svg += `<path d="${hills(196, 20, 2)}" fill="${c.nearHills}"/>`         // near hills
        for (let i = 0; i < 16; i++) {                                     // near trees
            const x = rand() * W, h = 44 + rand() * 30
            svg += tree(x, 200 + rand() * 12, h, c.nearTree, c.nearSnow)
        }
        svg += campfire(FIRE_X, hillY(196, 20, 2, FIRE_X) + 4)
        svg += `<path d="${hills(226, 6, 4)}" fill="${c.ground}" opacity="${c.groundOpacity}"/>`  // snow on the ground
        for (let i = 0; i < 7; i++) {                                      // snow piles along the ground
            const x = 60 + i * (W - 120) / 6 + (rand() - 0.5) * 120, w = 34 + rand() * 30
            if (Math.abs(x - FIRE_X) < 50 || Math.abs(x - RAMP_X) < 60) continue    // room for the fire and the ramp
            svg += snowPile(x, groundY(x) + 3, w, c, i % 3 === 1)
        }
        svg += snowPile(RAMP_X, groundY(RAMP_X) + 3, 54, c, false)          // the big pile he jumps from
        svg += crashTree(TREE_X, groundY(TREE_X) + 2, c)
        svg += snowmanOnBike()
        svg += '<circle class="xmas-snowball" r="4" fill="#ffffff" stroke="#c5d3e6" stroke-width=".8" opacity="0"/>'
        svg += '<path class="xmas-smash" opacity="0" d="M-20,0 C-18,-9 -10,-14 -2,-12 C4,-17 14,-13 16,-6 C22,-5 24,-1 22,0 Z" fill="#f4f7fc" stroke="#c5d3e6" stroke-width="1"/>'
        svg += '<g class="xmas-meteor" opacity="0"><line class="xmas-meteor__trail" stroke="#fff3b0" stroke-width="3" stroke-linecap="round" opacity=".7"/>' +
            '<path class="xmas-meteor__star" d="M0,-9 L2.6,-2.8 L9,-2.8 L3.8,1.2 L5.6,8 L0,4 L-5.6,8 L-3.8,1.2 L-9,-2.8 L-2.6,-2.8 Z" fill="#ffd94a" stroke="#fff6c4" stroke-width="1"/></g>'
        svg += '<circle class="xmas-flash" r="0" fill="#fff8d6" opacity="0"/>'
        svg += looseHead()
        svg += david()
        svg += bubble('david') + bubble('snowman') + bubble('head')
        svg += '<text class="xmas-david-name" text-anchor="middle" font-size="9" font-weight="700" fill="#9fb0cf" opacity="0">David</text>'
        svg += '</svg>'

        const el = document.createElement('div')
        el.className = 'xmas-land'
        el.setAttribute('aria-hidden', 'true')
        el.innerHTML = svg
        return el
    }

    // ── The snowman's ride ────────────────────────────────────────────
    // He crosses the band again and again, left to right then right to left, and on
    // each pass something different happens with what is around him (a scenario
    // picked at random, never the same twice in a row):
    //   crash   rides into the fir tree: it shakes and drops its snow, he falls over
    //           backwards with dizzy stars, gets up and rides on
    //   melt    stops in front of the campfire, melts into a puddle, freezes back
    //   sweat   stops to warm up at the fire, starts sweating, panics and sprints off
    //   jump    takes the big snow pile as a ramp, does a backflip and lands
    //   wheelie rides on his back wheel, wobbles, lands it
    //   hat     the wind blows his hat off, it spins up and he catches it on his head
    //   wish    stops to make a wish on a shooting star... and another one falls right
    //           on him: his body is squashed into a heap of snow, the bike rolls away
    //           alone, his head hops after it, jumps on the seat and rides off
    //   turbo   pedals faster and faster, skids to a stop in a spray of snow, rides on
    //   nap     slows down, stops and dozes off (Zzz), wakes up with a start
    //   snowball a snowball comes flying and hits him in the face: splat, wobble
    //   trick   stops and shows off: two spins on the back wheel, a bow, rides on
    //   david   David runs after his bike, the snowman rode off with it: they shout
    //           a few words at each other, David gives up and walks home
    //   fly     the bike turns into a flying bike: the wheels lie flat and become
    //           propellers, jets light up, it takes off over the trees and lands
    // Whatever the scenario, riding past the campfire makes him melt a bit (drops
    // run down), and he freezes back once he is away from it.

    const TREE_X = W * 0.45, FIRE_X = W * 0.71, RAMP_X = W * 0.22
    const SPEED = (W + 120) / 28                         // crosses the band in 28 s
    const RIDER_OFF_KEY = 'fi-xmas-rider-off'
    const riderOff = () => { try { return localStorage.getItem(RIDER_OFF_KEY) === '1' } catch { return false } }
    const ease = u => u * u * (3 - 2 * u)

    // Steps of a pass: [duration in s, u (0..1) -> state]. dir = 1 to the right, -1 to the left.
    function ride(from, to, dir, extra = () => ({}), speed = 1) {
        return [Math.abs(to - from) / (SPEED * speed), u => Object.assign({ x: from + (to - from) * u, dir, moving: speed }, extra(u))]
    }
    const stay = (duration, x, dir, extra = () => ({})) => [duration, u => Object.assign({ x, dir }, extra(u))]

    // Shown in the Christmas menu, in this order: [icon, label]
    const SCENARIO_LABELS = {
        crash: ['fa-tree', 'Crash into a tree'],
        melt: ['fa-fire', 'Melt at the campfire'],
        sweat: ['fa-temperature-high', 'Too hot!'],
        jump: ['fa-mountain', 'Jump the snow pile'],
        wheelie: ['fa-bicycle', 'Wheelie'],
        hat: ['fa-hat-wizard', 'Hat in the wind'],
        turbo: ['fa-bolt', 'Turbo and skid'],
        nap: ['fa-bed', 'Nap'],
        snowball: ['fa-circle', 'Snowball in the face'],
        trick: ['fa-star-half-stroke', 'Show-off'],
        fly: ['fa-helicopter', 'Flying bike'],
        david: ['fa-person-running', 'David wants his bike back'],
        wish: ['fa-wand-magic-sparkles', 'Wish upon a (falling) star'],
    }

    const SCENARIOS = {
        crash(dir, start, end) {
            const x = TREE_X - dir * 22                  // front wheel against the trunk
            return [
                ride(start, x, dir),
                stay(0.35, x, dir, u => ({ tumble: -72 * u * u, crash: u * 0.35 })),
                stay(2.4, x, dir, u => ({ tumble: -72, dizzy: Math.min(1, u * 8, (1 - u) * 8), crash: 0.35 + u * 2.4, say: { snowman: 'Who put a tree here?!' } })),
                stay(0.8, x, dir, u => ({ tumble: -72 * (1 - ease(u)) })),
                stay(0.6, x, dir),
                ride(x, end, dir),
            ]
        },
        melt(dir, start, end) {
            return [
                ride(start, FIRE_X, dir),
                stay(3, FIRE_X, dir, u => ({ melt: ease(u), drops: u, say: { snowman: u < 0.6 ? "I'm not fat... I'm melting!" : '' } })),
                stay(2.5, FIRE_X, dir, () => ({ melt: 1 })),
                stay(2, FIRE_X, dir, u => ({ melt: 1 - ease(u), say: { snowman: u > 0.5 ? 'Phew. Back in shape.' : '' } })),
                stay(0.6, FIRE_X, dir),
                ride(FIRE_X, end, dir),
            ]
        },
        sweat(dir, start, end) {
            return [
                ride(start, FIRE_X, dir),
                stay(2.2, FIRE_X, dir, u => ({ melt: 0.2 * ease(u), drops: u })),
                stay(0.9, FIRE_X, dir, u => ({ melt: 0.2, hop: Math.sin(u * Math.PI * 5) * 4, say: { snowman: 'Too hot! Too hot!' } })),    // panic!
                ride(FIRE_X, end, dir, u => ({ melt: 0.2 * (1 - Math.min(1, u * 3)), wheelie: -10 * Math.max(0, 1 - u * 4) }), 2.6),
            ]
        },
        jump(dir, start, end) {
            const takeOff = RAMP_X - dir * 18, landing = takeOff + dir * 150
            return [
                ride(start, takeOff, dir),
                ride(takeOff, landing, dir, u => ({ hop: 70 * 4 * u * (1 - u) + 14 * (1 - u), spin: -360 * ease(u), say: { snowman: 'Look mum, no carrots!' } }), 1.3),
                ride(landing, landing + dir * 30, dir, u => ({ hop: Math.sin(u * Math.PI) * 4 }), 0.8),        // a little bounce
                ride(landing + dir * 30, end, dir),
            ]
        },
        wheelie(dir, start, end) {
            const a = start + dir * W * 0.3, b = start + dir * W * 0.8
            return [
                ride(start, a, dir),
                ride(a, a + dir * 30, dir, u => ({ wheelie: -24 * ease(u) })),
                ride(a + dir * 30, b, dir, u => ({ wheelie: -24 + 5 * Math.sin(u * 22), say: { snowman: u < 0.4 ? 'Watch this!' : '' } })),
                ride(b, b + dir * 20, dir, u => ({ wheelie: -24 * (1 - ease(u)) })),
                ride(b + dir * 20, end, dir),
            ]
        },
        hat(dir, start, end) {
            const a = start + dir * W * 0.4
            return [
                ride(start, a, dir),
                ride(a, a + dir * 180, dir, u => ({ hatHop: 4 * u * (1 - u), hatSpin: 720 * u, say: { snowman: 'My hat! My precious!' } })),
                ride(a + dir * 180, end, dir),
            ]
        },
        turbo(dir, start, end) {
            const a = start + dir * W * 0.15, b = start + dir * W * 0.62
            return [
                ride(start, a, dir),
                ride(a, b, dir, u => ({ wheelie: -6 * Math.sin(u * 30) * u, say: { snowman: u > 0.2 ? 'Wheeeee!' : '' } }), 3.2),     // full speed
                ride(b, b + dir * 50, dir, u => ({ tumble: 10 * Math.sin(u * Math.PI), spray: u }), 1.2), // skid
                stay(1.2, b + dir * 50, dir, u => ({ spray: 1 + u, hop: u < 0.3 ? Math.sin(u / 0.3 * Math.PI) * 3 : 0 })),
                ride(b + dir * 50, end, dir),
            ]
        },
        nap(dir, start, end) {
            const x = start + dir * W * 0.36
            return [
                ride(start, x - dir * 80, dir),
                ride(x - dir * 80, x, dir, u => ({}), 0.45),                                             // slows down
                stay(0.8, x, dir, u => ({ tumble: 9 * ease(u) })),                                       // nods off
                stay(4, x, dir, u => ({ tumble: 9 + Math.sin(u * 12) * 1.5, zzz: u, say: { snowman: u > 0.55 ? 'Five more minutes, mum...' : '' } })),
                stay(0.5, x, dir, u => ({ tumble: 9 * (1 - u), hop: Math.sin(u * Math.PI) * 10 })),       // wakes up with a start
                ride(x, end, dir, () => ({}), 1.4),
            ]
        },
        snowball(dir, start, end) {
            const x = start + dir * W * 0.5
            return [
                ride(start, x - dir * 110, dir),
                ride(x - dir * 110, x, dir, u => ({ ball: u })),                                         // it flies at him
                stay(0.4, x, dir, u => ({ splat: 1, tumble: 14 * Math.sin(u * Math.PI) })),
                stay(1.8, x, dir, u => ({ splat: 1 - Math.max(0, u * 1.6 - 0.6), tumble: 4 * Math.sin(u * 14) * (1 - u), say: { snowman: 'Hey! Who did that?!' } })),
                ride(x, end, dir),
            ]
        },
        trick(dir, start, end) {
            const x = start + dir * W * 0.4
            return [
                ride(start, x, dir),
                stay(0.4, x, dir, u => ({ wheelie: -22 * ease(u) })),
                stay(1.6, x, dir, u => ({ wheelie: -22, hop: Math.abs(Math.sin(u * Math.PI * 2)) * 6, flip: Math.round(u * 4) % 2 })),
                stay(0.4, x, dir, u => ({ wheelie: -22 * (1 - ease(u)) })),
                stay(1.6, x, dir, u => ({ tumble: 16 * Math.sin(Math.min(1, u * 1.8) * Math.PI), say: { snowman: 'Ta-daa! Thank you, thank you.' } })),   // a bow
                ride(x, end, dir),
            ]
        },
        david(dir, start, end) {
            const p1 = start + dir * W * 0.35, p2 = start + dir * W * 0.7
            const gave = p2 - dir * 300                                           // where David gives up
            const runner = x => ({ x, mode: 'run', dir })
            return [
                ride(start, p1, dir, u => ({
                    david: runner(start + (p1 - start) * u - dir * 130),
                    say: { david: u > 0.2 ? "Hey!! That's MY bike!" : '' },
                }), 1.1),
                ride(p1, p2, dir, u => ({
                    david: runner(p1 + (p2 - p1) * u - dir * (130 + 170 * u)),
                    say: { david: u < 0.6 ? 'Come back! I still have 3 payments left on it!' : '', snowman: u > 0.5 ? 'Sorry David, Christmas emergency!' : '' },
                }), 1.5),
                ride(p2, end, dir, u => ({
                    david: { x: gave, mode: 'tired', dir },
                    say: { snowman: u < 0.3 ? 'Sorry David, Christmas emergency!' : '', david: u > 0.45 ? '*pant* ... *pant* ...' : '' },
                }), 1.5),
                stay(6, end, dir, u => ({
                    hidden: true,
                    david: { x: gave, mode: 'tired', dir },
                    say: { david: u < 0.5 ? "Brrr... it's at least minus 8000 out here!" : 'These snowmen are crazy!' },
                })),
                stay(Math.abs(gave - start) / 60, end, dir, u => ({
                    hidden: true,
                    david: { x: gave + (start - gave) * u, mode: 'walk', dir: -dir },
                    say: { david: u < 0.25 ? "Fine. I'll take the bus." : '' },
                })),
            ]
        },
        fly(dir, start, end) {
            const a = start + dir * W * 0.12, b = start + dir * W * 0.88
            const span = Math.abs(b - a)
            return [
                ride(start, a, dir),
                stay(1.4, a, dir, u => ({ fly: ease(u), hop: Math.sin(u * 40) * u, say: { snowman: 'Bike, transform!' } })),   // transforms, shaking
                stay(1, a, dir, u => ({ fly: 1, hop: 120 * ease(u) })),                                  // lift-off
                ride(a, b, dir, u => ({
                    fly: 1,
                    hop: 120 + 90 * Math.sin(u * Math.PI) + 10 * Math.sin(u * span / 40),               // up in the sky, bobbing
                    tumble: 6 * Math.sin(u * span / 60),
                }), 1.5),
                stay(1.3, b, dir, u => ({ fly: 1, hop: 120 * (1 - ease(u)), say: { snowman: 'Santa, eat your heart out.' } })),   // landing
                stay(1, b, dir, u => ({ fly: 1 - ease(u) })),
                ride(b, end, dir),
            ]
        },
        wish(dir, start, end) {
            const x = start + dir * W * 0.38                  // where the star hits him
            const landed = x - dir * 26                       // where his head lands
            const caught = x + dir * W * 0.3                  // where the head catches the bike
            const after = { riderless: true, smash: x }       // from the impact on
            const headAt = (hx, hop = 0, spin = 0) => ({ x: hx, hop, spin, dir })
            return [
                ride(start, x, dir),
                stay(0.4, x, dir, u => ({ star: u > 0.5 })),
                stay(2.2, x, dir, u => ({ say: { snowman: u < 0.7 ? 'I wish for... a fridge.' : '' } })),
                stay(1, x, dir, u => ({ meteor: { u, x }, say: { snowman: u > 0.45 ? 'Uh oh.' : '' } })),   // a star falls on him
                // impact: a flash, the body squashed, the head flies off and lands in the snow
                stay(0.7, x, dir, u => ({ ...after, flash: 1 - u, head: headAt(x + (landed - x) * u, 46 * (1 - u) + 40 * 4 * u * (1 - u), -540 * u) })),
                // the bike rolls on alone; the head, dizzy, then hops after it
                ride(x, caught, dir, u => {
                    const chase = Math.max(0, (u - 0.38) / 0.62)
                    const hx = landed + (caught - landed) * chase
                    return {
                        ...after,
                        dizzyHead: u < 0.3 ? 1 : 0,
                        head: headAt(hx, chase > 0 ? Math.abs(Math.sin(chase * Math.PI * 9)) * 16 : 0),
                        say: { head: u < 0.25 ? 'Ouch...' : u < 0.5 ? 'Hey! Wait for me!' : '' },
                    }
                }, 0.8),
                // the head jumps onto the seat
                stay(0.6, caught, dir, u => ({ ...after, head: headAt(caught, 30 * ease(u) + 20 * Math.sin(u * Math.PI)) })),
                ride(caught, end, dir, u => ({ ...after, headOnly: true, say: { head: u < 0.3 ? 'Who needs a body anyway?' : '' } })),
            ]
        },
    }

    function startRider(land) {
        const svg = land.querySelector('svg')
        const q = sel => svg.querySelector(sel)
        const rider = q('.xmas-rider'), tumble = q('.xmas-rider__tumble'), snowman = q('.xmas-rider__snowman')
        const hatEl = q('.xmas-rider__hat'), puddle = q('.xmas-rider__puddle'), dizzy = q('.xmas-rider__dizzy')
        const dizzySpin = q('.xmas-rider__dizzy-spin'), crashTreeEl = q('.xmas-crash-tree')
        const spokes = svg.querySelectorAll('.xmas-rider__spokes'), drops = svg.querySelectorAll('.xmas-rider__drop')
        const wheels = svg.querySelectorAll('.xmas-rider__wheel'), jets = svg.querySelectorAll('.xmas-rider__jet')
        const crashSnow = svg.querySelectorAll('.xmas-crash-snow'), sprays = svg.querySelectorAll('.xmas-rider__spray')
        const zzz = q('.xmas-rider__zzz'), splat = q('.xmas-rider__splat'), ball = q('.xmas-snowball')
        const davidEl = q('.xmas-david'), davidBody = q('.xmas-david__body'), davidName = q('.xmas-david-name')
        const davidLegs = svg.querySelectorAll('.xmas-david__leg'), davidArms = svg.querySelectorAll('.xmas-david__arm')
        const bubbles = { david: q('.xmas-bubble--david'), snowman: q('.xmas-bubble--snowman'), head: q('.xmas-bubble--head') }
        const smash = q('.xmas-smash'), meteor = q('.xmas-meteor'), meteorTrail = q('.xmas-meteor__trail'), meteorStar = q('.xmas-meteor__star')
        const flash = q('.xmas-flash'), looseHeadEl = q('.xmas-loose-head'), looseHeadSpin = q('.xmas-loose-head__spin')
        const looseHeadDizzy = q('.xmas-loose-head__dizzy')
        const treeGround = groundY(TREE_X) + 2
        // Melting from riding past the fire: builds up near it, freezes back slowly
        let warmth = 0

        if (reducedMotion) {                             // a still snowman on his bike
            rider.setAttribute('transform', `translate(${W * 0.32},${groundY(W * 0.32).toFixed(1)})`)
            return null
        }

        // The current pass: its steps, the step being played and the time spent in it
        let dir = -1, scenario = null, steps = [], index = 0, elapsed = 0, starShown = false
        let leaving = false, current = null          // stopped from the menu: he rides off first
        // The next pass, with a random scenario after a pause off screen (3–6 s),
        // or the one asked for from the menu, right away
        function nextPass(asked) {
            dir = -dir
            const names = Object.keys(SCENARIOS).filter(n => n !== scenario)
            scenario = asked || names[Math.floor(Math.random() * names.length)]
            const start = dir > 0 ? -60 : W + 60, end = dir > 0 ? W + 60 : -60
            steps = SCENARIOS[scenario](dir, start, end)
            if (!asked) steps.unshift(stay(3 + Math.random() * 3, start, dir, () => ({ hidden: true })))
            index = 0
            elapsed = 0
            starShown = false
        }
        nextPass()

        let last = null, wheelAngle = 0, frame = null
        const draw = now => {
            frame = requestAnimationFrame(draw)
            const dt = last === null ? 0 : Math.min(0.1, (now - last) / 1000)    // no jump after a hidden tab
            last = now
            if (riderOff() && !leaving) { hideAll(); return }
            elapsed += dt
            while (elapsed >= steps[index][0]) {
                elapsed -= steps[index][0]
                if (++index < steps.length) continue
                if (leaving) { leaving = false; current = null; hideAll(); return }
                nextPass()
            }
            const s = Object.assign({ tumble: 0, wheelie: 0, spin: 0, hop: 0, melt: 0, dizzy: 0, drops: 0, hatHop: 0, hatSpin: 0,
                crash: null, moving: 0, spray: 0, zzz: 0, splat: 0, ball: null, flip: 0, fly: 0 },
                steps[index][1](elapsed / steps[index][0]))
            current = s
            if (s.star && !starShown) { starShown = true; spawnShootingStar() }
            if (s.flip) s.dir = -s.dir                                             // the trick: facing the other way
            const heat = s.hidden ? 0 : Math.max(0, 1 - Math.abs(s.x - FIRE_X) / 110)
            const warming = heat > 0.15 && s.melt === 0
            warmth = warming ? Math.min(0.5, warmth + heat * dt * 0.9) : Math.max(0, warmth - dt * 0.12)
            if (s.melt === 0 && warmth > 0) { s.melt = warmth; if (warming) s.drops = (s.drops || 0) + (now / 1000 % 1) * 0.98 + 0.01 }

            rider.style.display = s.hidden ? 'none' : ''
            const slope = Math.atan2(groundY(s.x + 4) - groundY(s.x - 4), 8) * 180 / Math.PI
            rider.setAttribute('transform', `translate(${s.x.toFixed(1)},${(groundY(s.x) - s.hop).toFixed(1)}) rotate(${slope.toFixed(2)}) scale(${s.dir},1)`)
            wheelAngle += (s.moving * SPEED / 7.5 * 180 / Math.PI + s.fly * 2200) * dt     // propellers spin fast
            // flying bike: the wheels rise a little and lie flat, jets flicker under them
            wheels.forEach(el => el.setAttribute('transform', `translate(${el.dataset.cx},${(-8 - 5 * s.fly).toFixed(1)}) scale(${(1 + 0.4 * s.fly).toFixed(2)},${(1 - 0.8 * s.fly).toFixed(2)})`))
            jets.forEach((el, i) => {
                const flicker = 0.75 + 0.25 * Math.sin(now / 40 + i * 2)
                el.setAttribute('opacity', (s.fly * 0.95).toFixed(2))
                el.setAttribute('transform', `translate(${el.dataset.cx},-6) scale(1,${(s.fly * flicker * (1 + Math.min(1, s.hop / 40))).toFixed(2)}) translate(${-el.dataset.cx},6)`)
            })
            spokes.forEach(el => el.setAttribute('transform', `rotate(${(wheelAngle % 360).toFixed(1)})`))
            // falling over / wheelie pivot on the rear wheel, the backflip turns around his middle
            tumble.setAttribute('transform', `rotate(${(s.tumble + s.wheelie).toFixed(1)} -19 0) rotate(${s.spin.toFixed(1)} 0 -24)`)
            dizzy.setAttribute('opacity', s.dizzy.toFixed(2))
            dizzySpin.setAttribute('transform', `rotate(${((now / 1000) * 360) % 360})`)
            // melting: the snowman sinks onto the seat and spreads, the hat comes down with him
            const m = s.melt
            snowman.setAttribute('transform', `translate(-2,-22) scale(${(1 + 0.5 * m).toFixed(3)},${(1 - 0.9 * m).toFixed(3)}) translate(2,22)`)
            snowman.setAttribute('opacity', (1 - 0.6 * m).toFixed(2))
            hatEl.setAttribute('transform', `translate(${(14 * s.hatHop).toFixed(1)},${(31 * m - 60 * s.hatHop).toFixed(1)}) rotate(${(-25 * m + s.hatSpin).toFixed(1)} -1 -53)`)
            puddle.setAttribute('rx', (24 * m).toFixed(1))
            puddle.setAttribute('opacity', (0.75 * m).toFixed(2))
            drops.forEach((d, i) => {
                const p = (s.drops * 4 + i / 3) % 1
                d.setAttribute('cy', (-20 + 20 * p).toFixed(1))
                d.setAttribute('opacity', s.drops > 0 && s.drops < 1 ? (1 - p).toFixed(2) : '0')
            })
            drawDavid(s.david, now)
            drawWish(s, now)
            const say = s.say || {}
            const head = s.hidden || s.riderless ? null : [s.x, groundY(s.x) - s.hop - 64]
            const headPos = s.headOnly ? [s.x - s.dir * 2, groundY(s.x) - s.hop - 30] : s.head ? [s.head.x, groundY(s.head.x) - 6 - s.head.hop] : null
            setBubble(bubbles.snowman, head && say.snowman, head)
            setBubble(bubbles.david, s.david && say.david, s.david && [s.david.x, groundY(s.david.x) - 80])
            setBubble(bubbles.head, say.head, headPos && [headPos[0], headPos[1] - 18])
            zzz.setAttribute('opacity', s.zzz ? Math.min(1, s.zzz * 6, (1 - s.zzz) * 6).toFixed(2) : '0')
            zzz.setAttribute('transform', `translate(0,${(-3 * Math.sin(now / 500)).toFixed(1)})`)
            splat.setAttribute('opacity', s.splat.toFixed(2))
            sprays.forEach(el => {
                const i = +el.dataset.i, p = s.spray ? (s.spray * 2 + i / 5) % 1 : 0
                el.setAttribute('cx', (-20 - 30 * p).toFixed(1))
                el.setAttribute('cy', (-2 - 18 * p * (1 - p) * 4 * (0.6 + i * 0.1)).toFixed(1))
                el.setAttribute('opacity', s.spray ? (1 - p).toFixed(2) : '0')
            })
            if (s.ball === null) ball.setAttribute('opacity', '0')
            else {                                       // thrown from ahead of him, at his face
                const bx = s.x + s.dir * (8 + 260 * (1 - s.ball)), by = groundY(s.x) - 44 - 60 * 4 * s.ball * (1 - s.ball) * (1 - s.ball)
                ball.setAttribute('cx', bx.toFixed(1))
                ball.setAttribute('cy', by.toFixed(1))
                ball.setAttribute('opacity', '1')
            }
            // the crash: the tree shakes and drops a puff of snow
            const c = s.crash
            const shake = c === null ? 0 : 7 * Math.sin(c * 18) * Math.exp(-c * 2.2)
            crashTreeEl.setAttribute('transform', `rotate(${shake.toFixed(2)} ${TREE_X} ${treeGround})`)
            crashSnow.forEach(el => {
                const y0 = +el.dataset.y, p = c === null ? 0 : Math.min(1, c / 1.2)
                el.setAttribute('cy', (y0 + (treeGround - 2 - y0) * p).toFixed(1))
                el.setAttribute('opacity', c === null || p >= 1 ? '0' : (1 - p).toFixed(2))
            })
        }
        // The wish scenario: the falling star, the flash, the squashed body, the head on its own
        function drawWish(s, now) {
            const hideSnowman = s.riderless || s.headOnly
            snowman.style.display = hideSnowman ? 'none' : ''
            hatEl.style.display = hideSnowman ? 'none' : ''
            smash.setAttribute('opacity', s.smash === undefined ? '0' : '1')
            if (s.smash !== undefined) smash.setAttribute('transform', `translate(${s.smash},${groundY(s.smash).toFixed(1)})`)
            if (s.meteor) {                              // from high in the sky, behind him, onto his head
                const { u, x } = s.meteor, d = s.dir
                const x0 = x - d * 320, y0 = -SKY + 10, x1 = x, y1 = groundY(x) - 46
                const mx = x0 + (x1 - x0) * u * u, my = y0 + (y1 - y0) * u * u
                meteor.setAttribute('opacity', '1')
                meteorStar.setAttribute('transform', `translate(${mx.toFixed(1)},${my.toFixed(1)}) rotate(${(now / 3) % 360})`)
                meteorTrail.setAttribute('x1', (mx - (x1 - x0) * 0.18).toFixed(1))
                meteorTrail.setAttribute('y1', (my - (y1 - y0) * 0.18).toFixed(1))
                meteorTrail.setAttribute('x2', mx.toFixed(1))
                meteorTrail.setAttribute('y2', my.toFixed(1))
            } else meteor.setAttribute('opacity', '0')
            if (s.flash) {
                flash.setAttribute('cx', s.smash)
                flash.setAttribute('cy', (groundY(s.smash) - 30).toFixed(1))
                flash.setAttribute('r', (60 * (1 - s.flash) + 10).toFixed(1))
                flash.setAttribute('opacity', (0.9 * s.flash).toFixed(2))
            } else flash.setAttribute('opacity', '0')
            const at = s.headOnly ? { x: s.x - s.dir * 2, y: groundY(s.x) - s.hop - 30, spin: 0, dir: s.dir }
                : s.head ? { x: s.head.x, y: groundY(s.head.x) - 6 - s.head.hop, spin: s.head.spin, dir: s.head.dir } : null
            if (!at) { looseHeadEl.style.display = 'none'; return }
            looseHeadEl.style.display = ''
            looseHeadEl.setAttribute('transform', `translate(${at.x.toFixed(1)},${at.y.toFixed(1)}) scale(${at.dir},1)`)
            looseHeadSpin.setAttribute('transform', `rotate(${at.spin.toFixed(1)})`)
            looseHeadDizzy.setAttribute('opacity', s.dizzyHead ? '1' : '0')
            looseHeadDizzy.setAttribute('transform', `translate(0,-18) rotate(${(now / 3) % 360})`)
        }

        function hideAll() {
            rider.style.display = 'none'
            davidEl.style.display = 'none'
            davidName.setAttribute('opacity', '0')
            looseHeadEl.style.display = 'none'
            smash.setAttribute('opacity', '0')
            meteor.setAttribute('opacity', '0')
            Object.values(bubbles).forEach(b => b.setAttribute('opacity', '0'))
        }

        function drawDavid(d, now) {
            if (!d) { davidEl.style.display = 'none'; davidName.setAttribute('opacity', '0'); return }
            const t = now / 1000
            const swing = d.mode === 'run' ? 38 * Math.sin(t * 14) : d.mode === 'walk' ? 20 * Math.sin(t * 7) : 14
            const lean = d.mode === 'run' ? 12 : d.mode === 'tired' ? 38 + 2 * Math.sin(t * 6) : 4    // bent over, panting
            const bob = d.mode === 'run' ? Math.abs(Math.sin(t * 14)) * 2 : 0
            davidEl.style.display = ''
            davidEl.setAttribute('transform', `translate(${d.x.toFixed(1)},${(groundY(d.x) - bob).toFixed(1)}) scale(${d.dir},1)`)
            davidLegs.forEach((leg, i) => leg.setAttribute('transform', `rotate(${(i ? swing : -swing).toFixed(1)} 0 -22)`))
            // out of breath: hands on the knees; otherwise the arms swing with the legs
            davidArms.forEach((arm, i) => arm.setAttribute('transform', d.mode === 'tired'
                ? `rotate(-20 ${arm.dataset.x} -38)` : `rotate(${(i ? -swing : swing).toFixed(1)} ${arm.dataset.x} -38)`))
            davidBody.setAttribute('transform', `rotate(${lean.toFixed(1)} 0 -22)`)
            davidName.setAttribute('x', d.x.toFixed(1))
            davidName.setAttribute('y', (groundY(d.x) - bob - 64 + (d.mode === 'tired' ? 12 : 0)).toFixed(1))
            davidName.setAttribute('opacity', '1')
        }

        // A speech bubble above `at` = [x, y], kept inside the band
        function setBubble(el, text, at) {
            if (!text || !at) { el.setAttribute('opacity', '0'); return }
            const label = el.querySelector('text')
            if (label.textContent !== text) label.textContent = text
            const w = label.getComputedTextLength() + 16, h = 20
            const x = Math.min(W - w / 2 - 6, Math.max(w / 2 + 6, at[0])), y = at[1] - h - 8
            const tail = Math.min(x + w / 2 - 10, Math.max(x - w / 2 + 10, at[0]))
            el.querySelector('path').setAttribute('d',
                `M${x - w / 2 + 6},${y} h${w - 12} q6,0 6,6 v${h - 12} q0,6 -6,6 H${tail + 5} l-5,7 l-2,-7 H${x - w / 2 + 6} q-6,0 -6,-6 v${-(h - 12)} q0,-6 6,-6 Z`)
            label.setAttribute('x', x.toFixed(1))
            label.setAttribute('y', (y + 14).toFixed(1))
            el.setAttribute('opacity', '1')
        }

        frame = requestAnimationFrame(draw)
        return {
            stop: () => cancelAnimationFrame(frame),
            play(name) {
                try { localStorage.setItem(RIDER_OFF_KEY, '0') } catch { /* storage unavailable */ }
                leaving = false
                warmth = 0
                nextPass(name)
            },
            // Stopped from the menu: instead of vanishing he waves, then rides off
            // quickly by the nearest edge (David, if around, stays where he is no more)
            leave() {
                const s = current
                if (!s || s.hidden) { leaving = false; return }
                const out = s.x < W / 2 ? -1 : 1, edge = out > 0 ? W + 60 : -60
                leaving = true
                steps = [
                    stay(0.8, s.x, out, u => ({ hop: Math.abs(Math.sin(u * Math.PI * 2)) * 6, say: { snowman: 'Bye bye!' } })),
                    ride(s.x, edge, out, () => ({}), 2.6),
                ]
                index = 0
                elapsed = 0
            },
            resume() {
                leaving = false
                nextPass()
            },
        }
    }

    // Menu item to stop / start the snowman's ride (remembered in this browser)
    function riderSwitch(rider) {
        const btn = menuItem('fa-person-biking', 'Snowman')
        const update = () => {
            const off = riderOff()
            btn.classList.toggle('is-off', off)
            setLabel(btn, off ? 'Bring the snowman back' : 'Stop the snowman')
            btn.setAttribute('aria-pressed', String(off))
        }
        btn.addEventListener('click', () => {
            const off = !riderOff()
            try { localStorage.setItem(RIDER_OFF_KEY, off ? '1' : '0') } catch { /* storage unavailable */ }
            if (off) rider.leave(); else rider.resume()
            update()
        })
        btn._update = update
        update()
        return btn
    }

    // The Christmas menu, bottom right: one tree button that opens the list of
    // switches and of the snowman's scenarios (any one can be played right away).
    function christmasMenu(items, rider) {
        const menu = document.createElement('div')
        menu.className = 'xmas-menu'
        const toggle = document.createElement('button')
        toggle.type = 'button'
        toggle.className = 'xmas-menu__toggle'
        toggle.title = 'Christmas decorations'
        toggle.setAttribute('aria-label', toggle.title)
        toggle.setAttribute('aria-expanded', 'false')
        toggle.innerHTML = '<i class="fa-solid fa-tree"></i>'
        const panel = document.createElement('div')
        panel.className = 'xmas-menu__panel'
        panel.hidden = true
        const open = yes => {
            panel.hidden = !yes
            toggle.setAttribute('aria-expanded', String(yes))
            menu.classList.toggle('is-open', yes)
        }
        items.forEach(item => panel.appendChild(item))
        if (rider) {
            const title = document.createElement('div')
            title.className = 'xmas-menu__title'
            title.textContent = 'Snowman scenarios'
            panel.appendChild(title)
            Object.entries(SCENARIO_LABELS).forEach(([name, [icon, label]]) => {
                const btn = menuItem(icon, label, 'xmas-menu__scenario')
                btn.addEventListener('click', () => {
                    rider.play(name)
                    items.forEach(item => item._update && item._update())     // the snowman switch is back on
                    open(false)                                               // out of the way, to watch it
                    const land = document.querySelector('.xmas-land')
                    if (land) land.scrollIntoView({ behavior: reducedMotion ? 'auto' : 'smooth', block: 'end' })
                })
                panel.appendChild(btn)
            })
        }
        toggle.addEventListener('click', () => open(panel.hidden))
        menu._outside = e => { if (!menu.contains(e.target)) open(false) }
        menu._escape = e => { if (e.key === 'Escape') open(false) }
        document.addEventListener('click', menu._outside)
        document.addEventListener('keydown', menu._escape)
        menu.append(panel, toggle)
        return menu
    }

    // ── Mount / unmount ───────────────────────────────────────────────

    function mount() {
        const menuItems = []
        const nav = document.getElementById('main-navbar')
        if (nav) {
            nav.appendChild(garland(nav))
            menuItems.push(garlandSwitch())
            scheduleGarland()
        }
        const logo = document.querySelector('.custom-sidebar-header')
        if (logo) placeHat(logo)
        if (document.getElementById('accordionSidebar')) document.body.appendChild(baubles())
        const snowEl = snow()
        document.body.appendChild(snowEl)
        weather(snowEl)
        menuItems.unshift(snowSwitch(snowEl))
        document.body.appendChild(stars())
        menuItems.push(shootingStarSwitch())
        shootingTimer = setTimeout(shootingStar, (4 + Math.random() * 6) * 1000)    // a first one soon
        // Landscape band right above the footer, in the page flow
        const land = landscape()
        const footer = document.querySelector('footer.site-footer')
        if (footer) footer.parentNode.insertBefore(land, footer)
        else document.body.appendChild(land)
        const rider = startRider(land)
        if (rider) { stopRider = rider.stop; menuItems.push(riderSwitch(rider)) }
        document.body.appendChild(christmasMenu(menuItems, rider))
        setGarlandPattern(garlandPattern)              // the garland item's label
        mounted = true
    }

    function unmount() {
        clearTimeout(weatherTimer)
        clearTimeout(garlandTimer)
        clearTimeout(shootingTimer)
        stopRider()
        stopRider = () => {}
        document.querySelectorAll('.xmas-menu').forEach(menu => {
            document.removeEventListener('click', menu._outside)
            document.removeEventListener('keydown', menu._escape)
        })
        if (hatObserver) { hatObserver.disconnect(); hatObserver = null }
        document.querySelectorAll('.xmas-garland, .xmas-hat, .xmas-snow, .xmas-menu, .xmas-baubles, .xmas-stars, .xmas-land').forEach(el => el.remove())
        document.querySelectorAll('.xmas-logo').forEach(el => el.classList.remove('xmas-logo'))
        mounted = false
    }

    function sync() {
        if (wanted() === mounted) return
        if (mounted) unmount()
        else mount()
    }

    window.addEventListener('resize', () => {
        if (!mounted) return
        clearTimeout(resizeTimer)
        resizeTimer = setTimeout(() => {
            const nav = document.getElementById('main-navbar')
            const old = nav && nav.querySelector('.xmas-garland')
            if (old) old.replaceWith(garland(nav))
        }, 200)
    })
    new MutationObserver(sync).observe(html, { attributes: true, attributeFilter: ['data-theme-pref'] })
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', sync)
    else sync()
})()
