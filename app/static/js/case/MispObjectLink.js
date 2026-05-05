import { display_toast, create_message } from '../toaster.js'
const { ref, computed, watch } = Vue

/**
 * Modal for manually linking/unlinking a local MISP object
 * to a remote MISP object UUID on a connected instance.
 */
export default {
    delimiters: ['[[', ']]'],
    props: {
        case_id: Number,
        local_object: Object,   // the object whose synced_instances we edit
        modal_id: String
    },
    emits: ['link_updated'],
    setup(props, { emit }) {
        // MISP connector instances for this case
        const case_connectors = ref([])
        const selected_instance_id = ref(null)
        const is_loading_connectors = ref(false)

        // Remote objects from selected instance
        const remote_objects = ref([])
        const remote_search = ref('')
        const remote_type_filter = ref('')
        const is_loading_remote = ref(false)

        // UI state
        const is_linking = ref(false)

        const filtered_remote = computed(() => {
            let objs = remote_objects.value
            const q = remote_search.value.trim().toLowerCase()
            const t = remote_type_filter.value
            if (q) {
                objs = objs.filter(o =>
                    o.name.toLowerCase().includes(q) ||
                    o.attributes_preview.some(a => String(a.value).toLowerCase().includes(q))
                )
            }
            if (t) objs = objs.filter(o => o.name === t)
            return objs
        })

        const remote_type_options = computed(() =>
            [...new Set(remote_objects.value.map(o => o.name))].sort()
        )

        const misp_connectors = computed(() =>
            case_connectors.value.filter(c => c.is_misp_connector)
        )

        const selected_connector = computed(() =>
            misp_connectors.value.find(c => c.case_task_instance_id === selected_instance_id.value) || null
        )

        function current_link_for_instance(instance_id) {
            if (!props.local_object) return null
            const si = (props.local_object.synced_instances || []).find(s => s.instance_id === instance_id)
            return si ? si.object_uuid : null
        }

        watch(selected_instance_id, () => {
            remote_objects.value = []
            remote_search.value = ''
            remote_type_filter.value = ''
        })

        async function on_show() {
            selected_instance_id.value = null
            remote_objects.value = []
            remote_search.value = ''
            remote_type_filter.value = ''
            await load_connectors()
            // Pre-select if only one MISP connector
            if (misp_connectors.value.length === 1) {
                selected_instance_id.value = misp_connectors.value[0].case_task_instance_id
            }
        }

        async function load_connectors() {
            is_loading_connectors.value = true
            try {
                const res = await fetch('/case/' + props.case_id + '/get_case_connectors')
                if (res.status === 200) {
                    const loc = await res.json()
                    case_connectors.value = loc.case_connectors || []
                } else {
                    display_toast(res)
                }
            } finally {
                is_loading_connectors.value = false
            }
        }

        async function load_remote_objects() {
            if (!selected_instance_id.value) return
            is_loading_remote.value = true
            remote_objects.value = []
            try {
                const res = await fetch('/case/' + props.case_id + '/connectors/' + selected_instance_id.value + '/misp_objects_preview')
                if (res.status === 200) {
                    const loc = await res.json()
                    remote_objects.value = loc.objects || []
                } else {
                    display_toast(res)
                }
            } finally {
                is_loading_remote.value = false
            }
        }

        async function link_to(remote_uuid) {
            is_linking.value = remote_uuid
            const res = await fetch('/case/' + props.case_id + '/misp_object/' + props.local_object.object_id + '/link_remote', {
                method: 'POST',
                headers: { 'X-CSRFToken': $('#csrf_token').val(), 'Content-Type': 'application/json' },
                body: JSON.stringify({ instance_id: selected_instance_id.value, remote_uuid })
            })
            is_linking.value = false
            if (res.status === 200) {
                emit('link_updated')
            }
            display_toast(res)
        }

        async function unlink(instance_id) {
            is_linking.value = 'unlink-' + instance_id
            const res = await fetch('/case/' + props.case_id + '/misp_object/' + props.local_object.object_id + '/unlink_remote/' + instance_id, {
                method: 'DELETE',
                headers: { 'X-CSRFToken': $('#csrf_token').val() }
            })
            is_linking.value = false
            if (res.status === 200) {
                emit('link_updated')
            }
            display_toast(res)
        }

        return {
            case_connectors, selected_instance_id, is_loading_connectors,
            remote_objects, remote_search, remote_type_filter, is_loading_remote,
            is_linking,
            filtered_remote, remote_type_options, misp_connectors, selected_connector,
            current_link_for_instance,
            on_show, load_remote_objects, link_to, unlink
        }
    },
    template: `
    <div class="modal fade" :id="modal_id" tabindex="-1" aria-hidden="true">
        <div class="modal-dialog modal-xl">
            <div class="modal-content">
                <div class="modal-header">
                    <h5 class="modal-title">
                        <i class="fa-solid fa-link me-2"></i>
                        Link to remote MISP object
                        <span v-if="local_object" class="ms-2 text-muted small">[[ local_object.object_name ]]</span>
                    </h5>
                    <button type="button" class="btn-close" data-bs-dismiss="modal"></button>
                </div>
                <div class="modal-body">

                    <!-- Current link (at most one) -->
                    <template v-if="local_object && local_object.synced_instances && local_object.synced_instances.length">
                        <div class="alert alert-info d-flex align-items-center gap-3 py-2 mb-3">
                            <i class="fa-solid fa-link"></i>
                            <div class="flex-grow-1" style="min-width:0;">
                                <span class="badge bg-info text-dark me-2"><i class="fa-solid fa-cloud me-1"></i>[[ local_object.synced_instances[0].instance_name ]]</span>
                                <code style="font-size:0.8em;">[[ local_object.synced_instances[0].object_uuid ]]</code>
                                <a v-if="local_object.synced_instances[0].instance_url"
                                   :href="(local_object.synced_instances[0].instance_url.endsWith('/') ? local_object.synced_instances[0].instance_url : local_object.synced_instances[0].instance_url + '/') + 'objects/view/' + local_object.synced_instances[0].object_uuid"
                                   target="_blank" class="ms-2 small">
                                    <i class="fa-solid fa-arrow-up-right-from-square"></i> Open on MISP
                                </a>
                            </div>
                            <button type="button" class="btn btn-sm btn-outline-danger ms-auto"
                                    :disabled="is_linking === 'unlink-' + local_object.synced_instances[0].instance_id"
                                    @click="unlink(local_object.synced_instances[0].instance_id)">
                                <span v-if="is_linking === 'unlink-' + local_object.synced_instances[0].instance_id" class="spinner-border spinner-border-sm" style="width:0.7rem;height:0.7rem;"></span>
                                <i v-else class="fa-solid fa-link-slash"></i>
                                Unlink
                            </button>
                        </div>
                    </template>

                    <!-- Instance selector -->
                    <div class="row mb-3 align-items-end g-2">
                        <div class="col-md-5">
                            <label class="form-label fw-semibold mb-1">MISP connector instance</label>
                            <div v-if="is_loading_connectors" class="text-muted small"><span class="spinner-border spinner-border-sm me-2"></span>Loading…</div>
                            <select v-else class="form-select form-select-sm" v-model="selected_instance_id">
                                <option :value="null">-- select instance --</option>
                                <option v-for="c in misp_connectors" :key="c.case_task_instance_id" :value="c.case_task_instance_id">
                                    [[ c.details.name ]]<template v-if="c.identifier"> — [[ c.identifier ]]</template>
                                </option>
                            </select>
                            <div v-if="!is_loading_connectors && misp_connectors.length === 0" class="text-muted small mt-1">
                                No MISP connectors configured for this case.
                            </div>
                        </div>
                        <div class="col-md-auto">
                            <button type="button" class="btn btn-sm btn-outline-secondary"
                                    :disabled="!selected_instance_id || is_loading_remote"
                                    @click="load_remote_objects()">
                                <span v-if="is_loading_remote" class="spinner-border spinner-border-sm me-1" style="width:0.75rem;height:0.75rem;"></span>
                                <i v-else class="fa-solid fa-rotate me-1"></i>
                                [[ remote_objects.length ? 'Reload remote objects' : 'Load remote objects' ]]
                            </button>
                        </div>
                        <div v-if="selected_connector && current_link_for_instance(selected_connector.details && selected_connector.details.instance_id)" class="col-md-auto">
                            <span class="badge bg-success">
                                <i class="fa-solid fa-check me-1"></i>Already linked: [[ current_link_for_instance(selected_connector.details && selected_connector.details.instance_id) ]]
                            </span>
                        </div>
                    </div>

                    <!-- Two-column layout -->
                    <div class="row g-3">
                        <!-- LEFT: local object summary -->
                        <div class="col-md-4">
                            <div class="card h-100">
                                <div class="card-header py-2 fw-semibold">
                                    <i class="fa-solid fa-cube me-1"></i>Local object
                                </div>
                                <div class="card-body p-2" v-if="local_object">
                                    <p class="mb-1"><span class="badge bg-secondary">[[ local_object.object_name ]]</span></p>
                                    <table class="table table-sm table-borderless mb-0" style="font-size:0.8em;">
                                        <tbody>
                                            <tr v-for="attr in local_object.attributes" :key="attr.id">
                                                <td class="text-muted pe-2" style="white-space:nowrap;">[[ attr.object_relation ]]</td>
                                                <td>
                                                    <span :title="attr.value">
                                                        [[ attr.value.length > 50 ? attr.value.substring(0,50)+'…' : attr.value ]]
                                                    </span>
                                                </td>
                                            </tr>
                                        </tbody>
                                    </table>
                                    <div v-if="local_object.synced_instances && local_object.synced_instances.length" class="mt-2">
                                        <span v-for="si in local_object.synced_instances" :key="si.instance_id"
                                              class="badge bg-info text-dark me-1"
                                              :title="'UUID: '+si.object_uuid">
                                            <i class="fa-solid fa-cloud me-1"></i>[[ si.instance_name ]]
                                        </span>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- RIGHT: remote objects -->
                        <div class="col-md-8">
                            <div class="card h-100">
                                <div class="card-header d-flex justify-content-between align-items-center py-2">
                                    <span class="fw-semibold">
                                        <i class="fa-solid fa-cloud me-1"></i>Remote MISP objects
                                        <span v-if="remote_objects.length" class="badge bg-secondary ms-1">[[ filtered_remote.length ]]</span>
                                    </span>
                                </div>
                                <div class="card-body p-2">
                                    <div v-if="!selected_instance_id" class="text-muted small p-2">
                                        Select a MISP connector instance above.
                                    </div>
                                    <div v-else-if="is_loading_remote" class="text-center py-3">
                                        <span class="spinner-border spinner-border-sm me-2"></span>Loading from MISP…
                                    </div>
                                    <template v-else-if="remote_objects.length">
                                        <div class="d-flex gap-1 mb-2">
                                            <input v-model="remote_search" class="form-control form-control-sm" placeholder="Search by name or value…" type="text">
                                            <select v-model="remote_type_filter" class="form-select form-select-sm" style="max-width:140px;">
                                                <option value="">All types</option>
                                                <option v-for="t in remote_type_options" :key="t" :value="t">[[ t ]]</option>
                                            </select>
                                        </div>
                                        <div style="max-height:420px; overflow-y:auto;">
                                            <div v-if="!filtered_remote.length" class="text-muted small p-2">No objects match the filter.</div>
                                            <div v-for="obj in filtered_remote" :key="obj.uuid"
                                                 class="border rounded p-2 mb-1 d-flex align-items-start justify-content-between gap-2">
                                                <div style="min-width:0;">
                                                    <div>
                                                        <span class="badge bg-secondary me-1">[[ obj.name ]]</span>
                                                        <span class="text-muted" style="font-size:0.75em;">([[ obj.attribute_count ]] attrs)</span>
                                                        <template v-if="local_object && local_object.synced_instances && local_object.synced_instances.some(si => si.object_uuid === obj.uuid)">
                                                            <span class="badge bg-success ms-1" style="font-size:0.65em;"><i class="fa-solid fa-check me-1"></i>Linked</span>
                                                        </template>
                                                    </div>
                                                    <div class="text-muted mt-1" style="font-size:0.75em;">
                                                        <code style="font-size:0.9em;">[[ obj.uuid ]]</code>
                                                    </div>
                                                    <div v-if="obj.attributes_preview.length" class="text-muted" style="font-size:0.75em;">
                                                        <template v-for="(a,i) in obj.attributes_preview">
                                                            <span v-if="i>0"> · </span>[[ a.relation ]]: [[ a.value ]]
                                                        </template>
                                                    </div>
                                                </div>
                                                <div style="flex-shrink:0;">
                                                    <button type="button" class="btn btn-sm btn-outline-primary py-0"
                                                            :disabled="is_linking === obj.uuid"
                                                            @click="link_to(obj.uuid)">
                                                        <span v-if="is_linking === obj.uuid" class="spinner-border spinner-border-sm" style="width:0.7rem;height:0.7rem;"></span>
                                                        <i v-else class="fa-solid fa-link"></i>
                                                        <template v-if="local_object && local_object.synced_instances && local_object.synced_instances.some(si => si.object_uuid === obj.uuid)">
                                                            Re-link
                                                        </template>
                                                        <template v-else>Link</template>
                                                    </button>
                                                </div>
                                            </div>
                                        </div>
                                    </template>
                                    <div v-else class="text-muted small p-2">
                                        Click "Load remote objects" to fetch objects from MISP.
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Manual UUID input fallback -->
                    <hr class="my-3">
                    <div class="row align-items-end g-2">
                        <div class="col-auto fw-semibold small text-muted">Or link by UUID directly:</div>
                        <div class="col-md-5">
                            <input type="text" class="form-control form-control-sm" placeholder="Remote object UUID…" id="manual-uuid-input" pattern="[0-9a-fA-F-]{36}">
                        </div>
                        <div class="col-auto">
                            <button type="button" class="btn btn-sm btn-outline-secondary"
                                    :disabled="!selected_instance_id || !!is_linking"
                                    @click="link_to(document.getElementById('manual-uuid-input').value.trim())">
                                <i class="fa-solid fa-link me-1"></i>Link
                            </button>
                        </div>
                        <div v-if="!selected_instance_id" class="col-auto text-muted small">Select an instance first.</div>
                    </div>

                </div>
                <div class="modal-footer">
                    <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Close</button>
                </div>
            </div>
        </div>
    </div>
    `
}
