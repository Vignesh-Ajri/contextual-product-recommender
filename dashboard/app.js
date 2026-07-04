// ═══════════════════════════════════════════════════════════
// CPRP Admin Dashboard — App Logic
// ═══════════════════════════════════════════════════════════

const API = 'http://localhost:5000';
let currentTab = 'overview';

// ── Tab Navigation ────────────────────────────────────────

document.querySelectorAll('.nav-item').forEach(item => {
    item.addEventListener('click', (e) => {
        e.preventDefault();
        const tab = item.dataset.tab;
        switchTab(tab);
    });
});

function switchTab(tab) {
    currentTab = tab;

    // Update nav
    document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
    document.querySelector(`[data-tab="${tab}"]`).classList.add('active');

    // Update content
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.getElementById(`tab-${tab}`).classList.add('active');

    // Update title
    const titles = { overview: 'Overview', profiles: 'User Profiles', lifetimes: 'Product Lifetimes', activity: 'Activity Feed' };
    document.getElementById('page-title').textContent = titles[tab] || tab;

    loadCurrentTab();
}

function loadCurrentTab() {
    switch (currentTab) {
        case 'overview':  loadStats();     break;
        case 'profiles':  loadProfiles();  break;
        case 'lifetimes': loadLifetimes(); break;
        case 'activity':  loadActivity();  break;
    }
}

// ── Stats ─────────────────────────────────────────────────

async function loadStats() {
    try {
        const res = await fetch(`${API}/api/admin/stats`);
        const data = await res.json();

        animateValue('stat-users', data.total_users);
        animateValue('stat-email', data.users_with_email);
        animateValue('stat-interactions', data.total_interactions);
        animateValue('stat-profiled', data.profiled_users);
        animateValue('stat-high-interest', data.high_interest_alerts);
        animateValue('stat-suppressed', data.suppressed_profiles);
        animateValue('stat-categories', data.product_categories);
    } catch (err) {
        console.error('Failed to load stats:', err);
    }
}

function animateValue(id, target) {
    const el = document.getElementById(id);
    const start = parseInt(el.textContent) || 0;
    const duration = 400;
    const startTime = performance.now();

    function tick(now) {
        const progress = Math.min((now - startTime) / duration, 1);
        const eased = 1 - Math.pow(1 - progress, 3);
        el.textContent = Math.round(start + (target - start) * eased).toLocaleString();
        if (progress < 1) requestAnimationFrame(tick);
    }
    requestAnimationFrame(tick);
}

// ── Profiles ──────────────────────────────────────────────

async function loadProfiles() {
    try {
        const res = await fetch(`${API}/api/admin/profiles?limit=50`);
        const data = await res.json();
        const tbody = document.getElementById('profiles-body');

        tbody.innerHTML = data.map(p => {
            const scoreClass = p.interest_score >= 3 ? 'score-high' : p.interest_score >= 1.5 ? 'score-mid' : 'score-low';
            const userLabel = p.email || `<span class="user-id" title="${p.core_id}">${p.core_id.substring(0, 8)}…</span>`;
            const suppress = p.suppress_until ? formatDate(p.suppress_until) : '—';

            return `<tr>
                <td>${userLabel}</td>
                <td>${formatCategory(p.main_category)}</td>
                <td>${p.brand}</td>
                <td class="${scoreClass}">${p.interest_score.toFixed(1)}</td>
                <td>${p.browse_count}</td>
                <td>${p.cart_count}</td>
                <td>${p.purchase_count}</td>
                <td>₹${(p.total_spent || 0).toLocaleString()}</td>
                <td>${suppress}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        console.error('Failed to load profiles:', err);
    }
}

// ── Lifetimes ─────────────────────────────────────────────

async function loadLifetimes() {
    try {
        const res = await fetch(`${API}/api/admin/lifetimes`);
        const data = await res.json();
        const tbody = document.getElementById('lifetimes-body');

        tbody.innerHTML = data.map(lt => `
            <tr>
                <td>${formatCategory(lt.main_category)}</td>
                <td>
                    <input type="number" class="lifetime-input" 
                           id="lt-${lt.main_category}" 
                           value="${lt.lifetime_days}" min="1" max="365">
                </td>
                <td style="color: var(--text-dim)">${lt.description || '—'}</td>
                <td>
                    <button class="save-btn" onclick="saveLifetime('${lt.main_category}')">Save</button>
                </td>
            </tr>
        `).join('');
    } catch (err) {
        console.error('Failed to load lifetimes:', err);
    }
}

async function saveLifetime(category) {
    const input = document.getElementById(`lt-${category}`);
    const days = parseInt(input.value);
    if (!days || days < 1) return;

    try {
        const res = await fetch(`${API}/api/admin/lifetimes/${category}?lifetime_days=${days}`, { method: 'PUT' });
        if (res.ok) {
            showToast(`✓ Updated ${formatCategory(category)} to ${days} days`);
        } else {
            showToast('✗ Failed to update');
        }
    } catch (err) {
        showToast('✗ Network error');
    }
}

// ── Activity Feed ─────────────────────────────────────────

async function loadActivity() {
    try {
        const res = await fetch(`${API}/api/admin/activity?limit=30`);
        const data = await res.json();
        const tbody = document.getElementById('activity-body');

        tbody.innerHTML = data.map(a => {
            const userLabel = a.email || `<span class="user-id" title="${a.core_id}">${a.core_id.substring(0, 8)}…</span>`;
            const badgeClass = `badge-${a.event_type}`;

            return `<tr>
                <td style="color: var(--text-dim); font-size: 12px">${formatDate(a.event_time)}</td>
                <td>${userLabel}</td>
                <td><span class="badge ${badgeClass}">${a.event_type}</span></td>
                <td>${formatCategory(a.main_category)}</td>
                <td>${a.brand || '—'}</td>
                <td>${a.product_name || '—'}</td>
            </tr>`;
        }).join('');
    } catch (err) {
        console.error('Failed to load activity:', err);
    }
}

// ── Helpers ───────────────────────────────────────────────

function formatCategory(cat) {
    if (!cat) return '—';
    return cat.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
}

function formatDate(iso) {
    if (!iso) return '—';
    const d = new Date(iso);
    const now = new Date();
    const diff = now - d;

    if (diff < 60000) return 'Just now';
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`;

    return d.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' });
}

// ── Toast ─────────────────────────────────────────────────

function showToast(msg) {
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = msg;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2500);
}

// ── Init ──────────────────────────────────────────────────

loadStats();
