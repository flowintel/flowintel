export default {
	delimiters: ['[[', ']]'],
	emits: ['cases_list'],
	setup(props, {emit}) {
		let show_ongoing = true
		let current_filter = ""
		let asc_desc = true

		async function filter_ongoing(ongoing){
			show_ongoing = ongoing

			if(show_ongoing){
				const res = await fetch('/case/sort_by_ongoing?page=1')
				let loc = await res.json()
				emit('cases_list', loc)
			}else{
				const res = await fetch('/case/sort_by_finished?page=1')
				let loc = await res.json()
				emit('cases_list', loc)
			}
		}

		function sort_by_filter(filter){
			current_filter = filter
			asc_desc_filter()
		}

		async function asc_desc_filter(change=false){
			emit('current_filter', current_filter)
			if(change)
				asc_desc = !asc_desc

			let res
			if (current_filter){
				if(show_ongoing)
					res = await fetch('/case/ongoing?page=1&filter=' + current_filter)
				else
					res = await fetch('/case/finished?page=1&filter=' + current_filter)
				let loc = await res.json()
				if(asc_desc)
					emit('cases_list', loc)
				else{
                    loc["cases"] = loc["cases"].reverse()
					emit('cases_list', loc)
                }
			}
			
		}

		
		return {
			filter_ongoing,
			sort_by_filter,
			asc_desc_filter
		}
	},
	template: `
	<button class="btn btn-primary" type="button" data-bs-toggle="collapse" data-bs-target="#collapsefiltercase" aria-expanded="false" aria-controls="collapsefiltercase">
		filter
	</button>
	<div class="collapse" id="collapsefiltercase">
		<div class="card card-body">
			<div class="d-flex w-100 justify-content-between">
				<div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioStatus" id="radioStatusOngoing" @click="filter_ongoing(true)" checked>
						<label class="form-check-label" for="radioStatusOngoing">Ongoing Cases</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioStatus" id="radioStatusFinished" @click="filter_ongoing(false)">
						<label class="form-check-label" for="radioStatusFinished">Finished Cases</label>
					</div>
				</div>

				<div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOtherTitle" @click="sort_by_filter('title')">
						<label class="form-check-label" for="radioOtherTitle">Title</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOrderAsc" @click="sort_by_filter('last_modif')">
						<label class="form-check-label" for="radioOrderAsc">Last modification</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOtherDeadLine" @click="sort_by_filter('deadline')">
						<label class="form-check-label" for="radioOtherDeadLine">Deadline</label>
					</div>
					<div class="form-check">
						<input class="form-check-input" type="radio" name="radioOther" id="radioOtherStatus" @click="sort_by_filter('status_id')">
						<label class="form-check-label" for="radioOtherStatus">Status</label>
					</div>
				</div>

				<div style="display:flex">
				<span style="margin-right: 10px">Asc</span>
					<div class="form-check form-switch">
						<input class="form-check-input" type="checkbox" role="switch" id="flexSwitchCheckDefault" @click="asc_desc_filter(true)">
						<label class="form-check-label" for="flexSwitchCheckDefault">Desc</label>
					</div>
			  
				</div>
			</div>
		</div>
	</div>
	`
}