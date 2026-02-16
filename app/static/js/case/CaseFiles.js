import { display_toast } from '/static/js/toaster.js'

export default {
	delimiters: ['[[', ']]'],
	props: {
		case_id: Number,
		case_files_list: Array,
		cases_info: Object
	},
	emits: ['files_change'],
	setup(props, { emit }) {
		async function add_file() {
			// Add file to the case
			let files = document.getElementById('formFileMultipleCase').files

			// Create a form with all files upload
			let formData = new FormData();
			for (let i = 0; i < files.length; i++) {
				formData.append("files" + i, files[i]);
			}

			const res = await fetch(
				'/case/' + props.case_id + '/add_files', {
				headers: { "X-CSRFToken": $("#csrf_token").val() },
				method: "POST",
				files: files,
				body: formData
			}
			)
			if (await res.status == 200) {
				document.getElementById('formFileMultipleCase').value = ''
				emit('files_change')
			}

			await display_toast(res)
		}

		async function delete_file(file) {
			// Delete a file in the case
			if (!confirm('Are you sure you want to delete "' + file.name + '"?')) {
				return
			}
			const res = await fetch('/case/' + props.case_id + '/delete_case_file/' + file.id)
			if (await res.status == 200) {
				emit('files_change')
			}
			await display_toast(res)
		}

		return {
			add_file,
			delete_file
		}
	},
	template: `
	<fieldset class="analyzer-select-case">
        <legend class="analyzer-select-case"><i class="fa-solid fa-file fa-sm me-1"></i><span class="section-title">Files</span></legend>
        <div style="display: flex;" v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
            <input class="form-control" type="file" id="formFileMultipleCase" multiple/>
            <button class="btn btn-primary btn-sm" @click="add_file()" style="margin-left: 2px;">Submit</button>
        </div>
        <br/>
        <template v-if="case_files_list.length">
            <div class="table-responsive">
                <table class="table table-sm table-hover">
                    <thead>
                        <tr>
                            <th>Filename</th>
                            <th>Upload Date</th>
                            <th>Size</th>
                            <th>Type</th>
                            <th v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr v-for="file in case_files_list" :key="file.id">
                            <td>
                                <a :href="'/case/'+case_id+'/download_case_file/'+file.id">
                                    <i class="fa-solid fa-download me-1"></i>[[ file.name ]]
                                </a>
                            </td>
                            <td>[[ file.upload_date ]]</td>
                            <td><template v-if="file.file_size !== 'Unknown'">[[ (file.file_size / 1024).toFixed(2) ]] KB</template><template v-else>Unknown</template></td>
                            <td>[[ file.file_type ]]</td>
                            <td v-if="!cases_info.permission.read_only && cases_info.present_in_case || cases_info.permission.admin">
                                <button class="btn btn-danger btn-sm" @click="delete_file(file)" title="Delete file">
                                    <i class="fa-solid fa-trash"></i>
                                </button>
                            </td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </template>
        <p v-else class="text-muted"><i>No files attached to this case.</i></p>
    </fieldset>
    `
}
