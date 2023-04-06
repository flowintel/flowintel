$(document).ready(function() {
    get_case_info()
})

function get_case_info(){
    $.getJSON('get_case_info/'+window.location.pathname.split("/").slice(-1), function(data) {
        $('#data-task').empty()
        $('<tr>').append(
            $('<th>'),
            $('<th>').text("Status"),
            $('<th>').text("Title"),
            $('<th>').text("Description"),
            $('<th>').text("Times"),
            $('<th>').text("Tool/Link"),
            $('<th>').text("Assignation"),
            $('<th>').text(""),
            $('<th>').text(""),
            $('<th>').text("")
        ).appendTo('#data-task')

        $("#assign").empty()

        user_permission = data["permission"]
        present_in_case = data["present_in_case"]

        // List of user working in the case
        div_user_case = $("<div>").attr({"class": "dropdown", "id": "dropdown_user_case"}).appendTo($("#assign"))
        div_user_case.append(
            $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"}).text(
                "Orgs"
            )
        )

        ul_org = $("<ul>").attr("class", "dropdown-menu")
        if(!user_permission["read_only"] && present_in_case){
            ul_org.append(
                $("<li>").append(
                    $('<a>').attr({"href": "/case/view/" + data["case"]["id"] + "/add_orgs", "role": "button", "class": "btn btn-primary"}).
                    text("Add Orgs").
                    css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                )
            )
        }

        div_user_case.append(ul_org)
        for (org in data["orgs_in_case"]){
            ul_org.append(
                    $("<li>").append(
                        $("<div>").css({"display": "flex"}).append(
                            $("<button>").attr("class", "dropdown-item").text(data["orgs_in_case"][org]["name"]),
                            $("<button>").attr({"class": "btn btn-danger", "onclick": "remove_org_case(" + data["case"]["id"] + ", " + data["orgs_in_case"][org]["id"] + ")"}).text("delete")
                        )
                    )
                
            )
        }


        tr_completed_line = $("<tr>").appendTo("#data-task")

        // For each task
        $.each(data["tasks"], function(i, item) {
            tasks = data["tasks"][i][0]
            users = data["tasks"][i][1]
            current_user = data["tasks"][i][2]

            // cell to take or remove assignation to a task
            td_take_task = $("<td>").attr("id", "td_task_" + tasks["id"])
            if (!current_user){
                if(!user_permission["read_only"] && present_in_case){
                    td_take_task.append(
                        $('<button>').attr({"class": "btn btn-success", "onclick": "take_task(" + tasks["id"] + ")"}).text("Take Task").css({
                            "padding": "7px",
                            "box-sizing": "border-box",
                            "margin": "0",
                        })
                    )
                }
            }else{
                if(!user_permission["read_only"] && present_in_case){
                    td_take_task.append(
                        $('<button>').attr({"class": "btn btn-success", "onclick": "remove_assign_task(" + tasks["id"] + ")"}).text("Remove assign Task").css({
                            "padding": "7px",
                            "box-sizing": "border-box",
                            "margin": "0",
                        })
                    )
                }
            }
            
            // List of user on a tasks
            div_user = $("<div>").attr({"class": "dropdown", "id": "dropdown_user_" + tasks["id"]})
            if(users.length > 0){
                div_user.append(
                    $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"}).text(
                        "Users"
                    )
                )
                ul_org = $("<ul>").attr("class", "dropdown-menu")
                div_user.append(ul_org)
                for (user in users){
                    ul_org.append(
                        $("<li>").append(
                            $("<button>").attr("class", "dropdown-item").text(users[user]["first_name"] + " " + users[user]["last_name"])
                        )
                    )
                    
                }
            }
            else
                div_user.append(
                    $("<i>").text("No user assigned")
                )

            
            // Task finish
            tr_note = $('<tr>')
            if (tasks["status"] == "3"){
                tr_task = $('<tr>').css({"background-color": "antiquewhite"})
                tr_completed_line.after(tr_note)
                tr_completed_line.after(tr_task)
            }else{
                tr_task = $('<tr>')
                tr_completed_line.before(tr_task)
                tr_completed_line.before(tr_note)
            }

            // Delete a Task
            td_delete = $("<td>")
            if(!user_permission["read_only"] && present_in_case){
                td_delete.append(
                    $('<button>').attr({"class": "btn btn-danger", "onclick": "delete_task(" + tasks["id"] + ")"}).text("Remove").css({
                    "padding": "7px",
                    "box-sizing": "border-box",
                    "margin": "0",
                }))
            }


            // Edit a Task
            td_edit_task = $("<td>")
            if(!user_permission["read_only"] && present_in_case){
                td_edit_task.append(
                    $('<a>').attr({"href": "/case/view/" + data["case"]["id"] + "/edit_task/" + tasks["id"], "role": "button", "class": "btn btn-primary"}).text("Edit").css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                )
            }

            // Status
            td_status = $("<td>")
            button_status = $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "id": "button_" + tasks["id"], "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"})
            if(!user_permission["read_only"] && present_in_case){
                td_status.append(
                    $("<div>").attr({"class": "dropdown", "id": "dropdown_status_" + tasks["id"]}).append(
                        button_status,
                        ul_status = $("<ul>").attr({"class": "dropdown-menu", "id": "dropdown_ul_status_" + tasks["id"]})
                    )
                )
                $.get({
                    url: '/case/get_status/' + tasks["id"],
                    contentType: 'application/json',
                    success: function(data) {
                        status_list =  data["status"]
                        t = data["task"]
                        $("#button_" + t["id"]).text(status_list[t["status"]])

                        $.each(status_list, function(i, item) {
                            if(item != status_list[t["status"]]){
                                $("#dropdown_ul_status_" + t["id"]).append(
                                    $("<li>").append(
                                        $("<button>").attr({"class": "dropdown-item", "onclick": "change_status(" + i + "," + t["id"] + ")"}).text(item)
                                    )
                                )
                            }
                        })
                    }
                })               
                
            }

            // Main tr
            tr_task.append(
                td_status,
                $('<td>').text(tasks["title"]).css({
                    "padding": "7px",
                    "box-sizing": "border-box",
                    "margin": "0",
                }),
                $('<td>').text(tasks["description"]),
                $('<td>').append(
                    $("<div>").text("Creation: " + tasks["creation_date"]),
                    $("<div>").text("Dead Line: " + tasks["dead_line"])
                ),
                $('<td>').append(
                    $("<a>").attr("href", tasks["url"]).text(tasks["url"])
                ),
                $('<td>').append(
                    div_user
                ),
                td_take_task,
                td_edit_task,
                td_delete
            )


            if (tasks['notes']){
                tr_task.prepend($('<td>').append(
                    $("<a>").attr({"class": "btn", "data-bs-toggle": "collapse", "href": "#collapse_"+tasks["id"], "role": "button", "aria-expanded": "false", "aria-controls": "collapse_"+tasks["id"]}).css(
                        {"--bs-btn-border-width": 1}
                    ).append(
                        $("<i>").attr("class", "fas fa-chevron-down")
                    ),
                ))
                if(!user_permission["read_only"] && present_in_case)
                    button_edit = $('<button>').attr({"onclick": "edit_note(" + tasks["id"] + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+tasks["id"]}).append(
                        $('<div>').attr({"hidden":""}).text(tasks["title"]),
                        "Edit"
                    )
                else
                    button_edit=""
                tr_note.append(
                    $('<td>').attr({"colspan": "50"}).append(
                        $('<div>').attr({"class": "collapse", "id": "collapse_"+tasks["id"]}).append(
                            $('<div>').attr({"class": "card card-body", "id": "divNote"+tasks["id"]}).css("max-width", "900px").append(
                                $('<span>').append(
                                    button_edit
                                ).css({"right": "1em", "position": "relative"}),
                                tasks['notes']
                            )
                        )
                    )
                )
            }else{
                tr_task.prepend($('<td>'))
                if(!user_permission["read_only"] && present_in_case){
                    tr_task.append(
                        $("<td>").append(
                            $('<a>').attr({ "role": "button", "class": "btn btn-primary", "data-bs-toggle": "collapse", "href": "#collapse_"+tasks["id"], "aria-expanded": "false", "aria-controls": "collapse_"+tasks["id"]}).
                            text("Add Note").
                            css({
                                "padding": "7px",
                                "box-sizing": "border-box",
                                "margin": "0",
                            })
                    ))
                    tr_note.append(
                        $('<td>').attr({"colspan": "50"}).append(
                            $('<div>').attr({"class": "collapse", "id": "collapse_"+tasks["id"]}).append(
                                $('<div>').attr({"class": "card card-body", "id": "divNote"+tasks["id"]}).css("max-width", "900px").append(
                                    $('<span>').append(
                                        $('<button>').attr({"onclick": "modif_note(" + tasks["id"] + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+tasks["id"]}).append(
                                            $('<div>').attr({"hidden":""}).text(tasks["title"]),
                                            "Create"
                                        ),
                                    ).css({"right": "1em", "position": "relative"}),                                    
                                    $('<textarea>').attr({"id": "note_area_" + tasks["id"], "rows": "5", "cols": "50", "maxlength": "5000"})
                                )
                            )
                        )
                    )
                }
            }
        })
        tr_completed_line.before(
            $("<td>").attr("colspan", "50").append(
                $("<hr>")
            )
        )
    })
}

