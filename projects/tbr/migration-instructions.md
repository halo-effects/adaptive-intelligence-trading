# TrustedBusinessReviews.com - WordPress to HTML Migration Instructions
## Phase 1: Site Migration & Review System Implementation
**Document Version: 1.0 | Date: February 2026**

## 1. Project Overview

Migrate TrustedBusinessReviews.com from WordPress to static HTML, preserving all URLs, content, and reviews while modernizing design and implementing a review management system.

### 1.1 Project Goals
- Migrate from WordPress to clean static HTML/CSS/JS
- Preserve all existing URL paths and folder structure
- Document complete sitemap
- Preserve existing content and reviews, upgrade visual design
- Implement review submission system with admin moderation dashboard
- Implement Google Review schema markup (JSON-LD) on all business listing pages
- Prepare architecture for future Shadow Query listicle and mesh page integration

### 1.2 Key Constraints
- All existing URLs must remain functional (no URL changes)
- Business listing content optimized in Phase 2 (don't restructure business data)
- Review system is most critical functional component
- Must be compatible with future Shadow Query additions
- FTP access provided separately

### 1.3 NOT In Scope (Phase 2)
- Detailed SEO/GEO optimization of business listing page layouts
- Enhanced business schema beyond LocalBusiness + Review schema
- Adding more thorough business information fields
- Shadow Query listicle and mesh page creation

## 2. Current Site Audit & Documentation

WordPress-powered business review directory focused on Phoenix, AZ area businesses, with some listings in other regions (Eugene/Salem, OR).

### 2.1 Site Architecture & URL Structure

#### 2.1.1 Homepage
- https://trustedbusinessreviews.com/ — Feed of business listing excerpts

#### 2.1.2 Category Pages (Business Type)

| Category | URL Pattern | Known Businesses |
|----------|------------|-----------------|
| Auto Glass | /auto-glass/[business-slug]/ | SafePro Auto Glass, Southwest Auto Glass (Phoenix Auto Glass) |
| Auto Recyclers | /auto-recyclers/[business-slug]/ | Just Truck & Van |
| Window Repair/Replacement | /window-repair-replacement/[business-slug]/ | Superior Replacement Windows, SR Windows & Glass, Universal Glass |
| Dentist | /dentist/[business-slug]/ | Natural Smiles (Salem, OR) |
| Denturists | /denturists/[business-slug]/ | Natural Dentures (Eugene, OR) |
| Auto Auction | /auto-auction/[business-slug]/ (estimated) | Payless Auto Auction |
| Auto Parts / Salvage | /auto-parts/[business-slug]/ (estimated) | Pick A Part |

**IMPORTANT:** Must perform complete FTP crawl to discover ALL categories and listings. Table may be incomplete.

#### 2.1.3 Utility / Static Pages
- /review-policy/ — Review acceptance, privacy, publishing policies
- /contact-us/ — Contact info (info@TrustedBusinessReviews.com)
- /get-listed/ — Application page for businesses

#### 2.1.4 WordPress Infrastructure Pages
Identify via FTP: pagination, tag archives, author archives, etc.

### 2.2 Business Listing Page Structure
- Business Name (H1)
- Business Description (1-3 paragraphs)
- Customer Reviews (reviewer first name, text, star ratings)
- Business Contact Info (address, phone, website URL)
- Service Tags/Keywords

### 2.3 Review Policy Summary
- Only authentic consumer reviews accepted
- Only reviewer first name published
- Emails never published/sold/traded
- Reviews may be quarantined/removed per policy criteria
- No cookies for personal info, no personal info collected

### 2.4 Current Design Observations
- Dated WordPress theme, basic styling
- Standard layout with content area + sidebar
- Star ratings alongside review text
- Slow load times observed

## 3. Pre-Migration Steps

### 3.1 Complete Site Crawl & Documentation
1. Connect via FTP
2. Locate WordPress installation directory
3. Examine wp-content/themes/ for active theme
4. Access WordPress database (creds in wp-config.php), export:
   - All posts/pages (wp_posts)
   - All categories/taxonomies (wp_terms, wp_term_taxonomy)
   - All post metadata (wp_postmeta)
   - All comments/reviews (wp_comments)
   - All options (wp_options)
5. Create complete sitemap document
6. Download/backup all media from wp-content/uploads/
7. Document all existing review data per business

### 3.2 Full Backup
- Complete backup of all WordPress files
- Full database dump (mysqldump)
- Store in /backup_wordpress_YYYYMMDD/
- Verify backup before proceeding

## 4. New HTML Site File Structure
```
/public_html/
  index.html                          <- Homepage
  /[category-slug]/
    index.html                        <- Category page
    /[business-slug]/
      index.html                      <- Business listing page
  /review-policy/index.html
  /contact-us/index.html
  /get-listed/index.html
  /admin/
    index.html
    /login.html
  /api/reviews.php
  /assets/css/ (style.css, admin.css)
  /assets/js/ (main.js, reviews.js, admin.js)
  /assets/images/
  /data/reviews.json (or database)
  robots.txt
  sitemap.xml
  .htaccess
```

## 5. Page Templates & Design Specifications

### 5.1 Global Design System

#### Color Palette
| Element | Color | Usage |
|---------|-------|-------|
| Primary | #1F4E79 (Deep Blue) | Headers, nav, primary buttons |
| Secondary | #2E75B6 (Medium Blue) | Accents, links, hover states |
| Accent | #FFB800 (Gold/Amber) | Star ratings, trust badges, CTAs |
| Success | #28A745 (Green) | Approved status |
| Danger | #DC3545 (Red) | Rejected status |
| Background | #F8F9FA (Light Gray) | Page background |
| Card Background | #FFFFFF | Content cards |
| Text Primary | #212529 | Body text |
| Text Secondary | #6C757D | Meta/secondary text |

#### Typography
- Primary: Inter or system font stack
- Headings: 600-700 weight, H1 2rem → H6 1rem
- Body: 400 weight, 1rem (16px), 1.6 line-height

#### Global Navigation
- Header: Logo/name, Home, Categories (dropdown), Get Listed, Review Policy, Contact Us, mobile hamburger
- Footer: Copyright, policy links, site description

### 5.2 Homepage Template
- Hero section with tagline
- Category grid/cards with counts
- Featured/recent listings with ratings
- Trust section about review policy
- CTA for businesses and consumers

### 5.3 Category Page Template
- Category title (H1) + description
- Business grid/list cards (name, rating, review count, excerpt, location)
- Breadcrumbs: Home > Category

### 5.4 Business Listing Page Template
- Breadcrumbs: Home > Category > Business
- Business name (H1), aggregate rating, contact info
- Business description (preserved exactly)
- Service tags as badges
- Reviews section (cards: name, stars, date, text; most recent first)
- Write a Review form (name, email, rating, text)
- Business contact block

### 5.5 Utility Pages
- Review Policy: Migrate content verbatim
- Contact Us: Form + email
- Get Listed: Application form

## 6. Review Management System

### 6.1 Technology Stack
- PHP preferred (most likely available on shared hosting)
- Fallback: flat-file JSON + PHP, or SQLite + PHP

### 6.2 Review Data Model
Fields: id, business_slug, category_slug, reviewer_name, reviewer_email, rating (1-5), review_text, date_submitted, status (pending/approved/rejected), admin_notes, ip_address

### 6.3 Review API Endpoints
- POST /api/reviews.php?action=submit — Submit review (rate limited: 3/IP/hour)
- GET /api/reviews.php?action=get&business=[slug] — Get approved reviews
- POST /api/reviews.php?action=moderate — Admin: approve/reject (authenticated)
- GET /api/reviews.php?action=pending — Admin: pending queue
- GET /api/reviews.php?action=all — Admin: all reviews with filters

### 6.4 Migrating Existing Reviews
- Extract from WordPress DB
- Map to business_slug/category_slug
- Import as status='approved'
- Preserve dates and names
- Verify counts match original

## 7. Admin Dashboard

### 7.1 Authentication
- Login at /admin/login.html
- Hashed password (bcrypt), session-based auth
- Document default creds, instruct to change immediately

### 7.2 Dashboard Views
- Main: Stats, pending queue access, activity feed
- Pending Queue: Review cards with approve/reject buttons, bulk actions
- All Reviews: Filterable table (status, business, category, date, search)
- Business Directory: List with review counts and ratings

## 8. Google Review Schema (JSON-LD)

### 8.1 Eligibility
Third-party review site — eligible for review rich results.

### 8.2 JSON-LD Template
LocalBusiness with address, telephone, url, aggregateRating, and review array.

### 8.3 Rules
- aggregateRating MUST match visible display
- Only approved reviews in schema
- Every schema review must be visible on page
- Regenerate on approval/rejection
- Use specific LocalBusiness sub-types (AutoRepair, Dentist, etc.)
- Validate with Google Rich Results Test

### 8.4 Additional Structured Data
- BreadcrumbList on all pages
- WebSite schema on homepage
- Organization schema for TrustedBusinessReviews.com

## 9. Technical Requirements

### 9.1 .htaccess
- Force HTTPS
- Trailing slash normalization
- 301 redirects for WordPress URLs (/wp-admin/, /wp-login.php, etc.)
- Block /data/ directory access
- Protect /admin/
- Cache headers, custom 404

### 9.2 Performance
- <3 second load times
- Minified CSS/JS, optimized images, lazy loading

### 9.3 SEO
- Unique titles + meta descriptions
- Canonical tags, XML sitemap, robots.txt
- Open Graph tags, semantic HTML5, proper heading hierarchy

### 9.4 Security
- Input sanitization, CSRF protection
- Prepared statements, rate limiting
- Bcrypt passwords, XSS protection
- Block direct access to data/config files

### 9.5 Shadow Query Compatibility
- Modular architecture
- Consistent template system
- Reserve /best-[service]-in-[city]/ namespace
- Dynamic navigation, organized stylesheets

## 10. Deployment Procedure

### 10.1 Staging/Testing
- Build in staging subdirectory
- Verify all URLs, review workflows, schema, responsive design, migrated content, .htaccess

### 10.2 Go-Live
1. Confirm WordPress backup exists
2. Move WordPress to backup directory
3. Deploy new files to web root
4. Deploy .htaccess
5. Verify homepage + spot-check 5+ listing pages
6. Test review submission + admin dashboard
7. Submit sitemap.xml to Google Search Console

### 10.3 Post-Deployment
- Monitor Search Console for crawl errors
- Verify schema in Rich Results Test
- Document admin credentials, provide user guide

## 11. Deliverables Checklist
1. [ ] Complete sitemap documentation
2. [ ] Full WordPress backup
3. [ ] HTML homepage
4. [ ] HTML category pages (ALL)
5. [ ] HTML business listing pages (ALL) with content preserved
6. [ ] HTML utility pages
7. [ ] All reviews migrated and displaying
8. [ ] Review submission form functional
9. [ ] Server-side review API operational
10. [ ] Admin dashboard with moderation tools
11. [ ] Google Review schema (JSON-LD) on all listings
12. [ ] BreadcrumbList schema on all pages
13. [ ] .htaccess configured
14. [ ] XML sitemap
15. [ ] robots.txt
16. [ ] Responsive design tested
17. [ ] All URL paths verified
18. [ ] Schema validated
19. [ ] Admin user guide / credentials
20. [ ] WordPress backup preserved

## 12. Important Notes for the AI Agent
- **Autonomy:** Complete most work autonomously; document decisions and flag ambiguity
- **Content Fidelity:** Do NOT rewrite/alter existing business descriptions or reviews — migrate word-for-word
- **Review Integrity:** Every approved review must be migrated; include doubtful ones and flag
- **URL Preservation:** Critical — verify every URL before go-live
- **PHP Backend:** Preferred for review system; ensure file locking for JSON, or check PDO SQLite
- **Static Page Generation:** Consider PHP includes for dynamic review sections + schema
- **Future-Proofing:** Phase 2 adds business info/schema/SEO; Phase 3 adds Shadow Query pages
