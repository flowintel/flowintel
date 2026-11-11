/**
 * diff-view.js — Line diff between two texts, after Rulezet's DiffDisplay component
 * (rulezet-core static/js/codeMirror/diffDisplay.js). Same computation (jsdiff, copied
 * in static/js/vendor/jsdiff.js); the rendering is done here, as Flowintel's content
 * security policy only allows its own scripts (Rulezet draws it with diff2html from a CDN).
 *
 * Props:
 *   oldText, newText  String   the two versions
 *   oldName, newName  String   their labels (header)
 *   mode              String   'unified' | 'split' (default 'unified'), switchable in the header
 *   maxHeight         String   CSS height of the scroll area
 *
 * Usage:
 *   import DiffView from '/static/js/components/diff-view.js'
 *   <diff-view :old-text="a" :new-text="b" old-name="In this case" new-name="On Rulezet"></diff-view>
 */
import '/static/js/vendor/jsdiff.js'

const { ref, computed } = Vue

export default {
    name: 'DiffView',
    delimiters: ['[[', ']]'],
    props: {
        oldText: { type: String, default: '' },
        newText: { type: String, default: '' },
        oldName: { type: String, default: 'Original' },
        newName: { type: String, default: 'Modified' },
        mode: { type: String, default: 'unified' },
        maxHeight: { type: String, default: '420px' },
    },
    setup(props) {
        const view = ref(props.mode)
        const show_colors = ref(true)

        const identical = computed(() => (props.oldText || '').trim() === (props.newText || '').trim())

        // One row per line: {type: 'same' | 'del' | 'add', old: n, new: n, text}
        const rows = computed(() => {
            if (typeof Diff === 'undefined') return []
            const parts = Diff.diffLines(props.oldText || '', props.newText || '')
            const out = []
            let o = 1, n = 1
            for (const part of parts) {
                const lines = part.value.replace(/\n$/, '').split('\n')
                for (const text of lines) {
                    if (part.added) out.push({ type: 'add', old: null, new: n++, text })
                    else if (part.removed) out.push({ type: 'del', old: o++, new: null, text })
                    else out.push({ type: 'same', old: o++, new: n++, text })
                }
            }
            return out
        })

        // Inside a changed line, the words that actually changed (like diff2html): each
        // removed line is paired with the added line at the same place of the change
        const word_parts = computed(() => {
            const parts = new Map()
            if (typeof Diff === 'undefined') return parts
            const list = rows.value
            for (let i = 0; i < list.length;) {
                if (list[i].type === 'same') { i++; continue }
                const dels = [], adds = []
                while (i < list.length && list[i].type === 'del') dels.push(list[i++])
                while (i < list.length && list[i].type === 'add') adds.push(list[i++])
                for (let k = 0; k < Math.min(dels.length, adds.length); k++) {
                    const changes = Diff.diffWordsWithSpace(dels[k].text, adds[k].text)
                    parts.set(dels[k], changes.filter(c => !c.added).map(c => ({ text: c.value, hl: !!c.removed })))
                    parts.set(adds[k], changes.filter(c => !c.removed).map(c => ({ text: c.value, hl: !!c.added })))
                }
            }
            return parts
        })

        function segments(row) {
            return (row && word_parts.value.get(row)) || [{ text: row ? (row.text || ' ') : '', hl: false }]
        }

        const stats = computed(() => ({
            add: rows.value.filter(r => r.type === 'add').length,
            del: rows.value.filter(r => r.type === 'del').length,
        }))

        // Side by side: removed and added lines of a change are paired on the same row
        const split_rows = computed(() => {
            const out = []
            const list = rows.value
            for (let i = 0; i < list.length;) {
                if (list[i].type === 'same') { out.push({ left: list[i], right: list[i] }); i++; continue }
                const dels = [], adds = []
                while (i < list.length && list[i].type === 'del') dels.push(list[i++])
                while (i < list.length && list[i].type === 'add') adds.push(list[i++])
                for (let k = 0; k < Math.max(dels.length, adds.length); k++) out.push({ left: dels[k] || null, right: adds[k] || null })
            }
            return out
        })

        return { view, show_colors, identical, rows, stats, split_rows, segments }
    },
    template: `
    <div class="dv" :class="{ 'dv--plain': !show_colors }">
        <div class="dv-head">
            <span class="dv-name dv-name--old"><i class="fa-solid fa-file-lines me-1"></i>[[ oldName ]]</span>
            <span v-if="identical" class="dv-same"><i class="fa-solid fa-equals me-1"></i>Identical content</span>
            <span v-else class="dv-stats"><span class="dv-stat-add">+[[ stats.add ]]</span><span class="dv-stat-del">−[[ stats.del ]]</span></span>
            <span class="dv-tools">
                <button type="button" class="dv-tool" :class="{ active: view === 'unified' }" @click="view = 'unified'" title="One column">Unified</button>
                <button type="button" class="dv-tool" :class="{ active: view === 'split' }" @click="view = 'split'" title="Side by side">Split</button>
                <button type="button" class="dv-tool" @click="show_colors = !show_colors" :title="show_colors ? 'Hide colours' : 'Show colours'">
                    <i :class="show_colors ? 'fa-solid fa-eye-slash' : 'fa-solid fa-eye'"></i>
                </button>
            </span>
            <span class="dv-name dv-name--new">[[ newName ]]<i class="fa-solid fa-file-pen ms-1"></i></span>
        </div>
        <div class="dv-body" :style="{ maxHeight }">
            <table v-if="view === 'unified'" class="dv-table">
                <tr v-for="(r, i) in rows" :key="i" :class="'dv-' + r.type">
                    <td class="dv-ln">[[ r.old ?? '' ]]</td>
                    <td class="dv-ln">[[ r.new ?? '' ]]</td>
                    <td class="dv-sign">[[ r.type === 'add' ? '+' : r.type === 'del' ? '−' : '' ]]</td>
                    <td class="dv-code"><span v-for="(p, k) in segments(r)" :key="k" :class="{ 'dv-word': p.hl }">[[ p.text ]]</span></td>
                </tr>
            </table>
            <table v-else class="dv-table dv-table--split">
                <tr v-for="(r, i) in split_rows" :key="i">
                    <td class="dv-ln">[[ r.left ? r.left.old : '' ]]</td>
                    <td class="dv-code" :class="r.left ? 'dv-' + r.left.type : 'dv-empty'"><template v-if="r.left"><span v-for="(p, k) in segments(r.left)" :key="k" :class="{ 'dv-word': p.hl }">[[ p.text ]]</span></template></td>
                    <td class="dv-ln">[[ r.right ? r.right.new : '' ]]</td>
                    <td class="dv-code" :class="r.right ? 'dv-' + r.right.type : 'dv-empty'"><template v-if="r.right"><span v-for="(p, k) in segments(r.right)" :key="k" :class="{ 'dv-word': p.hl }">[[ p.text ]]</span></template></td>
                </tr>
            </table>
        </div>
    </div>
    `
}
