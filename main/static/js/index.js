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
        fileInput.addEventListener('change', async (e) => {
            const f = e.target.files[0];
            if (!f) return;
            //zip file before upload
            const zip = new JSZip();
            zip.file(f.name, f);
            const content = await zip.generateAsync({ type: "blob" });
            uploadFile(content, f.name + ".zip");
        });
    }

    // Dashboard behaviors moved from sample.html
    // Dropdown menu functionality
    $('#dropdown-menu').hide();
    $('#menu-toggle').on('click', function(e) {
        e.stopPropagation();
        $('#dropdown-menu').toggle();
    });
    $(document).on('click', function() {
        $('#dropdown-menu').hide();
    });
    $('#dropdown-menu').on('click', function(e) {
        e.stopPropagation();
    });

    // Deactivate modal functionality
    $('#deactivate-btn').on('click', function(e) {
        e.preventDefault();
        $('#deactivate-modal').removeClass('hidden');
    });
    $('#cancel-deactivate').on('click', function() {
        $('#deactivate-modal').addClass('hidden');
    });
    $('#confirm-deactivate').on('click', function() {
        // Submit the deactivate form
        $(this).closest('.dropdown-menu').find('form[action$="deactivate/"]').submit();
    });

    // View toggle functionality
    $('#tile-view-btn').on('click', function() {
        $('#file-list-container')
            .removeClass('flex flex-col')
            .addClass('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6');
        $('.file-item-tile').show();
        $('.file-item-list').hide();
    });
    $('#list-view-btn').on('click', function() {
        $('#file-list-container')
            .removeClass('grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6')
            .addClass('flex flex-col');
        $('.file-item-tile').hide();
        $('.file-item-list').show();
    });
    // Initial state: tile view only
    $('.file-item-list').hide();

    // Storage progress bar calculation
    (function() {
        var $container = $('#storage-container');
        if ($container.length) {
            var used = parseFloat($container.attr('data-used')) || 0;
            var quota = parseFloat($container.attr('data-quota')) || 0;
            var percent = quota > 0 ? (used / quota) * 100 : 0;
            var percentClamped = Math.min(Math.max(percent, 0), 100);
            $('#storage-bar').css('width', percentClamped.toFixed(2) + '%');
            $('#storage-bar').attr('title', 'Used ' + percentClamped.toFixed(2) + '% of total');
            $('#storage-bar').attr('role', 'progressbar');
            $('#storage-bar').attr('aria-valuemin', '0');
            $('#storage-bar').attr('aria-valuemax', '100');
            $('#storage-bar').attr('aria-valuenow', Math.round(percentClamped));
        }
    })();
});