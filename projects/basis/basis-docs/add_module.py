#!/usr/bin/env python3
"""
Basis SDK Docs — Add New Module
Usage:
  python add_module.py V3 --position 8 --slug "new-topic" --title "New Topic Title"
  python add_module.py V3 --append --slug "new-topic" --title "New Topic Title"

Modes:
  --append     Add module at the end (no renumbering)
  --position N Insert module at position N (renumbers all subsequent modules)

What it does:
  1. Creates a skeleton module file (NN-slug_VX.md)
  2. Adds a placeholder entry to INDEX_DESCRIPTIONS.md
  3. If inserting (not appending):
     a. Renames all subsequent module files (NN+1, NN+2, ...)
     b. Updates internal cross-refs in ALL module files
     c. Updates the MODULES list in build_docs.py
  4. Updates the MODULES list in build_docs.py (for append too)
  5. Prints next steps (fill in content, fill in description, run build_docs.py)

IMPORTANT: This script modifies files in place for the given version.
           Always commit/backup before running.
"""

import sys
import os
import re
import argparse
from pathlib import Path

DOCS_DIR = Path(__file__).parent


def get_current_modules(ver: str) -> list:
    """Scan directory for existing versioned modules, return sorted base names."""
    pattern = re.compile(r"^(\d{2}-[\w-]+)_" + re.escape(ver) + r"\.md$")
    modules = []
    for f in DOCS_DIR.iterdir():
        m = pattern.match(f.name)
        if m:
            modules.append(m.group(1))
    return sorted(modules)


def parse_module_number(base: str) -> int:
    """Extract the number prefix from a base name like '08-how'."""
    return int(base.split("-", 1)[0])


def parse_module_slug(base: str) -> str:
    """Extract the slug from a base name like '08-how'."""
    return base.split("-", 1)[1]


def make_base(num: int, slug: str) -> str:
    """Create a base name like '08-how'."""
    return f"{num:02d}-{slug}"


def create_skeleton(base: str, ver: str, title: str):
    """Create a skeleton module file."""
    filename = f"{base}_{ver}.md"
    filepath = DOCS_DIR / filename
    content = f"""# {title}

**What this covers:** _TODO — describe what this section covers._
**Related sections:** _TODO — add cross-refs._

---

_Content goes here._
"""
    filepath.write_text(content, encoding="utf-8")
    print(f"  ✅ Created {filename}")


def add_to_descriptions(base: str, position: int = None):
    """Add a placeholder entry to INDEX_DESCRIPTIONS.md."""
    desc_path = DOCS_DIR / "INDEX_DESCRIPTIONS.md"
    text = desc_path.read_text(encoding="utf-8")

    new_entry = f"""
### {base}.md
**What's in it:** _TODO — pending description._
**Use this when:** _TODO_
**Key topics:** _TODO_

---"""

    if position is not None:
        # Insert before the entry at `position + 1` (the one we just bumped)
        next_num = position + 1
        pattern = rf"(### {next_num:02d}-)"
        match = re.search(pattern, text)
        if match:
            # Insert before this entry (with a preceding ---)
            insert_at = match.start()
            # Walk back to find the --- separator before this entry
            sep_pos = text.rfind("---", 0, insert_at)
            if sep_pos > 0:
                text = text[:sep_pos] + "---" + new_entry + "\n\n" + text[sep_pos + 3:]
            else:
                text = text[:insert_at] + new_entry + "\n\n" + text[insert_at:]
        else:
            # Fallback: append at end
            text = text.rstrip() + "\n" + new_entry + "\n"
    else:
        # Append at end
        text = text.rstrip() + "\n" + new_entry + "\n"

    desc_path.write_text(text, encoding="utf-8")
    print(f"  ✅ Added placeholder to INDEX_DESCRIPTIONS.md")


def rename_modules(ver: str, from_pos: int, modules: list):
    """Rename module files from from_pos onward (+1 to their number)."""
    # Work backwards to avoid collisions
    to_rename = [(base, parse_module_number(base)) for base in modules
                 if parse_module_number(base) >= from_pos]
    to_rename.sort(key=lambda x: x[1], reverse=True)

    renames = {}  # old_base -> new_base
    for old_base, num in to_rename:
        slug = parse_module_slug(old_base)
        new_base = make_base(num + 1, slug)
        old_file = DOCS_DIR / f"{old_base}_{ver}.md"
        new_file = DOCS_DIR / f"{new_base}_{ver}.md"
        if old_file.exists():
            old_file.rename(new_file)
            renames[old_base] = new_base
            print(f"  📁 {old_base}_{ver}.md → {new_base}_{ver}.md")

    return renames