function complete_task(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/complete_task',
        data: JSON.stringify({"id_task": id.toString()}),
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
            $(".flashes").append(
                $("<div>").attr({"class": "alert alert-danger alert-dismissible fade show message", "data-autohide": "5"}).append(
                    xhr.responseJSON['message'],
                    $("<button>").attr({"type": "button", "class": "btn-close", "data-bs-dismiss": "alert", "aria-label": "Close"})
                )
            )
            flash_messg()
        },
    });
}


function delete_task(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/delete_task',
        data: JSON.stringify({"id_task": id.toString()}),
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
        },
    });
}

function modif_note(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/modif_note',
        data: JSON.stringify({"id_task": id.toString(), "notes": $("#note_area_" + id).val()}),
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
        },
    });
}

function edit_note(id){
   
    $.getJSON('/case/get_note_text?id='+id, function(data) {
        $("#divNote"+id).empty()

        $("#divNote"+id).append(
            $('<span>').append($('<button>').attr({"onclick": "modif_note(" + id + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+id}).text("Save")).css(
                {
                    "right": "1em",
                    "position": "relative"
                }
            ),
            $('<textarea>').attr({"id": "note_area_" + id, "rows": "5", "cols": "50", "maxlength": "5000"}).val(
                data['note']
            )
        )
        
    })
}

