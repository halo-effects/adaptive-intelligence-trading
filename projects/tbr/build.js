/**
 * TrustedBusinessReviews.com — Static Site Generator
 * Reads wp_export_data.json and generates full static HTML site
 */
const fs = require('fs');
const path = require('path');

const data = require('./wp_export_data.json');
const BUILD = path.join(__dirname, 'build');

// ── Helpers ──
function mkdirp(dir) { fs.mkdirSync(dir, { recursive: true }); }
function writeFile(filePath, content) {
  mkdirp(path.dirname(filePath));
  fs.writeFileSync(filePath, content, 'utf8');
}
function he(s) { // HTML-encode
  if (!s) return '';
  return s.replace(/&/g,'&amp;').replace(/</g,'&lt;').replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}
function decodeHtmlEntities(s) {
  if (!s) return '';
  return s.replace(/&amp;/g,'&').replace(/&lt;/g,'<').replace(/&gt;/g,'>').replace(/&quot;/g,'"').replace(/&#039;/g,"'");
}
function stripHtml(s) {
  if (!s) return '';
  return s.replace(/<[^>]+>/g, '').replace(/\[.*?\]/g, '').trim();
}
function wpContentToHtml(content) {
  if (!content) return '';
  // Convert WP content: preserve paragraphs, strip shortcodes
  let html = content
    .replace(/\[contact-form-7[^\]]*\]/g, '') // remove CF7 shortcodes
    .replace(/\[.*?\]/g, '') // remove other shortcodes
    .replace(/<iframe[^>]*>.*?<\/iframe>/gi, '') // remove iframes
    .replace(/http:\/\/trustedbusinessreviews\.com/g, 'https://trustedbusinessreviews.com');
  
  // Convert double newlines to paragraphs
  const paras = html.split(/\n\n+/).filter(p => p.trim());
  if (paras.length > 1) {
    html = paras.map(p => {
      p = p.trim();
      if (p.startsWith('<') && !p.startsWith('<a')) return p;
      return `<p>${p.replace(/\n/g, '<br>')}</p>`;
    }).join('\n');
  }
  return html;
}

function starHtml(rating = 5) {
  return '★'.repeat(rating) + '☆'.repeat(5 - rating);
}

function formatDate(dateStr) {
  if (!dateStr) return '';
  const d = new Date(dateStr);
  return d.toLocaleDateString('en-US', { year: 'numeric', month: 'long', day: 'numeric' });
}

// ── Data Processing ──
const postCats = {};
data.post_categories.forEach(pc => {
  if (pc.taxonomy === 'category' && pc.slug !== 'uncategorized') {
    postCats[pc.post_id] = { name: decodeHtmlEntities(pc.name), slug: pc.slug };
  }
});

const postMeta = {};
data.post_meta.forEach(m => {
  if (!postMeta[m.post_id]) postMeta[m.post_id] = {};
  postMeta[m.post_id][m.meta_key] = m.meta_value;
});

const postComments = {};
data.comments.forEach(c => {
  if (c.comment_approved !== '1') return;
  if (!postComments[c.comment_post_ID]) postComments[c.comment_post_ID] = [];
  postComments[c.comment_post_ID].push({
    author: c.comment_author,
    content: c.comment_content,
    date: c.comment_date
  });
});

const businesses = data.posts
  .filter(p => p.post_type === 'post' && p.post_status === 'publish')
  .map(p => {
    const cat = postCats[p.ID];
    const meta = postMeta[p.ID] || {};
    const reviews = (postComments[p.ID] || []).sort((a,b) => new Date(b.date) - new Date(a.date));
    return {
      id: p.ID, title: decodeHtmlEntities(p.post_title), slug: p.post_name,
      content: p.post_content, date: p.post_date,
      category: cat?.slug || 'uncategorized', categoryName: cat?.name || 'Uncategorized',
      vcard: {
        website: meta.vcard_website, phone: meta.vcard_phone, email: meta.vcard_email,
        address: meta.vcard_address, city: meta.vcard_city, state: meta.vcard_state,
        zip: meta.vcard_zip, services: meta.vcard_services
      },
      reviews
    };
  });

