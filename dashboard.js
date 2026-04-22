// ══════════════════════════════════════════════════════════════
// CPRP Dashboard — JavaScript
// ══════════════════════════════════════════════════════════════

// ── State ─────────────────────────────────────────────────────
let currentSection = "overview";
let pages = { profiles: 1 };
let totals = { profiles: 0 };
const PER_PAGE = 20;
let autoRefreshInterval = null;
let autoRefreshEnabled = false;
let searchQuery = "";

// ── Clock ─────────────────────────────────────────────────────
function updateClock() {
  const el = document.getElementById("topbar-clock");
  if (el) el.textContent = new Date().toLocaleTimeString();
}
setInterval(updateClock, 1000);
updateClock();

// ── Toast notifications ───────────────────────────────────────
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  const icons = { success: "✓", error: "✕", info: "ℹ" };
  toast.innerHTML = `<span>${icons[type] || "ℹ"}</span> ${message}`;
  container.appendChild(toast);
  setTimeout(() => {
    toast.style.animation = "toastOut 0.3s ease-in forwards";
    setTimeout(() => toast.remove(), 300);
  }, 3000);
}

// ── Theme toggle ──────────────────────────────────────────────
function toggleTheme() {
  const current = document.documentElement.getAttribute("data-theme");
  const next = current === "light" ? "dark" : "light";
  document.documentElement.setAttribute("data-theme", next);
  localStorage.setItem("cprp-theme", next);
  document.getElementById("theme-icon").textContent = next === "light" ? "☀️" : "🌙";
}
(function initTheme() {
  const saved = localStorage.getItem("cprp-theme") || "dark";
  document.documentElement.setAttribute("data-theme", saved);
  const el = document.getElementById("theme-icon");
  if (el) el.textContent = saved === "light" ? "☀️" : "🌙";
})();

// ── Sidebar collapse ─────────────────────────────────────────
function toggleSidebar() {
  document.querySelector(".sidebar").classList.toggle("collapsed");
}
function toggleMobileSidebar() {
  document.querySelector(".sidebar").classList.toggle("mobile-open");
}

// ── Auto-refresh ──────────────────────────────────────────────
function toggleAutoRefresh() {
  autoRefreshEnabled = !autoRefreshEnabled;
  const sw = document.getElementById("auto-refresh-switch");
  if (sw) sw.classList.toggle("active", autoRefreshEnabled);
  if (autoRefreshEnabled) {
    autoRefreshInterval = setInterval(() => loadCurrentSection(), 30000);
    showToast("Auto-refresh ON (30s)", "info");
  } else {
    clearInterval(autoRefreshInterval);
    showToast("Auto-refresh OFF", "info");
  }
}

// ── Animated counter ──────────────────────────────────────────
function animateCounter(el, target) {
  if (!el || isNaN(target)) { if (el) el.textContent = target; return; }
  const duration = 800;
  const start = parseInt(el.textContent.replace(/,/g, "")) || 0;
  const diff = target - start;
  if (diff === 0) { el.textContent = target.toLocaleString(); return; }
  const startTime = performance.now();
  function step(now) {
    const elapsed = now - startTime;
    const progress = Math.min(elapsed / duration, 1);
    const eased = 1 - Math.pow(1 - progress, 3);
    el.textContent = Math.round(start + diff * eased).toLocaleString();
    if (progress < 1) requestAnimationFrame(step);
  }
  requestAnimationFrame(step);
}

// ── Skeleton HTML ─────────────────────────────────────────────
function skeletonRows(n = 5, cols = 6) {
  let html = "";
  for (let i = 0; i < n; i++) {
    html += '<div class="skeleton-row">';
    for (let j = 0; j < cols; j++) {
      const w = 40 + Math.random() * 80;
      html += `<div class="skeleton skeleton-cell" style="width:${w}px"></div>`;
    }
    html += "</div>";
  }
  return html;
}

// ── Empty state SVG ───────────────────────────────────────────
function emptyState(title, sub) {
  return `<div class="empty-state">
    <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
      <rect x="12" y="20" width="56" height="44" rx="6" stroke="var(--muted)" stroke-width="2" fill="none"/>
      <line x1="20" y1="34" x2="48" y2="34" stroke="var(--border)" stroke-width="2" stroke-linecap="round"/>
      <line x1="20" y1="42" x2="60" y2="42" stroke="var(--border)" stroke-width="2" stroke-linecap="round"/>
      <line x1="20" y1="50" x2="40" y2="50" stroke="var(--border)" stroke-width="2" stroke-linecap="round"/>
      <circle cx="58" cy="18" r="10" fill="var(--accent)" opacity="0.2"/>
      <text x="55" y="22" font-size="12" fill="var(--accent)" text-anchor="middle">?</text>
    </svg>
    <p>${title}</p>
    <p class="empty-sub">${sub}</p>
  </div>`;
}

