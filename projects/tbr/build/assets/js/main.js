/* TrustedBusinessReviews.com — Main JS */

// Mobile menu toggle
document.addEventListener('DOMContentLoaded', () => {
  const hamburger = document.getElementById('hamburger');
  const nav = document.getElementById('mainNav');
  if (hamburger && nav) {
    hamburger.addEventListener('click', () => {
      nav.classList.toggle('open');
      hamburger.classList.toggle('active');
    });
  }

  // Star rating input
  const starContainer = document.getElementById('starRating');
  const ratingInput = document.getElementById('ratingValue');
  if (starContainer) {
    const stars = starContainer.querySelectorAll('.star-input');
    let currentRating = 5;
    
    function setRating(rating) {
      currentRating = rating;
      ratingInput.value = rating;
      stars.forEach((s, i) => {
        s.textContent = i < rating ? '★' : '☆';
        s.classList.toggle('active', i < rating);
      });
    }
    
    stars.forEach(star => {
      star.addEventListener('click', () => setRating(parseInt(star.dataset.rating)));
      star.addEventListener('mouseenter', () => {
        const r = parseInt(star.dataset.rating);
        stars.forEach((s, i) => s.classList.toggle('hover', i < r));
      });
    });
    starContainer.addEventListener('mouseleave', () => {
      stars.forEach(s => s.classList.remove('hover'));
    });
    
    setRating(5);
  }

  // Form submissions (placeholder — needs backend)
  document.querySelectorAll('form').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      alert('Thank you for your submission! This feature will be fully functional soon.');
    });
  });
});
