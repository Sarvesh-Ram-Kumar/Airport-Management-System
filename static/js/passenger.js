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