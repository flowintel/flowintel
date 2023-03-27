$(document).ready(function() {
    get_case_info()
})

function get_case_info(){
    $.getJSON('get_case_info/'+window.location.pathname.split("/").slice(-1), function(data) {
        $('#data-task').empty()
        $('<tr>').append(
            $('<th>'),
            $('<th>').text("Complete"),
            $('<th>').text("Title"),
            $('<th>').text("Description"),
            $('<th>').text(""),
            $('<th>').text(""),
            $('<th>').text("Assignation"),
            $('<th>').text("Times"),
            $('<th>').text("Tool/Link"),
            $('<th>').text("")
        ).appendTo('#data-task')

        $("#assign").empty()

        user_permission = data["permission"]

        // List of user working in the case
        div_user_case = $("<div>").attr({"class": "dropdown", "id": "dropdown_user_case"}).appendTo($("#assign"))
        div_user_case.append(
            $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"}).text(
                "Orgs"
            )
        )

        ul_org = $("<ul>").attr("class", "dropdown-menu")
        if(!user_permission["read_only"]){
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
                    $("<button>").attr("class", "dropdown-item").text(data["orgs_in_case"][org]["name"])
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
                if(!user_permission["read_only"]){
                    td_take_task.append(
                        $('<button>').attr("onclick", "take_task(" + tasks["id"] + ")").text("Take Task").css({
                            "padding": "7px",
                            "box-sizing": "border-box",
                            "margin": "0",
                        })
                    )
                }
            }else{
                if(!user_permission["read_only"]){
                    td_take_task.append(
                        $('<button>').attr("onclick", "remove_assign_task(" + tasks["id"] + ")").text("Remove assign Task").css({
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


            tr_note = $('<tr>')
            if (tasks["completed"]){
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
            if(!user_permission["read_only"]){
                td_delete.append(
                    $('<button>').attr("onclick", "delete_task(" + tasks["id"] + ")").text("Remove").css({
                    "padding": "7px",
                    "box-sizing": "border-box",
                    "margin": "0",
                }))
            }


            // Edit a Task
            td_edit_task = $("<td>")
            if(!user_permission["read_only"]){
                td_edit_task.append(
                    $('<a>').attr({"href": "/case/view/" + data["case"]["id"] + "/edit_task/" + tasks["id"], "role": "button", "class": "btn btn-primary"}).text("Edit").css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                )
            }

            // Complete
            td_complete = $("<td>")
            if(!user_permission["read_only"]){
                td_complete.append($('<input>').attr({"onclick": "complete_task(" + tasks["id"] + ")", "type": "checkbox"}))
            }

            // Main tr
            tr_task.append(
                td_complete,
                $('<td>').text(tasks["title"]).css({
                    "padding": "7px",
                    "box-sizing": "border-box",
                    "margin": "0",
                }),
                $('<td>').text(tasks["description"]),
                td_take_task,
                td_delete,
                $('<td>').append(
                    div_user
                ),
                $('<td>').append(
                    $("<div>").text("Creation: " + tasks["creation_date"]),
                    $("<div>").text("Dead Line: " + tasks["dead_line"])
                ),
                $('<td>').append(
                    $("<a>").attr("href", tasks["url"]).text(tasks["url"])
                ),
                td_edit_task
            )


            if (tasks['notes']){
                tr_task.prepend($('<td>').append(
                    $("<a>").attr({"class": "btn", "data-bs-toggle": "collapse", "href": "#collapse_"+tasks["id"], "role": "button", "aria-expanded": "false", "aria-controls": "collapse_"+tasks["id"]}).css(
                        {"--bs-btn-border-width": 1}
                    ).append(
                        $("<i>").attr("class", "fas fa-chevron-down")
                    ),
                ))
                if(!user_permission["read_only"])
                    button_edit = ('<button>').attr({"onclick": "edit_note(" + tasks["id"] + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+tasks["id"]}).append(
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
                if(!user_permission["read_only"]){
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
            $('#status').empty()
            $('#status').css("color", "green")
            $('#status').text(data['message'])
            get_case_info()
        },
        error: function(xhr, status, error) {
            $('#status').empty()
            $('#status').css("color", "brown")
            $('#status').text(xhr.responseJSON['message'])
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
            $('#status').empty()
            $('#status').css("color", "green")
            $('#status').text(data['message'])
            get_case_info()
        },
        error: function(xhr, status, error) {
            $('#status').empty()
            $('#status').css("color", "brown")
            $('#status').text(xhr.responseJSON['message'])
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
            $('#status').empty()
            $('#status').css("color", "green")
            $('#status').text(data['message'])
            get_case_info()
        },
        error: function(xhr, status, error) {
            $('#status').empty()
            $('#status').css("color", "brown")
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
            $('#status').empty()
            $('#status').css("color", "green")
            $('#status').text(data['message'])
            // take_task_after(data, id)
            get_case_info()
        },
        error: function(xhr, status, error) {
            $('#status').empty()
            $('#status').css("color", "brown")
            $('#status').text(xhr.responseJSON['message'])
        },
    });
}

function take_task_after(data, id){
    $("#dropdown_user_" + id).empty()
    $("#dropdown_user_" + id).append(
        $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"}).text(
            "Users"
        ),
        $("<ul>").attr("class", "dropdown-menu").append(
            $("<li>").append(
                $("<button>").attr("class", "dropdown-item").text(data["user"]["first_name"] + " " + data["user"]["last_name"])
            )
        )
    )
    $("#td_task_" + id).empty()
    
}

function remove_assign_task(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/remove_assign_task',
        data: JSON.stringify({"task_id": id.toString()}),
        contentType: 'application/json',
        success: function(data) {
            $('#status').empty()
            $('#status').css("color", "green")
            $('#status').text(data['message'])
            // take_task_after(data, id)
            get_case_info()
        },
        error: function(xhr, status, error) {
            $('#status').empty()
            $('#status').css("color", "brown")
            $('#status').text(xhr.responseJSON['message'])
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
