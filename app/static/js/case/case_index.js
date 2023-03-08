$(document).ready(function() {
    get_case()
})

function get_case(){
    $.getJSON('case/get_cases', function(data) {
        $("#case-card").empty()
        $.each(data, function(i, item) {
            for(let c in item){
                if(item[c]["description"])
                    p_desc = $("<p>").attr({"class": "card-text"}).text(item[c]["description"])
                else
                    p_desc = $("<p>").attr({"class": "card-text"}).append($("<i>").text("No description").css("font-size", "12px"))
                $("<div>").attr({"class": "col mb-3 mb-sm-0"}).append(
                    $("<div>").attr({"class": "card"}).append(
                        $("<div>").attr({"class": "card-body"}).append(
                            $("<h5>").attr({"class": "card-title"}).text(item[c]["title"]),
                            p_desc,
                            $("<a>").attr({"href": "/case/view/"+ item[c]["id"], "class": "btn btn-primary"}).text("Consult"),
                            $("<a>").attr({"onclick": 'delete_case(' + item[c]["id"] + ')', "class": "btn btn-danger"}).text("Delete"),
                        ),
                        $("<div>").attr("class", "card-footer").append(
                            $("<small>").attr("class", "text-muted").text("Last updated " + item[c]["last_modif"])
                        )
                    )
                ).appendTo($("#case-card"))
            }
        })
    })
}

function delete_case(id){
    $.post({
        headers: { "X-CSRFToken": $("#csrf_token").val() },
        url: '/case/delete',
        data: JSON.stringify({"id_case": id.toString()}),
        contentType: 'application/json',
        success: function(data) {
            $('#status').empty()
            $('#status').css("color", "green")
            $('#status').text(data['message'])
            get_case()
        },
        error: function(xhr, status, error) {
            $('#status').empty()
            $('#status').css("color", "brown")
            $('#status').text(xhr.responseJSON['message'])
        },
    });
}