"""
Fix display text in markdown links where the visible number doesn't match the URL number.
e.g. [22-trust-safety](23-trust-safety.md) -> [23-trust-safety](23-trust-safety.md)
"""
import re, os

modules_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "modules")

# Pattern: [XX-slug](YY-slug.md) where XX != YY
# Captures: [display_num-slug](link_num-slug.md)
pattern = re.compile(r'\[(\d{2})-([-\w]+)\]\((\d{2})-([-\w]+)\.md\)')

total_fixes = 0

for f in sorted(os.listdir(modules_dir)):
    if not f.endswith(".md"):
        continue
    filepath = os.path.join(modules_dir, f)
    with open(filepath, "r", encoding="utf-8") as fh:
        content = fh.read()

    fixes = []

    def replace_mismatch(match):
        display_num = match.group(1)
        display_slug = match.group(2)
        link_num = match.group(3)
        link_slug = match.group(4)
        # If slugs match but numbers differ, fix display to match link
        if display_slug == link_slug and display_num != link_num:
            fixes.append(f"  {f}: [{display_num}-{display_slug}]({link_num}-{link_slug}.md) -> [{link_num}-{link_slug}]({link_num}-{link_slug}.md)")
            return f"[{link_num}-{link_slug}]({link_num}-{link_slug}.md)"
        return match.group(0)

    new_content = pattern.sub(replace_mismatch, content)

    if fixes:
        with open(filepath, "w", encoding="utf-8") as fh:
            fh.write(new_content)
        for fix in fixes:
            print(fix)
        total_fixes += len(fixes)

print(f"\nDone. {total_fixes} display text mismatches fixed.")
