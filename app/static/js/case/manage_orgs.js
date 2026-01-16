import { display_toast } from '../toaster.js'
const { ref } = Vue
export default {
    delimiters: ['[[', ']]'],
    props: {
        cases_info: Object
    },
    setup(props) {
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
            const res = await fetch('/case/' + cases_info.case.id + '/remove_org/' + org.id)
            if (await res.status == 200) {
                let index = cases_info.orgs_in_case.indexOf(org)
                if (index > -1)
                    cases_info.orgs_in_case.splice(index, 1)
            }
            display_toast(res)
        }

        function check_org_not_in(org_id) {
            for (let i in props.cases_info.orgs_in_case) {
                if (props.cases_info.orgs_in_case[i].id == org_id) {
                    return true
                }
            }
            return false
        }

        async function submit_add_orgs() {
            $("#add_orgs_error").text("")
            if ($("#add_orgs_select").val().includes("None") || !$("#add_orgs_select").val().length) {
                $("#add_orgs_error").text("Give me more")
            } else {
                const res = await fetch('/case/' + props.cases_info.case.id + '/add_orgs', {
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({ "org_id": $("#add_orgs_select").val() })
                })
                if (await res.status == 200) {
                    let loc = $("#add_orgs_select").val()
                    for (let index in loc) {
                        for (let i in orgs.value) {
                            if (orgs.value[i].id == loc[index]) {
                                props.cases_info.orgs_in_case.push(orgs.value[i])
                            }
                        }
                    }
                    var myModalEl = document.getElementById('add_orgs');
                    var modal = bootstrap.Modal.getInstance(myModalEl)
                    modal.hide();
                }
                display_toast(res)
            }
        }

        async function submit_change_owner() {
            $("#change_owner_error").text("")
            if ($("#change_owner_select").val() == "None" || !$("#change_owner_select")) {
                $("#change_owner_error").text("Give me more")
            } else {
                const res = await fetch('/case/' + props.cases_info.case.id + '/change_owner', {
                    headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
                    method: "POST",
                    body: JSON.stringify({ "org_id": $("#change_owner_select").val() })
                })
                if (await res.status == 200) {
                    props.cases_info.case.owner_org_id = $("#change_owner_select").val()
                }
                display_toast(res)
            }
        }


        return {
            orgs,
            remove_org_case,
            check_org_not_in,
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
                        <button class="btn btn-primary btn-sm me-1" title="Change owner of the case" data-bs-toggle="modal" data-bs-target="#change_owner">
                            <i class="fa-solid fa-user-pen fa-sm"></i>
                        </button>
                        <button class="btn btn-outline-primary btn-sm" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#collapseOrgs" aria-expanded="true" aria-controls="collapseOrgs">
                            <i class="fa-solid fa-chevron-down fa-sm"></i>
                        </button>
                    </div>
                </template>
                <div class="d-flex align-items-center">
                    <h6 class="section-title mb-0"><i class="fa-solid fa-building fa-sm me-2"></i>Organizations</h6>
                    <span class="badge text-bg-secondary ms-2">[[cases_info.orgs_in_case.length]]</span>
                </div>

                <hr class="fading-line-2 mt-2 mb-2">

                <div class="collapse show" id="collapseOrgs">
                    <div class="row mt-2">
                        <div class="col-6 link-style-first" v-for="org in cases_info.orgs_in_case" :key="org.id">
                            <span style="margin-left: 8%;  padding: 5px;">
                                [[org.name]]
                                <small v-if="org.id == cases_info.case.owner_org_id" class="text-success">
                                    <i class="fa-solid fa-crown fa-sm"></i> owner
                                </small>
                            </span>
                            <template v-if="org.id != cases_info.case.owner_org_id">
                                <button class="btn btn-outline-danger btn-sm ms-4"
                                @click="remove_org_case(cases_info, org)"
                                v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin"
                                title="Remove org from case">
                                    <i class="fa-solid fa-trash fa-sm"></i>
                                </button>
                            </template>
                        </div>
                    </div>
                </div>


                <!-- Modal add orgs -->
                <div class="modal fade" id="add_orgs" tabindex="-1" aria-labelledby="add_orgs_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h1 class="modal-title fs-5" id="add_orgs_modal">Add Orgs</h1>
                                <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                Orgs:
                                <select data-placeholder="Orgs" class="select2-select-add-orgs form-control" multiple name="add_orgs_select" id="add_orgs_select">
                                    <option value="None">--</option>
                                    <template v-for="org in orgs">
                                        <option v-if="!check_org_not_in(org.id)" :value="[[org.id]]">[[org.name]]</option>
                                    </template>
                                </select>
                                <div style="color: brown;" id="add_orgs_error"></div>
                            </div>
                            <div class="modal-footer">
                                <button @click="submit_add_orgs()" class="btn btn-primary">Submit</button>
                            </div>
                        </div>
                    </div>
                </div>
                
                <!-- Modal change owner -->
                <div class="modal fade" id="change_owner" tabindex="-1" aria-labelledby="change_owner_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h1 class="modal-title fs-5" id="change_owner_modal">Change Owner</h1>
                                <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                Orgs:
                                <select class="form-control" name="change_owner_select" id="change_owner_select" style="width: 50%">
                                    <option value="None">--</option>
                                    <template v-for="org in orgs">
                                        <option v-if="org.id != cases_info.case.owner_org_id" :value="[[org.id]]">[[org.name]]</option>
                                    </template>
                                </select>
                                <div style="color: brown;" id="change_owner_error"></div>
                            </div>
                            <div class="modal-footer">
                                <button @click="submit_change_owner()" class="btn btn-primary">Submit</button>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </template>
    `
}