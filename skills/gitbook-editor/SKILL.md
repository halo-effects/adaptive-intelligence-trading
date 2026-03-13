---
name: gitbook-editor
description: Edit GitBook documentation pages via browser automation. Use when updating, rewriting, or formatting content on GitBook-hosted docs (app.gitbook.com). Covers page editing, table creation, Change Request workflow, and content verification. Triggers on "update GitBook", "edit the docs", "add tables to GitBook", "publish to GitBook", "update documentation".
---

# GitBook Editor

Edit GitBook pages programmatically via browser automation using the `browser` tool.

## Prerequisites

- Logged into `app.gitbook.com` in the browser (Google auth or email)
- Know the **org ID** and **space ID** from the GitBook URL

## URL Structure

```
# View published page
https://docs.{custom-domain}/{page-slug}

# Edit page in a Change Request
https://app.gitbook.com/o/{ORG_ID}/s/{SPACE_ID}/~/edit/~/changes/{CR_NUMBER}/{page-slug}

# View page (no CR)
https://app.gitbook.com/o/{ORG_ID}/s/{SPACE_ID}/{page-slug}
```

Sub-pages use path nesting: `basis-utility-token/token-distribution`

## Core Workflow

### 1. Start a Change Request

Navigate to any page in edit mode. GitBook auto-creates a CR:

```
browser → navigate to: app.gitbook.com/o/{ORG}/s/{SPACE}/~/edit/~/changes/{NEXT_CR_NUM}/{page-slug}
```

Or click "Edit" button on any page to enter the latest draft CR.

### 2. Edit a Page

```javascript
// Focus the editor
const m = document.querySelector('main');
const t = m.querySelectorAll('[role="textbox"]');
for (const x of t) {
  if (x.textContent.length > 5) { x.focus(); x.click(); break; }
}

// Select all + delete existing content
// Then use Ctrl+A, Delete key presses

// Paste new content (see Paste Methods below)
```

### 3. Merge the CR

```javascript
const buttons = document.querySelectorAll('button');
for (const b of buttons) {
  if (b.textContent.trim() === 'Merge') { b.click(); break; }
}
```

### 4. Verify Live

Fetch the published URL and confirm content rendered correctly.

## Paste Methods

### ⚠️ CRITICAL: HTML-Only for Tables

GitBook's paste handler has a specific behavior:
- `text/html` + `text/plain` → GitBook saves ONLY `text/plain` (tables lost!)
- `text/html` ONLY (no `text/plain`) → GitBook saves HTML including tables ✅
- `text/plain` ONLY → Works for prose, headings, bold, lists. No table formatting.

### Paste with Tables (HTML-only)

```javascript
() => {
  const html = `<h3>Title</h3>
<p>Paragraph text with <strong>bold</strong>.</p>
<table><thead><tr><th>Col A</th><th>Col B</th></tr></thead><tbody>
<tr><td>Row 1A</td><td>Row 1B</td></tr>
<tr><td>Row 2A</td><td>Row 2B</td></tr>
</tbody></table>
<ul><li>Bullet point</li></ul>`;

  const el = document.activeElement;
  const cd = new DataTransfer();
  cd.setData('text/html', html);  // HTML ONLY — no text/plain!
  el.dispatchEvent(new ClipboardEvent('paste', {
    bubbles: true, cancelable: true, clipboardData: cd
  }));
  return 'OK';
}
```

### Paste without Tables (text/plain)

```javascript
() => {
  const text = `### Title\n\nParagraph text.\n\n- Bullet point`;
  const el = document.activeElement;
  const cd = new DataTransfer();
  cd.setData('text/plain', text);
  el.dispatchEvent(new ClipboardEvent('paste', {
    bubbles: true, cancelable: true, clipboardData: cd
  }));
  return 'OK';
}
```

## Supported HTML Elements

GitBook converts these HTML elements into native blocks:

| HTML | GitBook Block |
|------|--------------|
| `<h1>` - `<h4>` | Headings (h1 = page title) |
| `<p>` | Paragraph |
| `<strong>` | Bold |
| `<em>` | Italic |
| `<code>` | Inline code |
| `<ul>/<li>` | Bullet list |
| `<ol>/<li>` | Numbered list |
| `<table>` | Table (only via HTML-only paste!) |
| `<a href>` | Link |
| `<blockquote>` | Quote block |

## Batch Editing Multiple Pages

1. Open one CR for all changes (navigate to first page in CR)
2. Edit each page: navigate → focus → select all → delete → paste
3. Merge once when all pages are done
4. Verify each page on published site

This minimizes CR count. GitBook tracks changes per-page within a CR.

## Gotchas

- **Page descriptions/subtitles**: Not editable via paste — must be changed in GitBook's page settings UI
- **Images**: Cannot be pasted via this method — use GitBook's upload UI
- **Large pages**: If paste silently fails, the page may be too large for a single paste. Split into sections.
- **CR numbering**: Auto-increments. Check the URL bar for current CR number.
- **Merge confirmation**: Some CRs show a confirmation dialog — look for a second "Merge" button click.
- **Heading levels shift**: `<h3>` in paste may render as `####` (H4) depending on GitBook's page title hierarchy. Test and adjust.
