document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-upload');
    // const createModal = document.getElementById('create-modal');

    function uploadFile(zipFile, zipFileName) {
        // Logic to Upload to AFS using SAS URL
        // will take some time  

        // send AJAX Response with file_name value to server
        // redirect with a json with zipFileName
        window.location.href = '/addFile/?file_name=' + encodeURIComponent(zipFileName);
    }


    fileInput.addEventListener('change', async (event) => {
        if (event) {
          event.preventDefault(); 
        }
    
        const file = fileInput.files[0];  
        
        if (file) {
          console.log(`File selected: ${file.name}`);
          file_size_mb = file.size / (1024 * 1024)
          console.log(`File selected: ${file_size_mb} mb`);
    
          const zip = new JSZip();
          zip.file(file.name, file);
    
          // try {
            // progressContainer.style.display = 'block';
            // progressBar.style.width = '0%';
    
            const zippedContent = await zip.generateAsync(
              {type: "blob"},
              // updateCallbackOnZip
            );
    
            // const formData = new FormData();
            // formData.append('file', zippedContent, file.name+'.zip');
    
            // const response = await fetch('/upload/', {
            //     method: 'POST',
            //     headers: {
            //       'X-CSRFToken': csrftoken,
            //     },
            //     body: formData
            // });
            uploadFile(zippedContent, file.name+'.zip');
          // }
          // catch (error) {
          //   console.error("Error zipping or uploading the file:", error);
          //   alert("An error occurred during the upload.");
          // }
          // finally {
          //   // Reset the progress bar after operation is complete
          //   progressBar.style.width = '0%';
          //   progressContainer.style.display = 'none'; // Hide the progress bar
          // }
        }
        else {
          alert('No file selected. Please select a file to upload.');
        }
        
      });
});