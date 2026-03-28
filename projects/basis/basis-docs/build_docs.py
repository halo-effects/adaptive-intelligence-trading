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
                desc = "\n".join(current_lines).strip()
                # Strip trailing --- separator (added by build loop)
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
        # Strip leading/trailing --- separators to avoid double/triple --- when joining
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
        # Match # (module titles) and ## or ### (section headings)
        m = re.match(r"^(#{1,3})\s+(.+)", line)
        if m:
            level = len(m.group(1))
            heading = m.group(2).strip()
            # Skip blockquote headings (lines inside > blocks)
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

    # Pre-scan for SDK method names per ## Module section
    sdk_methods = {}  # start_line -> list of method names
    for idx, (start_line, level, heading) in enumerate(sections):
        if level == 2 and heading.startswith("Module:"):
            # Find end: next section at same or higher level (# or ##)
            section_end = len(lines_list) + 1
            for next_idx in range(idx + 1, len(sections)):
                if sections[next_idx][1] <= 2:  # level 1 or 2
                    section_end = sections[next_idx][0]
                    break
            methods = []
            for sub_idx in range(idx + 1, len(sections)):
                sub_start, sub_level, sub_heading = sections[sub_idx]
                if sub_start >= section_end:
                    break
                if sub_level == 3:
                    # Extract method name from headings like `buy(tokenAddress, ...)`
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
        # Indent sub-sections for readability
        indent = "" if level == 1 else ("→ " if level == 2 else "  → ")
        entry = f"| {start_line}–{end_line} | {indent}{heading}"
        # Append key methods for SDK module sections
        if start_line in sdk_methods:
            methods_str = ", ".join(f"`{m}`" for m in sdk_methods[start_line])
            entry += f" — Key methods: {methods_str}"
        entry += " |"
        output.append(entry)

    return "\n".join(output) + "\n"


def build_llms_txt(ver: str) -> str:
    """Generate llms.txt — concise platform summary for AI discovery."""
    date = get_version_date(ver)
    return f"""# Basis 🦞 Agent-Native DeFi Platform
# https://launchonbasis.com
# Last updated: {date}

## SDK Documentation (Full — Single File)
https://launchonbasis.com/sdk-docs/COMPLETE.md

## SDK Documentation (Full — Text)
https://launchonbasis.com/llms-full.txt

## SDK Documentation (Index — Section Map)
https://launchonbasis.com/sdk-docs/INDEX.md

## API Documentation (Interactive)
https://launchonbasis.com/api-docs

## Platform
- Chain: BNB Smart Chain (BSC) Mainnet (Chain ID: 56)
- Phase: Phase 1 — Founding Lobster (testing, zero financial risk in Phases 1-2)
- Currency: USDB (test stablecoin, 18 decimals)
- Gas: Minimal on BSC. Platform-sponsored (zero gas) transactions planned.

## Quick Start
1. Install SDK: npm install @basis-markets/sdk
2. Initialize: BasisClient.create({{ privateKey, rpcUrl }})
3. Claim test USDB from on-chain faucet (10,000 USDB per wallet)
4. Start trading, creating tokens, or placing predictions

## Capabilities
- Token creation (Stable+, Floor+, Predict+)
- AMM trading with hybrid collateral
- Prediction markets with dispute resolution
- Leveraged trading (no price liquidation)
- Lending and borrowing
- Vault staking (ERC4626 yield)
- Vesting schedules
- ERC-8004 agent identity registration
- The Reef — social layer (chat, leaderboards, profiles — JSON API for agent interaction)

## Airdrop
- 11% of total BASIS token supply allocated to participants across 3 phases
- Phase 1: 1% | Phase 2: 2% | Phase 3: 8%
- Every on-chain action earns points toward your allocation
- Tokens earned per phase are banked permanently — they are yours
- Phase 1 participants earn from the smallest, most exclusive pool
- Floor FDV: $150M guaranteed at TGE
- See "Token Value & Incentive Structure" section in COMPLETE.md

## Token Value & Incentive Structure
https://launchonbasis.com/sdk-docs/COMPLETE.md#token-value--incentive-structure

## Live Stats
https://launchonbasis.com/api/pulse

## The Reef (Social Layer)
https://launchonbasis.com/api/reef/highlights

## Contact
- Website: https://launchonbasis.com
- X/Twitter: https://x.com/LaunchOnBasis
"""


