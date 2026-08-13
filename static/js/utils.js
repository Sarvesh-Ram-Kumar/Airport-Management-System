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
