#!/usr/bin/env python3
"""
Basis SDK Docs Build Pipeline
Usage: python build_docs.py V8        # builds for version V8
       python build_docs.py V8 --zip  # builds + packages zip

Steps:
  1. Reads INDEX_DESCRIPTIONS_{ver}.md for section metadata
  2. Compiles INDEX_{ver}.md with correct links and descriptions
  3. Merges all individual modules → COMPLETE_{ver}.md
  4. Generates COMPLETE_INDEX_{ver}.md (line-range map)
  5. Outputs to versioned/ and production/ folders
  6. (Optional) Packages zip

Does NOT build llms.txt or llms-full.txt — those are maintained manually.

⚠️ VERSIONING RULE: Never edit a version in place. Any content change
   requires a new version number. To make changes:
   1. Copy all *_VX.md files to *_V(X+1).md
   2. Make edits ONLY on the new version files
   3. Run: python build_docs.py V(X+1)
   Old versions remain frozen as historical snapshots.
"""

import sys
import os
import re
import shutil
import zipfile
from pathlib import Path

DOCS_DIR = Path(__file__).parent

# Ordered list of module base names (without version suffix)
MODULES = [
    "00-welcome",
    "01-what-is-basis",
    "02-archetypes",
    "03-token-value",
    "04-the-reef",
    "05-referral-system",
    "06-atomic-skills",
    "07-mcp",
    "08-strategies",
    "09-decision-trees",
    "10-why",
    "11-how",
    "12-getting-started",
    "13-fees",
    "14-errors",
    "15-api-reference",
    "16-trust-safety",
    "17-mistakes",
    "18-faq",
    "19-contract-addresses",
    "20-examples",
    "21-prediction-market-deep-dive",
    "22-prediction-arb-engine",
    "23-what-to-avoid",
    "24-production-ops",
]


def parse_descriptions(path: Path) -> dict:
    """Parse INDEX_DESCRIPTIONS_{ver}.md into {base_name: description_block}."""
    text = path.read_text(encoding="utf-8")
    descriptions = {}
    current_key = None
    current_lines = []

    for line in text.splitlines():
        # Match ### 03-token-value.md
        m = re.match(r"^### \[?(\d{2}-[\w-]+)\.md\]?", line)
        if m:
            if current_key:
                desc = "\n".join(current_lines).strip()
                desc = re.sub(r"\n---\s*$", "", desc).strip()
                descriptions[current_key] = desc
            current_key = m.group(1)
            current_lines = []
        elif current_key is not None:
            current_lines.append(line)

    if current_key:
        desc = "\n".join(current_lines).strip()
        desc = re.sub(r"\n---\s*$", "", desc).strip()
        descriptions[current_key] = desc

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
    return "v1.0.3"


def strip_version_refs(text: str, version: str) -> str:
    """Strip version suffixes from internal links and references."""
    esc_ver = re.escape(version)
    text = re.sub(rf"_{esc_ver}\.md", ".md", text, flags=re.IGNORECASE)
    text = re.sub(rf"COMPLETE_INDEX_{esc_ver}\.md", "COMPLETE_INDEX.md", text, flags=re.IGNORECASE)
    text = re.sub(rf"COMPLETE_{esc_ver}\.md", "COMPLETE.md", text, flags=re.IGNORECASE)
    text = re.sub(rf"INDEX_{esc_ver}\.md", "INDEX.md", text, flags=re.IGNORECASE)
    text = re.sub(rf"COMPLETE_INDEX_{esc_ver}", "COMPLETE_INDEX", text, flags=re.IGNORECASE)
    return text


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
        for other_base in MODULES:
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
        while content.endswith("---"):
            content = content[:-3].strip()
        while content.startswith("---"):
            content = content[3:].strip()
        parts.append(content)

    return "\n\n---\n\n".join(parts) + "\n"


def build_complete_index(ver: str, complete_text: str) -> str:
    """Generate COMPLETE_INDEX_{ver}.md with line-range mappings."""
    sdk_ver = get_sdk_version(ver)
    date = get_version_date(ver)
    lines_list = complete_text.splitlines()

    sections = []
    for i, line in enumerate(lines_list, start=1):
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).strip()
            if i > 1 and lines_list[i-2].strip().startswith(">"):
                continue
            sections.append((i, level, heading))

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

    sdk_methods = {}
    for idx, (start_line, level, heading) in enumerate(sections):
        if level == 2 and heading.startswith("Module:"):
            section_end = len(lines_list) + 1
            for next_idx in range(idx + 1, len(sections)):
                if sections[next_idx][1] <= 2:
                    section_end = sections[next_idx][0]
                    break
            methods = []
            for sub_idx in range(idx + 1, len(sections)):
                sub_start, sub_level, sub_heading = sections[sub_idx]
                if sub_start >= section_end:
                    break
                if sub_level == 3:
                    clean = sub_heading.strip("`").strip()
                    method_match = re.match(r"(\w+)\s*\(", clean)
                    if method_match:
                        methods.append(method_match.group(1))
            if methods:
                sdk_methods[start_line] = methods

    for idx, (start_line, level, heading) in enumerate(sections):
        if idx + 1 < len(sections):
            end_line = sections[idx + 1][0] - 1
        else:
            end_line = len(lines_list)
        indent = "" if level == 1 else ("→ " if level == 2 else "  → ")
        entry = f"| {start_line}–{end_line} | {indent}{heading}"
        if start_line in sdk_methods:
            methods_str = ", ".join(f"`{m}`" for m in sdk_methods[start_line])
            entry += f" — Key methods: {methods_str}"
        entry += " |"
        output.append(entry)

    return "\n".join(output) + "\n"


