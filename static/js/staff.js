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
