$(document).ready(function () {

    // $(".delete-button").click(function () {
    //     const blobName = $(this).attr("data-blob-name");
    //     console.log(blobName);
    //     const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    //     $.ajax({
    //         type    : "GET",
    //         url     : "/deleteFile/",
    //         data    : {
    //             blob_name           : JSON.stringify(blobName),
    //             csrfmiddlewaretoken : csrftoken
    //         },
    //     });
    // });

    // $("#addFile").submit(function(event) {
    //     // event.preventDefault();

    //     // var formData = $(this).serialize();
    //     const fileName = $("#filename").val();
        
    //     console.log(fileName);

    //     const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;

    //     // Submit the form
    //     $.ajax({
    //         type    : "POST",
    //         url     : "/addFile/",
    //         data    : {
    //             fileName            : JSON.stringify(fileName),
    //             csrfmiddlewaretoken : csrftoken
    //         },
    //         success: function (response) {
    //             //Handle the success response here
    //             console.log("add blob AJAX")
    //         },
    //         error: function (xhr, status, error) {
    //             // Handle errors here
    //             console.error(error);
    //         }
    //     });
    // });

// let selectedBlobs = [];

// $("#bulk-delete-button").click(function () {
//     if (selectedBlobs.length === 0) {
//     alert("Please select one or more blobs to delete.");
//     return;
//     }

//     if (confirm("Are you sure you want to delete selected blobs?")) {
//     $.ajax({
//         type: "POST",
//         url: "/deleteBlob/",
//         data: {
//             blob_names: JSON.stringify(selectedBlobs),
//             csrfmiddlewaretoken: csrftoken
//         },
//         success: function (response) {
//         // Handle the response from the server (e.g., update the UI)
//         console.log(response);
//         },
//         error: function (xhr, status, error) {
//         // Handle any errors
//         console.error(error);
//         }
//     });
//     }
// });
});