// ── Error state ───────────────────────────────────────────────
function errorState(msg, retryFn) {
  return `<div class="error-state">
    <p>⚠️ ${msg}</p>
    <button class="btn btn-sm" onclick="${retryFn}">↺ Retry</button>
  </div>`;
}

// ── Navigation ────────────────────────────────────────────────
function showSection(name) {
  document.querySelectorAll(".section").forEach(s => s.classList.remove("active"));
  document.querySelectorAll(".nav-item").forEach(n => n.classList.remove("active"));
  document.getElementById(`section-${name}`).classList.add("active");
  document.querySelectorAll(".nav-item").forEach(n => {
    if (n.getAttribute("data-section") === name) n.classList.add("active");
  });
  const titles = {
    overview: "Overview", profiles: "User Profiles",
    notifications: "Notifications", recommendations: "Recommendations"
  };
  document.getElementById("section-title").textContent = titles[name];
  currentSection = name;
  loadSection(name);
}

function loadCurrentSection() {
  loadSection(currentSection);
}

function loadSection(name) {
  document.getElementById("last-updated").textContent = "Updated: " + new Date().toLocaleTimeString();
  if (name === "overview") loadOverview();
  if (name === "profiles") loadProfiles();
  if (name === "notifications") loadNotifications();
}

// ── Overview ──────────────────────────────────────────────────
async function loadOverview() {
  try {
    const r = await fetch("/api/stats");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();

    animateCounter(document.getElementById("stat-users"), d.total_users || 0);
    animateCounter(document.getElementById("stat-interactions"), d.total_interactions || 0);
    animateCounter(document.getElementById("stat-notifications"), d.total_notifications || 0);
    animateCounter(document.getElementById("stat-active"), d.active_profiles || 0);
    document.getElementById("info-top-cat").textContent = d.top_category || "—";
    document.getElementById("info-top-brand").textContent = d.top_brand || "—";
    showToast("Dashboard refreshed", "success");
  } catch (e) {
    console.error("Stats error:", e);
    showToast("Failed to load stats", "error");
  }

  // Categories
  try {
    const r = await fetch("/api/dashboard/categories");
    const d = await r.json();
    const cats = d.categories || [];
    const max = cats[0]?.count || 1;
    document.getElementById("category-chart").innerHTML = cats.length
      ? cats.map(c => `
        <div class="category-row">
          <span class="cat-name">${c.main_category}</span>
          <div class="cat-bar-bg"><div class="cat-bar-fill" style="width:${((c.count/max)*100).toFixed(0)}%"></div></div>
          <span class="cat-count">${c.count}</span>
        </div>`).join("")
      : emptyState("No categories yet", "Run the Kafka consumer to generate data");
  } catch (e) {
    document.getElementById("category-chart").innerHTML = errorState("Failed to load categories", "loadOverview()");
  }

  // Health check
  loadHealthCheck();
}

async function loadHealthCheck() {
  const panel = document.getElementById("health-panel");
  if (!panel) return;
  try {
    const r = await fetch("/api/health");
    const d = await r.json();
    const apiOk = d.status === "ok";
    const modelOk = d.model_loaded;
    panel.innerHTML = `
      <div class="health-row"><span class="health-label">API Status</span>
        <span class="badge ${apiOk ? 'badge-green' : 'badge-red'}"><span class="dot ${apiOk ? 'dot-green' : 'dot-red'}"></span>${apiOk ? 'Online' : 'Down'}</span></div>
      <div class="health-row"><span class="health-label">ML Model</span>
        <span class="badge ${modelOk ? 'badge-green' : 'badge-red'}"><span class="dot ${modelOk ? 'dot-green' : 'dot-red'}"></span>${modelOk ? 'Loaded' : 'Not loaded'}</span></div>
      <div class="health-row"><span class="health-label">Last Check</span>
        <span class="badge badge-blue">${new Date().toLocaleTimeString()}</span></div>`;
  } catch (e) {
    panel.innerHTML = `<div class="health-row"><span class="health-label">API Status</span>
      <span class="badge badge-red"><span class="dot dot-red"></span>Unreachable</span></div>`;
  }
}

