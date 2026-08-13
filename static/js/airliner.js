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
