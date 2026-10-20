// ─── PASSENGER ────────────────────────────────────────────

// ─── BANK ─────────────────────────────────────────────────

async function checkBankAccount() {
    const errEl = document.getElementById('bank-check-error');
    const el    = document.getElementById('bank-details');
    errEl.textContent = '';
    el.innerHTML      = '';

    const res = await fetch('/api/bank/check', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            bank_id: document.getElementById('bank-check-id').value,
            pin:     document.getElementById('bank-check-pin').value
        })
    });
    const acc = await res.json();

    if (!res.ok) {
        errEl.textContent = acc.bank_not_found
            ? 'Bank ID not found. You can create an account on the right.'
            : acc.error;
        return;
    }

    el.innerHTML = `
        <p>Holder: ${acc.holder_name} | Balance: ${money(acc.balance)}</p>
        <ul class="txn-list">
            ${acc.transactions.map(t => `
                <li>
                    <span class="txn-${t.txn_type}">
                        ${t.txn_type === 'payment' ? '−' : '+'}${money(t.amount)}
                    </span>
                    ${t.txn_type} for ${t.flight_no} seat ${t.seat_no} — ${t.created_at}
                </li>
            `).join('') || '<li>No transactions yet</li>'}
        </ul>
    `;
}

// flight card that asked for a new account, so its Bank ID can be filled in
let pendingFlightId = null;

function offerCreateBank(flightId) {
    pendingFlightId = flightId;
    const card = document.getElementById('bank-create-card');
    card.scrollIntoView({ behavior: 'smooth' });
    document.getElementById('bank-new-pin').focus();
}

async function createBankAccount() {
    const pin  = document.getElementById('bank-new-pin').value;
    const pin2 = document.getElementById('bank-new-pin2').value;
    const msg  = document.getElementById('bank-create-msg');

    if (pin !== pin2) {
        msg.className   = 'error';
        msg.textContent = 'PINs do not match';
        return;
    }

    const res = await fetch('/api/bank/create', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ pin })
    });
    const data = await res.json();

    msg.className   = res.ok ? 'success' : 'error';
    msg.textContent = res.ok
        ? `${data.message}. Note your Bank ID: ${data.bank_id}`
        : data.error;

    if (res.ok) {
        document.getElementById('bank-new-pin').value  = '';
        document.getElementById('bank-new-pin2').value = '';
        document.getElementById('bank-check-id').value = data.bank_id;

        // send them back to the flight they were paying for
        if (pendingFlightId !== null) {
            const bankInput = document.getElementById(`bank-${pendingFlightId}`);
            if (bankInput) {
                bankInput.value = data.bank_id;
                document.getElementById(`msg-${pendingFlightId}`).innerHTML =
                    '<span class="success">Account created. Enter your PIN and pay.</span>';
                bankInput.scrollIntoView({ behavior: 'smooth' });
            }
            pendingFlightId = null;
        }
    }
}

// ─── FLIGHTS / BOOKINGS ───────────────────────────────────

async function loadAvailableFlights() {
    const res     = await fetch('/api/flights/available');
    const flights = await res.json();
    const el      = document.getElementById('flights-list');

    el.innerHTML = flights.map(f => `
        <div class="item-card">
            <h3>${f.flight_no} — ${f.origin} → ${f.destination}</h3>
            <p>${f.airline_name} | ${f.flight_date} at ${f.flight_time}</p>
            <p>Gate: ${f.gate} | Seats left: ${f.seats_remaining}</p>
            <p>Price: ${money(f.price)}</p>
            <input type="text"
                   id="seat-${f.flight_id}"
                   placeholder="Seat no (e.g. 12A)"
                   style="margin-top:8px">
            <input type="text"
                   id="bank-${f.flight_id}"
                   placeholder="Bank ID">
            <input type="password"
                   id="pin-${f.flight_id}"
                   placeholder="Bank PIN"
                   inputmode="numeric"
                   maxlength="6">
            <button onclick="bookSeat(${f.flight_id})"
                    style="margin-top:8px">Book &amp; Pay ${money(f.price)}</button>
            <div id="msg-${f.flight_id}" class="error"></div>
        </div>
    `).join('') || '<p>No available flights</p>';
}

async function bookSeat(flightId) {
    const msg = document.getElementById(`msg-${flightId}`);
    msg.innerHTML = '';

    const res = await fetch('/api/bookings/book', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            flight_id: flightId,
            seat_no:   document.getElementById(`seat-${flightId}`).value,
            bank_id:   document.getElementById(`bank-${flightId}`).value,
            bank_pin:  document.getElementById(`pin-${flightId}`).value
        })
    });
    const data = await res.json();

    if (res.ok) {
        loadAvailableFlights();
        loadMyBookings();
    } else if (data.bank_not_found) {
        msg.innerHTML = `
            Bank ID not found.
            <button onclick="offerCreateBank(${flightId})"
                    style="margin-top:8px">Create a bank account</button>
        `;
    } else {
        msg.textContent = data.error;
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
            <p>Paid: ${money(b.amount_paid)}${b.bank_id ? ` from bank account ${b.bank_id}` : ''}</p>
            ${statusBadge(b.status)}
            ${b.status === 'confirmed'
                ? `<button onclick="cancelBooking(${b.booking_id})"
                           style="background:#e63946; margin-top:8px">
                        Cancel &amp; Refund
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
    if (res.ok) {
        loadAvailableFlights();
        loadMyBookings();
    } else {
        const data = await res.json();
        alert(data.error);
    }
}