// ── Profiles ──────────────────────────────────────────────────
async function loadProfiles() {
  const page = pages.profiles;
  document.getElementById("profiles-table-body").innerHTML = skeletonRows(8, 7);
  try {
    let url = `/api/dashboard/profiles?page=${page}&per_page=${PER_PAGE}`;
    if (searchQuery) url += `&search=${encodeURIComponent(searchQuery)}`;
    const r = await fetch(url);
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    totals.profiles = d.total || 0;
    document.getElementById("profiles-count").textContent = `${totals.profiles} profiles`;
    document.getElementById("profiles-page-info").textContent =
      `Page ${page} of ${Math.ceil(totals.profiles / PER_PAGE)} · ${totals.profiles} total`;
    document.getElementById("profiles-prev").disabled = page <= 1;
    document.getElementById("profiles-next").disabled = page >= Math.ceil(totals.profiles / PER_PAGE);

    // Update notification badge
    const badge = document.getElementById("nav-badge-profiles");
    if (badge) badge.textContent = totals.profiles;

    if (!d.profiles?.length) {
      document.getElementById("profiles-table-body").innerHTML =
        emptyState("No profiles yet", "Run the Kafka consumer first");
      return;
    }
    document.getElementById("profiles-table-body").innerHTML = `
      <table><thead><tr>
        <th>Core ID</th><th>Category</th><th>Brand</th><th>Price Range</th>
        <th>Interest Score</th><th>Views</th><th>Purchases</th><th>Status</th>
      </tr></thead><tbody>
      ${d.profiles.map(p => `<tr>
        <td class="mono">${p.core_id}</td>
        <td><span style="text-transform:capitalize">${p.main_category}</span></td>
        <td><span style="text-transform:capitalize">${p.brand}</span></td>
        <td class="mono">${p.price_range}</td>
        <td><div class="score-bar">
          <div class="bar-bg"><div class="bar-fill" style="width:${Math.min(p.interest_score*10,100).toFixed(0)}%"></div></div>
          <span class="mono" style="font-size:11px;width:32px">${p.interest_score?.toFixed(1)}</span>
        </div></td>
        <td class="mono">${p.browse_count}</td>
        <td class="mono">${p.purchase_count}</td>
        <td>${p.suppressed
          ? '<span class="badge badge-amber"><span class="dot dot-amber"></span>Suppressed</span>'
          : '<span class="badge badge-green"><span class="dot dot-green"></span>Active</span>'}</td>
      </tr>`).join("")}
      </tbody></table>`;
  } catch (e) {
    document.getElementById("profiles-table-body").innerHTML =
      errorState("Error loading profiles — is the API running?", "loadProfiles()");
  }
}

function changePage(type, delta) {
  pages[type] = Math.max(1, pages[type] + delta);
  if (type === "profiles") loadProfiles();
}

function handleProfileSearch(e) {
  searchQuery = e.target.value.trim();
  pages.profiles = 1;
  clearTimeout(window._searchDebounce);
  window._searchDebounce = setTimeout(() => loadProfiles(), 300);
}

// ── CSV Export ────────────────────────────────────────────────
async function exportProfilesCSV() {
  showToast("Exporting CSV...", "info");
  try {
    const r = await fetch(`/api/dashboard/profiles?page=1&per_page=10000`);
    const d = await r.json();
    if (!d.profiles?.length) { showToast("No data to export", "error"); return; }
    const headers = ["core_id","main_category","brand","price_range","interest_score","browse_count","purchase_count","suppressed"];
    let csv = headers.join(",") + "\n";
    d.profiles.forEach(p => {
      csv += headers.map(h => `"${(p[h]??"").toString().replace(/"/g,'""')}"`).join(",") + "\n";
    });
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url; a.download = `cprp_profiles_${new Date().toISOString().slice(0,10)}.csv`;
    a.click(); URL.revokeObjectURL(url);
    showToast("CSV exported!", "success");
  } catch (e) {
    showToast("Export failed", "error");
  }
}

