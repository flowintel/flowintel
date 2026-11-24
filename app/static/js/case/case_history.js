import {display_toast} from '/static/js/toaster.js'
const { ref, nextTick, onMounted, onUnmounted } = Vue
import { url_set, url_get } from './url_state.js'
import history_log from './history_log.js'

import { Flowtime } from '../vendor/vitrine/flowtime.js'
import { fromMispObjects } from './misp_timeline.js'
import { savedFlowtimeTextScale, rememberFlowtimeTextScale } from './flowtime_preferences.js'

export default {
    delimiters: ['[[', ']]'],
    components: { history_log },
	props: {
		case_id: Number,
		can_view_history: Boolean
	},
	setup(props) {
        const history = ref()
        const audit_history = ref()
        const main_tab = ref("history-case")
        // Line to scroll to and outline, set by the Calendar panel before opening this tab
        const focus_entry = ref(null)
        const case_misp_objects = ref()
        const misp_timeline_embed = ref(null)
        const misp_timeline_rejected_count = ref(0)
        const misp_timeline_error = ref('')
        const misp_request = new AbortController()
        let misp_timeline = null
        let misp_timeline_view = 'timeline'
        let unmounted = false


        // Both logs are lines "[YYYY-MM-DD HH:MM](user): text", read into entries for history_log.js
        function parse_log(lines) {
            const out = []
            for (const line of lines || []) {
                const m = line.match(/^\[(.*?)\]\((.*?)\):?\s*(.*)$/)
                if (m) out.push({ date: m[1], user: m[2], text: m[3] })
            }
            return out
        }

        async function fetch_history(){
            const res = await fetch("/case/history/" + props.case_id)
            if (res.status == 404) {
                display_toast(res)
                return
            }
            const loc = await res.json()
            history.value = parse_log(loc["history"])
        }

        async function fetch_audit_logs(){
            const res = await fetch("/case/audit_logs/" + props.case_id)
            if (res.status == 404) {
                display_toast(res)
                return
            }
            const loc = await res.json()
            audit_history.value = parse_log(loc["audit_logs"])
        }

        if (props.can_view_history) {
            fetch_history()
            fetch_audit_logs()
        }

        async function fetch_case_misp_object(){
            try {
                const res = await fetch('/case/' + props.case_id + '/get_case_misp_object', { signal: misp_request.signal })
                if (unmounted) return
                if (!res.ok) {
                    misp_timeline_error.value = 'Unable to load the MISP timeline.'
                    display_toast(res)
                    return
                }
                const data = await res.json()
                if (unmounted) return
                case_misp_objects.value = data['misp-object']
                await nextTick()
                if (!unmounted && main_tab.value === 'history-misp') prepare_misp_timeline()
            } catch (error) {
                if (unmounted || misp_request.signal.aborted) return
                misp_timeline_error.value = 'Unable to load the MISP timeline.'
                console.error('MISP Flowtime load error:', error)
            }
        }

        if (props.can_view_history) {
            fetch_case_misp_object()
        }

        function destroy_misp_timeline() {
            if (!misp_timeline) return
            misp_timeline_view = misp_timeline.view
            misp_timeline.destroy()
            misp_timeline = null
        }

        function prepare_misp_timeline(){
            if (unmounted || !misp_timeline_embed.value || !case_misp_objects.value) return
            const { events, rejected } = fromMispObjects(case_misp_objects.value)
            misp_timeline_rejected_count.value = rejected.length
            if (misp_timeline) {
                misp_timeline.setEvents(events)
            } else {
                misp_timeline_embed.value.addEventListener('flowtime:textscalechange', rememberFlowtimeTextScale, { signal: misp_request.signal })
                misp_timeline = new Flowtime(misp_timeline_embed.value, {
                    events,
                    view: misp_timeline_view,
                    textScale: savedFlowtimeTextScale(),
                    label: 'MISP object history timeline',
                    groups: [{ id: 'objects', label: 'MISP objects', color: '#249790', icon: '◇' }],
                    timeZone: 'UTC'
                })
            }
        }

        async function active_tab(tab_name){
            if (tab_name !== 'history-misp') destroy_misp_timeline()
            url_set('history', tab_name, 'history-case')
            if(tab_name == 'history-case'){
                main_tab.value = 'history-case'
                if ( !document.getElementById("tab-history-case").classList.contains("active") ){
                    document.getElementById("tab-history-case").classList.add("active")
                    document.getElementById("tab-history-misp").classList.remove("active")
                    document.getElementById("tab-history-audit").classList.remove("active")
                }
            }else if(tab_name == 'history-misp'){
                main_tab.value = 'history-misp'
                if ( !document.getElementById("tab-history-misp").classList.contains("active") ){
                    document.getElementById("tab-history-misp").classList.add("active")
                    document.getElementById("tab-history-case").classList.remove("active")
                    document.getElementById("tab-history-audit").classList.remove("active")
                    await nextTick()
                    prepare_misp_timeline()
                }
            }else if(tab_name == 'history-audit'){
                main_tab.value = 'history-audit'
                if ( !document.getElementById("tab-history-audit").classList.contains("active") ){
                    document.getElementById("tab-history-audit").classList.add("active")
                    document.getElementById("tab-history-case").classList.remove("active")
                    document.getElementById("tab-history-misp").classList.remove("active")
                }
            }
        }

        onMounted(async () => {
            const pending = window.flowintel_history_focus
            if (pending) {
                window.flowintel_history_focus = null
                focus_entry.value = pending.entry
                if (pending.sub && pending.sub !== 'history-case' && props.can_view_history) {
                    await nextTick()
                    active_tab(pending.sub)
                }
                return
            }
            const saved = url_get('history')
            if (saved && saved !== 'history-case' && props.can_view_history) {
                await nextTick()
                active_tab(saved)
            }
        })

        onUnmounted(() => {
            unmounted = true
            misp_request.abort()
            destroy_misp_timeline()
        })

		return {
            focus_entry,
            history,
            audit_history,
            main_tab,
            case_misp_objects,
            misp_timeline_embed,
            misp_timeline_rejected_count,
            misp_timeline_error,
            can_view_history: props.can_view_history,

            active_tab
		}
    },
	template: `
    <ul class="nav nav-tabs" style="margin-bottom: 10px;">
        <li class="nav-item">
            <button 
                class="nav-link active" 
                id="tab-history-case" 
                aria-current="page" 
                @click="can_view_history ? active_tab('history-case') : null"
                :disabled="!can_view_history"
                :title="can_view_history ? 'View case history' : 'Requires Admin, Case Admin, or Audit Viewer permission'"
                :style="!can_view_history ? 'cursor: not-allowed; opacity: 0.6;' : ''">
                <i v-if="!can_view_history" class="fa-solid fa-lock me-1"></i>Case
            </button>
        </li>
        <li class="nav-item">
            <button 
                class="nav-link" 
                id="tab-history-misp" 
                @click="can_view_history ? active_tab('history-misp') : null"
                :disabled="!can_view_history"
                :title="can_view_history ? 'View MISP timeline' : 'Requires Admin, Case Admin, or Audit Viewer permission'"
                :style="!can_view_history ? 'cursor: not-allowed; opacity: 0.6;' : ''">
                <i v-if="!can_view_history" class="fa-solid fa-lock me-1"></i>MISP
            </button>
        </li>
        <li class="nav-item">
            <button 
                class="nav-link" 
                id="tab-history-audit" 
                @click="can_view_history ? active_tab('history-audit') : null"
                :disabled="!can_view_history"
                :title="can_view_history ? 'View audit logs' : 'Requires Admin, Case Admin, or Audit Viewer permission'"
                :style="!can_view_history ? 'cursor: not-allowed; opacity: 0.6;' : ''">
                <i v-if="!can_view_history" class="fa-solid fa-lock me-1"></i>Audit
            </button>
        </li>
    </ul>

    <template v-if="main_tab == 'history-case'">
        <template v-if="!can_view_history">
            <div class="alert alert-warning" role="alert">
                <i class="fa-solid fa-lock me-2"></i>
                <strong>Access Restricted:</strong> You need Admin, Case Admin, or Audit Viewer permission to view case history.
            </div>
        </template>
        <template v-else-if="history">
            <history_log :entries="history" :focus="main_tab == 'history-case' ? focus_entry : null" empty_text="No history"
                :exports="[{label: 'Text', href: '/case/' + case_id + '/download_history'}, {label: 'Markdown', href: '/case/' + case_id + '/download_history_md'}]">
            </history_log>
        </template>
        <template v-else>
            <i>Loading…</i>
        </template>
    </template>
    <template v-else-if="main_tab == 'history-misp'">
        <template v-if="!can_view_history">
            <div class="alert alert-warning" role="alert">
                <i class="fa-solid fa-lock me-2"></i>
                <strong>Access Restricted:</strong> You need Admin, Case Admin, or Audit Viewer permission to view MISP timeline.
            </div>
        </template>
        <p v-else-if="misp_timeline_error" class="alert alert-danger" role="alert">[[ misp_timeline_error ]]</p>
        <template v-else-if="case_misp_objects && case_misp_objects.length > 0">
            <p v-if="misp_timeline_rejected_count" class="alert alert-warning" role="status">
                [[ misp_timeline_rejected_count ]] MISP object(s) have no valid date and cannot be placed in the viewer.
            </p>
            <div ref="misp_timeline_embed" class="case-flowtime"></div>
        </template>
        <template v-else-if="!case_misp_objects">
            <i>Loading…</i>
        </template>
        <template v-else>
            <i>No MISP objects</i>
        </template>
    </template>
    <template v-else-if="main_tab == 'history-audit'">
        <template v-if="!can_view_history">
            <div class="alert alert-warning" role="alert">
                <i class="fa-solid fa-lock me-2"></i>
                <strong>Access Restricted:</strong> You need Admin, Case Admin, or Audit Viewer permission to view audit logs.
            </div>
        </template>
        <template v-else-if="audit_history">
            <p class="text-muted mb-2 small"><i class="fa-solid fa-info-circle"></i> Audit entries are extracted from the audit log file</p>
            <history_log :entries="audit_history" :focus="main_tab == 'history-audit' ? focus_entry : null" empty_text="No audit logs"
                :exports="[{label: 'Text', href: '/case/' + case_id + '/download_audit_logs'}, {label: 'Markdown', href: '/case/' + case_id + '/download_audit_logs_md'}]">
            </history_log>
        </template>
        <template v-else>
            <i>Loading…</i>
        </template>
    </template>
    `
}
