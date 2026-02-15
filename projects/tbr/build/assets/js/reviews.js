/* TrustedBusinessReviews.com — Review Submission & Dynamic Loading */

(function() {
  'use strict';

  const API_URL = '/api/reviews.php';
  let csrfToken = null;

  // Fetch CSRF token
  async function getCSRF() {
    if (csrfToken) return csrfToken;
    try {
      const res = await fetch(API_URL + '?action=csrf', { credentials: 'same-origin' });
      const data = await res.json();
      csrfToken = data.token;
      return csrfToken;
    } catch (e) {
      console.error('CSRF fetch failed:', e);
      return null;
    }
  }

  // Star rating HTML
  function starsHtml(rating) {
    return '★'.repeat(rating) + '☆'.repeat(5 - rating);
  }

  // Format date
  function formatDate(dateStr) {
    const d = new Date(dateStr);
    return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
  }

  // Escape HTML
  function esc(s) {
    const d = document.createElement('div');
    d.textContent = s;
    return d.innerHTML;
  }

  // Load dynamic reviews for a business
  async function loadReviews(businessSlug) {
    const container = document.getElementById('dynamicReviews');
    if (!container) return;

    try {
      const res = await fetch(API_URL + '?action=get&business=' + encodeURIComponent(businessSlug));
      const data = await res.json();

      if (!data.reviews || data.reviews.length === 0) return;

      // Get IDs of statically rendered reviews to avoid duplicates
      const staticReviews = document.querySelectorAll('.review-card[data-static]');
      const staticSet = new Set();
      staticReviews.forEach(el => {
        // Use author+date combo as dedup key
        const key = (el.dataset.author || '') + '|' + (el.dataset.date || '');
        if (key !== '|') staticSet.add(key);
      });

      let html = '';
      data.reviews.forEach(r => {
        // Skip if already rendered statically
        const key = r.reviewer_name + '|' + r.date.split(' ')[0];
        if (staticSet.has(key)) return;

        html += `<div class="review-card">
          <div class="review-header">
            <span class="reviewer-name">${esc(r.reviewer_name)}</span>
            <span class="stars">${starsHtml(r.rating)}</span>
            <span class="review-date">${formatDate(r.date)}</span>
          </div>
          <div class="review-text"><p>${esc(r.text)}</p></div>
        </div>`;
      });

      if (html) {
        container.innerHTML = html;
      }
    } catch (e) {
      console.error('Failed to load reviews:', e);
    }
  }

  // Handle review form submission
  async function initReviewForm() {
    const form = document.getElementById('reviewForm');
    if (!form) return;

    // Get CSRF token on page load
    await getCSRF();

    form.addEventListener('submit', async function(e) {
      e.preventDefault();

      const btn = form.querySelector('button[type="submit"]');
      const originalText = btn.textContent;
      btn.disabled = true;
      btn.textContent = 'Submitting...';

      // Remove old messages
      const oldMsg = form.querySelector('.form-message');
      if (oldMsg) oldMsg.remove();

      try {
        const token = await getCSRF();
        const formData = new FormData(form);
        const body = {};
        formData.forEach((v, k) => body[k] = v);

        const res = await fetch(API_URL + '?action=submit', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRF-Token': token || ''
          },
          credentials: 'same-origin',
          body: JSON.stringify(body)
        });

        const data = await res.json();

        const msg = document.createElement('div');
        msg.className = 'form-message';

        if (data.success) {
          msg.className += ' form-success';
          msg.innerHTML = '<strong>✓ Thank you!</strong> ' + esc(data.message);
          form.reset();
          // Reset stars
          const starContainer = document.getElementById('starRating');
          if (starContainer) {
            starContainer.querySelectorAll('.star-input').forEach((s, i) => {
              s.textContent = i < 5 ? '★' : '☆';
            });
          }
          document.getElementById('ratingValue').value = '5';
          // Reset CSRF token for next submission
          csrfToken = null;
        } else {
          msg.className += ' form-error';
          msg.innerHTML = '<strong>Error:</strong> ' + esc(data.error || 'Something went wrong');
        }

        form.insertBefore(msg, btn);
      } catch (e) {
        const msg = document.createElement('div');
        msg.className = 'form-message form-error';
        msg.innerHTML = '<strong>Error:</strong> Could not submit review. Please try again.';
        form.insertBefore(msg, btn);
      } finally {
        btn.disabled = false;
        btn.textContent = originalText;
      }
    });
  }

  // Init on DOM ready
  document.addEventListener('DOMContentLoaded', function() {
    // Load dynamic reviews if on a business page
    const businessSlugInput = document.querySelector('input[name="business_slug"]');
    if (businessSlugInput) {
      loadReviews(businessSlugInput.value);
    }
    initReviewForm();
  });
})();
