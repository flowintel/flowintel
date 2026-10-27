/**
 * themes/tour.js — Decorations of the "Yellow Jersey" theme (css/themes/tour.css).
 *
 * Present only while <html data-theme-pref="tour">, added and removed live when the
 * theme is switched (user_settings.js sets the attribute); nothing for other themes.
 * A race band above the footer: mountains, a road with "GO GO GO" painted on it, fans
 * with flags behind the barriers, the flamme rouge, and the peloton riding by again
 * and again: the yellow jersey, the polka-dot and the green jerseys and the others,
 * pedalling, jostling a little; now and then the yellow jersey attacks. Far behind
 * comes David, smaller and very slow (black curly hair, glasses, a beard): he crashes
 * in the middle of the road, and Christian, with glasses, rides right over
 * him and carries on as if nothing happened. David gets up and finishes the race.
 */
(function () {
    const html = document.documentElement
    const reducedMotion = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches
    const W = 1440, H = 300
    const ROAD_Y = 262                 // where the wheels touch the road
    let mounted = false, frame = null

    const wanted = () => html.getAttribute('data-theme-pref') === 'tour'

    // ── Scenery ───────────────────────────────────────────────────────

    function ridge(base, amp, waves, phase) {
        let d = `M0,${H} L0,${base}`
        for (let x = 0; x <= W; x += 30) {
            const y = base - amp * Math.abs(Math.sin(x / W * Math.PI * waves + phase)) - amp * 0.25 * Math.sin(x / 37)
            d += ` L${x},${y.toFixed(1)}`
        }
        return d + ` L${W},${H} Z`
    }

    function scenery() {
        let seed = 11
        const rand = () => ((seed = (seed * 16807) % 2147483647) / 2147483647)
        let g = ''
        // the Alps far away, with snow on the summits, then green hills
        g += `<path d="${ridge(150, 95, 3.2, 0.4)}" fill="#c9d6e6"/>`
        g += `<path d="${ridge(150, 95, 3.2, 0.4)}" fill="#ffffff" opacity=".55" clip-path="url(#tour-snowline)"/>`
        g += `<path d="${ridge(200, 40, 2.1, 1.3)}" fill="#a9cf8f"/>`
        g += `<path d="${ridge(222, 22, 3.7, 0.2)}" fill="#86bb6e"/>`
        // fans behind the barriers, some waving flags
        const shirts = ['#d4262c', '#2f6fb0', '#f2c200', '#ffffff', '#2e8b57', '#ff8a00', '#7a4fbf', '#26282c']
        for (let x = 12; x < W; x += 15 + rand() * 9) {
            const y = 236 + rand() * 3, c = shirts[Math.floor(rand() * shirts.length)]
            const delay = (-rand() * 0.9).toFixed(2)
            g += `<g class="tour-fan" style="animation-delay:${delay}s">` +
                `<rect x="${(x - 3.5).toFixed(1)}" y="${(y - 9).toFixed(1)}" width="7" height="9" rx="2" fill="${c}"/>` +
                `<circle cx="${x.toFixed(1)}" cy="${(y - 12).toFixed(1)}" r="3" fill="#f2c9a0"/></g>`
            if (rand() < 0.16) {
                const fc = ['#f2c200', '#d4262c', '#2f6fb0', '#2e8b57'][Math.floor(rand() * 4)]
                g += `<line x1="${(x + 3).toFixed(1)}" y1="${(y - 8).toFixed(1)}" x2="${(x + 3).toFixed(1)}" y2="${(y - 27).toFixed(1)}" stroke="#6b5a3a" stroke-width="1"/>` +
                    `<rect class="tour-flag" style="animation-delay:${delay}s" x="${(x + 3).toFixed(1)}" y="${(y - 27).toFixed(1)}" width="12" height="8" fill="${fc}"/>`
            }
        }
        // barriers
        g += `<rect x="0" y="236" width="${W}" height="6" fill="#e9edf2"/>`
        for (let x = 0; x < W; x += 60) g += `<rect x="${x}" y="236" width="28" height="6" fill="#f2c200"/>`
        // the road, its edge line, the dashed middle line and a bit of fans' paint
        g += `<rect x="0" y="242" width="${W}" height="${H - 242}" fill="#4a4d52"/>`
        g += `<rect x="0" y="244" width="${W}" height="1.5" fill="#ffffff" opacity=".8"/>`
        g += `<line x1="0" y1="280" x2="${W}" y2="280" stroke="#ffffff" stroke-width="2.5" stroke-dasharray="34 26" opacity=".85"/>`
        g += '<text x="560" y="293" font-family="system-ui, Arial, sans-serif" font-weight="800" font-size="14" fill="#ffffff" opacity=".35" letter-spacing="8">GO  GO  GO</text>'
        // the flamme rouge: a red triangle hanging over the road
        const fx = W * 0.82
        g += `<line x1="${fx - 70}" y1="150" x2="${fx - 70}" y2="246" stroke="#9aa0a8" stroke-width="3"/>`
        g += `<line x1="${fx + 70}" y1="150" x2="${fx + 70}" y2="246" stroke="#9aa0a8" stroke-width="3"/>`
        g += `<line x1="${fx - 72}" y1="150" x2="${fx + 72}" y2="150" stroke="#9aa0a8" stroke-width="3"/>`
        g += `<path class="tour-banner" d="M${fx - 26},152 L${fx + 26},152 L${fx},190 Z" fill="#d4262c"/>`
        return g
    }

    // ── The riders ────────────────────────────────────────────────────
    // jersey colours; "dots" is the polka-dot pattern

    const RIDERS = [
        { jersey: '#f2c200', helmet: '#f2c200', lead: true },     // the yellow jersey
        { jersey: 'url(#tour-dots)', helmet: '#ffffff' },          // the climber
        { jersey: '#2e9e4f', helmet: '#2e9e4f' },                  // the sprinter
        { jersey: '#ffffff', helmet: '#26282c' },                  // the best young rider
        { jersey: '#2f6fb0', helmet: '#2f6fb0' },
        { jersey: '#d4262c', helmet: '#26282c' },
        { jersey: '#ff8a00', helmet: '#ff8a00' },
        { jersey: '#26282c', helmet: '#26282c' },
        { jersey: '#17a2b8', helmet: '#ffffff' },
        { jersey: '#7a4fbf', helmet: '#7a4fbf' },
    ]

    // The two riders far behind the peloton
    const DAVID = { jersey: '#1f3763', helmet: '#ffffff', who: 'david' }
    const CHRISTIAN = { jersey: '#c0392b', helmet: '#26282c', who: 'christian' }

    // A rider on a bike, drawn around (0,0) = the ground under the crank, facing right.
    // The legs are drawn by the loop (they follow the pedals).
    function rider(r, i) {
        const wheel = cx => `<g transform="translate(${cx},-10)"><circle r="10" fill="none" stroke="#1a1b1e" stroke-width="2"/>` +
            `<g class="tour-spokes"><line x1="0" y1="-9" x2="0" y2="9" stroke="#9aa0a8" stroke-width=".7"/><line x1="-9" y1="0" x2="9" y2="0" stroke="#9aa0a8" stroke-width=".7"/></g></g>`
        return `<g class="tour-rider${r.who ? ' tour-rider--' + r.who : ''}" data-i="${i}">` +
            wheel(-16) + wheel(16) +
            '<path d="M-16,-10 L-3,-10 L-7,-27 Z M-3,-10 L11,-26 L-7,-27 M11,-26 L16,-10 M11,-26 L12,-30" fill="none" stroke="#d9dde3" stroke-width="2" stroke-linejoin="round"/>' +
            '<path d="M10,-30 q5,0 5,4" fill="none" stroke="#1a1b1e" stroke-width="1.8" stroke-linecap="round"/>' +           // drop bars
            '<line class="tour-leg tour-leg--back" stroke="#1a1b1e" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>' +
            `<path d="M-8,-29 Q0,-41 9,-37" fill="none" stroke="${r.jersey}" stroke-width="7.5" stroke-linecap="round"/>` +   // back, bent over the bars
            '<path d="M-9,-31 l4,5" stroke="#1a1b1e" stroke-width="6" stroke-linecap="round"/>' +                             // shorts
            `<line x1="7" y1="-36" x2="14" y2="-28" stroke="${r.jersey === 'url(#tour-dots)' ? '#ffffff' : r.jersey}" stroke-width="3" stroke-linecap="round"/>` +   // arm
            '<circle cx="12" cy="-41" r="3.6" fill="#f2c9a0"/>' +
            `<path d="M8,-42 q4,-7 10,-1 z" fill="${r.helmet}" stroke="#1a1b1e" stroke-width=".6"/>` +
            (r.who === 'david' ? david() : r.who === 'christian' ? christian() : '') +
            '<line class="tour-leg tour-leg--front" stroke="#1a1b1e" stroke-width="3.2" stroke-linecap="round" stroke-linejoin="round"/>' +
            '</g>'
    }

    // David's face over the rider's head: black curls sticking out of the helmet,
    // a short beard along the jaw, glasses, and his name above him
    function david() {
        return '<circle cx="8.4" cy="-40.6" r="1.5" fill="#17120f"/><circle cx="8.1" cy="-38.6" r="1.4" fill="#17120f"/>' +
            '<circle cx="9.4" cy="-37.4" r="1.3" fill="#17120f"/><circle cx="9.6" cy="-42.6" r="1.2" fill="#17120f"/>' +
            '<path d="M9.6,-40.2 Q10.6,-35.4 15.3,-37.4 L15.6,-39.2 Q12.6,-37.9 10.8,-40.6 Z" fill="#17120f"/>' +       // beard
            '<circle cx="14.3" cy="-41.6" r="1.35" fill="rgba(255,255,255,.35)" stroke="#111" stroke-width=".55"/>' +   // glasses
            '<line x1="10.6" y1="-42" x2="13" y2="-41.8" stroke="#111" stroke-width=".55"/>'
    }

    // Christian's face: short brown hair and square glasses
    function christian() {
        return '<path d="M8.4,-41.5 q-.6,2.6 1,3.6 l.6,-3 z" fill="#5a3d2b"/>' +
            '<rect x="12.6" y="-42.8" width="3.2" height="2.3" rx=".5" fill="rgba(255,255,255,.35)" stroke="#111" stroke-width=".6"/>' +
            '<line x1="10.4" y1="-41.9" x2="12.6" y2="-41.7" stroke="#111" stroke-width=".6"/>'
    }

    // A name or a few words above a rider, in the band's coordinates
    const label = cls => `<text class="${cls}" text-anchor="middle" font-family="system-ui, Arial, sans-serif" font-size="11" font-weight="700" ` +
        'fill="#1f2430" stroke="#ffffff" stroke-width="3" paint-order="stroke" opacity="0"></text>'

    function band() {
        let svg = `<svg viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMax slice" xmlns="http://www.w3.org/2000/svg">`
        svg += '<defs>' +
            '<pattern id="tour-dots" width="5" height="5" patternUnits="userSpaceOnUse"><rect width="5" height="5" fill="#ffffff"/><circle cx="2.5" cy="2.5" r="1.3" fill="#d4262c"/></pattern>' +
            `<clipPath id="tour-snowline"><rect x="0" y="0" width="${W}" height="95"/></clipPath>` +
            '</defs>'
        svg += scenery()
        svg += '<g class="tour-peloton">' + RIDERS.map(rider).join('') + '</g>'
        svg += rider(DAVID, 'd') + rider(CHRISTIAN, 'c')
        svg += label('tour-name tour-name--david') + label('tour-name tour-name--christian') + label('tour-say tour-say--david')
        svg += '</svg>'
        const el = document.createElement('div')
        el.className = 'tour-road'
        el.setAttribute('aria-hidden', 'true')
        el.innerHTML = svg
        return el
    }

    // ── The race ──────────────────────────────────────────────────────
    // One loop of CYCLE seconds. The peloton crosses the band (left to right) in
    // PASS seconds; each rider keeps a place in the group and jostles around it, and
    // every other loop the yellow jersey attacks. Far behind, David rides in very
    // slowly and crashes in the middle of the road; Christian then comes by, rides
    // right over him (a bump) and carries on as if nothing happened. David then gets
    // up and finishes the race, still slowly.

    const CYCLE = 55, PASS = 16, SPREAD = 380, SCALE = 1.35
    const DAVID_SCALE = 1.05, DAVID_SPEED = 45, DAVID_START = 1, CRASH_X = W * 0.42
    const CHRISTIAN_SCALE = SCALE, CHRISTIAN_SPEED = 115, CHRISTIAN_START = 21   // the size of the peloton
    const FALL = 0.5, GET_UP_AT = 30, GET_UP = 0.9
    const ease = u => u * u * (3 - 2 * u)

    // the leg from the hip to the pedal, the knee bent forward (two segments of 13)
    function legPath(angle) {
        const hip = [-7, -28], crank = [-3, -10]
        const pedal = [crank[0] + 6 * Math.cos(angle), crank[1] + 6 * Math.sin(angle)]
        const dx = pedal[0] - hip[0], dy = pedal[1] - hip[1], dist = Math.min(25.5, Math.hypot(dx, dy))
        const along = dist / 2, up = Math.sqrt(Math.max(0, 13 * 13 - along * along))
        const mx = hip[0] + dx / 2, my = hip[1] + dy / 2, n = Math.hypot(dx, dy) || 1
        const knee = [mx + (-dy / n) * -up, my + (dx / n) * -up]
        return [hip, knee, pedal]
    }

    function setLeg(el, angle) {
        const [hip, knee, pedal] = legPath(angle)
        // a <line> can't bend: draw the thigh, the shin goes in a sibling polyline
        el.setAttribute('x1', hip[0].toFixed(1)); el.setAttribute('y1', hip[1].toFixed(1))
        el.setAttribute('x2', knee[0].toFixed(1)); el.setAttribute('y2', knee[1].toFixed(1))
        el._shin.setAttribute('points', `${knee[0].toFixed(1)},${knee[1].toFixed(1)} ${pedal[0].toFixed(1)},${pedal[1].toFixed(1)}`)
    }

    // place a rider: position, size, tilt (around the front wheel), squash (1 = upright,
    // smaller = lying flat on the road, seen from the side), pedals
    function placeRider(el, x, y, scale, pedal, tilt = 0, squash = 1) {
        el.setAttribute('transform', `translate(${x.toFixed(1)},${y.toFixed(1)}) scale(${scale},${(scale * squash).toFixed(3)}) rotate(${tilt.toFixed(1)} 16 0)`)
        setLeg(el.querySelector('.tour-leg--front'), pedal)
        setLeg(el.querySelector('.tour-leg--back'), pedal + Math.PI)
        el.querySelectorAll('.tour-spokes').forEach(s => s.setAttribute('transform', `rotate(${((pedal * 57) % 360).toFixed(1)})`))
    }

    function setText(el, text, x, y) {
        el.setAttribute('opacity', text ? '1' : '0')
        if (!text) return
        if (el.textContent !== text) el.textContent = text
        el.setAttribute('x', x.toFixed(1))
        el.setAttribute('y', y.toFixed(1))
    }

    function startRace(road) {
        const svg = road.querySelector('svg'), q = sel => svg.querySelector(sel)
        const all = Array.from(svg.querySelectorAll('.tour-rider'))
        // each leg gets its shin
        all.forEach(r => r.querySelectorAll('.tour-leg').forEach(leg => {
            const shin = document.createElementNS('http://www.w3.org/2000/svg', 'polyline')
            shin.setAttribute('fill', 'none')
            shin.setAttribute('stroke', leg.getAttribute('stroke'))
            shin.setAttribute('stroke-width', '2.8')
            shin.setAttribute('stroke-linecap', 'round')
            leg.after(shin)
            leg._shin = shin
        }))
        const riders = all.filter(r => !r.classList.contains('tour-rider--david') && !r.classList.contains('tour-rider--christian'))
        const david = q('.tour-rider--david'), christian = q('.tour-rider--christian')
        const names = { david: q('.tour-name--david'), christian: q('.tour-name--christian') }
        const says = { david: q('.tour-say--david') }
        // places in the group: the yellow jersey in front, the others behind in rows
        const places = riders.map((r, i) => i === 0 ? 0 : -(Math.ceil(i / 2) * 46 + (i % 2) * 16))
        const lanes = riders.map((r, i) => (i % 2 ? -3 : 3))
        const crashAt = DAVID_START + (CRASH_X + 80) / DAVID_SPEED

        const draw = (time, still) => {
            const n = Math.floor(time / CYCLE), t = time % CYCLE, u = t / PASS
            const attack = n % 2 === 1

            // the peloton
            riders.forEach((el, i) => {
                const jostle = still ? 0 : Math.sin(time * 0.8 + i * 1.7) * 9
                let x = -80 + (W + SPREAD + 80) * u + places[i] + jostle
                if (i === 0 && attack) x += 160 * Math.max(0, Math.min(1, (u - 0.35) / 0.3))   // the attack
                el.style.display = u > 1 && !still ? 'none' : ''
                placeRider(el, x, ROAD_Y + lanes[i], SCALE, still ? 0.6 + i : time * (i === 0 && attack && u > 0.35 ? 13 : 9) + i)
            })

            // David: in very slowly, then the crash, then he lies on the road
            const dy = ROAD_Y + 2
            let dx, tilt = 0, squash = 1, dpedal = time * 4
            if (still) { dx = W * 0.3 }
            else if (t < crashAt) { dx = -80 + (t - DAVID_START) * DAVID_SPEED }
            else if (t < GET_UP_AT) {
                // the crash: he goes up on the front wheel, then slams down flat on the road
                const c = Math.min(1, (t - crashAt) / FALL)
                dx = CRASH_X + 10 * ease(c)
                tilt = c < 0.4 ? 30 * ease(c / 0.4) : 30 * (1 - ease((c - 0.4) / 0.6))
                squash = c < 0.4 ? 1 : 1 - 0.68 * ease((c - 0.4) / 0.6)
                dpedal = crashAt * 4
            } else if (t < GET_UP_AT + GET_UP) {
                // back on his feet, back in the saddle
                dx = CRASH_X + 10
                squash = 0.32 + 0.68 * ease((t - GET_UP_AT) / GET_UP)
                dpedal = crashAt * 4
            } else {
                dx = CRASH_X + 10 + (t - GET_UP_AT - GET_UP) * DAVID_SPEED      // and on to the finish
            }
            david.style.display = (!still && t < DAVID_START) || dx > W + 80 ? 'none' : ''
            placeRider(david, dx, dy, DAVID_SCALE, dpedal, tilt, squash)
            setText(names.david, david.style.display ? '' : 'David', dx + 8, dy - 62 * squash)
            setText(says.david, !still && t > crashAt + FALL && t < crashAt + 4 ? 'Ouch...' : '', dx + 34, dy - 46)

            // Christian: rides straight over David and carries on
            const cx = -120 + (t - CHRISTIAN_START) * CHRISTIAN_SPEED
            const over = Math.abs(cx - CRASH_X - 6)
            const bump = over < 46 ? 13 * (1 - (over / 46) ** 2) : 0
            christian.style.display = still || t < CHRISTIAN_START || cx > W + 140 ? 'none' : ''
            placeRider(christian, cx, ROAD_Y - bump, CHRISTIAN_SCALE, time * 8, over < 46 ? -6 * Math.sign(cx - CRASH_X - 6) : 0)
            setText(names.christian, christian.style.display ? '' : 'Christian', cx + 14, ROAD_Y - bump - 70)
        }
        if (reducedMotion) { draw(PASS * 0.55, true); return }
        let start = null
        const loop = now => {
            frame = requestAnimationFrame(loop)
            if (start === null) start = now
            draw((now - start) / 1000, false)
        }
        frame = requestAnimationFrame(loop)
    }

    // ── Mount / unmount ───────────────────────────────────────────────

    function mount() {
        const road = band()
        const footer = document.querySelector('footer.site-footer')
        if (footer) footer.parentNode.insertBefore(road, footer)
        else document.body.appendChild(road)
        startRace(road)
        mounted = true
    }

    function unmount() {
        cancelAnimationFrame(frame)
        document.querySelectorAll('.tour-road').forEach(el => el.remove())
        mounted = false
    }

    function sync() {
        if (wanted() === mounted) return
        if (mounted) unmount()
        else mount()
    }

    new MutationObserver(sync).observe(html, { attributes: true, attributeFilter: ['data-theme-pref'] })
    if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', sync)
    else sync()
})()