const categories = {};
businesses.forEach(b => {
  if (!categories[b.category]) categories[b.category] = { name: b.categoryName, slug: b.category, businesses: [] };
  categories[b.category].businesses.push(b);
});

const pages = data.posts.filter(p => p.post_type === 'page' && p.post_status === 'publish');

// ── Templates ──
const SITE_NAME = 'Trusted Business Reviews';
const SITE_URL = 'https://trustedbusinessreviews.com';

function navHtml(currentPath = '/') {
  const catLinks = Object.values(categories)
    .sort((a,b) => a.name.localeCompare(b.name))
    .map(c => `<li><a href="/${c.slug}/">${he(c.name)}</a></li>`).join('\n              ');
  
  return `<header class="site-header">
    <div class="container">
      <a href="/" class="logo">${SITE_NAME}</a>
      <nav class="main-nav" id="mainNav">
        <ul>
          <li><a href="/"${currentPath === '/' ? ' class="active"' : ''}>Home</a></li>
          <li class="dropdown">
            <a href="#" class="dropdown-toggle">Categories <span class="caret">▾</span></a>
            <ul class="dropdown-menu">
              ${catLinks}
            </ul>
          </li>
          <li><a href="/get-listed/"${currentPath === '/get-listed/' ? ' class="active"' : ''}>Get Listed</a></li>
          <li><a href="/review-policy/"${currentPath === '/review-policy/' ? ' class="active"' : ''}>Review Policy</a></li>
          <li><a href="/contact-us/"${currentPath === '/contact-us/' ? ' class="active"' : ''}>Contact Us</a></li>
        </ul>
      </nav>
      <button class="hamburger" id="hamburger" aria-label="Menu">
        <span></span><span></span><span></span>
      </button>
    </div>
  </header>`;
}

function footerHtml() {
  return `<footer class="site-footer">
    <div class="container">
      <div class="footer-grid">
        <div class="footer-about">
          <h3>${SITE_NAME}</h3>
          <p>Your trusted source for authentic, verified business reviews. We connect consumers with quality businesses they can trust.</p>
        </div>
        <div class="footer-links">
          <h4>Quick Links</h4>
          <ul>
            <li><a href="/">Home</a></li>
            <li><a href="/get-listed/">Get Listed</a></li>
            <li><a href="/review-policy/">Review Policy</a></li>
            <li><a href="/contact-us/">Contact Us</a></li>
          </ul>
        </div>
        <div class="footer-contact">
          <h4>Contact</h4>
          <p><a href="mailto:info@TrustedBusinessReviews.com">info@TrustedBusinessReviews.com</a></p>
        </div>
      </div>
      <div class="footer-bottom">
        <p>&copy; ${new Date().getFullYear()} ${SITE_NAME}. All rights reserved.</p>
      </div>
    </div>
  </footer>`;
}

function pageShell(title, content, { path: pagePath = '/', breadcrumbs = null, schema = null } = {}) {
  const depth = pagePath.split('/').filter(Boolean).length;
  const prefix = depth === 0 ? '.' : '../'.repeat(depth).slice(0, -1);
  
  const bcHtml = breadcrumbs ? `<nav class="breadcrumbs" aria-label="Breadcrumb">
    <ol>
      ${breadcrumbs.map((bc, i) => i < breadcrumbs.length - 1 
        ? `<li><a href="${bc.url}">${he(bc.label)}</a></li>`
        : `<li aria-current="page">${he(bc.label)}</li>`
      ).join('\n      ')}
    </ol>
  </nav>` : '';

  const schemaScript = schema ? `\n  <script type="application/ld+json">${JSON.stringify(schema)}</script>` : '';

  return `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>${he(title)} | ${SITE_NAME}</title>
  <meta name="description" content="${he(title)} - ${SITE_NAME}">
  <link rel="canonical" href="${SITE_URL}${pagePath}">
  <link rel="stylesheet" href="${prefix}/assets/css/style.css">
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap" rel="stylesheet">${schemaScript}
</head>
<body>
  ${navHtml(pagePath)}
  <main>
    ${bcHtml}
    ${content}
  </main>
  ${footerHtml()}
  <script src="${prefix}/assets/js/main.js"></script>
  <script src="${prefix}/assets/js/reviews.js"></script>
</body>
</html>`;
}

