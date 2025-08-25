document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file-upload');
    const uploadForm = document.getElementById('upload-form');

    // prevent native form submit
    if (uploadForm) {
        uploadForm.addEventListener('submit', function(e) { e.preventDefault(); });
    }

    function getCsrfToken() {
        const input = document.querySelector('[name=csrfmiddlewaretoken]');
        return input ? input.value : null;
    }

    function uploadFile(file, fileName) {
        if (!file) return;
        const csrftoken = getCsrfToken();
        if (fileInput) fileInput.disabled = true;

        const fd = new FormData();
        fd.append('blob_file', file, fileName);
        fd.append('file_name', fileName);

        fetch('/addFile/', {
            method: 'POST',
            body: fd,
            headers: csrftoken ? { 'X-CSRFToken': csrftoken } : {},
            credentials: 'same-origin'
        })
        .then(async res => {
            if (res.ok) { window.location = '/'; return; }
            const data = await res.json().catch(()=>null);
            alert(data?.error || 'Upload failed');
        })
        .catch(err => { console.error('Upload error', err); alert('Upload error'); })
        .finally(() => { if (fileInput) fileInput.disabled = false; });
    }

    if (fileInput) {
        fileInput.addEventListener('change', (e) => {
            const f = e.target.files[0];
            if (!f) return;
            // optionally zip or process file here
            uploadFile(f, f.name);
        });
    }
});