// ── Notifications ─────────────────────────────────────────────
async function loadNotifications() {
  document.getElementById("notifications-table-body").innerHTML = skeletonRows(5, 6);
  try {
    const r = await fetch("/api/dashboard/notifications");
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    const d = await r.json();
    const notifs = d.notifications || [];
    document.getElementById("notif-count").textContent = `${notifs.length} recent`;

    // Update badge
    const badge = document.getElementById("nav-badge-notif");
    if (badge) badge.textContent = notifs.length;

    if (!notifs.length) {
      document.getElementById("notifications-table-body").innerHTML =
        emptyState("No notifications sent yet", "Run notifications/notify.py");
      return;
    }
    document.getElementById("notifications-table-body").innerHTML = `
      <table><thead><tr>
        <th>ID</th><th>User</th><th>Channel</th><th>Message</th>
        <th>Products</th><th>Status</th><th>Sent At</th>
      </tr></thead><tbody>
      ${notifs.map(n => `<tr>
        <td class="mono">#${n.notification_id}</td>
        <td class="mono">${n.core_id}</td>
        <td><span class="badge badge-blue">${n.channel}</span></td>
        <td style="max-width:180px;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;font-size:12px;color:var(--muted)">${n.message}</td>
        <td style="font-size:12px;color:var(--muted)">${n.product_ids||"—"}</td>
        <td>${n.status==="sent"
          ? '<span class="badge badge-green"><span class="dot dot-green"></span>Sent</span>'
          : '<span class="badge badge-red"><span class="dot dot-red"></span>Failed</span>'}</td>
        <td style="font-size:12px;color:var(--muted)">${n.sent_at?.substring(0,16)||"—"}</td>
      </tr>`).join("")}
      </tbody></table>`;
  } catch (e) {
    document.getElementById("notifications-table-body").innerHTML =
      errorState("Error loading notifications", "loadNotifications()");
  }
}

// ── Recommendations ───────────────────────────────────────────
async function fetchRecommendation() {
  const userId = document.getElementById("rec-user-input").value.trim();
  if (!userId) return;
  document.getElementById("rec-result").innerHTML = skeletonRows(3, 4);
  try {
    const loginRes = await fetch("/api/login", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username: "admin", password: "admin123" })
    });
    const loginData = await loginRes.json();
    const token = loginData.token;
    const r = await fetch(`/api/recommend/${userId}`, {
      headers: { Authorization: `Bearer ${token}` }
    });
    const d = await r.json();
    if (d.suppressed) {
      document.getElementById("rec-result").innerHTML = `
        <div style="padding:16px;background:rgba(245,158,11,0.08);border:1px solid rgba(245,158,11,0.2);border-radius:10px">
          <p style="color:var(--amber);font-size:14px">⚠️ User is in suppression period</p>
          <p style="color:var(--muted);font-size:12px;margin-top:4px">${d.message}</p>
        </div>`;
      return;
    }
    if (!d.recommendations?.length) {
      document.getElementById("rec-result").innerHTML =
        emptyState(d.message || "No recommendations found", "Try a different user ID");
      return;
    }
    document.getElementById("rec-result").innerHTML = `
      <div style="margin-bottom:12px;padding:12px 16px;background:rgba(59,130,246,0.08);border:1px solid rgba(59,130,246,0.2);border-radius:10px">
        <p style="font-size:13px;color:var(--muted)">Top interest:
          <span style="color:var(--text)">${d.top_interest?.category} · ${d.top_interest?.brand} · ${d.top_interest?.price_range}</span>
          &nbsp;·&nbsp; Score: <span class="mono" style="color:var(--accent)">${d.top_interest?.score?.toFixed(1)}</span>
        </p>
      </div>
      <table><thead><tr><th>#</th><th>Category</th><th>Brand</th><th>Price Range</th><th>Hybrid Score</th></tr></thead>
      <tbody>${d.recommendations.map((r,i) => `<tr>
        <td class="mono">${i+1}</td>
        <td style="text-transform:capitalize">${r.main_category}</td>
        <td style="text-transform:capitalize">${r.brand}</td>
        <td class="mono">${r.price_range}</td>
        <td><div class="hybrid-bar-bg"><div class="hybrid-bar-fill" style="width:${Math.min((r.hybrid_score||0)*100,100).toFixed(0)}%"></div></div>
          <span class="mono" style="font-size:11px">${r.hybrid_score?.toFixed(3)||"—"}</span></td>
      </tr>`).join("")}</tbody></table>`;
  } catch (e) {
    document.getElementById("rec-result").innerHTML =
      errorState("Error — is the API running on port 5000?", "fetchRecommendation()");
  }
}

// ── Init ──────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadOverview();
  // Init theme icon
  const saved = localStorage.getItem("cprp-theme") || "dark";
  const el = document.getElementById("theme-icon");
  if (el) el.textContent = saved === "light" ? "☀️" : "🌙";
});