// ── Generate Homepage ──
function buildHomepage() {
  const catCards = Object.values(categories)
    .sort((a,b) => a.name.localeCompare(b.name))
    .map(c => {
      const totalReviews = c.businesses.reduce((s,b) => s + b.reviews.length, 0);
      return `<a href="/${c.slug}/" class="category-card">
          <h3>${he(c.name)}</h3>
          <p class="count">${c.businesses.length} business${c.businesses.length !== 1 ? 'es' : ''} · ${totalReviews} review${totalReviews !== 1 ? 's' : ''}</p>
        </a>`;
    }).join('\n        ');

  // Recent listings with most reviews
  const featured = [...businesses]
    .sort((a,b) => b.reviews.length - a.reviews.length)
    .slice(0, 6)
    .map(b => {
      const loc = [b.vcard.city, b.vcard.state].filter(Boolean).join(', ');
      return `<div class="listing-card">
          <div class="listing-header">
            <h3><a href="/${b.category}/${b.slug}/">${he(b.title)}</a></h3>
            <span class="category-badge">${he(b.categoryName)}</span>
          </div>
          <div class="listing-meta">
            <span class="stars" aria-label="5 stars">${starHtml(5)}</span>
            <span class="review-count">${b.reviews.length} review${b.reviews.length !== 1 ? 's' : ''}</span>
            ${loc ? `<span class="location">📍 ${he(loc)}</span>` : ''}
          </div>
          <p class="listing-excerpt">${he(stripHtml(b.content).substring(0, 150))}...</p>
        </div>`;
    }).join('\n        ');

  const content = `
    <section class="hero">
      <div class="container">
        <h1>Find Businesses You Can Trust</h1>
        <p class="hero-sub">Authentic, verified reviews from real customers across the Phoenix metro area and beyond.</p>
      </div>
    </section>

    <section class="categories-section">
      <div class="container">
        <h2>Browse by Category</h2>
        <div class="category-grid">
        ${catCards}
        </div>
      </div>
    </section>

    <section class="featured-section">
      <div class="container">
        <h2>Top Reviewed Businesses</h2>
        <div class="listing-grid">
        ${featured}
        </div>
      </div>
    </section>

    <section class="trust-section">
      <div class="container">
        <h2>Why Trust Our Reviews?</h2>
        <div class="trust-grid">
          <div class="trust-item">
            <span class="trust-icon">✓</span>
            <h3>Verified Reviews</h3>
            <p>Every review is submitted by an authentic customer and verified before publishing.</p>
          </div>
          <div class="trust-item">
            <span class="trust-icon">🔒</span>
            <h3>Privacy Protected</h3>
            <p>Only first names are published. Your email is never shared, sold, or traded.</p>
          </div>
          <div class="trust-item">
            <span class="trust-icon">⚖️</span>
            <h3>Fair & Unbiased</h3>
            <p>Published reviews are never altered. Our strict policy ensures honest representation.</p>
          </div>
        </div>
      </div>
    </section>

    <section class="cta-section">
      <div class="container">
        <h2>Are You a Business Owner?</h2>
        <p>Get your business listed on Trusted Business Reviews and showcase your customer satisfaction.</p>
        <a href="/get-listed/" class="btn btn-primary">Get Listed Today</a>
      </div>
    </section>`;

  const schema = {
    "@context": "https://schema.org",
    "@type": "WebSite",
    "name": SITE_NAME,
    "url": SITE_URL,
    "description": "Authentic, verified business reviews from real customers."
  };

  writeFile(path.join(BUILD, 'index.html'), pageShell('Home', content, { path: '/', schema }));
}

