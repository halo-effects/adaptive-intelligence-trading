#!/usr/bin/env python3
"""
Basis SDK Docs Build Pipeline
Usage: python build_docs.py V3        # builds for version V3
       python build_docs.py V4        # builds for version V4
       python build_docs.py V3 --zip  # builds + packages zip

Steps:
  1. Reads INDEX_DESCRIPTIONS.md for section metadata
  2. Compiles INDEX_{ver}.md with correct links and descriptions
  3. Merges all individual modules → COMPLETE_{ver}.md
  4. Generates COMPLETE_INDEX_{ver}.md (line-range map)
  5. (Optional) Packages zip with versioned/ and production/ folders
"""

import sys
import os
import re
import zipfile
from pathlib import Path

DOCS_DIR = Path(__file__).parent

# Ordered list of module base names (without version suffix)
MODULES = [
    "00-welcome",
    "01-what-is-basis",
    "02-archetypes",
    "03-token-value",
    "04-atomic-skills",
    "05-strategies",
    "06-decision-trees",
    "07-why",
    "08-how",
    "09-getting-started",
    "10-fees",
    "11-errors",
    "12-api-reference",
    "13-trust-safety",
    "14-mistakes",
    "15-faq",
    "16-contract-addresses",
    "17-examples",
    "18-prediction-market-deep-dive",
    "19-what-to-avoid",
    "20-production-ops",
]


def parse_descriptions(path: Path) -> dict:
    """Parse INDEX_DESCRIPTIONS.md into {base_name: description_block}."""
    text = path.read_text(encoding="utf-8")
    descriptions = {}
    current_key = None
    current_lines = []

    for line in text.splitlines():
        # Match ### 03-token-value.md
        m = re.match(r"^### \[?(\d{2}-[\w-]+)\.md\]?", line)
        if m:
            if current_key:
                descriptions[current_key] = "\n".join(current_lines).strip()
            current_key = m.group(1)
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key:
        descriptions[current_key] = "\n".join(current_lines).strip()

    return descriptions


def get_version_date(ver: str) -> str:
    """Read the first module to extract the version date, or use today."""
    first_module = DOCS_DIR / f"{MODULES[0]}_{ver}.md"
    if first_module.exists():
        text = first_module.read_text(encoding="utf-8")
        m = re.search(r"Last updated:\s*(\d{4}-\d{2}-\d{2})", text)
        if m:
            return m.group(1)
    from datetime import date
    return date.today().isoformat()


def get_sdk_version(ver: str) -> str:
    """Try to extract SDK version from first module header."""
    first_module = DOCS_DIR / f"{MODULES[0]}_{ver}.md"
    if first_module.exists():
        text = first_module.read_text(encoding="utf-8")
        m = re.search(r"v(\d+\.\d+\.\d+)", text)
        if m:
            return m.group(0)
    return "v1.0.2"


def build_index(ver: str, descriptions: dict) -> str:
    """Build INDEX_{ver}.md content."""
    sdk_ver = get_sdk_version(ver)
    date = get_version_date(ver)

    lines = [
        "# Basis Documentation Index",
        "",
        f"_SDK Documentation {sdk_ver} | Last updated: {date}_",
        "",
        f"> **⚡ Agents: Use [`COMPLETE_INDEX_{ver}.md`](COMPLETE_INDEX_{ver}.md) instead.** It maps line ranges into the monolithic `COMPLETE_{ver}.md`, enabling surgical 20–50 line reads instead of loading entire section files. Far more token-efficient.",
        ">",
        f"> This file maps to individual section files — useful for human editing and git diffs, but agents should prefer `COMPLETE_INDEX_{ver}.md` → `COMPLETE_{ver}.md` for lookups.",
        "",
        "**Human guidance:** Use the section map below to find and edit individual files. Each file is self-contained.",
        "",
        "---",
        "",
        "## Section Map",
    ]

    for base in MODULES:
        filename = f"{base}_{ver}.md"
        filepath = DOCS_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  Missing module: {filename}")
            continue

        desc = descriptions.get(base, "")
        # Update cross-ref links to use versioned filenames
        desc = re.sub(
            r"\[(\d{2}-[\w-]+)_V\d+\.md\]\(\1_V\d+\.md\)",
            lambda m: f"[{m.group(1)}_{ver}.md]({m.group(1)}_{ver}.md)",
            desc,
        )
        # Also fix cross-refs that use generic names from descriptions file
        for other_base in MODULES:
            # Match → strategies, → atomic-skills style refs
            short = other_base.split("-", 1)[1] if "-" in other_base else other_base
            desc = desc.replace(
                f"→ [{other_base}.md]({other_base}.md)",
                f"→ [{other_base}_{ver}.md]({other_base}_{ver}.md)",
            )

        lines.append("")
        lines.append(f"### [{filename}]({filename})")
        lines.append(desc)
        lines.append("")
        lines.append("---")

    return "\n".join(lines) + "\n"


def build_complete(ver: str) -> str:
    """Merge all modules into COMPLETE_{ver}.md."""
    parts = []
    for base in MODULES:
        filename = f"{base}_{ver}.md"
        filepath = DOCS_DIR / filename
        if not filepath.exists():
            print(f"  ⚠️  Missing module: {filename}")
            continue
        content = filepath.read_text(encoding="utf-8").strip()
        parts.append(content)

    return "\n\n---\n\n".join(parts) + "\n"


