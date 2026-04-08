"""
Fix all module cross-reference links to use the correct module numbers.
Scans all .md files in modules/ and corrects any wrong-numbered references.
"""
import re, os

modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules")

# Build canonical map: slug -> correct number from actual filenames
canonical = {}
for f in sorted(os.listdir(modules_dir)):
    m = re.match(r"^(\d{2})-(.+)\.md$", f)
    if m:
        canonical[m.group(2)] = m.group(1)

print(f"Found {len(canonical)} modules:")
for slug, num in canonical.items():
    print(f"  {num}-{slug}.md")
print()

# Pattern matches any 2-digit prefix followed by a known slug
slugs_pattern = "|".join(re.escape(s) for s in canonical.keys())
pattern = re.compile(r"(\d{2})-(" + slugs_pattern + r")\.md")

total_fixes = 0

for f in sorted(os.listdir(modules_dir)):
    if not f.endswith(".md"):
        continue
    filepath = os.path.join(modules_dir, f)
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()

    fixes = []

    def replace_ref(match):
        old_num = match.group(1)
        slug = match.group(2)
        correct_num = canonical[slug]
        if old_num != correct_num:
            fixes.append(f"  {f}: {old_num}-{slug}.md -> {correct_num}-{slug}.md")
            return f"{correct_num}-{slug}.md"
        return match.group(0)

    new_content = pattern.sub(replace_ref, content)

    if fixes:
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        for fix in fixes:
            print(fix)
        total_fixes += len(fixes)

print(f"\nDone. {total_fixes} references fixed across all modules.")