// ── Generate Category Pages ──
function buildCategoryPages() {
  Object.values(categories).forEach(cat => {
    const listings = cat.businesses.map(b => {
      const loc = [b.vcard.city, b.vcard.state].filter(Boolean).join(', ');
      const excerpt = stripHtml(b.content).substring(0, 200);
      return `<div class="listing-card">
          <div class="listing-header">
            <h3><a href="/${cat.slug}/${b.slug}/">${he(b.title)}</a></h3>
          </div>
          <div class="listing-meta">
            <span class="stars">${starHtml(5)}</span>
            <span class="review-count">${b.reviews.length} review${b.reviews.length !== 1 ? 's' : ''}</span>
            ${loc ? `<span class="location">📍 ${he(loc)}</span>` : ''}
          </div>
          ${b.vcard.services ? `<div class="service-tags">${b.vcard.services.split(',').map(s => `<span class="tag">${he(s.trim())}</span>`).join('')}</div>` : ''}
          <p class="listing-excerpt">${he(excerpt)}${excerpt.length >= 200 ? '...' : ''}</p>
          <a href="/${cat.slug}/${b.slug}/" class="btn btn-outline">View Reviews →</a>
        </div>`;
    }).join('\n        ');

    const content = `
    <section class="page-section">
      <div class="container">
        <h1>${he(cat.name)}</h1>
        <p class="category-description">${cat.businesses.length} trusted business${cat.businesses.length !== 1 ? 'es' : ''} in ${he(cat.name)}</p>
        <div class="listing-grid">
        ${listings}
        </div>
      </div>
    </section>`;

    const breadcrumbs = [
      { label: 'Home', url: '/' },
      { label: cat.name, url: `/${cat.slug}/` }
    ];

    writeFile(path.join(BUILD, cat.slug, 'index.html'),
      pageShell(cat.name, content, { path: `/${cat.slug}/`, breadcrumbs }));
  });
}