def update_cross_refs(ver: str, renames: dict):
    """Update internal cross-references in all module files."""
    if not renames:
        return

    pattern = re.compile(r"(\d{2}-[\w-]+)(_" + re.escape(ver) + r"\.md)")
    all_modules = get_current_modules(ver)

    count = 0
    for base in all_modules:
        filepath = DOCS_DIR / f"{base}_{ver}.md"
        if not filepath.exists():
            continue
        text = filepath.read_text(encoding="utf-8")
        original = text

        for old_base, new_base in renames.items():
            text = text.replace(f"{old_base}_{ver}.md", f"{new_base}_{ver}.md")
            text = text.replace(f"{old_base}.md", f"{new_base}.md")

        if text != original:
            filepath.write_text(text, encoding="utf-8")
            count += 1

    print(f"  ✅ Updated cross-refs in {count} file(s)")


def update_descriptions_numbering(renames: dict):
    """Update module numbers in INDEX_DESCRIPTIONS.md."""
    desc_path = DOCS_DIR / "INDEX_DESCRIPTIONS.md"
    if not desc_path.exists():
        return

    text = desc_path.read_text(encoding="utf-8")
    original = text

    # Sort by old number descending to avoid double-replacement
    sorted_renames = sorted(renames.items(), key=lambda x: parse_module_number(x[0]), reverse=True)
    for old_base, new_base in sorted_renames:
        text = text.replace(f"### {old_base}.md", f"### {new_base}.md")

    if text != original:
        desc_path.write_text(text, encoding="utf-8")
        print(f"  ✅ Updated numbering in INDEX_DESCRIPTIONS.md")


def update_build_script(ver: str):
    """Update the MODULES list in build_docs.py to match current files."""
    build_path = DOCS_DIR / "build_docs.py"
    if not build_path.exists():
        print(f"  ⚠️  build_docs.py not found, skipping MODULES update")
        return

    modules = get_current_modules(ver)
    text = build_path.read_text(encoding="utf-8")

    # Build new MODULES list
    module_lines = ",\n".join(f'    "{base}"' for base in modules)
    new_modules = f"MODULES = [\n{module_lines},\n]"

    # Replace existing MODULES list
    pattern = r"MODULES\s*=\s*\[.*?\]"
    text = re.sub(pattern, new_modules, text, flags=re.DOTALL)

    build_path.write_text(text, encoding="utf-8")
    print(f"  ✅ Updated MODULES in build_docs.py ({len(modules)} modules)")


def main():
    parser = argparse.ArgumentParser(description="Add a new module to Basis SDK docs")
    parser.add_argument("version", help="Version suffix (e.g. V3, V4)")
    parser.add_argument("--slug", required=True, help="Module slug (e.g. 'token-value', 'new-topic')")
    parser.add_argument("--title", required=True, help="Module title for the skeleton header")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--position", type=int, help="Insert at this position (renumbers subsequent)")
    group.add_argument("--append", action="store_true", help="Append at the end (no renumbering)")
    args = parser.parse_args()

    ver = args.version.upper()
    slug = args.slug.lower().strip("-")
    title = args.title

    modules = get_current_modules(ver)
    if not modules:
        print(f"❌ No {ver} modules found in {DOCS_DIR}")
        sys.exit(1)

    print(f"📄 Adding module '{slug}' to {ver} docs...")
    print(f"   Current modules: {len(modules)}")
    print()

    if args.append:
        # Append mode
        last_num = max(parse_module_number(b) for b in modules)
        new_num = last_num + 1
        new_base = make_base(new_num, slug)
        print(f"  Mode: APPEND at position {new_num}")
        print()

        create_skeleton(new_base, ver, title)
        add_to_descriptions(new_base)
        update_build_script(ver)

    else:
        # Insert mode
        pos = args.position
        max_num = max(parse_module_number(b) for b in modules)
        if pos < 0 or pos > max_num + 1:
            print(f"❌ Position {pos} out of range (0-{max_num + 1})")
            sys.exit(1)

        new_base = make_base(pos, slug)
        print(f"  Mode: INSERT at position {pos}")
        print()

        # Step 1: Rename existing files from pos onward
        renames = rename_modules(ver, pos, modules)
        print()

        # Step 2: Update cross-refs
        update_cross_refs(ver, renames)

        # Step 3: Update INDEX_DESCRIPTIONS.md numbering
        update_descriptions_numbering(renames)

        # Step 4: Create the new module
        create_skeleton(new_base, ver, title)

        # Step 5: Add to descriptions
        add_to_descriptions(new_base, pos)

        # Step 6: Update build script
        update_build_script(ver)

    print()
    print("📋 Next steps:")
    print(f"   1. Fill in content: {new_base}_{ver}.md")
    print(f"   2. Fill in description: INDEX_DESCRIPTIONS.md (search for {new_base})")
    print(f"   3. Run: python build_docs.py {ver}")
    print(f"   4. (Optional) Run: python build_docs.py {ver} --zip")


if __name__ == "__main__":
    main()
