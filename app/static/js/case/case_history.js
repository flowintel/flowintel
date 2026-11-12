import {display_toast} from '/static/js/toaster.js'
const { ref, nextTick, onMounted } = Vue
import { url_set, url_get } from './url_state.js'
import history_log from './history_log.js'

function textToHtml(value) {
    const span = document.createElement('span')
    span.textContent = String(value ?? '')
    return span.innerHTML
}

function buildMispTimelineText(obj) {
    const container = document.createElement('div')

    const uuid = document.createElement('div')
    uuid.style.marginBottom = '20px'
    uuid.textContent = 'Object uuid: ' + String(obj.object_uuid ?? '')
    container.appendChild(uuid)

    const heading = document.createElement('div')
    const title = document.createElement('h6')
    title.textContent = 'Attributes'
    heading.appendChild(title)
    container.appendChild(heading)

    const table = document.createElement('table')
    table.className = 'table ms-2'

    const headerRow = document.createElement('tr')
    for (const label of ['value', 'type', 'comment', 'first seen', 'last seen', 'IDS']) {
        const th = document.createElement('th')
        th.textContent = label
        headerRow.appendChild(th)
    }
    table.appendChild(headerRow)

    for (const attr of obj.attributes) {
        const row = document.createElement('tr')
        for (const field of ['value', 'type', 'comment', 'first_seen', 'last_seen', 'ids_flag']) {
            const cell = document.createElement('td')
            cell.className = 'p-1'
            cell.textContent = String(attr[field] ?? '')
            row.appendChild(cell)
        }
        table.appendChild(row)
    }

    container.appendChild(table)
    return container.innerHTML
}

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
            const res = await fetch("/case/"+props.case_id+"/get_case_misp_object")
            if(await res.status==404 ){
                display_toast(res)
            }else{
                let loc = await res.json()
                case_misp_objects.value = loc["misp-object"]
            }
        }
        
        if (props.can_view_history) {
            fetch_case_misp_object()
        }

        function prepare_misp_timeline(){
            // Check if there are MISP objects
            if (!case_misp_objects.value || case_misp_objects.value.length === 0) {
                return; // Don't create timeline if no objects exist
            }

            function toStartDateObject(date) {
                return {
                  year: String(date.getFullYear()),
                  month: String(date.getMonth() + 1).padStart(2, "0"),
                  day: String(date.getDate()).padStart(2, "0"),
                  hour: String(date.getHours()).padStart(2, "0"),
                  minute: String(date.getMinutes()).padStart(2, "0")
                };
            }

            let loc_list=[]

            for (const obj of case_misp_objects.value) {
                let firstSeenDates = [];
              
                for (const attr of obj.attributes) {
                    if (attr.first_seen) {
                        const date = new Date(attr.first_seen);
                        if (!isNaN(date)) {
                            firstSeenDates.push(date);
                        }
                    }
                }
              
                let resultDate;
                if (firstSeenDates.length > 0) {
                    resultDate = new Date(Math.min(...firstSeenDates));
                } else if (obj.object_creation_date) {
                    resultDate = new Date(obj.object_creation_date);
                } else {
                    resultDate = null;
                }
                let startDate

                if(resultDate){
                    startDate = toStartDateObject(resultDate)
                }else{
                    startDate = toStartDateObject(new Date(obj.creation_date))
                }

                loc_list.push({
                    // Linkification would rewrite HTML built from text nodes.
                    "autolink": false,
                    "start_date": startDate,
                    "text": {"headline": textToHtml(obj.object_name), "text": buildMispTimelineText(obj)}
                })
            }


            // Only create timeline if there are events
            if (loc_list.length > 0) {
                const timelineJson = {
                    "events":loc_list
                };
                new TL.Timeline('timeline-embed', timelineJson);
            }
        }

        async function active_tab(tab_name){
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

		return {
            focus_entry,
            history,
            audit_history,
            main_tab,
            case_misp_objects,
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
        <template v-else-if="case_misp_objects && case_misp_objects.length > 0">
            <div id="timeline-embed" style="width: 100%; height: 60vh;"></div>
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
