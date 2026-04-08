const fs = require('fs');
const path = require('path');
const dir = path.join(__dirname, 'modules');

// Old number -> new number (process highest first to avoid double-rename)
const remap = [];
for (let i = 26; i >= 15; i--) {
  remap.push([String(i).padStart(2, '0'), String(i + 1).padStart(2, '0')]);
}

const files = fs.readdirSync(dir).filter(f => f.endsWith('.md')).sort();
let totalChanges = 0;

for (const file of files) {
  const fp = path.join(dir, file);
  let content = fs.readFileSync(fp, 'utf8');
  let fileChanges = 0;

  for (const [oldNum, newNum] of remap) {
    const re = new RegExp(`${oldNum}-([-\\w]+)\\.md`, 'g');
    const matches = content.match(re);
    if (matches) {
      content = content.replace(re, `${newNum}-$1.md`);
      console.log(`  ${file}: ${oldNum}-*.md -> ${newNum}-*.md (${matches.length} refs)`);
      fileChanges += matches.length;
    }
  }

  if (fileChanges > 0) {
    fs.writeFileSync(fp, content, 'utf8');
    totalChanges += fileChanges;
  }
}

console.log(`\nDone. ${totalChanges} references updated across ${files.length} files scanned.`);