def build_complete_index(ver: str, complete_text: str) -> str:
    """Generate COMPLETE_INDEX_{ver}.md with line-range mappings."""
    sdk_ver = get_sdk_version(ver)
    date = get_version_date(ver)
    lines_list = complete_text.splitlines()

    sections = []
    for i, line in enumerate(lines_list, start=1):
        # Match top-level markdown headers (# or ##)
        if re.match(r"^#{1,2}\s+\S", line) and not line.startswith("###"):
            sections.append((i, line.strip()))

    output = [
        f"# COMPLETE_INDEX_{ver}.md",
        "",
        f"_SDK Documentation {sdk_ver} | Last updated: {date}_",
        "",
        f"Line-range index into [`COMPLETE_{ver}.md`](COMPLETE_{ver}.md).",
        f"Total lines: {len(lines_list)} | Total size: {len(complete_text):,} bytes",
        "",
        "---",
        "",
        "| Lines | Section |",
        "|-------|---------|",
    ]

    for idx, (start_line, header) in enumerate(sections):
        if idx + 1 < len(sections):
            end_line = sections[idx + 1][0] - 1
        else:
            end_line = len(lines_list)
        # Clean up the header for display
        display = re.sub(r"^#+\s*", "", header)
        output.append(f"| {start_line}–{end_line} | {display} |")

    return "\n".join(output) + "\n"


def build_zip(ver: str):
    """Package into zip with versioned/ and production/ folders."""
    zip_name = DOCS_DIR / f"basis-docs-{ver.lower()}.zip"

    # Files to include
    files_versioned = [
        f"INDEX_{ver}.md",
        f"COMPLETE_{ver}.md",
        f"COMPLETE_INDEX_{ver}.md",
    ]
    for base in MODULES:
        files_versioned.append(f"{base}_{ver}.md")

    # Production names (strip version suffix)
    production_map = {}
    production_map[f"INDEX_{ver}.md"] = "INDEX.md"
    production_map[f"COMPLETE_{ver}.md"] = "COMPLETE.md"
    production_map[f"COMPLETE_INDEX_{ver}.md"] = "COMPLETE_INDEX.md"
    for base in MODULES:
        production_map[f"{base}_{ver}.md"] = f"{base}.md"

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in files_versioned:
            fpath = DOCS_DIR / fname
            if not fpath.exists():
                print(f"  ⚠️  Missing for zip: {fname}")
                continue
            content = fpath.read_bytes()
            zf.writestr(f"versioned/{fname}", content)
            zf.writestr(f"production/{production_map[fname]}", content)

    print(f"  📦 Packaged: {zip_name.name} ({zip_name.stat().st_size:,} bytes)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_docs.py <VERSION> [--zip]")
        print("  e.g: python build_docs.py V3")
        print("  e.g: python build_docs.py V4 --zip")
        sys.exit(1)

    ver = sys.argv[1].upper()
    do_zip = "--zip" in sys.argv

    print(f"🔨 Building Basis SDK docs for {ver}...")
    print()

    # Check modules exist
    missing = []
    for base in MODULES:
        if not (DOCS_DIR / f"{base}_{ver}.md").exists():
            missing.append(f"{base}_{ver}.md")
    if missing:
        print(f"❌ Missing {len(missing)} module(s):")
        for m in missing:
            print(f"   - {m}")
        print("\nCreate these files first, then re-run.")
        sys.exit(1)

    # Step 1: Parse descriptions
    desc_path = DOCS_DIR / "INDEX_DESCRIPTIONS.md"
    if not desc_path.exists():
        print("❌ INDEX_DESCRIPTIONS.md not found!")
        sys.exit(1)
    descriptions = parse_descriptions(desc_path)
    print(f"  ✅ Parsed {len(descriptions)} section descriptions")

    # Step 2: Build INDEX
    index_content = build_index(ver, descriptions)
    index_path = DOCS_DIR / f"INDEX_{ver}.md"
    index_path.write_text(index_content, encoding="utf-8")
    print(f"  ✅ INDEX_{ver}.md ({len(index_content):,} bytes)")

    # Step 3: Build COMPLETE
    complete_content = build_complete(ver)
    complete_path = DOCS_DIR / f"COMPLETE_{ver}.md"
    complete_path.write_text(complete_content, encoding="utf-8")
    line_count = len(complete_content.splitlines())
    print(f"  ✅ COMPLETE_{ver}.md ({len(complete_content):,} bytes, {line_count:,} lines)")

    # Step 4: Build COMPLETE_INDEX
    ci_content = build_complete_index(ver, complete_content)
    ci_path = DOCS_DIR / f"COMPLETE_INDEX_{ver}.md"
    ci_path.write_text(ci_content, encoding="utf-8")
    print(f"  ✅ COMPLETE_INDEX_{ver}.md ({len(ci_content):,} bytes)")

    # Step 5: Optional zip
    if do_zip:
        print()
        build_zip(ver)

    print()
    print(f"✅ Done! All {ver} docs built.")


if __name__ == "__main__":
    main()
