/**
 * flow_loader.js — Flowintel's own loading animation, built on the official logo mark
 * (flow_logo_markup.js, from github.com/flowintel/flowintel-logos).
 * One cycle (2.2 s): the data dashes stream in on the left, the strands ripple, two bands of light
 * sweep along the braid from left to right, then the nodes on the right pop and glow one after the other.
 *
 *   <flow_loader></flow_loader>                 default 110px wide
 *   <flow_loader :size="160"></flow_loader>     any width in px (height follows the logo ratio)
 *
 * Every id inside the SVG is made unique per instance, so several loaders can live on the
 * same page. Styles: /static/css/components/flow_loader.css (prefers-reduced-motion honoured).
 */
import LOGO, { VIEWBOX } from './flow_logo_markup.js'

let counter = 0
const [, , VB_W, VB_H] = VIEWBOX.split(' ').map(Number)

// The strands again, filled white: the light band (a moving mask) only shows them through.
const STRANDS = [...LOGO.matchAll(/<path class="fl-(?:dark|light)"[^>]*\/>/g)]
    .map(m => m[0].replace(/class="fl-(dark|light)"/, 'class="fl-shine"').replace(/fill="[^"]*"/, 'fill="#fff"'))
    .join('')

export default {
    name: 'flow_loader',
    props: {
        size:  { type: Number, default: 110 },
        label: { type: String, default: 'Loading' },   // for screen readers
    },
    data() {
        return { uid: 'fl' + (++counter) + '-' }
    },
    computed: {
        height() { return Math.round(this.size * VB_H / VB_W) },
        inner() {
            const u = this.uid
            return LOGO.replaceAll('__U__', u) + `
              <defs>
                <linearGradient id="${u}band" x1="0" x2="1" y1="0" y2="0">
                  <stop offset="0" stop-color="#fff" stop-opacity="0"/>
                  <stop offset=".5" stop-color="#fff" stop-opacity="1"/>
                  <stop offset="1" stop-color="#fff" stop-opacity="0"/>
                </linearGradient>
                <mask id="${u}sweep" maskUnits="userSpaceOnUse" x="-100" y="0" width="500" height="260">
                  <rect class="fl-band" x="-90" y="0" width="90" height="260" fill="url(#${u}band)"/>
                  <rect class="fl-band fl-band--2" x="-60" y="0" width="60" height="260" fill="url(#${u}band)"/>
                </mask>
              </defs>
              <g class="fl-shine-group" mask="url(#${u}sweep)" transform="translate(-8,-39.565239)">${STRANDS}</g>`
        },
    },
    template: /* html */ `
    <svg class="fl-loader" :viewBox="'${VIEWBOX}'" :width="size" :height="height" role="img" :aria-label="label" v-html="inner"></svg>
    `,
}
