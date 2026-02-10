import { display_toast, create_message } from '/static/js/toaster.js'

export default {
    delimiters: ['[[', ']]'],
    props: {
        task: Object,
        cases_info: Object
    },
    setup(props) {
        async function create_external_reference(task) {
            $("#textarea-external-ref-error-" + task.id).text("")
            let url = $("#textarea-external-ref-" + task.id).val()
            if (!url) {
                $("#textarea-external-ref-error-" + task.id).text("Cannot be empty...").css("color", "brown")
                return
            }

            const res = await fetch("/case/" + task.case_id + "/task/" + task.id + "/create_external_reference", {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "url": url
                })
            });
            if (res.status == 200) {
                let loc = await res.json()

                task.external_references.push({ "id": loc["id"], "url": url, "task_id": task.id })
                create_message("External reference created", "success-subtle", false, "fas fa-plus")
                $("#textarea-external-ref-" + task.id).val("")
                $("#create_external_ref_" + task.id).modal("hide")
            } else {
                await display_toast(res)
            }
        }

        async function edit_external_reference(task, external_ref_id) {
            $("#edit-external-ref-error-" + external_ref_id).text("")
            let url = $("#edit-external-ref-" + external_ref_id).val()
            if (!url) {
                $("#edit-external-ref-error-" + external_ref_id).text("Cannot be empty...").css("color", "brown")
                return
            }

            const res = await fetch("/case/" + task.case_id + "/task/" + task.id + "/edit_external_reference/" + external_ref_id, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "url": url
                })
            });
            if (res.status == 200) {
                for (let i in task.external_references) {
                    if (task.external_references[i].id == external_ref_id) {
                        task.external_references[i].url = url
                        break
                    }
                }
                $("#edit_external_ref_" + external_ref_id).modal("hide")
            }
            await display_toast(res)
        }

        async function delete_external_reference(task, external_ref_id) {
            const res = await fetch('/case/' + task.case_id + '/task/' + task.id + "/delete_external_reference/" + external_ref_id)

            if (res.status == 200) {
                const index = task.external_references.findIndex(ref => ref.id == external_ref_id)
                if (index > -1) {
                    task.external_references.splice(index, 1)
                }
            }
            await display_toast(res)
        }

        async function convert_to_note(task, external_ref_id) {
            if (!confirm('Convert this external reference to a task note?')) {
                return
            }
            const res = await fetch('/case/' + task.case_id + '/task/' + task.id + '/convert_external_reference_to_note/' + external_ref_id, {
                headers: { "X-CSRFToken": $("#csrf_token").val() },
                method: "POST"
            })
            const loc = await res.json()
            if (res.status == 200) {
                task.last_modif = Date.now()
                if (loc.note) {
                    task.notes.push(loc.note)
                    task.nb_notes += 1
                }
            }
            await create_message(loc.message, loc.toast_class, false, loc.icon)
        }

        return {
            create_external_reference,
            edit_external_reference,
            delete_external_reference,
            convert_to_note
        }
    },
    template: `
	<div class="col">
        <fieldset class="analyzer-select-case">
            <legend class="analyzer-select-case">
                <i class="fa-solid fa-link fa-sm me-1"></i><span class="section-title">External references</span>
				<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
					<button class="btn btn-primary btn-sm" title="Add new external reference" data-bs-toggle="modal" :data-bs-target="'#create_external_ref_'+task.id" style="float: right; margin-left:3px;">
						<i class="fa-solid fa-plus"></i>
					</button>
				</template>
            </legend>
            <template v-for="external_ref in task.external_references">
                <div>
                    <a :href="external_ref.url" target="_blank" rel="noopener noreferrer">[[external_ref.url]]</a>
                    <template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                        <button @click="delete_external_reference(task, external_ref.id)" class="btn btn-danger btn-sm" style="float: right;">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                        <button @click="convert_to_note(task, external_ref.id)" class="btn btn-success btn-sm" title="Visit external reference and convert HTML to Markdown" style="float: right; margin-right: 2px;">
                            <i class="fa-solid fa-file-import"></i>
                        </button>
                        <button class="btn btn-primary btn-sm" title="Edit external reference" data-bs-toggle="modal" :data-bs-target="'#edit_external_ref_'+external_ref.id" style="float: right; margin-right: 2px;">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                    </template>
                </div>
                <hr>
                <!-- Modal edit external reference -->
                <div class="modal fade" :id="'edit_external_ref_'+external_ref.id" tabindex="-1" aria-labelledby="edit_external_ref_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h1 class="modal-title fs-5" id="edit_external_ref_modal">Edit External Reference</h1>
                                <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <textarea class="form-control" :value="external_ref.url" :id="'edit-external-ref-'+external_ref.id"/>
                                <div :id="'edit-external-ref-error-'+external_ref.id"></div>
                            </div>
                            <div class="modal-footer">
                                <button @click="edit_external_reference(task, external_ref.id)" class="btn btn-primary">Submit</button>
                            </div>
                        </div>
                    </div>
                </div>
            </template>
        </fieldset>

        <!-- Modal create external reference -->
        <div class="modal fade" :id="'create_external_ref_'+task.id" tabindex="-1" aria-labelledby="create_external_ref_modal" aria-hidden="true">
            <div class="modal-dialog modal-lg">
                <div class="modal-content">
                    <div class="modal-header">
                        <h1 class="modal-title fs-5" id="create_external_ref_modal">Create External Reference</h1>
                        <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                    </div>
                    <div class="modal-body">
                        <textarea class="form-control" :id="'textarea-external-ref-'+task.id" placeholder="Enter URL..."/>
                        <div :id="'textarea-external-ref-error-'+task.id"></div>
                    </div>
                    <div class="modal-footer">
                        <button @click="create_external_reference(task)" class="btn btn-primary">Submit</button>
                    </div>
                </div>
            </div>
        </div>
    </div>
	`
}
