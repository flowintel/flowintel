$(document).ready(function() {
    get_case_info()
})

function get_case_info(){
    $.getJSON('get_case_info/'+window.location.pathname.split("/").slice(-1), function(data) {
        $('#data').empty()
        $('<tr>').append(
            $('<th>'),
            $('<th>').text("Title"),
            $('<th>').text("Description"),
            $('<th>').text("")
        ).appendTo('#data')

        $("#assign").empty()

        // List of user working in the case
        div_user = $("<div>").attr({"class": "dropdown", "id": "dropdown_user_case"}).appendTo($("#assign"))
        if(data["case_users"].length > 0){
            div_user.append(
                $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"}).text(
                    "Users"
                )
            )
            ul_user = $("<ul>").attr("class", "dropdown-menu")
            div_user.append(ul_user)
            for (user in data["case_users"]){
                ul_user.append(
                    $("<li>").append(
                        $("<button>").attr("class", "dropdown-item").text(data["case_users"][user]["first_name"] + " " + data["case_users"][user]["last_name"])
                    )
                )
                
            }
        }
        else
            div_user.append(
                $("<i>").text("No user assigned")
            )


        // For each task
        $.each(data["tasks"], function(i, item) {
            tasks = data["tasks"][i][0]
            users = data["tasks"][i][1]
            current_user = data["tasks"][i][2]

            // cell to take or remove assignation to a task
            td_take_task = $("<td>").attr("id", "td_task_" + tasks["id"])
            if (!current_user){
                td_take_task.append(
                    $('<button>').attr("onclick", "take_task(" + tasks["id"] + ")").text("Take Task").css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                )
            }else{
                td_take_task.append(
                    $('<button>').attr("onclick", "remove_assign_task(" + tasks["id"] + ")").text("Remove assign Task").css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                )
            }
            
            // List of user on a tasks
            div_user = $("<div>").attr({"class": "dropdown", "id": "dropdown_user_" + tasks["id"]})
            if(users.length > 0){
                div_user.append(
                    $("<button>").attr({"class": "btn btn-secondary dropdown-toggle", "type": "button", "data-bs-toggle": "dropdown", "aria-expanded": "false"}).text(
                        "Users"
                    )
                )
                ul_user = $("<ul>").attr("class", "dropdown-menu")
                div_user.append(ul_user)
                for (user in users){
                    ul_user.append(
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


            $('<tr>').append(
                $('<td>').append(
                    $("<a>").attr({"class": "btn btn-primary", "data-bs-toggle": "collapse", "href": "#collapse_"+tasks["id"], "role": "button", "aria-expanded": "false", "aria-controls": "collapse_"+tasks["id"]}).text("🔽"),
                ),
                $('<td>').text(tasks["title"]).css({
                    "padding": "7px",
                    "box-sizing": "border-box",
                    "margin": "0",
                }),
                $('<td>').text(tasks["description"]),
                td_take_task,
                $('<td>').append(
                    $('<button>').attr("onclick", "delete_task(" + tasks["id"] + ")").text("Remove").css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                ),
                $('<td>').append(
                    div_user
                ),
                $('<td>').append(
                    $("<div>").text(tasks["creation_date"]),
                    $("<div>").text(tasks["dead_line"])
                )
                
            ).appendTo("#data")


            if (tasks['notes']){
                $.getJSON('/case/get_note_markdown?id='+tasks["id"], function(data_note) {
                    $('<tr>').append(
                        $('<td>').attr({"colspan": "5"}).append(
                            $('<div>').attr({"class": "collapse", "id": "collapse_"+tasks["id"]}).append(
                                $('<div>').attr({"class": "card card-body", "id": "divNote"+tasks["id"]}).css("max-width", "900px").append(
                                    $('<span>').append(
                                        $('<button>').attr({"onclick": "edit_note(" + tasks["id"] + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+tasks["id"]}).append(
                                            $('<div>').attr({"hidden":""}).text(tasks["title"]),
                                            "Edit"
                                        ),
                                    ).css({"right": "1em", "position": "relative"}),
                                    data_note['note']
                                )
                            )
                        )
                    ).appendTo("#data")
                })
            }else{
                $('<tr>').append(
                    $('<td>').attr({"colspan": "5"}).append(
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
                ).appendTo("#data")
            }
        })
    })
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
        console.log(data);

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
