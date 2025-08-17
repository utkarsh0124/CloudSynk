const $ = require('jquery');
const fetchMock = require('jest-fetch-mock');

fetchMock.enableMocks();

describe('Auth Frontend Tests', () => {
    beforeEach(() => {
        fetch.resetMocks();
        document.body.innerHTML = `
            <form class="modal-content animate" action="/auth_login/" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="mock-csrf-token">
                <div class="container">
                    <input type="text" name="username" value="testuser">
                    <input type="password" name="password" value="testpassword123">
                    <button type="submit">Login</button>
                </div>
            </form>
            <form action="/logout/" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="mock-csrf-token">
                <button type="submit" value="Logout">Log Out</button>
            </form>
            <form class="modal-content animate" action="/signup/" method="post">
                <input type="hidden" name="csrfmiddlewaretoken" value="mock-csrf-token">
                <div class="container">
                    <input type="text" name="username" value="testuser">
                    <input type="email" name="email" value="testuser@example.com">
                    <input type="password" name="password1" value="testpassword123">
                    <input type="password" name="password2" value="testpassword123">
                    <button type="submit">Sign Up</button>
                </div>
            </form>
        `;
    });

    test('Successful login form submission', async () => {
        fetch.mockResponseOnce(JSON.stringify({ success: true }));
        const loginForm = $('form[action="/auth_login/"]');
        let submitted = false;
        loginForm.on('submit', (e) => {
            e.preventDefault();
            $.ajax({
                url: loginForm.attr('action'),
                method: 'POST',
                data: loginForm.serialize(),
                headers: { 'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val() },
                success: () => {
                    submitted = true;
                }
            });
        });
        loginForm.submit();
        await new Promise(resolve => setTimeout(resolve, 0));
        expect(submitted).toBe(true);
        expect(fetch).toHaveBeenCalledWith('/auth_login/', expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({ 'X-CSRFToken': 'mock-csrf-token' })
        }));
    });

    test('Failed login with invalid credentials', async () => {
        fetch.mockResponseOnce(JSON.stringify({ error: 'Invalid credentials' }), { status: 400 });
        const loginForm = $('form[action="/auth_login/"]');
        loginForm.find('input[name="password"]').val('wrongpassword');
        let errorHandled = false;
        loginForm.on('submit', (e) => {
            e.preventDefault();
            $.ajax({
                url: loginForm.attr('action'),
                method: 'POST',
                data: loginForm.serialize(),
                headers: { 'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val() },
                error: () => {
                    errorHandled = true;
                }
            });
        });
        loginForm.submit();
        await new Promise(resolve => setTimeout(resolve, 0));
        expect(errorHandled).toBe(true);
        expect(fetch).toHaveBeenCalledWith('/auth_login/', expect.any(Object));
    });

    test('Successful logout form submission', async () => {
        fetch.mockResponseOnce(JSON.stringify({ success: true }));
        const logoutForm = $('form[action="/logout/"]');
        let submitted = false;
        logoutForm.on('submit', (e) => {
            e.preventDefault();
            $.ajax({
                url: logoutForm.attr('action'),
                method: 'POST',
                data: logoutForm.serialize(),
                headers: { 'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val() },
                success: () => {
                    submitted = true;
                }
            });
        });
        logoutForm.submit();
        await new Promise(resolve => setTimeout(resolve, 0));
        expect(submitted).toBe(true);
        expect(fetch).toHaveBeenCalledWith('/logout/', expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({ 'X-CSRFToken': 'mock-csrf-token' })
        }));
    });

    test('Successful signup form submission', async () => {
        fetch.mockResponseOnce(JSON.stringify({ success: true }));
        const signupForm = $('form[action="/signup/"]');
        let submitted = false;
        signupForm.on('submit', (e) => {
            e.preventDefault();
            $.ajax({
                url: signupForm.attr('action'),
                method: 'POST',
                data: signupForm.serialize(),
                headers: { 'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val() },
                success: () => {
                    submitted = true;
                }
            });
        });
        signupForm.submit();
        await new Promise(resolve => setTimeout(resolve, 0));
        expect(submitted).toBe(true);
        expect(fetch).toHaveBeenCalledWith('/signup/', expect.objectContaining({
            method: 'POST',
            headers: expect.objectContaining({ 'X-CSRFToken': 'mock-csrf-token' })
        }));
    });

    test('Failed signup with mismatched passwords', async () => {
        fetch.mockResponseOnce(JSON.stringify({ error: 'Passwords do not match' }), { status: 400 });
        const signupForm = $('form[action="/signup/"]');
        signupForm.find('input[name="password2"]').val('differentpassword');
        let errorHandled = false;
        signupForm.on('submit', (e) => {
            e.preventDefault();
            $.ajax({
                url: signupForm.attr('action'),
                method: 'POST',
                data: signupForm.serialize(),
                headers: { 'X-CSRFToken': $('input[name=csrfmiddlewaretoken]').val() },
                error: () => {
                    errorHandled = true;
                }
            });
        });
        signupForm.submit();
        await new Promise(resolve => setTimeout(resolve, 0));
        expect(errorHandled).toBe(true);
        expect(fetch).toHaveBeenCalledWith('/signup/', expect.any(Object));
    });
});