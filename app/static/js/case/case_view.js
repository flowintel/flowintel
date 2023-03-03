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
        $.each(data["tasks"], function(i, item) {            
            $('<tr>').append(
                $('<td>').append(
                    $("<a>").attr({"class": "btn btn-primary", "data-bs-toggle": "collapse", "href": "#collapse_"+data["tasks"][i]["id"], "role": "button", "aria-expanded": "false", "aria-controls": "collapse_"+data["tasks"][i]["id"]}).text("🔽"),
                ),
                $('<td>').text(data["tasks"][i]["title"]).css({
                    "padding": "7px",
                    "box-sizing": "border-box",
                    "margin": "0",
                }),
                $('<td>').text(data["tasks"][i]["description"]),
                $('<td>').append(
                    $('<button>').attr("onclick", "delete_task(" + data["tasks"][i]["id"] + ")").text("Remove").css({
                        "padding": "7px",
                        "box-sizing": "border-box",
                        "margin": "0",
                    })
                ),
                
            ).appendTo("#data")


            if (data["tasks"][i]['notes']){
                $.getJSON('/case/get_note_markdown?id='+data["tasks"][i]["id"], function(data_note) {
                    $('<tr>').append(
                        $('<td>').attr({"colspan": "4"}).append(
                            $('<div>').attr({"class": "collapse", "id": "collapse_"+data["tasks"][i]["id"]}).append(
                                $('<div>').attr({"class": "card card-body", "id": "divNote"+data["tasks"][i]["id"]}).css("max-width", "900px").append(
                                    $('<span>').append(
                                        $('<button>').attr({"onclick": "edit_note(" + data["tasks"][i]["id"] + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+data["tasks"][i]["id"]}).append(
                                            $('<div>').attr({"hidden":""}).text(data["tasks"][i]["title"]),
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
                    $('<td>').attr({"colspan": "4"}).append(
                        $('<div>').attr({"class": "collapse", "id": "collapse_"+data["tasks"][i]["id"]}).append(
                            $('<div>').attr({"class": "card card-body", "id": "divNote"+data["tasks"][i]["id"]}).css("max-width", "900px").append(
                                $('<span>').append(
                                    $('<button>').attr({"onclick": "modif_note(" + data["tasks"][i]["id"] + ")", "type": "button", "class": "btn btn-primary", "id": "note_"+data["tasks"][i]["id"]}).append(
                                        $('<div>').attr({"hidden":""}).text(data["tasks"][i]["title"]),
                                        "Create"
                                    ),
                                ).css({"right": "1em", "position": "relative"}),                                    
                                $('<textarea>').attr({"id": "note_area_" + data["tasks"][i]["id"], "rows": "5", "cols": "50", "maxlength": "5000"})
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

