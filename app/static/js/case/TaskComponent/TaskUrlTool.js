import { display_toast, create_message } from '/static/js/toaster.js'

export default {
    delimiters: ['[[', ']]'],
    props: {
        task: Object,
        cases_info: Object,
        is_template: Boolean
    },
    setup(props) {
        async function create_url_tool(task) {
            $("#textarea-url_tool-error-" + task.id).text("")
            let name = $("#textarea-url_tool-" + task.id).val()
            if (!name) {
                $("#textarea-url_tool-error-" + task.id).text("Cannot be empty...").css("color", "brown")
            }

            let url
            if (props.is_template) {
                url = "/templating/task/" + task.id + "/create_url_tool"
            } else {
                url = "/case/" + task.case_id + "/task/" + task.id + "/create_url_tool"
            }

            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "name": name
                })
            });
            if (await res.status == 200) {
                let loc = await res.json()

                task.urls_tools.push({ "id": loc["id"], "name": name, "task_id": task.id })
                create_message("url_tool created", "success-subtle", false, "fas fa-plus")
                $("#textarea-url_tool-" + task.id).val("")
                $("#create_url_tool_" + task.id).modal("hide")
            } else {
                await display_toast(res)
            }
        }

        async function edit_url_tool(task, url_tool_id) {
            $("#edit-url_tool-error-" + url_tool_id).text("")
            let name = $("#edit-url_tool-" + url_tool_id).val()
            if (!name) {
                $("#edit-url_tool-error-" + url_tool_id).text("Cannot be empty...").css("color", "brown")
            }

            let url
            if (props.is_template) {
                url = "/templating/task/" + task.id + "/edit_url_tool/" + url_tool_id
            } else {
                url = "/case/" + task.case_id + "/task/" + task.id + "/edit_url_tool/" + url_tool_id
            }

            const res = await fetch(url, {
                method: "POST",
                headers: {
                    "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json"
                },
                body: JSON.stringify({
                    "name": name
                })
            });
            if (await res.status == 200) {
                for (let i in task.urls_tools) {
                    if (task.urls_tools[i].id == url_tool_id) {
                        task.urls_tools[i].name = name
                        break
                    }
                }
                $("#edit_url_tool_" + url_tool_id).modal("hide")
            }
            await display_toast(res)
        }

        async function delete_url_tool(task, url_tool_id) {
            let url
            if (props.is_template) {
                url = "/templating/task/" + task.id + "/delete_url_tool/" + url_tool_id
            } else {
                url = '/case/' + task.case_id + '/task/' + task.id + "/delete_url_tool/" + url_tool_id
            }
            const res = await fetch(url)

            if (await res.status == 200) {
                let loc_i
                for (let i in task.urls_tools) {
                    if (task.urls_tools[i].id == url_tool_id) {
                        loc_i = i
                        break
                    }
                }
                task.urls_tools.splice(loc_i, 1)
            }
            await display_toast(res)
        }

        return {
            create_url_tool,
            edit_url_tool,
            delete_url_tool
        }
    },
    template: `
	<div class="col">
        <fieldset class="analyzer-select-case">
            <legend class="analyzer-select-case">
                <i class="fa-solid fa-screwdriver-wrench fa-sm me-1"></i><span class="section-title">Urls/Tools</span>
				<template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
					<button class="btn btn-primary btn-sm" title="Add new url/tool" data-bs-toggle="modal" :data-bs-target="'#create_url_tool_'+task.id" style="float: right; margin-left:3px;">
						<i class="fa-solid fa-plus"></i>
					</button>
				</template>
            </legend>
            <template v-for="url_tool in task.urls_tools">
                <div>
                    [[url_tool.name]]
                    <template v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                        <button @click="delete_url_tool(task, url_tool.id)" class="btn btn-danger btn-sm" style="float: right;">
                            <i class="fa-solid fa-trash"></i>
                        </button>
                        <button class="btn btn-primary btn-sm" title="Edit Url/Tool" data-bs-toggle="modal" :data-bs-target="'#edit_url_tool_'+url_tool.id" style="float: right;">
                            <i class="fa-solid fa-pen-to-square"></i>
                        </button>
                    </template>
                </div>
                <hr>
                <!-- Modal edit url/tool -->
                <div class="modal fade" :id="'edit_url_tool_'+url_tool.id" tabindex="-1" aria-labelledby="edit_url_tool_modal" aria-hidden="true">
                    <div class="modal-dialog modal-lg">
                        <div class="modal-content">
                            <div class="modal-header">
                                <h1 class="modal-title fs-5" id="edit_url_tool_modal">Edit Url/Tool</h1>
                                <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                            </div>
                            <div class="modal-body">
                                <textarea class="form-control" :value="url_tool.name" :id="'edit-url_tool-'+url_tool.id"/>
                                <div :id="'edit-url_tool-error-'+url_tool.id"></div>
                            </div>
                            <div class="modal-footer">
                                <button @click="edit_url_tool(task, url_tool.id)" class="btn btn-primary">Submit</button>
                            </div>
                        </div>
                    </div>
                </div>
            </template>
        </fieldset>
    </div>

    <!-- Modal create Url/Tool -->
    <div class="modal fade" :id="'create_url_tool_'+task.id" tabindex="-1" aria-labelledby="create_url_tool_modal" aria-hidden="true">
        <div class="modal-dialog modal-lg">
            <div class="modal-content">
                <div class="modal-header">
                    <h1 class="modal-title fs-5" id="create_url_tool_modal">Create Url/Tool</h1>
                    <button class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body">
					<div class="form-floating">
						<textarea class="form-control" :id="'textarea-url_tool-'+task.id"/>
						<label>New Url/Tool</label>
						<div :id="'textarea-url_tool-error-'+task.id"></div>
					</div>
                </div>
                <div class="modal-footer">
                    <button @click="create_url_tool(task)" class="btn btn-primary">Submit</button>
                </div>
            </div>
        </div>
    </div>
    `
}