import {display_toast, message_list, create_message} from '/static/js/toaster.js'
const { ref, nextTick } = Vue
export default {
	delimiters: ['[[', ']]'],
	setup() {
		const cp_entries = ref(1)
		const misp_attributes_list = ref([])
		const modules_list = ref([])
		const config_query = ref([])
		const attr_selected = ref([])

		function add_entry(){
			cp_entries.value += 1
		}
		function delete_entry(){
			if(cp_entries.value > 1)
				cp_entries.value -= 1
		}

		async function query_misp_attributes(){
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
				if(attr_selected.value == 'None' ){
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
						config_query.value = []
						for(let el in loc_list){
							for(let index in modules_list.value){
								if(modules_list.value[index].name == loc_list[el]){
									if(modules_list.value[index].request_on_query){
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

		async function query_modules(){
			let res = await fetch("/analyzer/misp-modules/get_modules")
			let loc = await res.json()
			modules_list.value = loc

			await query_misp_attributes()
		}
		query_modules()

		function checked_attr(arr1){
			let loc = arr1.includes(attr_selected.value)
			if(!loc && attr_selected.value == 'ip'){
				loc = arr1.includes('ip-dst')
				if(!loc && attr_selected.value == 'ip'){
					loc = arr1.includes('ip-src')
				}
			}
			return loc
		}

		async function submit(){
			let current_query = []
			for(let i=1;i<=cp_entries.value;i++){
				let loc_query_res = $("#process-query-"+i).val()
				if(loc_query_res)
					current_query.push(loc_query_res)
			}

			let loc = undefined
			if($("#input_select").val() != "None"){
				loc = $("#input_select").val()
			}

			let loc_modules = undefined
			if($("#modules_select").val().length){
				loc_modules = $("#modules_select").val()
			}


			let result_dict = {
				"modules": loc_modules, 
				"input": loc,
				"query": current_query,
			}

			const res = await fetch('/analyzer/misp-modules/run',{
				headers: { "X-CSRFToken": $("#csrf_token").val(), "Content-Type": "application/json" },
				method: "POST",
				body: JSON.stringify(result_dict)
			})
			if(await res.status == 201){
				let loc = await res.json()
				await nextTick()
				window.location.href="/analyzer/misp-modules/loading/" + loc['id']
			}else{
				display_toast(res, true)
			}
		}
		
		
		return {
			cp_entries,
			misp_attributes_list,
			modules_list,
			attr_selected,

			add_entry,
			delete_entry,
			query_misp_attributes,
			checked_attr,
			submit
		}
	},
	template: `
		<div class="analyse-editor-container d-none" style="margin-top: 50px;">
			<button class="btn btn-primary" @click="submit()">Submit</button>
			<div class="row">
				<div class="col-6" v-if="misp_attributes_list.length">
					<div>
						<h4>Input Attributes</h4>
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
						<h4>Modules</h4>
						<select data-placeholder="Modules" class="select2-modules form-control" multiple name="modules_select" id="modules_select">
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
				<button @click="delete_entry()" class="btn btn-danger" style="margin-top: 10px;" title="Delete an entry">
					<i class="fa-solid fa-trash"></i>
				</button>
			</div>
			<template v-for="elem in cp_entries">
				<div style="margin-top: 10px;">
					<input type="text" :id="'process-query-'+elem" placeholder="Enter here..." autofocus class="form-control" style="border-radius: 5px;" />
				</div>
			</template>
		</div>
	`
}