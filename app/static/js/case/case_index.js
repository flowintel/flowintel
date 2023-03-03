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
                            $("<p>").attr({"class": "card-text"}).append(
                                $("<span>").attr({"class": "text-muted"}).text("Last updated 3 mins ago")
                            ),
                        )
                    )
                ).appendTo($("#case-card"))
            }
            // for(i=0; i< 11; i++){
            //     $("<div>").attr({"class": "col mb-3 mb-sm-0"}).append(
            //         $("<div>").attr({"class": "card"}).append(
            //             $("<div>").attr({"class": "card-body"}).append(
            //                 $("<h5>").attr({"class": "card-title"}).append("Title"),
            //                 $("<p>").attr({"class": "card-text"}).append("With supporting text below as a"),
            //                 $("<a>").attr({"href": "/case/view/1", "class": "btn btn-primary"}).append("Go somewhere"),
            //                 $("<p>").attr({"class": "card-text"}).append(
            //                     $("<span>").attr({"class": "text-muted"}).append("Last updated 3 mins ago")
            //                 ),
            //             )
            //         )
            //     ).appendTo($("#case-card"))
            // }
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