/**
 * Signup page JavaScript functionality
 * Handles show/hide password functionality and form submission
 */

document.addEventListener('DOMContentLoaded', function() {
    // Show/hide password functionality
    function togglePassword(toggleButtonId, passwordFieldId) {
        const toggleButton = document.getElementById(toggleButtonId);
        const passwordField = document.getElementById(passwordFieldId);
        
        if (!toggleButton || !passwordField) {
            console.warn(`Toggle password elements not found: ${toggleButtonId}, ${passwordFieldId}`);
            return;
        }
        
        const icon = toggleButton.querySelector('i');
        
        toggleButton.addEventListener('click', function() {
            if (passwordField.type === 'password') {
                passwordField.type = 'text';
                icon.classList.remove('fa-eye');
                icon.classList.add('fa-eye-slash');
                toggleButton.setAttribute('aria-label', 'Hide password');
            } else {
                passwordField.type = 'password';
                icon.classList.remove('fa-eye-slash');
                icon.classList.add('fa-eye');
                toggleButton.setAttribute('aria-label', 'Show password');
            }
        });
    }
    
    // Initialize show/hide password for both fields
    togglePassword('toggle-password1', 'password1');
    togglePassword('toggle-password2', 'password2');
    
    // Form submission handling
    const signupForm = document.getElementById('signup-form');
    const signupBtn = document.getElementById('signup-btn');
    const signupText = document.getElementById('signup-text');
    const signupSpinner = document.getElementById('signup-spinner');
    
    if (signupForm && signupBtn) {
        signupForm.addEventListener('submit', function() {
            // Show loading state
            signupBtn.disabled = true;
            if (signupText) signupText.textContent = 'Creating Account...';
            if (signupSpinner) signupSpinner.classList.remove('hidden');
        });
    }
    
    // Password strength validation (optional enhancement)
    const password1 = document.getElementById('password1');
    const password2 = document.getElementById('password2');
    
    if (password1 && password2) {
        // Real-time password matching validation
        function validatePasswordMatch() {
            if (password2.value && password1.value !== password2.value) {
                password2.setCustomValidity('Passwords do not match');
            } else {
                password2.setCustomValidity('');
            }
        }
        
        password1.addEventListener('input', validatePasswordMatch);
        password2.addEventListener('input', validatePasswordMatch);
    }
    
    // AJAX signup and OTP handling
    if (signupForm) {
        signupForm.addEventListener('submit', async function(e) {
            e.preventDefault();
            // Show loading state
            signupBtn.disabled = true;
            if (signupText) signupText.textContent = 'Creating Account...';
            if (signupSpinner) signupSpinner.classList.remove('hidden');

            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            const formData = {
                username: document.getElementById('username').value,
                email: document.getElementById('email').value,
                password1: document.getElementById('password1').value,
                password2: document.getElementById('password2').value
            };
            try {
                const response = await fetch('/signup/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify(formData)
                });
                const data = await response.json();
                if (data.success && data.pending_id) {
                    // Show OTP modal and start 180s timer
                    const otpModal = document.getElementById('otp-modal');
                    otpModal.classList.remove('hidden');
                    // Store pending_id
                    otpModal.dataset.pendingId = data.pending_id;
                    // Initialize timer display and start countdown
                    startResendTimer(180);
                } else {
                    // Show error alert
                    const alertContainer = document.getElementById('alert-container');
                    const alertMessage = document.getElementById('alert-message');
                    alertMessage.textContent = data.error || 'Signup failed';
                    alertContainer.classList.remove('hidden');
                }
            } catch (err) {
                console.error('Signup error', err);
            } finally {
                signupBtn.disabled = false;
                if (signupText) signupText.textContent = 'Sign Up';
                if (signupSpinner) signupSpinner.classList.add('hidden');
            }
        });
    }

    // OTP modal handlers
    const otpModal = document.getElementById('otp-modal');
    const otpSubmit = document.getElementById('otp-submit');
    const otpCancel = document.getElementById('otp-cancel');
    const otpInput = document.getElementById('otp-code');
    const otpError = document.getElementById('otp-error');

    if (otpCancel) {
        otpCancel.addEventListener('click', function() {
            otpModal.classList.add('hidden');
        });
    }

    if (otpSubmit) {
        otpSubmit.addEventListener('click', async function() {
            const code = otpInput.value;
            const pendingId = otpModal.dataset.pendingId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            try {
                const response = await fetch('/signup/verify-otp/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ pending_id: pendingId, code })
                });
                const data = await response.json();
                if (data.success) {
                    window.location.href = '/login/';
                } else {
                    // Determine error message
                    let errMsg = 'Invalid OTP';
                    if (data.error) {
                        if (typeof data.error === 'string') {
                            errMsg = data.error;
                        } else if (Array.isArray(data.error)) {
                            errMsg = data.error.join(', ');
                        } else if (typeof data.error === 'object') {
                            errMsg = Object.values(data.error).flat().join(', ');
                        }
                    }
                    // Append attempts left if provided
                    if (data.attempts_left !== undefined) {
                        if (data.attempts_left > 0) {
                            errMsg += ` (${data.attempts_left} attempts left)`;
                        } else {
                            errMsg = 'Maximum OTP attempts exceeded. Please signup again.';
                        }
                    }
                    // Display error
                    otpError.textContent = errMsg;
                    otpError.classList.remove('hidden');
                    otpError.classList.add('error');
                    // Shake modal to indicate error
                    const modal = document.getElementById('otp-modal');
                    modal.classList.add('error');
                    setTimeout(() => modal.classList.remove('error'), 500);
                }
            } catch (err) {
                console.error('OTP verify error', err);
            }
        });
    }

    // Resend OTP timer
    const otpResend = document.getElementById('otp-resend');
    const resendTimerEl = document.getElementById('resend-timer');
    const resendInfo = document.getElementById('resend-info');
    let resendInterval;

    // Format time in seconds
    function formatTime(sec) {
        return `${sec}s`;
    }

    function startResendTimer(duration) {
        let remaining = duration;
        otpResend.disabled = true;
        resendTimerEl.textContent = formatTime(remaining);
        resendInfo.textContent = '';
        clearInterval(resendInterval);
        resendInterval = setInterval(() => {
            remaining -= 1;
            if (remaining > 0) {
                resendTimerEl.textContent = formatTime(remaining);
            } else {
                clearInterval(resendInterval);
                otpResend.disabled = false;
                resendTimerEl.textContent = '';
                resendInfo.textContent = 'You can resend OTP now';
            }
        }, 1000);
    }

    // Resend OTP click
    if (otpResend) {
        otpResend.addEventListener('click', async () => {
            const pendingId = otpModal.dataset.pendingId;
            const csrfToken = document.querySelector('[name=csrfmiddlewaretoken]').value;
            try {
                const res = await fetch('/signup/resend-otp/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': csrfToken,
                        'Accept': 'application/json'
                    },
                    body: JSON.stringify({ pending_id: pendingId })
                });
                const data = await res.json();
                if (data.success) {
                    resendInfo.textContent = `OTP resent. Attempts used: ${data.resend_count}. Attempts left: ${data.resends_left}.`;
                    startResendTimer(180);
                } else {
                    resendInfo.textContent = data.error || 'Cannot resend OTP yet';
                }
            } catch (err) {
                console.error('Resend OTP error', err);
                resendInfo.textContent = 'Error resending OTP';
            }
        });
    }
});