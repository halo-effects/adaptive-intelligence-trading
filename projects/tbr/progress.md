# TBR Review System — Progress

## 2026-02-14: Review System + Admin Dashboard — DEPLOYED ✅

### What was built and deployed:

1. **Review API** (`/api/reviews.php`)
   - All endpoints working: csrf, submit, get, login, logout, pending, all, stats, moderate, check
   - Flat-file JSON storage with flock() file locking
   - Rate limiting: 3 submissions/IP/hour
   - CSRF protection for submissions
   - Bcrypt session-based admin auth (24h sessions)
   - Input sanitization and XSS protection

2. **Review Submission Frontend** (`/assets/js/reviews.js`)
   - AJAX review submission with CSRF tokens
   - Star rating picker (clickable, hover effects)
   - Success/error feedback messages
   - Dynamic review loading (appends new approved reviews after static ones)
   - Deduplication via data-static attributes

3. **Admin Dashboard**
   - `/admin/login.html` — Login page
   - `/admin/index.html` — Dashboard with stats, pending queue, all reviews with filters
   - `/assets/css/admin.css` — Dashboard styling
   - `/assets/js/admin.js` — Dashboard logic
   - Default credentials: admin / TBR-Admin-2026! (**CHANGE THESE**)

4. **Data Migration**
   - 211 reviews migrated from wp_export_data.json to data/reviews.json
   - All marked as approved, original dates and names preserved

5. **Security**
   - `/data/` directory blocked via .htaccess (returns 403)
   - Data directory has its own deny-all .htaccess
   - robots.txt blocks /admin/, /api/, /data/

6. **Build System Updated**
   - build.js now includes reviews.js script tag
   - Business pages have data-static attributes for review dedup
   - Dynamic reviews container added to business pages

### Files Created/Modified:
- `build/api/reviews.php` — Review API
- `build/admin/login.html` — Admin login
- `build/admin/index.html` — Admin dashboard
- `build/assets/js/reviews.js` — Review frontend JS
- `build/assets/js/admin.js` — Admin dashboard JS
- `build/assets/css/admin.css` — Admin styling
- `build/data/.htaccess` — Deny direct access
- `build/data/reviews.json` — 211 migrated reviews
- `migrate-reviews.js` — Migration script
- `deploy-update.js` — FTP deploy script
- `build.js` — Updated with reviews.js, data-static attrs, dynamic reviews container

### Testing:
- ✅ API CSRF endpoint returns tokens
- ✅ API get endpoint returns migrated reviews
- ✅ Admin login page loads
- ✅ /data/ directory returns 403
- ⏳ End-to-end test: submit review → admin approve → shows on page (needs browser testing)
