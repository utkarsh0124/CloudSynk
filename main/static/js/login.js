document.addEventListener('DOMContentLoaded', function() {
    const $ = jQuery; // Ensure jQuery is available

    // Read CSRF token safely
    const csrftokenElem = document.querySelector('[name=csrfmiddlewaretoken]');
    const csrftoken = csrftokenElem ? csrftokenElem.value : '';

    // Note: This project exposes API endpoints under /api/ for XHR calls.
    // Example fetch usage (see README):
    // const csrftoken = document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    // fetch('/api/login/', { method: 'POST', headers: { 'Content-Type': 'application/json', 'Accept': 'application/json', 'X-Requested-With': 'XMLHttpRequest', 'X-CSRFToken': csrftoken }, credentials: 'same-origin', body: JSON.stringify({username, password}) })
    //   .then(r => r.json()).then(console.log)

    // Determine endpoint prefix based on feature flag injected into templates
    const apiPrefix = (window.ENABLE_API_ENDPOINTS) ? '/api' : '';

    // New: Handle login form submission
    $('form[action="/login/"]').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        $.ajax({
            url: apiPrefix + '/login/',
            method: 'POST',
            data: form.serialize(),
            headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' },
            dataType: 'json',
            success: function(response, status, xhr) {
                if (response.success) {
                    window.location.href = response.redirect || '/';
                } else {
                    alert('Login failed: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr, status, error) {
                alert('Login failed: ' + (xhr.responseJSON?.error || 'Server error'));
            }
        });
    });

    // New: Handle logout form submission
    $('form[action="/logout/"]').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        $.ajax({
            url: apiPrefix + '/logout/',
            method: 'POST',
            data: form.serialize(),
            headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' },
            dataType: 'json',
            success: function(response) {
                if (response.success) {
                    window.location.href = '/login/'; // Adjust redirect URL
                } else {
                    alert('Logout failed: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr) {
                alert('Logout failed: ' + (xhr.responseJSON?.error || 'Server error'));
            }
        });
    });

    // New: Handle signup form submission (assumed in signup.html)
    $('form[action="/signup/"]').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        const method = form.attr('method').toUpperCase();
        if (method === 'POST') {
            $.ajax({
                url: apiPrefix + '/signup/',
                method: 'POST',
                data: form.serialize(),
                headers: { 'X-CSRFToken': csrftoken, 'X-Requested-With': 'XMLHttpRequest' },
                dataType: 'json',
                success: function(response) {
                    if (response.success) {
                        window.location.href = '/'; // Adjust redirect URL
                    } else {
                        console.log("Line 77");
                        alert('Signup failed: ' + (response.error || 'Unknown error'));
                    }
                },
                error: function(xhr) {
                    console.error('Signup AJAX error:', xhr.status, xhr.statusText, xhr.responseText);
                    console.log("Line 82");
                    alert('Signup failed: ' + (xhr.responseJSON?.error || 'Server error'));
                }
            });
        }
        else if (method === 'GET') {
            window.location.href = '/signup/';
        } else {
            console.error('Unsupported form method for signup:', method);
        }
    });
});