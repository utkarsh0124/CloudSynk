document.addEventListener('DOMContentLoaded', function() {
    const $ = jQuery; // Ensure jQuery is available

    // New: Handle login form submission
    $('form[action="/auth_login/"]').on('submit', function(e) {
        e.preventDefault();
        const form = $(this);
        $.ajax({
            url: '/auth_login/',
            method: 'POST',
            data: form.serialize(),
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
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
            url: '/logout/',
            method: 'POST',
            data: form.serialize(),
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
            success: function(response) {
                if (response.success) {
                    window.location.href = '/auth_login/'; // Adjust redirect URL
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
        $.ajax({
            url: '/signup/',
            method: 'POST',
            data: form.serialize(),
            headers: { 'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value },
            success: function(response) {
                if (response.success) {
                    window.location.href = '/'; // Adjust redirect URL
                } else {
                    alert('Signup failed: ' + (response.error || 'Unknown error'));
                }
            },
            error: function(xhr) {
                alert('Signup failed: ' + (xhr.responseJSON?.error || 'Server error'));
            }
        });
    });
});