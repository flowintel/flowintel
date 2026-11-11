import { display_toast } from '../toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchCaseLastModif } from '/static/js/case/helpers.js'
import org_picker from '/static/js/components/org-picker.js'
const { ref, computed } = Vue
export default {
    delimiters: ['[[', ']]'],
    components: { org_picker },
    props: {
        cases_info: Object
    },
    setup(props, { emit }) {
        const orgs = ref([])

        async function fetch_orgs() {
            const res = await fetch("/case/get_orgs")
            if (await res.status == 404) {
                display_toast(res)
            } else {
                let loc = await res.json()
                orgs.value = loc
            }
        }
        fetch_orgs()

        async function remove_org_case(cases_info, org) {
            const ok = await confirmDelete({
                title: 'Remove organisation?',
                message: 'Are you sure you want to remove this organisation from the case?',
                confirmText: 'Remove'
            })
            if (!ok) return
            const res = await fetch('/case/' + cases_info.case.id + '/remove_org/' + org.id, {
                method: 'POST',
                headers: {'X-CSRFToken': $('#csrf_token').val()}
            })
            if (await res.status == 200) {
                let index = cases_info.orgs_in_case.indexOf(org)
                if (index > -1)
                    cases_info.orgs_in_case.splice(index, 1)
                touchCaseLastModif(cases_info)
                // notify parent to refresh users list
                try { emit('case_orgs_changed') } catch (e) {}
            }
            display_toast(res)
        }

        // Organisations picked in the "Add organisations" / "Change owner" modals
        const orgs_to_add = ref([])
        const new_owner = ref([])
        const add_error = ref('')
        const owner_error = ref('')
        const owner_candidates = computed(() => (props.cases_info ? props.cases_info.orgs_in_case : [])
            .filter(o => o.id != props.cases_info.case.owner_org_id))

        async function submit_add_orgs() {
            add_error.value = ''
            if (!orgs_to_add.value.length) {
                add_error.value = 'Pick at least one organisation.'
                return
            }
            const ids = orgs_to_add.value.map(String)
            const res = await fetch('/case/' + props.cases_info.case.id + '/add_orgs', {
                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                method: "POST",
                body: JSON.stringify({ "org_id": ids })
            })
            if (res.status == 200) {
                for (const id of ids) {
                    const org = orgs.value.find(o => String(o.id) === id)
                    if (org) props.cases_info.orgs_in_case.push(org)
                }
                orgs_to_add.value = []
                touchCaseLastModif(props.cases_info)
                bootstrap.Modal.getInstance(document.getElementById('add_orgs')).hide()
                // notify parent to refresh users list after adding orgs
                try { emit('case_orgs_changed') } catch (e) {}
            }
            display_toast(res)
        }

        async function submit_change_owner() {
            owner_error.value = ''
            if (!new_owner.value.length) {
                owner_error.value = 'Pick the organisation that will own the case.'
                return
            }
            const res = await fetch('/case/' + props.cases_info.case.id + '/change_owner', {
                headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                method: "POST",
                body: JSON.stringify({ "org_id": String(new_owner.value[0]) })
            })
            if (res.status == 200) {
                props.cases_info.case.owner_org_id = Number(new_owner.value[0])
                new_owner.value = []
                touchCaseLastModif(props.cases_info)
                bootstrap.Modal.getInstance(document.getElementById('change_owner')).hide()
            }
            display_toast(res)
        }

        function owner_name() {
            const o = props.cases_info && props.cases_info.orgs_in_case.find(o => o.id == props.cases_info.case.owner_org_id)
            return o ? o.name : 'none'
        }


        return {
            orgs,
            orgs_to_add, new_owner, add_error, owner_error, owner_candidates, owner_name,
            remove_org_case,
            submit_add_orgs,
            submit_change_owner
        }
    },
    template: `
		<template v-if="cases_info">
            <div class="case-tags-style mt-2">
                <template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                    <div class="justify-content-center" style="display: flex; float: right">
                        <button class="btn btn-primary btn-sm" title="Add an org to the case" style="margin-right: 3px" data-bs-toggle="modal" data-bs-target="#add_orgs">
                            <i class="fa-solid fa-users fa-sm"></i>+
                        </button>
                        <button class="btn btn-primary btn-sm me-1" title="Change owner of the case" 
                                :disabled="cases_info.orgs_in_case.length <= 1"
                                data-bs-toggle="modal" data-bs-target="#change_owner">
                            <i class="fa-solid fa-user-pen fa-sm"></i>
                        </button>
                        <button class="btn btn-outline-primary btn-sm" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#collapseOrgs" aria-expanded="true" aria-controls="collapseOrgs">
                            <i class="fa-solid fa-chevron-down fa-sm"></i>
                        </button>
                    </div>
                </template>
                <div class="d-flex align-items-center">
                    <h6 class="section-title mb-0"><i class="fa-solid fa-building fa-sm me-2"></i>Organisations</h6>
                    <span class="badge text-bg-secondary ms-2">[[cases_info.orgs_in_case.length]]</span>
                </div>

                <hr class="fading-line-2 mt-2 mb-2">

                <div class="collapse show" id="collapseOrgs">
                    <div class="morg-grid mt-2">
                        <div v-for="org in cases_info.orgs_in_case" :key="org.id" :class="['morg-card', { 'is-owner': org.id == cases_info.case.owner_org_id }]">
                            <span class="morg-card-icon"><i class="fa-solid fa-building"></i></span>
                            <div class="morg-card-text">
                                <div class="morg-card-name">
                                    [[ org.name ]]
                                    <span v-if="org.id == cases_info.case.owner_org_id" class="morg-owner" title="This organisation owns the case"><i class="fa-solid fa-crown"></i>Owner</span>
                                </div>
                                <div class="morg-card-desc" :title="org.description">[[ org.description || 'No description' ]]</div>
                            </div>
                            <button v-if="org.id != cases_info.case.owner_org_id && (!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin)"
                                    class="morg-remove" @click="remove_org_case(cases_info, org)" title="Remove the organisation from the case" :aria-label="'Remove ' + org.name">
                                <i class="fa-solid fa-trash-can"></i>
                            </button>
                        </div>
                    </div>
                </div>


                <!-- Modal add organisations -->
                <div class="modal fade" id="add_orgs" tabindex="-1" aria-labelledby="add_orgs_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-centered">
                        <div class="modal-content morg-modal">
                            <div class="modal-header">
                                <span class="morg-modal-icon"><i class="fa-solid fa-building-circle-arrow-right"></i></span>
                                <div>
                                    <h1 class="modal-title fs-5" id="add_orgs_modal">Add organisations</h1>
                                    <div class="morg-modal-sub">Their members will see the case and can be assigned to its tasks.</div>
                                </div>
                                <button class="btn-close ms-auto" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <org_picker v-model="orgs_to_add" :orgs="orgs" :exclude="cases_info.orgs_in_case.map(o => o.id)" placeholder="Search the organisations to add…"></org_picker>
                                <div v-if="add_error" class="morg-error">[[ add_error ]]</div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button @click="submit_add_orgs()" class="btn btn-primary" :disabled="!orgs_to_add.length">
                                    <i class="fa-solid fa-plus me-1"></i>Add [[ orgs_to_add.length > 1 ? orgs_to_add.length + ' organisations' : 'organisation' ]]
                                </button>
                            </div>
                        </div>
                    </div>
                </div>

                <!-- Modal change owner -->
                <div class="modal fade" id="change_owner" tabindex="-1" aria-labelledby="change_owner_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg modal-dialog-centered">
                        <div class="modal-content morg-modal">
                            <div class="modal-header">
                                <span class="morg-modal-icon"><i class="fa-solid fa-crown"></i></span>
                                <div>
                                    <h1 class="modal-title fs-5" id="change_owner_modal">Change the owner</h1>
                                    <div class="morg-modal-sub">Currently owned by <b>[[ owner_name() ]]</b>. Only an organisation already in the case can own it.</div>
                                </div>
                                <button class="btn-close ms-auto" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <org_picker v-model="new_owner" :orgs="owner_candidates" :multiple="false" placeholder="Search the new owner…"></org_picker>
                                <div v-if="owner_error" class="morg-error">[[ owner_error ]]</div>
                            </div>
                            <div class="modal-footer">
                                <button type="button" class="btn btn-secondary" data-bs-dismiss="modal">Cancel</button>
                                <button @click="submit_change_owner()" class="btn btn-primary" :disabled="!new_owner.length"><i class="fa-solid fa-crown me-1"></i>Make it the owner</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    `
}
