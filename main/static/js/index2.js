document.addEventListener('DOMContentLoaded', function() {
  const mobileNavBtn = document.querySelector('.top-nav-mobile-sidebar-toggle');
  const mobileSidebar = document.querySelector('.sidebar-mobile');
  const mobileNavSvg = document.getElementById('side-nav-toggle-svg');
  mobileNavSvg.style.transition = 'transform 0.5s';

  mobileNavBtn.addEventListener('click', toggleSidebar);

  function toggleSidebar() {
    if (mobileSidebar.classList.contains('open')) { 
      // Close the mobile sidebar 
      mobileSidebar.classList.remove('open');
      mobileNavSvg.setAttribute('transform', `rotate(0)`);
    }
    else { // Open the mobile sidebar
      mobileSidebar.classList.toggle('open');
      mobileNavSvg.setAttribute('transform', `rotate(180)`);
    }
  }

  const fullNavBtn = document.querySelector('.top-nav-full-toggle-span');
  const fullNavToggleDiv = document.querySelector('.top-nav-full-toggle-div');
  const fulNavToggleCtr = document.querySelector('.top-nav-full-toggle-div-ctr')

  fullNavBtn.addEventListener('click', () => {
    if (fullNavToggleDiv.classList.contains('hidden')) { 
      // Close the mobile sidebar 
      fullNavToggleDiv.classList.remove('hidden');
      fulNavToggleCtr.classList.remove('hidden');
    }
    else { // Open the mobile sidebar
      fullNavToggleDiv.classList.toggle('hidden');
      fulNavToggleCtr.classList.toggle('hidden');
    }
  });


  const fileInput = document.getElementById('file-input');
  const uploadButton = document.getElementById('upload-button');

  // const fileInfo = document.getElementById('fileInfo');
  // const progressContainer = document.getElementById('progressContainer');
  // const progressBar = document.getElementById('progressBar');

  uploadButton.addEventListener('click', function() {
      console.log('Upload Button clicked');
      fileInput.click();
  });

  // function updateCallbackOnZip(metaData) {
  //   const percent = metaData.percent;
    
  //   setTimeout(function() { 
  //       const percentComplete = (metaData.percent || 0);
  //       progressBar.style.width = percentComplete + '%';      
  //     }, 10);
  // }

  function uploadFile(zipFile, zipFileName) {
    const xhr = new XMLHttpRequest();
    const formData = new FormData();
    formData.append('file', zipFile, zipFileName);

    xhr.open('POST', '/upload/', true); // Replace '/upload' with your server upload URL

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
    console.log(formData);
    xhr.send(formData);
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
