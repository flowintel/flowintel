import {display_toast, create_message} from '/static/js/toaster.js'
const { ref } = Vue
export default {
    delimiters: ['[[', ']]'],
	props: {
		task: Object
	},
	setup(props) {
        async function add_file(task){
			// Add file to the task
			let files = document.getElementById('formFileMultiple'+task.id).files

			// Create a form with all files upload
			let formData = new FormData();
			for(let i=0;i<files.length;i++){
				formData.append("files"+i, files[i]);
			}

			const res = await fetch(
				'/case/' + task.case_id + '/add_files/' + task.id,{
					headers: { "X-CSRFToken": $("#csrf_token").val() },
					method: "POST",
					files: files,
					body: formData
				}
			)
			if(await res.status == 200){
				// Get the new list of files of the task
				const res_files = await fetch('/case/' + task.case_id + '/get_files/'+task.id)

				if(await res_files.status == 200){
					task.last_modif = Date.now()
					let loc = await res_files.json()
					task.files = []
					for(let file in loc['files']){
						task.files.push(loc['files'][file])
					}
				}else{
					await display_toast(res_files)
				}
			}

			await display_toast(res)
		}

        async function delete_file(file, task){
			// Delete a file in the task
			const res = await fetch('/case/task/' + task.id + '/delete_file/' + file.id)
			if(await res.status == 200){
				task.last_modif = Date.now()

				// Remove the file from list
				let index = task.files.indexOf(file)
				if(index > -1)
					task.files.splice(index, 1)
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
        <legend class="analyzer-select-case"><i class="fa-solid fa-file"></i> Files</legend>
        <div style="display: flex;">
            <input class="form-control" type="file" :id="'formFileMultiple'+task.id" multiple/>
            <button class="btn btn-primary btn-sm" @click="add_file(task)" style="margin-left: 2px;">Submit</button>
        </div>
        <br/>
        <template v-if="task.files.length">
            <template v-for="file in task.files">
                <div>
                    <a class="btn btn-link" :href="'/case/task/'+task.id+'/download_file/'+file.id">
                        [[ file.name ]]
                    </a>
                    <button class="btn btn-danger" @click="delete_file(file, task)"><i class="fa-solid fa-trash"></i></button>
                </div>
            </template>
        </template>
    </fieldset>
    `
}