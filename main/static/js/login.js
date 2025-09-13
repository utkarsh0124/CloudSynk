// login.js: handles login form submission for SSR of sample.html
$(function() {
    const $form = $('#login-form');
    const $btn = $('#login-btn');
    const $text = $('#login-text');
    const $spinner = $('#login-spinner');
    const $alertContainer = $('#alert-container');
    const $alertMessage = $('#alert-message');

    function showAlert(message, type = 'error') {
        const classes = type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700';
        $alertMessage.attr('class', classes).html(message);
        $alertContainer.show();
        setTimeout(() => $alertContainer.hide(), 5000);
    }

    function hideAlert() {
        $alertContainer.hide();
    }

    function setLoading(isLoading) {
        $btn.prop('disabled', isLoading);
        $text.text(isLoading ? 'Signing In...' : 'Sign In');
        $spinner.toggle(isLoading);
    }

    $form.on('submit', function(e) {
        e.preventDefault();
        hideAlert();
        setLoading(true);
        $.ajax({
            url: '/login/',
            type: 'POST',
            data: new FormData(this),
            processData: false,
            contentType: false,
            success(res) {
                if (res.success) {
                    window.location.href = '/home/';
                } else {
                    showAlert(res.error || 'Invalid credentials');
                    setLoading(false);
                }
            },
            error(xhr) {
                const msg = (xhr.responseJSON && xhr.responseJSON.error) || 'Server error';
                showAlert(msg);
                setLoading(false);
            }
        });
    });

    // Password show/hide
    $('#toggle-password').on('click', function() {
        const $pwd = $('#password');
        const $icon = $(this).find('i');
        if ($pwd.attr('type') === 'password') {
            $pwd.attr('type', 'text');
            $icon.removeClass('fa-eye').addClass('fa-eye-slash');
        } else {
            $pwd.attr('type', 'password');
            $icon.removeClass('fa-eye-slash').addClass('fa-eye');
        }
    });

    // Enter key submission
    $('#username, #password').on('keypress', function(e) {
        if (e.which === 13) {
            $form.submit();
        }
    });

    // Autofocus username
    $('#username').focus();

    // Logout success message
    if (window.location.hash === '#logout') {
        showAlert('You have been successfully logged out.', 'success');
        history.replaceState(null, null, window.location.pathname);
    }
});