// login.js: handles login form submission for SSR of sample.html
$(function() {
    const $form = $('#login-form');
    const $btn = $('#login-btn');
    const $text = $('#login-text');
    const $spinner = $('#login-spinner');
    const $alertContainer = $('#alert-container');
    const $alertMessage = $('#alert-message');
    const $passwordContainer = $('#password-container');
    const $otpInfo = $('#otp-info');
    const $passwordField = $('#password');
    const $loginMethodInput = $('#login_method');

    // Login method selection
    $('.login-method-tab').on('click', function() {
        const method = $(this).data('method');
        
        // Update active state
        $('.login-method-tab').removeClass('active');
        $(this).addClass('active');
        
        // Update hidden input
        $loginMethodInput.val(method);
        
        // Show/hide password field and OTP info
        if (method === 'password') {
            $passwordContainer.show();
            $otpInfo.hide();
            $passwordField.prop('required', true);
            $text.text('Sign In');
        } else {
            $passwordContainer.hide();
            $otpInfo.show();
            $passwordField.prop('required', false);
            $text.text('Send OTP');
        }
        
        hideAlert();
    });

    function showAlert(message, type = 'error') {
        const classes = type === 'success' ? 'bg-green-100 text-green-700' : 'bg-red-100 text-red-700';
        $alertMessage.attr('class', classes).html(message);
        $alertContainer.show();
        setTimeout(() => $alertContainer.hide(), 5000);
    }

    function hideAlert() {
        $alertContainer.hide();
    }

    function setLoading(isLoading, method = 'password') {
        $btn.prop('disabled', isLoading);
        if (method === 'password') {
            $text.text(isLoading ? 'Signing In...' : 'Sign In');
        } else {
            $text.text(isLoading ? 'Sending OTP...' : 'Send OTP');
        }
        $spinner.toggle(isLoading);
    }

    $form.on('submit', function(e) {
        e.preventDefault();
        hideAlert();
        
        const method = $loginMethodInput.val();
        setLoading(true, method);
        
        const formData = {
            username: $('#username').val(),
            login_method: method
        };
        
        // Only include password for password method
        if (method === 'password') {
            formData.password = $('#password').val();
        }
        
        $.ajax({
            url: '/login/',
            type: 'POST',
            data: JSON.stringify(formData),
            contentType: 'application/json',
            headers: {
                'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val(),
                'Accept': 'application/json'
            },
            success(res) {
                if (res.success) {
                    if (res.login_otp_id) {
                        // OTP sent - redirect to verification page
                        showAlert(res.message || 'OTP sent to your email. Redirecting...', 'success');
                        setTimeout(() => {
                            window.location.href = '/login/verify-otp/?login_otp_id=' + res.login_otp_id;
                        }, 1500);
                    } else if (res.redirect_to_home) {
                        // Password login successful - redirect to home
                        showAlert('Login successful! Redirecting...', 'success');
                        setTimeout(() => {
                            window.location.href = '/home/';
                        }, 1000);
                    } else {
                        // Fallback
                        window.location.href = '/home/';
                    }
                } else {
                    showAlert(res.error || 'Login failed');
                    setLoading(false, method);
                }
            },
            error(xhr) {
                const msg = (xhr.responseJSON && xhr.responseJSON.error) || 'Server error';
                showAlert(msg);
                setLoading(false, method);
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