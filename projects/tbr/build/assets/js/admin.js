/* TBR Admin Dashboard */
(function() {
  'use strict';

  const API = '/api/reviews.php';
  const session = localStorage.getItem('tbr_session');

  function authHeaders() {
    return { 'Authorization': 'Bearer ' + (session || ''), 'Content-Type': 'application/json' };
  }

  async function api(action, opts = {}) {
    const params = new URLSearchParams({ action, ...opts.params });
    const fetchOpts = { headers: authHeaders(), credentials: 'same-origin' };
    if (opts.method === 'POST') {
      fetchOpts.method = 'POST';
      fetchOpts.body = JSON.stringify(opts.body || {});
    }
    const res = await fetch(API + '?' + params, fetchOpts);
    if (res.status === 401) { logout(); return null; }
    return res.json();
  }

  function logout() {
    localStorage.removeItem('tbr_session');
    document.cookie = 'tbr_admin_session=; expires=Thu, 01 Jan 1970 00:00:00 UTC; path=/;';
    window.location.href = '/admin/login.html';
  }

  function esc(s) { const d = document.createElement('div'); d.textContent = s || ''; return d.innerHTML; }
  function stars(n) { return '★'.repeat(n) + '☆'.repeat(5 - n); }
  function formatDate(d) { return d ? new Date(d).toLocaleDateString('en-US', { year:'numeric', month:'short', day:'numeric', hour:'2-digit', minute:'2-digit' }) : ''; }
  function slugToName(s) { return (s||'').replace(/-/g, ' ').replace(/\b\w/g, c => c.toUpperCase()); }

  function reviewCard(r, showActions = false) {
    const status = r.status || 'unknown';
    return `<div class="admin-review-card status-${status}">
      <div class="review-meta">
        <span class="name">${esc(r.reviewer_name)}</span>
        <span class="stars">${stars(r.rating || 5)}</span>
        <span class="business">${slugToName(r.business_slug)}</span>
        <span class="date">${formatDate(r.submitted_at)}</span>
        <span class="status-badge ${status}">${status}</span>
        ${r.reviewer_email ? `<span class="email">${esc(r.reviewer_email)}</span>` : ''}
      </div>
      <div class="review-body">${esc(r.text)}</div>
      ${showActions && status === 'pending' ? `<div class="review-actions">
        <button class="btn btn-sm btn-approve" onclick="moderateReview('${r.id}','approved')">✓ Approve</button>
        <button class="btn btn-sm btn-reject" onclick="moderateReview('${r.id}','rejected')">✕ Reject</button>
      </div>` : ''}
      ${!showActions && status !== 'pending' ? `<div class="review-actions">
        ${status === 'rejected' ? `<button class="btn btn-sm btn-approve" onclick="moderateReview('${r.id}','approved')">✓ Approve</button>` : ''}
        ${status === 'approved' ? `<button class="btn btn-sm btn-reject" onclick="moderateReview('${r.id}','rejected')">✕ Reject</button>` : ''}
      </div>` : ''}
    </div>`;
  }

  // Global moderate function
  window.moderateReview = async function(id, status) {
    if (!confirm(`${status === 'approved' ? 'Approve' : 'Reject'} this review?`)) return;
    const data = await api('moderate', { method: 'POST', body: { review_id: id, status } });
    if (data && data.success) {
      loadStats();
      loadPending();
      loadAll();
    } else {
      alert(data?.error || 'Failed to moderate review');
    }
  };

  async function loadStats() {
    const data = await api('stats');
    if (!data) return;
    document.getElementById('statTotal').textContent = data.total || 0;
    document.getElementById('statPending').textContent = data.pending || 0;
    document.getElementById('statApproved').textContent = data.approved || 0;
    document.getElementById('statRejected').textContent = data.rejected || 0;
  }

  async function loadPending() {
    const data = await api('pending');
    const el = document.getElementById('pendingList');
    if (!data || !data.reviews) { el.innerHTML = '<p class="loading">Failed to load</p>'; return; }
    if (data.reviews.length === 0) {
      el.innerHTML = '<div class="empty-state"><div class="emoji">🎉</div><p>No pending reviews!</p></div>';
      return;
    }
    el.innerHTML = data.reviews.map(r => reviewCard(r, true)).join('');
  }

  let allReviewsCache = [];
  async function loadAll(filters = {}) {
    const el = document.getElementById('allList');
    const data = await api('all', { params: filters });
    if (!data || !data.reviews) { el.innerHTML = '<p class="loading">Failed to load</p>'; return; }
    allReviewsCache = data.reviews;
    if (data.reviews.length === 0) {
      el.innerHTML = '<div class="empty-state"><p>No reviews found</p></div>';
      return;
    }
    el.innerHTML = data.reviews.map(r => reviewCard(r, false)).join('');
  }

  // Init
  async function init() {
    // Check auth
    const check = await api('check');
    if (!check || !check.authenticated) { logout(); return; }

    loadStats();
    loadPending();

    // Tabs
    document.querySelectorAll('.tab').forEach(tab => {
      tab.addEventListener('click', function() {
        document.querySelectorAll('.tab').forEach(t => t.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
        this.classList.add('active');
        document.getElementById('tab-' + this.dataset.tab).classList.add('active');
        if (this.dataset.tab === 'all' && allReviewsCache.length === 0) loadAll();
      });
    });

    // Filters
    let filterTimeout;
    function applyFilters() {
      clearTimeout(filterTimeout);
      filterTimeout = setTimeout(() => {
        loadAll({
          status: document.getElementById('filterStatus').value,
          search: document.getElementById('filterSearch').value
        });
      }, 300);
    }
    document.getElementById('filterStatus').addEventListener('change', applyFilters);
    document.getElementById('filterSearch').addEventListener('input', applyFilters);

    // Logout
    document.getElementById('logoutBtn').addEventListener('click', async function() {
      await fetch(API + '?action=logout', { credentials: 'same-origin' });
      logout();
    });
  }

  init();
})();
