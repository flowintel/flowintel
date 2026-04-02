const { nextTick, ref } = Vue

export const message_list = ref([])

function manage_icon(toast_class){
	let icon = ""
	if(toast_class){
		switch(toast_class){
			case "success-subtle":
				icon = "fas fa-check"
				break
			case "warning-subtle":
				icon = "fas fa-triangle-exclamation"
				break
			case "danger-subtle":
				icon = "fas fa-xmark"
				break
		}
	}
	return icon
}

export async function create_message(message, toast_class, not_hide, icon){
	let id = Math.random()
	
	if(!icon){
		icon = manage_icon(toast_class)
	}
	let message_loc = {"message": message, "toast_class": toast_class, "id": id, "icon": icon}	
	
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

export async function display_toast(res, not_hide=false) {
	let loc
	try {
		loc = await res.json()
	} catch (e) {
		let message = "An unexpected error occurred"
		if (res.status === 413) {
			message = "The uploaded file is too large for the server to accept"
		} else if (res.status) {
			message = "Server returned an error (HTTP " + res.status + ")"
		}
		await create_message(message, "danger-subtle", not_hide)
		return
	}
	
	if (typeof loc["message"] == "object"){
		for(let index in loc["message"]){
			await create_message(loc["message"][index], loc["toast_class"][index], not_hide, loc["icon"])
		}
	}
	else{
		await create_message(loc["message"], loc["toast_class"], not_hide, loc["icon"])
	}
}
