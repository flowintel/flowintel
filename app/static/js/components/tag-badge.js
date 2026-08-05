/**
 * tag-badge.js — Consistent display for tags, custom tags, galaxies, and clusters
 *
 * The app has 4 kinds of "tag-like" things (custom tags, MISP taxonomy tags, galaxies,
 * clusters), each with slightly different data shapes but rendered with the same two
 * visual styles: a colored pill (custom tags, MISP tags) or the fixed-blue "cluster"
 * pill (galaxies, clusters). This component covers both from one place instead of the
 * markup being copy-pasted across a dozen files.
 *
 * Props:
 *   label        String   (required) — display text
 *   color        String   — background color (hex). Omit for galaxies/clusters, which
 *                           always render the fixed-blue "cluster" style instead of a
 *                           colored pill.
 *   iconClass    String   — a ready FontAwesome class string, e.g. "fa-solid fa-bug"
 *                           (custom tags / MISP tags store a full class already)
 *   iconName     String   — a bare icon name looked up via utils.js's mapIcon(), e.g.
 *                           "bug" (galaxies/clusters store just a name)
 *   fallbackIcon String   — shown when neither iconClass nor iconName is set, only for
 *                           the colored-pill style (default: a generic tag icon)
 *   title        String   — tooltip, e.g. a description, or "Description:\n...\n\nMetadata:\n..."
 *
 * Usage:
 *   <tag_badge :label="custom_tag.name" :color="custom_tag.color" :icon-class="custom_tag.icon"></tag_badge>
 *   <tag_badge :label="tag.name" :color="tag.color" :icon-class="tag.icon" :title="tag.description"></tag_badge>
 *   <tag_badge :label="cluster.tag" :icon-name="cluster.icon" :title="'Description:\n' + cluster.description"></tag_badge>
 *   <tag_badge :label="galaxy.name" :icon-name="galaxy.icon" :title="galaxy.description"></tag_badge>
 */

import { getTextColor, mapIcon } from '/static/js/utils.js'

const { computed } = Vue

export default {
    name: 'TagBadge',

    props: {
        label:        { type: String, required: true },
        color:        { type: String, default: '' },
        iconClass:    { type: String, default: '' },
        iconName:     { type: String, default: '' },
        fallbackIcon: { type: String, default: 'fa-solid fa-tag' },
        title:        { type: String, default: '' },
    },

    template: `
        <span v-if="color" class="tag" :title="title || null" :style="{ 'background-color': color, color: text_color }">
            <i v-if="iconClass" :class="iconClass" style="margin-right: 4px"></i>
            <i v-else-if="!iconName" :class="fallbackIcon" style="margin-right: 4px"></i>
            <span v-else v-html="mapped_icon" style="margin-right: 4px"></span>
            {{ label }}
        </span>
        <span v-else class="cluster" :title="title || null">
            <i v-if="iconClass" :class="iconClass"></i>
            <span v-else-if="iconName" v-html="mapped_icon"></span>
            {{ label }}
        </span>
    `,

    setup(props) {
        const text_color = computed(() => getTextColor(props.color || '#000000'))
        const mapped_icon = computed(() => (props.iconName ? mapIcon(props.iconName) : '') || '')
        return { text_color, mapped_icon }
    }
}
