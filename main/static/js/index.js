document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-input');
    const uploadButton = document.getElementById('upload-button');
    const createModal = document.getElementById('create-modal');

    uploadButton.addEventListener('click', function() {
        console.log('Upload Button clicked');
        fileInput.click();
    });
  
    function uploadFile(zipFile, zipFileName) {
        const xhr = new XMLHttpRequest();
        const formData = new FormData();
        formData.append('blob_file', zipFile, zipFileName);
    
        xhr.open('POST', '/addFile/', true); // Replace '/upload' with your server upload URL
    
        const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]').value;
        xhr.setRequestHeader('X-CSRFToken', csrftoken);
    
        // xhr.upload.addEventListener('progress', (event) => {
        //   if (event.lengthComputable) {
        //       const percentComplete = (event.loaded / event.total) * 100;
        //       progressContainer.style.display = 'block'; // Show progress bar
        //       progressBar.style.width = percentComplete + '%';
        //   }
        // });
    
        // xhr.onload = () => {
        //     if (xhr.status === 200) {
        //         fileInfo.textContent = 'Upload complete!';
        //     } else {
        //         fileInfo.textContent = 'Upload failed.';
        //     }
        //     // progressBar.style.width = '0'; // Reset the progress bar
        //     // progressContainer.style.display = 'none'; // Hide progress bar
        // };
        console.log("Printing FormData : ")
        for (var pair of formData.entries()) {
            console.log(pair[0]+ ', ' + pair[1]);
        }
        
        xhr.send(formData);
        createModal.classList.add("hidden");  
        // createModal.close();
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