// ── Generate Business Listing Pages ──
function buildBusinessPages() {
  businesses.forEach(b => {
    const loc = [b.vcard.address, b.vcard.city, b.vcard.state, b.vcard.zip].filter(Boolean).join(', ');
    
    const reviewsHtml = b.reviews.length > 0
      ? b.reviews.map(r => `<div class="review-card" data-static data-author="${he(r.author)}" data-date="${(r.date||'').split(' ')[0]}">
            <div class="review-header">
              <span class="reviewer-name">${he(r.author)}</span>
              <span class="stars">${starHtml(5)}</span>
              <span class="review-date">${formatDate(r.date)}</span>
            </div>
            <div class="review-text">${wpContentToHtml(r.content)}</div>
          </div>`).join('\n          ')
      : '<p class="no-reviews">No reviews yet. Be the first to leave a review!</p>';

    const contactHtml = `<div class="business-contact">
          <h3>Contact Information</h3>
          ${loc ? `<p><strong>Address:</strong> ${he(loc)}</p>` : ''}
          ${b.vcard.phone ? `<p><strong>Phone:</strong> <a href="tel:${b.vcard.phone}">${he(b.vcard.phone)}</a></p>` : ''}
          ${b.vcard.website ? `<p><strong>Website:</strong> <a href="${he(b.vcard.website)}" target="_blank" rel="noopener">${he(b.vcard.website)}</a></p>` : ''}
          ${b.vcard.email ? `<p><strong>Email:</strong> <a href="mailto:${he(b.vcard.email)}">${he(b.vcard.email)}</a></p>` : ''}
        </div>`;

    const servicesHtml = b.vcard.services 
      ? `<div class="service-tags">${b.vcard.services.split(',').map(s => `<span class="tag">${he(s.trim())}</span>`).join('')}</div>`
      : '';

    const content = `
    <section class="page-section business-page">
      <div class="container">
        <div class="business-layout">
          <div class="business-main">
            <h1>${he(b.title)}</h1>
            <div class="business-rating">
              <span class="stars stars-large">${starHtml(5)}</span>
              <span class="rating-summary">${b.reviews.length} review${b.reviews.length !== 1 ? 's' : ''}</span>
            </div>
            ${servicesHtml}
            <div class="business-description">
              ${wpContentToHtml(b.content)}
            </div>
            
            <div class="reviews-section">
              <h2>Customer Reviews</h2>
              ${reviewsHtml}
              <div id="dynamicReviews"></div>
            </div>

            <div class="review-form-section">
              <h2>Write a Review</h2>
              <form id="reviewForm" class="review-form">
                <input type="hidden" name="business_slug" value="${b.slug}">
                <input type="hidden" name="category_slug" value="${b.category}">
                <div class="form-group">
                  <label for="reviewerName">Your First Name *</label>
                  <input type="text" id="reviewerName" name="reviewer_name" required>
                </div>
                <div class="form-group">
                  <label for="reviewerEmail">Your Email (private) *</label>
                  <input type="email" id="reviewerEmail" name="reviewer_email" required>
                  <small>Your email will never be published or shared.</small>
                </div>
                <div class="form-group">
                  <label>Your Rating *</label>
                  <div class="star-rating-input" id="starRating">
                    ${[1,2,3,4,5].map(i => `<span class="star-input" data-rating="${i}">☆</span>`).join('')}
                  </div>
                  <input type="hidden" name="rating" id="ratingValue" value="5">
                </div>
                <div class="form-group">
                  <label for="reviewText">Your Review *</label>
                  <textarea id="reviewText" name="review_text" rows="5" required></textarea>
                </div>
                <button type="submit" class="btn btn-primary">Submit Review</button>
              </form>
            </div>
          </div>
          <aside class="business-sidebar">
            ${contactHtml}
          </aside>
        </div>
      </div>
    </section>`;

    const breadcrumbs = [
      { label: 'Home', url: '/' },
      { label: b.categoryName, url: `/${b.category}/` },
      { label: b.title, url: `/${b.category}/${b.slug}/` }
    ];

    // JSON-LD schema
    const schema = {
      "@context": "https://schema.org",
      "@type": "LocalBusiness",
      "name": b.title,
      "url": `${SITE_URL}/${b.category}/${b.slug}/`,
      ...(loc && { "address": {
        "@type": "PostalAddress",
        ...(b.vcard.address && { "streetAddress": b.vcard.address }),
        ...(b.vcard.city && { "addressLocality": b.vcard.city }),
        ...(b.vcard.state && { "addressRegion": b.vcard.state }),
        ...(b.vcard.zip && { "postalCode": b.vcard.zip }),
        "addressCountry": "US"
      }}),
      ...(b.vcard.phone && { "telephone": b.vcard.phone }),
      ...(b.vcard.website && { "url": b.vcard.website }),
      ...(b.reviews.length > 0 && {
        "aggregateRating": {
          "@type": "AggregateRating",
          "ratingValue": "5",
          "reviewCount": String(b.reviews.length),
          "bestRating": "5",
          "worstRating": "1"
        },
        "review": b.reviews.map(r => ({
          "@type": "Review",
          "author": { "@type": "Person", "name": r.author },
          "datePublished": r.date?.split(' ')[0],
          "reviewBody": stripHtml(r.content),
          "reviewRating": {
            "@type": "Rating",
            "ratingValue": "5",
            "bestRating": "5",
            "worstRating": "1"
          }
        }))
      })
    };

    writeFile(path.join(BUILD, b.category, b.slug, 'index.html'),
      pageShell(b.title, content, { path: `/${b.category}/${b.slug}/`, breadcrumbs, schema }));
  });
}

