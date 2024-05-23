const { nextTick, ref } = Vue

export const message_list = ref([])

export async function create_message(message, toast_class, not_hide){
	let id = Math.random()
	let message_loc = {"message": message, "toast_class": toast_class, "id": id}
	message_list.value.push(message_loc)
	await nextTick()
	const toastLiveExample = document.getElementById('liveToast-'+id)

	if(not_hide){
		toastLiveExample.setAttribute("data-bs-autohide", "false")
	}

	const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastLiveExample)
	toastBootstrap.show()
	toastLiveExample.addEventListener('hidden.bs.toast', () => {
		let index = message_list.value.indexOf(message_loc)
		if(index > -1)
			message_list.value.splice(index, 1)
	})
}

export async function display_toast(res, not_hide=false, toast_class = "") {
	let loc = await res.json()
	let loc_toast = toast_class
	if(!loc_toast) loc_toast = loc["toast_class"]
	
	if (typeof loc["message"] == "object"){
		for(let index in loc["message"]){
			await create_message(loc["message"][index], loc["toast_class"][index], not_hide)
		}
	}
	else
		await create_message(loc["message"], loc_toast, not_hide)
}