function take_task(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/take_task',
        data: JSON.stringify({"task_id": id.toString()}),
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
        },
    });
}


function remove_assign_task(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/remove_assign_task',
        data: JSON.stringify({"task_id": id.toString()}),
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
        },
    });
}


function remove_org_case(case_id, org_id){
    $.get({
        url: '/case/' + case_id + '/remove_org/' + org_id,
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
        },
    });
}


function request_result(message, success){
    if(success){
        $(".flashes").append(
            $("<div>").attr({"class": "alert alert-success alert-dismissible fade show message", "data-autohide": "4"}).append(
                message,
                $("<button>").attr({"type": "button", "class": "btn-close", "data-bs-dismiss": "alert", "aria-label": "Close"})
            )
        )
        get_case_info()
        flash_messg()
    }else{
        $(".flashes").append(
            $("<div>").attr({"class": "alert alert-danger alert-dismissible fade show message", "data-autohide": "4"}).append(
                message,
                $("<button>").attr({"type": "button", "class": "btn-close", "data-bs-dismiss": "alert", "aria-label": "Close"})
            )
        )
        flash_messg()
    }
}


function flash_messg(){
    $('.message').each((i, el) => {
        const $el = $(el);
        const $xx = $el.find('.close');
        const sec = $el.data('autohide');
        const triggerRemove = () => clearTimeout($el.trigger('remove').T);
    
        $el.one('remove', () => $el.remove());
        $xx.one('click', triggerRemove);
        if (sec) $el.T = setTimeout(triggerRemove, sec * 1000);
      });
}


function change_status(status, task_id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/change_status/' + task_id,
        data: JSON.stringify({"status": status}),
        contentType: 'application/json',
        success: function(data) {
            request_result(data["message"], true)
        },
        error: function(xhr, status, error) {
            request_result(xhr.responseJSON['message'], false)
        },
    });
}


// var tempFn = doT.template("<h1>Here is a sample template {{=it.foo}}</h1>");
// var resultText = tempFn({foo: 'with doT'});
// $("#divNote"+1).append(resultText)


// myClass = "mr-2"
// tempateF = `
// <button
//     id="{{=it.noteId}}"
//     onclick="modif_note({{=it.noteId}})"
//     class="${myClass}"
// >
// <button/>
// `