// ── Generate Utility Pages ──
function buildUtilityPages() {
  // Review Policy
  const reviewPolicyPage = pages.find(p => p.post_name === 'review-policy');
  if (reviewPolicyPage) {
    const content = `<section class="page-section"><div class="container content-page">
      <h1>Review Policy</h1>
      <div class="page-content">${wpContentToHtml(reviewPolicyPage.post_content)}</div>
    </div></section>`;
    writeFile(path.join(BUILD, 'review-policy', 'index.html'),
      pageShell('Review Policy', content, { 
        path: '/review-policy/',
        breadcrumbs: [{ label: 'Home', url: '/' }, { label: 'Review Policy', url: '/review-policy/' }]
      }));
  }

  // Contact Us
  const contactContent = `<section class="page-section"><div class="container content-page">
    <h1>Contact Us</h1>
    <p>To learn more about Trusted Business Reviews or to have your business reviews featured on our website, please complete the contact form below and a representative will contact you shortly.</p>
    <form class="contact-form" id="contactForm">
      <div class="form-group">
        <label for="contactName">Your Name *</label>
        <input type="text" id="contactName" name="name" required>
      </div>
      <div class="form-group">
        <label for="contactEmail">Your Email *</label>
        <input type="email" id="contactEmail" name="email" required>
      </div>
      <div class="form-group">
        <label for="contactSubject">Subject</label>
        <input type="text" id="contactSubject" name="subject">
      </div>
      <div class="form-group">
        <label for="contactMessage">Message *</label>
        <textarea id="contactMessage" name="message" rows="6" required></textarea>
      </div>
      <button type="submit" class="btn btn-primary">Send Message</button>
    </form>
    <p class="contact-email">Or email us directly at <a href="mailto:info@TrustedBusinessReviews.com">info@TrustedBusinessReviews.com</a></p>
  </div></section>`;
  writeFile(path.join(BUILD, 'contact-us', 'index.html'),
    pageShell('Contact Us', contactContent, {
      path: '/contact-us/',
      breadcrumbs: [{ label: 'Home', url: '/' }, { label: 'Contact Us', url: '/contact-us/' }]
    }));

  // Get Listed
  const getListedContent = `<section class="page-section"><div class="container content-page">
    <h1>Get Listed</h1>
    <p>Want your business featured on Trusted Business Reviews? Complete the form below to apply for a listing.</p>
    <form class="contact-form" id="getListedForm">
      <div class="form-group">
        <label for="bizName">Business Name *</label>
        <input type="text" id="bizName" name="business_name" required>
      </div>
      <div class="form-group">
        <label for="bizContact">Contact Name *</label>
        <input type="text" id="bizContact" name="contact_name" required>
      </div>
      <div class="form-group">
        <label for="bizEmail">Email *</label>
        <input type="email" id="bizEmail" name="email" required>
      </div>
      <div class="form-group">
        <label for="bizPhone">Phone</label>
        <input type="tel" id="bizPhone" name="phone">
      </div>
      <div class="form-group">
        <label for="bizWebsite">Website</label>
        <input type="url" id="bizWebsite" name="website">
      </div>
      <div class="form-group">
        <label for="bizCategory">Business Category *</label>
        <input type="text" id="bizCategory" name="category" required>
      </div>
      <div class="form-group">
        <label for="bizDescription">Tell us about your business</label>
        <textarea id="bizDescription" name="description" rows="5"></textarea>
      </div>
      <button type="submit" class="btn btn-primary">Submit Application</button>
    </form>
  </div></section>`;
  writeFile(path.join(BUILD, 'get-listed', 'index.html'),
    pageShell('Get Listed', getListedContent, {
      path: '/get-listed/',
      breadcrumbs: [{ label: 'Home', url: '/' }, { label: 'Get Listed', url: '/get-listed/' }]
    }));
}

