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
	if (!res) {
		await create_message("An unexpected error occurred", "danger-subtle", not_hide)
		return
	}

	let loc = null
	// If caller already passed a plain object with message/toast_class, use it
	if (typeof res === 'object' && (res.message !== undefined || res.toast_class !== undefined || res.icon !== undefined)) {
		loc = res
	} else if (typeof res.json === 'function') {
		try {
			loc = await res.json()
		} catch (e) {
			let message = "An unexpected error occurred"
			if (res && res.status === 413) {
				message = "The uploaded file is too large for the server to accept"
			} else if (res && res.status) {
				message = "Server returned an error (HTTP " + res.status + ")"
			}
			await create_message(message, "danger-subtle", not_hide)
			return
		}
	} else {
		// Fallbacks: if it's a string, show it; otherwise generic error
		if (typeof res === 'string') {
			await create_message(res, "danger-subtle", not_hide)
			return
		}
		await create_message("An unexpected error occurred", "danger-subtle", not_hide)
		return
	}

	if (typeof loc === 'string') {
		await create_message(loc, "danger-subtle", not_hide)
		return
	}

	if (typeof loc["message"] == "object"){
		for(let index in loc["message"]){
			const toastClass = Array.isArray(loc["toast_class"]) ? loc["toast_class"][index] : loc["toast_class"]
			const icon = Array.isArray(loc["icon"]) ? loc["icon"][index] : loc["icon"]
			await create_message(loc["message"][index], toastClass, not_hide, icon)
		}
	}
	else{
		await create_message(loc["message"] || loc, loc["toast_class"] || "danger-subtle", not_hide, loc["icon"])
	}
}