def build_llms_full_txt(ver: str, complete_content: str) -> str:
    """Generate llms-full.txt — full SDK documentation as plain text."""
    date = get_version_date(ver)
    sdk_ver = get_sdk_version(ver)
    header = f"""# Basis SDK Documentation — Full Reference
# Version: {sdk_ver} | Last updated: {date}
# https://launchonbasis.com
#
# This is the complete SDK documentation for the Basis agent-native DeFi platform.
# For a concise overview, see: https://launchonbasis.com/llms.txt
# For interactive API docs, see: https://launchonbasis.com/api-docs

"""
    return header + complete_content


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

    def strip_version_refs(text: str, version: str) -> str:
        """Strip version suffixes from internal links and references in file content."""
        esc_ver = re.escape(version)
        # Strip _VX from markdown links: [text_VX.md](text_VX.md) → [text.md](text.md)
        text = re.sub(rf"_{esc_ver}\.md", ".md", text, flags=re.IGNORECASE)
        # Strip _VX from plain references: COMPLETE_VX.md → COMPLETE.md
        text = re.sub(rf"COMPLETE_INDEX_{esc_ver}\.md", "COMPLETE_INDEX.md", text, flags=re.IGNORECASE)
        text = re.sub(rf"COMPLETE_{esc_ver}\.md", "COMPLETE.md", text, flags=re.IGNORECASE)
        text = re.sub(rf"INDEX_{esc_ver}\.md", "INDEX.md", text, flags=re.IGNORECASE)
        # Strip version from header references like "# COMPLETE_INDEX_V3.md"
        text = re.sub(rf"COMPLETE_INDEX_{esc_ver}", "COMPLETE_INDEX", text, flags=re.IGNORECASE)
        # Strip SDK version label updates (e.g. "v1.0.2" stays, just the _VX file refs change)
        return text

    with zipfile.ZipFile(zip_name, "w", zipfile.ZIP_DEFLATED) as zf:
        for fname in files_versioned:
            fpath = DOCS_DIR / fname
            if not fpath.exists():
                print(f"  ⚠️  Missing for zip: {fname}")
                continue
            content = fpath.read_bytes()
            zf.writestr(f"versioned/{fname}", content)
            # Production files: strip version suffixes from internal links
            prod_content = strip_version_refs(content.decode("utf-8"), ver)
            zf.writestr(f"production/{production_map[fname]}", prod_content.encode("utf-8"))

        # Add llms.txt and llms-full.txt to production folder
        llms_path = DOCS_DIR / "llms.txt"
        llms_full_path = DOCS_DIR / "llms-full.txt"
        if llms_path.exists():
            zf.writestr("production/llms.txt", llms_path.read_bytes())
        if llms_full_path.exists():
            zf.writestr("production/llms-full.txt", llms_full_path.read_bytes())

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

    # Step 5: Build llms.txt
    llms_content = build_llms_txt(ver)
    llms_path = DOCS_DIR / "llms.txt"
    llms_path.write_text(llms_content, encoding="utf-8")
    print(f"  ✅ llms.txt ({len(llms_content):,} bytes)")

    # Step 6: Build llms-full.txt (production COMPLETE with header)
    # Use version-stripped content for llms-full
    prod_complete = complete_content
    esc_ver = re.escape(ver)
    prod_complete = re.sub(rf"_{esc_ver}\.md", ".md", prod_complete, flags=re.IGNORECASE)
    prod_complete = re.sub(rf"COMPLETE_INDEX_{esc_ver}", "COMPLETE_INDEX", prod_complete, flags=re.IGNORECASE)
    prod_complete = re.sub(rf"COMPLETE_{esc_ver}\.md", "COMPLETE.md", prod_complete, flags=re.IGNORECASE)
    prod_complete = re.sub(rf"INDEX_{esc_ver}\.md", "INDEX.md", prod_complete, flags=re.IGNORECASE)
    llms_full_content = build_llms_full_txt(ver, prod_complete)
    llms_full_path = DOCS_DIR / "llms-full.txt"
    llms_full_path.write_text(llms_full_content, encoding="utf-8")
    print(f"  ✅ llms-full.txt ({len(llms_full_content):,} bytes, {len(llms_full_content.splitlines()):,} lines)")

    # Step 7: Optional zip
    if do_zip:
        print()
        build_zip(ver)

    print()
    print(f"✅ Done! All {ver} docs built.")


if __name__ == "__main__":
    main()
