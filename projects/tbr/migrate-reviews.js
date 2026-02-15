/**
 * Migrate reviews from wp_export_data.json to data/reviews.json format
 */
const fs = require('fs');
const path = require('path');

const data = require('./wp_export_data.json');
const OUTPUT = path.join(__dirname, 'build', 'data', 'reviews.json');

// Build post slug/category lookup
const postCats = {};
data.post_categories.forEach(pc => {
  if (pc.taxonomy === 'category' && pc.slug !== 'uncategorized') {
    postCats[pc.post_id] = pc.slug;
  }
});

const postSlugs = {};
data.posts.filter(p => p.post_type === 'post' && p.post_status === 'publish').forEach(p => {
  postSlugs[p.ID] = p.post_name;
});

const reviews = [];
let id = 1;

data.comments.forEach(c => {
  if (c.comment_approved !== '1') return;
  const postId = c.comment_post_ID;
  const businessSlug = postSlugs[postId];
  const categorySlug = postCats[postId];
  if (!businessSlug || !categorySlug) return;

  reviews.push({
    id: 'migrated_' + String(id++).padStart(4, '0'),
    reviewer_name: c.comment_author || 'Anonymous',
    reviewer_email: c.comment_author_email || '',
    rating: 5,
    text: (c.comment_content || '').replace(/<[^>]+>/g, '').trim(),
    business_slug: businessSlug,
    category_slug: categorySlug,
    status: 'approved',
    ip: c.comment_author_IP || '',
    submitted_at: c.comment_date || new Date().toISOString(),
    moderated_at: c.comment_date || new Date().toISOString(),
    migrated: true
  });
});

// Ensure output dir
fs.mkdirSync(path.dirname(OUTPUT), { recursive: true });
fs.writeFileSync(OUTPUT, JSON.stringify(reviews, null, 2));
console.log(`Migrated ${reviews.length} reviews to ${OUTPUT}`);
