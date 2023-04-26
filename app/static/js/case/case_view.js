export default {
	delimiters: ['[[', ']]'],
	props: {
		msg: String,
		cases_info: Object
	},

	template: `
	<h2>[[ msg || 'No props passed yet' ]]</h2>
	<template v-for="task in cases_info.tasks" :key="task.id">

                <div class="list-group" style="margin-bottom: 20px;" v-if="!task.completed">
                    <div style="display: flex;">                          
                        <a :href="'#collapse'+task.id" class="list-group-item list-group-item-action" data-bs-toggle="collapse" role="button" aria-expanded="false" :aria-controls="'collapse'+task.id">
                            <div class="d-flex w-100 justify-content-between">
                                <h5 class="mb-1">[[task.title]]</h5>
                                <small><i>Changed ${ moment('task.last_modif').fromNow() }</i></small>
                            </div>

                            <div class="d-flex w-100 justify-content-between">
                                <p v-if="task.description" class="card-text">[[ task.description ]]</p>
                                <p v-else class="card-text"><i style="font-size: 12px;">No description</i></p>
        
                                <small v-if="status_info"><span :class="'badge rounded-pill text-bg-'+status_info.status[task.status_id -1].bootstrap_style">[[ status_info.status[task.status_id -1].name ]]</span></small>
                            </div>

                            <div v-if="task.users.length">
                                Users: 
                                <template v-for="user in task.users">
                                    [[user.first_name]] [[user.last_name]],
                                </template>
                            </div>

                            <div v-else>
                                <i>No user assigned</i>
                            </div>
                        </a>
                        <div v-if="!cases_info.permission.read_only && cases_info.present_in_case" style="display: grid;">
                            <button class="btn btn-success btn-sm"  @click="[[complete_task(task)]]"><i class="fa-solid fa-check"></i></button>
                            <button v-if="!task.is_current_user_assigned" class="btn btn-secondary btn-sm"  @click="take_task(task, cases_info.current_user)"><i class="fa-solid fa-hand"></i></button>
                            <button v-else class="btn btn-secondary btn-sm"  @click="remove_assign_task(task, cases_info.current_user)"><i class="fa-solid fa-handshake-slash"></i></button>
                            <a class="btn btn-primary btn-sm" :href="'/case/view/'+cases_info.case.id+'/edit_task/'+task.id" type="button"><i class="fa-solid fa-pen-to-square"></i></a>
                            <button class="btn btn-danger btn-sm"  @click="delete_task(task, cases_info.tasks)"><i class="fa-solid fa-trash"></i></button>
                        </div>
                    </div>

                    
                    <!-- Collapse Part -->
                    <div class="collapse" :id="'collapse'+task.id">
                        <div class="card card-body" style="background-color: whitesmoke;">
                            <div class="d-flex w-100 justify-content-between">
                                <div>
                                    <div>
                                        <h3>Notes</h3>
                                    </div>
                                    <div v-if="task.notes">
                                        <template v-if="edit_mode">
                                            <div>
                                                <button class="btn btn-primary" @click="modif_note(task)" type="button" :id="'note_'+task.id">
                                                    <div hidden>[[task.title]]</div>
                                                    Save
                                                </button>
                                            </div>
                                            <textarea :ref="'ref_note_'+task.id" :id="'note_area_'+task.id" rows="5" cols="30" maxlength="5000" v-html="task.notes"></textarea>
                                        </template>
                                        <template v-else>
                                            <template v-if="!cases_info.permission.read_only && cases_info.present_in_case">
                                                <button class="btn btn-primary" @click="edit_note(task)" type="button" :id="'note_'+task.id">
                                                    <div hidden>[[task.title]]</div>
                                                    Edit
                                                </button>
                                            </template> 
                                            <p v-html="task.notes"></p>
                                        </template>
                                    </div>
                                    <div v-else>
                                        <template v-if="!cases_info.permission.read_only && cases_info.present_in_case">
                                            <div>
                                                <button class="btn btn-primary" @click="modif_note(task)" type="button" :id="'note_'+task.id">
                                                    <div hidden>[[task.title]]</div>
                                                    Create
                                                </button>
                                            </div>
                                            <textarea :ref="'ref_note_'+task.id" :id="'note_area_'+task.id" rows="5" cols="30" maxlength="5000"></textarea>
                                        </template>
                                    </div>
                                </div>

                                <div>
                                    <div>
                                        <h3>Files</h3>
                                    </div>
                                    <div>
                                        <div>
                                            <input class="form-control" type="file" :id="'formFileMultiple'+task.id" multiple/>
                                            <button class="btn btn-primary" @click="add_file(task)">Add</button>
                                        </div>
                                        <br/>
                                        <template v-if="task.files.length">
                                            <template v-for="file in task.files">
                                                <div>
                                                    
                                                    <button class="btn btn-danger" @click="delete_file(file, task)"><i class="fa-solid fa-trash"></i></button>
                                                </div>
                                            </template>
                                        </template>
                                    </div>
                                </div>
                                <div>
                                    <div>
                                        <h3>Change Status</h3>
                                    </div>
                                    <div>
                                        <div class="dropdown" :id="'dropdown_status_'+task.id">
                                            <template v-if="status_info">
                                                <button class="btn btn-secondary dropdown-toggle" :id="'button_'+task.id" type="button" data-bs-toggle="dropdown" aria-expanded="false">[[ status_info.status[task.status_id -1].name ]]</button>
                                                <ul class="dropdown-menu" :id="'dropdown_ul_status_'+task.id">
                                                    <template v-for="status_list in status_info.status">
                                                        <li v-if="status_list.id != task.status_id">
                                                            <button class="dropdown-item" @click="change_status(status_list.id, task)">[[ status_list.name ]]</button>
                                                        </li>
                                                    </template>
                                                </ul>
                                            </template>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>

            </template>
	`
}