// ── Generate sitemap.xml ──
function buildSitemap() {
  const urls = [{ loc: '/', priority: '1.0', changefreq: 'weekly' }];
  
  Object.values(categories).forEach(c => {
    urls.push({ loc: `/${c.slug}/`, priority: '0.8', changefreq: 'weekly' });
    c.businesses.forEach(b => {
      urls.push({ loc: `/${c.slug}/${b.slug}/`, priority: '0.7', changefreq: 'monthly' });
    });
  });

  ['/review-policy/', '/contact-us/', '/get-listed/'].forEach(p => {
    urls.push({ loc: p, priority: '0.5', changefreq: 'monthly' });
  });

  const xml = `<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
${urls.map(u => `  <url>
    <loc>${SITE_URL}${u.loc}</loc>
    <changefreq>${u.changefreq}</changefreq>
    <priority>${u.priority}</priority>
  </url>`).join('\n')}
</urlset>`;
  writeFile(path.join(BUILD, 'sitemap.xml'), xml);
}

// ── Generate robots.txt ──
function buildRobots() {
  writeFile(path.join(BUILD, 'robots.txt'), `User-agent: *
Allow: /
Disallow: /admin/
Disallow: /api/
Disallow: /data/

Sitemap: ${SITE_URL}/sitemap.xml`);
}

// ── Generate .htaccess ──
function buildHtaccess() {
  writeFile(path.join(BUILD, '.htaccess'), `# Force HTTPS
RewriteEngine On
RewriteCond %{HTTPS} off
RewriteRule ^(.*)$ https://%{HTTP_HOST}%{REQUEST_URI} [L,R=301]

# Trailing slash normalization
RewriteCond %{REQUEST_FILENAME} !-f
RewriteCond %{REQUEST_URI} !(.*)/$
RewriteRule ^(.*)$ %{REQUEST_URI}/ [L,R=301]

# Block direct access to data directory
<IfModule mod_rewrite.c>
  RewriteRule ^data/ - [F,L]
</IfModule>

# Block direct access to admin sessions data
<IfModule mod_rewrite.c>
  RewriteRule ^data/sessions/ - [F,L]
</IfModule>

# WordPress URL redirects
RewriteRule ^wp-admin/?$ / [R=301,L]
RewriteRule ^wp-login\\.php$ / [R=301,L]
RewriteRule ^wp-content/ - [R=404,L]

# Cache headers
<IfModule mod_expires.c>
  ExpiresActive On
  ExpiresByType text/css "access plus 1 month"
  ExpiresByType application/javascript "access plus 1 month"
  ExpiresByType image/jpeg "access plus 1 year"
  ExpiresByType image/png "access plus 1 year"
  ExpiresByType image/svg+xml "access plus 1 year"
</IfModule>

# Custom 404
ErrorDocument 404 /404.html

# Security headers
<IfModule mod_headers.c>
  Header set X-Content-Type-Options "nosniff"
  Header set X-Frame-Options "SAMEORIGIN"
  Header set X-XSS-Protection "1; mode=block"
</IfModule>`);
}

// ── Build 404 page ──
function build404() {
  const content = `<section class="page-section"><div class="container content-page" style="text-align:center;padding:4rem 0;">
    <h1>Page Not Found</h1>
    <p>Sorry, the page you're looking for doesn't exist.</p>
    <a href="/" class="btn btn-primary">Return Home</a>
  </div></section>`;
  writeFile(path.join(BUILD, '404.html'), pageShell('Page Not Found', content, { path: '/404' }));
}

// ── Run Build ──
console.log('Building TrustedBusinessReviews.com static site...');
buildHomepage();
console.log('✓ Homepage');
buildCategoryPages();
console.log(`✓ ${Object.keys(categories).length} category pages`);
buildBusinessPages();
console.log(`✓ ${businesses.length} business listing pages`);
buildUtilityPages();
console.log('✓ Utility pages (Review Policy, Contact Us, Get Listed)');
buildSitemap();
console.log('✓ sitemap.xml');
buildRobots();
console.log('✓ robots.txt');
buildHtaccess();
console.log('✓ .htaccess');
build404();
console.log('✓ 404 page');
console.log(`\nBuild complete! ${Object.keys(categories).length} categories, ${businesses.length} businesses, ${businesses.reduce((s,b)=>s+b.reviews.length,0)} reviews.`);
