/**
 * loading_overlay.js — loading state for a list or a panel: the content stays in the
 * background (dimmed, not clickable) under a badge with the animated Flowintel logo
 * (flow_loader.js).
 * On a first load (nothing to show yet) the `skeleton` slot is shown instead of the content.
 *
 *   <loading_overlay :loading="loading" :empty="!items.length"
 *                    label="Loading cases…">
 *       <template #skeleton> ...placeholder rows, built with .lo-sk bars... </template>
 *       ...the real content...
 *   </loading_overlay>
 *
 * Skeleton bars: <span class="lo-sk"></span>, modifiers .lo-sk-sm (thin) and .lo-sk-pill (badge),
 * width set inline. Styles: /static/css/components/loading_overlay.css
 */
import flow_loader from './flow_loader.js'

export default {
    name: 'loading_overlay',
    components: { flow_loader },
    delimiters: ['[[', ']]'],
    props: {
        loading: { type: Boolean, default: false },
        empty:   { type: Boolean, default: false },   // nothing loaded yet → show the skeleton slot
        label:   { type: String, default: 'Loading…' },
        size:    { type: Number, default: 180 },      // logo size; small values give a compact badge (side panels)
        delay:   { type: Number, default: 100 },      // ms before the logo badge shows (the skeleton shows at once): a fast load never flashes the logo
    },
    data() { return { shown: false, timer: null } },
    watch: {
        loading: {
            immediate: true,
            handler(v) {
                clearTimeout(this.timer)
                if (!v) { this.shown = false; return }
                if (this.delay <= 0) { this.shown = true; return }
                this.timer = setTimeout(() => { this.shown = true }, this.delay)
            },
        },
    },
    unmounted() { clearTimeout(this.timer) },
    template: /* html */ `
    <div class="lo-wrap" :class="{ 'is-loading': shown, 'is-compact': size < 120 }" :aria-busy="loading">
      <div v-if="shown" class="lo-badge" role="status" :title="label">
        <flow_loader :size="size" :label="label"></flow_loader>
        <span class="lo-label">[[ label ]]</span>
      </div>
      <div v-if="loading && empty && $slots.skeleton" class="lo-skeleton" aria-hidden="true">
        <slot name="skeleton"></slot>
      </div>
      <div v-else class="lo-content">
        <slot></slot>
      </div>
    </div>
    `,
}
