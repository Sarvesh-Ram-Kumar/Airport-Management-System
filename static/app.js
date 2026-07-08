// ─── UTILITIES ────────────────────────────────────────────

function showView(id) {
    document.querySelectorAll('.view').forEach(v => v.classList.add('hidden'));
    document.getElementById(id).classList.remove('hidden');
}

function showNav(name) {
    document.getElementById('navbar').classList.remove('hidden');
    document.getElementById('nav-welcome').textContent = `Welcome, ${name}`;
}

function hideNav() {
    document.getElementById('navbar').classList.add('hidden');
}

function statusBadge(status) {
    return `<span class="status status-${status}">${status.replace('_', ' ')}</span>`;
}

function toggleAirlinerFields() {
    const role = document.getElementById('signup-role').value;
    const fields = document.getElementById('airliner-fields');
    role === 'airliner' 
        ? fields.classList.remove('hidden') 
        : fields.classList.add('hidden');
}

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

// ─── AIRLINER ─────────────────────────────────────────────

async function requestFlight() {
    const res = await fetch('/api/flights/request', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            flight_no:    document.getElementById('f-flight-no').value,
            aircraft_type: document.getElementById('f-aircraft').value,
            origin:       document.getElementById('f-origin').value,
            destination:  document.getElementById('f-destination').value,
            flight_date:  document.getElementById('f-date').value,
            flight_time:  document.getElementById('f-time').value,
            gate:         document.getElementById('f-gate').value,
            capacity:     document.getElementById('f-capacity').value,
        })
    });
    const data = await res.json();
    const msg  = document.getElementById('flight-msg');

    if (res.ok) {
        msg.textContent = 'Flight requested successfully';
        msg.className   = 'success';
        loadMyFlights();
    } else {
        msg.textContent = data.error;
        msg.className   = 'error';
    }
}

async function loadMyFlights() {
    const res     = await fetch('/api/flights/mine');
    const flights = await res.json();
    const el      = document.getElementById('my-flights');

    el.innerHTML = flights.map(f => `
        <div class="item-card">
            <h3>${f.flight_no} — ${f.origin} → ${f.destination}</h3>
            <p>${f.flight_date} at ${f.flight_time}</p>
            <p>Aircraft: ${f.aircraft_type} | Gate: ${f.gate}</p>
            <p>Capacity: ${f.capacity}</p>
            ${statusBadge(f.status)}
        </div>
    `).join('') || '<p>No flights yet</p>';
}

// ─── STAFF ────────────────────────────────────────────────

async function loadPendingFlights() {
    const res     = await fetch('/api/flights/pending');
    const flights = await res.json();
    const el      = document.getElementById('pending-flights');

    el.innerHTML = flights.map(f => `
        <div class="item-card">
            <h3>${f.flight_no} — ${f.origin} → ${f.destination}</h3>
            <p>${f.airline_name} | ${f.flight_date} at ${f.flight_time}</p>
            <p>Aircraft: ${f.aircraft_type} | Gate: ${f.gate} | Capacity: ${f.capacity}</p>
            ${statusBadge(f.status)}
            <div style="display:flex; gap:8px; margin-top:8px">
                <button onclick="updateStatus(${f.flight_id}, 'approved')">Approve</button>
                <button onclick="updateStatus(${f.flight_id}, 'rejected')" 
                        style="background:#e63946">Reject</button>
            </div>
        </div>
    `).join('') || '<p>No pending flights</p>';
}

async function updateStatus(flightId, status) {
    const res = await fetch('/api/flights/update_status', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flight_id: flightId, status })
    });
    if (res.ok) {
        loadPendingFlights();
        loadAllBookings();
    }
}

async function loadAllBookings() {
    const res      = await fetch('/api/bookings/all');
    const bookings = await res.json();
    const el       = document.getElementById('all-bookings');

    el.innerHTML = bookings.map(b => `
        <div class="item-card">
            <h3>${b.flight_no} — ${b.origin} → ${b.destination}</h3>
            <p>Passenger: ${b.passenger_name} (@${b.username})</p>
            <p>Seat: ${b.seat_no} | ${b.flight_date} at ${b.flight_time}</p>
            <p>Booked: ${b.booked_at}</p>
            ${statusBadge(b.status)}
        </div>
    `).join('') || '<p>No bookings yet</p>';
}

// ─── PASSENGER ────────────────────────────────────────────

async function loadAvailableFlights() {
    const res     = await fetch('/api/flights/available');
    const flights = await res.json();
    const el      = document.getElementById('flights-list');

    el.innerHTML = flights.map(f => `
        <div class="item-card">
            <h3>${f.flight_no} — ${f.origin} → ${f.destination}</h3>
            <p>${f.airline_name} | ${f.flight_date} at ${f.flight_time}</p>
            <p>Gate: ${f.gate} | Seats left: ${f.seats_remaining}</p>
            <input type="text" 
                   id="seat-${f.flight_id}" 
                   placeholder="Seat no (e.g. 12A)"
                   style="margin-top:8px">
            <button onclick="bookSeat(${f.flight_id})" 
                    style="margin-top:8px">Book</button>
        </div>
    `).join('') || '<p>No available flights</p>';
}

async function bookSeat(flightId) {
    const seat_no = document.getElementById(`seat-${flightId}`).value;
    const res = await fetch('/api/bookings/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ flight_id: flightId, seat_no })
    });
    const data = await res.json();

    if (res.ok) {
        loadAvailableFlights();
        loadMyBookings();
    } else {
        alert(data.error);
    }
}

async function loadMyBookings() {
    const res      = await fetch('/api/bookings/mine');
    const bookings = await res.json();
    const el       = document.getElementById('my-bookings');

    el.innerHTML = bookings.map(b => `
        <div class="item-card">
            <h3>${b.flight_no} — ${b.origin} → ${b.destination}</h3>
            <p>${b.airline_name} | ${b.flight_date} at ${b.flight_time}</p>
            <p>Seat: ${b.seat_no} | Gate: ${b.gate}</p>
            ${statusBadge(b.status)}
            ${b.status === 'confirmed' 
                ? `<button onclick="cancelBooking(${b.booking_id})" 
                           style="background:#e63946; margin-top:8px">
                        Cancel
                   </button>` 
                : ''}
        </div>
    `).join('') || '<p>No bookings yet</p>';
}

async function cancelBooking(bookingId) {
    const res = await fetch('/api/bookings/cancel', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ booking_id: bookingId })
    });
    if (res.ok) loadMyBookings();
}