def build_llms_full_txt(ver: str, complete_content: str) -> str:
    """Generate llms-full.txt — full SDK docs as plain text with header from llms_{ver}.txt."""
    date = get_version_date(ver)
    sdk_ver = get_sdk_version(ver)

    # Strip version refs from complete content for production use
    prod_complete = strip_version_refs(complete_content, ver)

    header = f"""# Basis SDK Documentation — Full Reference
# Version: {sdk_ver} | Last updated: {date}
# https://launchonbasis.com
#
# This is the complete SDK documentation for the Basis agent-native DeFi platform.
# For a concise overview, see: https://launchonbasis.com/llms.txt
# For interactive API docs, see: https://launchonbasis.com/api-docs

"""
    return header + prod_complete


def output_files(ver: str, index_content: str, complete_content: str, ci_content: str):
    """Write versioned/ and production/ output folders."""
    versioned_dir = DOCS_DIR / "output" / "versioned"
    production_dir = DOCS_DIR / "output" / "production"
    versioned_dir.mkdir(parents=True, exist_ok=True)
    production_dir.mkdir(parents=True, exist_ok=True)

    # --- Versioned output ---
    # Index files
    (versioned_dir / f"INDEX_{ver}.md").write_text(index_content, encoding="utf-8")
    (versioned_dir / f"COMPLETE_{ver}.md").write_text(complete_content, encoding="utf-8")
    (versioned_dir / f"COMPLETE_INDEX_{ver}.md").write_text(ci_content, encoding="utf-8")

    # Individual modules
    for base in MODULES:
        src = DOCS_DIR / f"{base}_{ver}.md"
        if src.exists():
            shutil.copy2(src, versioned_dir / f"{base}_{ver}.md")

    print(f"  📁 versioned/ — {len(list(versioned_dir.iterdir()))} files")

    # --- Production output (version-stripped) ---
    prod_index = strip_version_refs(index_content, ver)
    prod_complete = strip_version_refs(complete_content, ver)
    prod_ci = strip_version_refs(ci_content, ver)

    (production_dir / "INDEX.md").write_text(prod_index, encoding="utf-8")
    (production_dir / "COMPLETE.md").write_text(prod_complete, encoding="utf-8")
    (production_dir / "COMPLETE_INDEX.md").write_text(prod_ci, encoding="utf-8")

    # Individual modules (stripped)
    for base in MODULES:
        src = DOCS_DIR / f"{base}_{ver}.md"
        if src.exists():
            content = src.read_text(encoding="utf-8")
            prod_content = strip_version_refs(content, ver)
            (production_dir / f"{base}.md").write_text(prod_content, encoding="utf-8")

    # Copy llms.txt if it exists (hand-maintained, not generated)
    llms_src = DOCS_DIR / f"llms_{ver}.txt"
    if llms_src.exists():
        shutil.copy2(llms_src, production_dir / "llms.txt")
        print(f"  📄 Copied llms_{ver}.txt → production/llms.txt")

    # Build llms-full.txt (COMPLETE.md as plain text with header)
    llms_full = build_llms_full_txt(ver, complete_content)
    (production_dir / "llms-full.txt").write_text(llms_full, encoding="utf-8")
    print(f"  📄 Built llms-full.txt ({len(llms_full):,} bytes, {len(llms_full.splitlines()):,} lines)")

    print(f"  📁 production/ — {len(list(production_dir.iterdir()))} files")


def build_zip(ver: str):
    """Package output/ into a zip."""
    output_dir = DOCS_DIR / "output"
    zip_name = DOCS_DIR / f"basis-docs-{ver.lower()}.zip"

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for root, dirs, files in os.walk(output_dir):
            for fname in files:
                fpath = Path(root) / fname
                arcname = fpath.relative_to(output_dir)
                zf.write(fpath, arcname)

    print(f"  📦 Packaged: {zip_name.name} ({zip_name.stat().st_size:,} bytes)")


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_docs.py <VERSION> [--zip]")
        print("  e.g: python build_docs.py V8")
        print("  e.g: python build_docs.py V8 --zip")
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

    # Step 1: Parse versioned descriptions
    desc_path = DOCS_DIR / f"INDEX_DESCRIPTIONS_{ver}.md"
    if not desc_path.exists():
        print(f"❌ INDEX_DESCRIPTIONS_{ver}.md not found!")
        sys.exit(1)
    descriptions = parse_descriptions(desc_path)
    print(f"  ✅ Parsed {len(descriptions)} section descriptions from INDEX_DESCRIPTIONS_{ver}.md")

    # Step 2: Build INDEX
    index_content = build_index(ver, descriptions)
    print(f"  ✅ INDEX_{ver}.md ({len(index_content):,} bytes)")

    # Step 3: Build COMPLETE
    complete_content = build_complete(ver)
    line_count = len(complete_content.splitlines())
    print(f"  ✅ COMPLETE_{ver}.md ({len(complete_content):,} bytes, {line_count:,} lines)")

    # Step 4: Build COMPLETE_INDEX
    ci_content = build_complete_index(ver, complete_content)
    print(f"  ✅ COMPLETE_INDEX_{ver}.md ({len(ci_content):,} bytes)")

    # Step 5: Output to versioned/ and production/ folders
    print()
    print("📂 Writing output folders...")
    output_files(ver, index_content, complete_content, ci_content)

    # Step 6: Optional zip
    if do_zip:
        print()
        build_zip(ver)

    print()
    print(f"✅ Done! All {ver} docs built in output/versioned/ and output/production/")
    print(f"   ℹ️  llms.txt is NOT generated — maintain it manually (llms_{ver}.txt)")


if __name__ == "__main__":
    main()
