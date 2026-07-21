import { display_toast, create_message } from '/static/js/toaster.js'
import { confirmDelete } from '/static/js/confirm.js'
import { touchTaskAndCaseLastModif } from '/static/js/case/helpers.js'

const { ref } = Vue

export default {
    delimiters: ['[[', ']]'],
    props: {
        task: Object,
        cases_info: Object,
        is_template: Boolean
    },
    setup(props) {
        const create_name = ref("")
        const edit_names = ref({})

        function url_tools(task) {
            return Array.isArray(task?.urls_tools) ? task.urls_tools : []
        }

        function ensure_url_tools(task) {
            if (!task) return []
            if (!Array.isArray(task.urls_tools)) task.urls_tools = []
            return task.urls_tools
        }

        function text_value(value) {
            return String(value ?? "")
        }

        function is_blank(value) {
            return !text_value(value).trim()
        }

        function url_tool_label(url_tool) {
            return text_value(url_tool?.name)
        }

        function edit_url_tool_name(url_tool) {
            if (!url_tool) return ""
            return text_value(edit_names.value[url_tool.id] ?? url_tool.name)
        }

        async function create_url_tool(task) {
            $("#textarea-url_tool-error-" + task.id).text("")
            let name = text_value(create_name.value).trim()
            if (!name) {
                $("#textarea-url_tool-error-" + task.id).text("Cannot be empty...").css("color", "brown")
                return
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

                ensure_url_tools(task).push({ "id": loc["id"], "name": name, "task_id": task.id })
                touchTaskAndCaseLastModif(task, props.cases_info)
                create_message("url_tool created", "success-subtle", false, "fas fa-plus")
                create_name.value = ""
                $("#create_url_tool_" + task.id).modal("hide")
            } else {
                await display_toast(res)
            }
        }

        async function edit_url_tool(task, url_tool_id) {
            $("#edit-url_tool-error-" + url_tool_id).text("")
            const task_url_tools = ensure_url_tools(task)
            let current = task_url_tools.find(ut => ut.id == url_tool_id)
            let name = text_value(edit_names.value[url_tool_id] ?? current?.name).trim()
            if (!name) {
                $("#edit-url_tool-error-" + url_tool_id).text("Cannot be empty...").css("color", "brown")
                return
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
                for (let i in task_url_tools) {
                    if (task_url_tools[i].id == url_tool_id) {
                        task_url_tools[i].name = name
                        break
                    }
                }
                touchTaskAndCaseLastModif(task, props.cases_info)
                $("#edit_url_tool_" + url_tool_id).modal("hide")
            }
            await display_toast(res)
        }

        async function delete_url_tool(task, url_tool_id) {
            const ok = await confirmDelete({
                title: 'Delete URL/Tool?',
                message: 'Are you sure you want to delete this URL/Tool? This cannot be undone.'
            })
            if (!ok) return
            let url
            if (props.is_template) {
                url = "/templating/task/" + task.id + "/delete_url_tool/" + url_tool_id
            } else {
                url = '/case/' + task.case_id + '/task/' + task.id + "/delete_url_tool/" + url_tool_id
            }
            const res = await fetch(url)

            if (await res.status == 200) {
                let loc_i
                const task_url_tools = ensure_url_tools(task)
                for (let i in task_url_tools) {
                    if (task_url_tools[i].id == url_tool_id) {
                        loc_i = i
                        break
                    }
                }
                if (loc_i !== undefined) task_url_tools.splice(loc_i, 1)
                touchTaskAndCaseLastModif(task, props.cases_info)
            }
            await display_toast(res)
        }

        return {
            create_name,
            edit_names,
            url_tools,
            is_blank,
            url_tool_label,
            edit_url_tool_name,
            create_url_tool,
            edit_url_tool,
            delete_url_tool
        }
    },
    template: `
    <div class="col">
        <div class="task-section">
            <div class="task-section-header">
                <i class="fa-solid fa-screwdriver-wrench fa-sm me-1"></i><span class="section-title">Urls/Tools</span>
                <template v-if="task.can_edit && cases_info.present_in_case || cases_info.permission.admin">
                    <div class="ms-auto">
                        <button class="btn btn-primary btn-sm" title="Add new url/tool" data-bs-toggle="modal" :data-bs-target="'#create_url_tool_'+task.id">
                            <i class="fa-solid fa-plus"></i>
                        </button>
                    </div>
                </template>
            </div>
            <div class="task-section-body">
                <template v-for="url_tool in url_tools(task)">
                    <div>
                        [[ url_tool_label(url_tool) || 'Untitled URL/Tool' ]]
                        <template v-if="task.can_edit && cases_info.present_in_case || cases_info.permission.admin">
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
                                    <textarea class="form-control" :value="edit_url_tool_name(url_tool)" @input="edit_names[url_tool.id] = $event.target.value" :id="'edit-url_tool-'+url_tool.id"/>
                                    <div :id="'edit-url_tool-error-'+url_tool.id"></div>
                                </div>
                                <div class="modal-footer">
                                    <button @click="edit_url_tool(task, url_tool.id)" :disabled="is_blank(edit_url_tool_name(url_tool))" class="btn btn-primary">Submit</button>
                                </div>
                            </div>
                        </div>
                    </div>
                </template>
            </div>
        </div>
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
						<textarea class="form-control" v-model="create_name" :id="'textarea-url_tool-'+task.id"/>
						<label>New Url/Tool</label>
						<div :id="'textarea-url_tool-error-'+task.id"></div>
					</div>
                </div>
                <div class="modal-footer">
                    <button @click="create_url_tool(task)" :disabled="is_blank(create_name)" class="btn btn-primary">Submit</button>
                </div>
            </div>
        </div>
    </div>
    `
}
