// ─── AUTH ─────────────────────────────────────────────────

async function signup() {
    const role = document.getElementById('signup-role').value;
    const body = {
        name:     document.getElementById('signup-name').value,
        username: document.getElementById('signup-username').value,
        password: document.getElementById('signup-password').value,
        role
    };

    if (role === 'airliner') {
        body.airline_name  = document.getElementById('signup-airline-name').value;
        body.license_no    = document.getElementById('signup-license').value;
        body.contact_email = document.getElementById('signup-email').value;
        body.country       = document.getElementById('signup-country').value;
    }

    const res  = await fetch('/api/signup', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(body)
    });
    const data = await res.json();

    if (res.ok) {
        showView('view-login');
    } else {
        document.getElementById('signup-error').textContent = data.error;
    }
}

async function login() {
    const res = await fetch('/api/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            username: document.getElementById('login-username').value,
            password: document.getElementById('login-password').value
        })
    });
    const data = await res.json();

    if (res.ok) {
        showNav(data.name);
        if (data.role === 'staff') {
            showView('view-staff');
            loadPendingFlights();
            loadAllBookings();
        } else if (data.role === 'airliner') {
            showView('view-airliner');
            loadMyFlights();
        } else {
            showView('view-passenger');
            loadAvailableFlights();
            loadMyBookings();
        }
    } else {
        document.getElementById('login-error').textContent = data.error;
    }
}

async function logout() {
    await fetch('/api/logout', { method: 'POST' });
    hideNav();
    showView('view-login');
}
