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
});