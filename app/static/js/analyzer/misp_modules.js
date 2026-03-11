import { display_toast } from '/static/js/toaster.js'
const { ref, nextTick } = Vue
export default {
	delimiters: ['[[', ']]'],
	setup() {
		const entries = ref([1])
		const isSubmitting = ref(false)
		let next_id = 2
		const misp_attributes_list = ref([])
		const modules_list = ref([])
		const config_query = ref([])
		const attr_selected = ref([])
		const modules_selected = ref([])

		function add_entry() {
			entries.value.push(next_id++)
		}
		function delete_entry(id) {
			if (entries.value.length > 1)
				entries.value = entries.value.filter(e => e !== id)
		}

		async function query_misp_attributes() {
			let res = await fetch("/analyzer/misp-modules/get_list_misp_attributes")
			let loc = await res.json()
			misp_attributes_list.value = loc

			await nextTick()

			if (!$('.select2-input').hasClass("select2-hidden-accessible")) {
				$('.select2-input').select2({
					theme: 'bootstrap-5'
				})
			}

			$('#input_select').on('change.select2', async function (e) {
				attr_selected.value = $(this).select2('data').map(item => item.id)[0]
				if (attr_selected.value == 'None') {
					attr_selected.value = []
				}

				await nextTick()

				if (!$('.select2-modules').hasClass("select2-hidden-accessible")) {
					$('.select2-modules').select2({
						theme: 'bootstrap-5',
						closeOnSelect: false
					})
					$('#modules_select').on('change.select2', async function (e) {
						let loc_list = $(this).select2('data').map(item => item.id)
						modules_selected.value = loc_list
						config_query.value = []
						for (let el in loc_list) {
							for (let index in modules_list.value) {
								if (modules_list.value[index].name == loc_list[el]) {
									if (modules_list.value[index].request_on_query) {
										config_query.value.push(modules_list.value[index])
									}
									break
								}
							}
						}
					})
				}
			})

			$('#input_select').on('select2:open', function (e) {
				document.querySelector('.select2-search__field').focus();
			})
		}

		async function query_modules() {
			let res = await fetch("/analyzer/misp-modules/get_modules")
			if (await res.status == 200) {
				let loc = await res.json()
				modules_list.value = loc

				await query_misp_attributes()
			} else {
				display_toast(res, true)
			}
		}
		query_modules()

		function checked_attr(arr1) {
			let loc = arr1.includes(attr_selected.value)
			if (!loc && attr_selected.value == 'ip') {
				loc = arr1.includes('ip-dst')
				if (!loc && attr_selected.value == 'ip') {
					loc = arr1.includes('ip-src')
				}
			}
			return loc
		}

		async function submit() {
			isSubmitting.value = true
			let current_query = []
			for (let id of entries.value) {
				let loc_query_res = $("#process-query-" + id).val()
				if (loc_query_res)
					current_query.push(loc_query_res)
			}

			let loc = undefined
			const input_val = $("#input_select").val()
			if (input_val && input_val != "None") {
				loc = input_val
			}

			let loc_modules = undefined
			const modules_val = $("#modules_select").val()
			if (modules_val && modules_val.length) {
				loc_modules = modules_val
			}


			let result_dict = {
				"modules": loc_modules,
				"input": loc,
				"query": current_query,
				"case_id": window._analyzer_case_id || ''
			}

			const res = await fetch('/analyzer/misp-modules/run', {
				headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
				method: "POST",
				body: JSON.stringify(result_dict)
			})
			if (await res.status == 201) {
				let loc = await res.json()
				await nextTick()
				isSubmitting.value = false
				window.location.href = "/analyzer/misp-modules/loading/" + loc['id']
			} else {
				isSubmitting.value = false
				display_toast(res, true)
			}
		}


		return {
			entries,
			misp_attributes_list,
			modules_list,
			attr_selected,
			modules_selected,
			isSubmitting,

			add_entry,
			delete_entry,
			query_misp_attributes,
			checked_attr,
			submit
		}
	},
	template: `
		<div class="analyse-editor-container d-none" style="height: calc(100vh - 470px);">
			<button class="btn btn-primary" @click="submit()" :disabled="isSubmitting || !modules_selected.length">
				<span v-if="isSubmitting" class="spinner-border spinner-border-sm me-2" role="status" aria-hidden="true"></span>
				<span v-if="!isSubmitting">Submit</span>
				<span v-else>Submitting...</span>
			</button>
			<div class="row">
				<div class="col-6" v-if="misp_attributes_list.length">
					<div>
						<h4><i class="fa-solid fa-keyboard fa-sm me-1"></i><span class="section-title">Input attributes</span></h4>
					</div>
					<div>
						<select data-placeholder="Input" class="select2-input form-control" name="input_select" id="input_select">
							<option value="None">--</option>
							<template v-for="attributes in misp_attributes_list">
								<option :value="attributes">[[attributes]]</option>
							</template>
						</select>
					</div>
				</div>
				<template v-if="modules_list.length">
					<div v-if="attr_selected.length" class="col-6">
						<h4><i class="fa-solid fa-puzzle-piece fa-sm me-1"></i><span class="section-title">Analyser modules</span></h4>
						<select data-placeholder="Analyser modules" class="select2-modules form-control" multiple name="modules_select" id="modules_select">
							<template v-for="key in modules_list">
								<option v-if="checked_attr(key.mispattributes.input)" :value="key.name" :title="key.meta.description">[[key.name]]</option>
							</template>
						</select>
					</div>
				</template>
			</div>

		
			<div style="float: right; margin-bottom: 3px;">
				<button @click="add_entry()" class="btn btn-primary" style="margin-top: 10px;" title="Add an entry">
					<i class="fa-solid fa-plus"></i>
				</button>
			</div>
			<template v-for="elem in entries" :key="elem">
				<div class="d-flex align-items-center" style="margin-top: 10px;">
					<input type="text" :id="'process-query-'+elem" placeholder="Enter here..." autofocus class="form-control" style="border-radius: 5px;" />
					<button v-if="entries.length > 1" @click="delete_entry(elem)" class="btn btn-danger btn-sm ms-2" title="Delete this entry">
						<i class="fa-solid fa-trash"></i>
					</button>
				</div>
			</template>
		</div>
	`
}