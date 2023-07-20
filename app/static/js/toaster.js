const { nextTick, ref } = Vue

export const message_list = ref([])

export async function display_toast(res) {
	let loc = await res.json()
	let id = Math.random()
	let message_loc = {"message": loc["message"], "toast_class": loc["toast_class"], "id": id}
	message_list.value.push(message_loc)
	await nextTick()
	const toastLiveExample = document.getElementById('liveToast-'+id)
	const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastLiveExample)
	toastBootstrap.show()
	toastLiveExample.addEventListener('hidden.bs.toast', () => {
		let index = message_list.value.indexOf(message_loc)
		if(index > -1)
			message_list.value.splice(index, 1)
	})
}

export async function prepare_toast(res){
	let loc = await res.json()
	return {"message": loc["message"], "toast_class": loc["toast_class"], "id": Math.random()}
}

export async function display_prepared_toast(message){
	message_list.value.push(message)
	await nextTick()
	const toastLiveExample = document.getElementById('liveToast-'+message.id)
	const toastBootstrap = bootstrap.Toast.getOrCreateInstance(toastLiveExample)
	toastBootstrap.show()
	toastLiveExample.addEventListener('hidden.bs.toast', () => {
		let index = message_list.value.indexOf(message)
		if(index > -1)
			message_list.value.splice(index, 1)
	})
}