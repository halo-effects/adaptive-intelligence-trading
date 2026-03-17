"""
Package all 10 articles with proper frontmatter for the Basis website.
Output: content/blog/<slug>.md files ready to drop into the project.
"""
import os, shutil, re
from pathlib import Path

SRC = Path(__file__).parent / "articles"
OUT = Path(__file__).parent / "website-ready" / "content" / "blog"
OUT.mkdir(parents=True, exist_ok=True)

# Article metadata: (source_filename, slug, title, excerpt, readTime, category, tags, coverImage)
ARTICLES = [
    (
        "01-why-ai-agents-need-their-own-financial-layer.md",
        "why-ai-agents-need-their-own-financial-layer",
        "Why AI Agents Need Their Own Financial Layer",
        "DeFi was built for humans clicking buttons. AI agents need programmable finance with real business logic — not another DEX.",
        8,
        "Vision",
        ["AI Agents", "DeFi", "Infrastructure"],
        "/content/blog/why-ai-agents-need-their-own-financial-layer.png",
    ),
    (
        "02-polymarket-slot-machine-vs-basis-business.md",
        "polymarket-slot-machine-vs-basis-business",
        "Polymarket Gives Agents a Slot Machine. Basis Gives Them a Business.",
        "$836M in losing bets exposed Polymarket's structural flaw. Here's what happens when prediction markets actually pay.",
        8,
        "Analysis",
        ["Polymarket", "Predict+", "Prediction Markets"],
        "/content/blog/polymarket-slot-machine-vs-basis-business.png",
    ),
    (
        "05-token-launch-without-the-rug.md",
        "token-launch-without-the-rug",
        "Token Launch Without the Rug: How Zero Pre-Mint Changes Everything",
        "No pre-mint. No insider allocation. Elastic supply with a rising floor. The anti-Pump.fun.",
        9,
        "Product",
        ["Token Launch", "Stable+", "Floor+"],
        "/content/blog/token-launch-without-the-rug.png",
    ),
    (
        "07-stable-plus-the-token-that-can-only-go-up.md",
        "stable-plus-the-token-that-can-only-go-up",
        "Stable+: The Token That Can Only Go Up",
        "A token with a mathematically enforced floor that only rises. Pair it with BTC, ETH, or SOL for blue-chip exposure with structural protection.",
        10,
        "Product",
        ["Stable+", "Trading", "Blue-Chip Pairs"],
        "/content/blog/stable-plus-the-token-that-can-only-go-up.png",
    ),
    (
        "08-floor-plus-speculation-with-a-safety-net.md",
        "floor-plus-speculation-with-a-safety-net",
        "Floor+: Speculation With a Safety Net",
        "Full price discovery above a rising floor. Trade like you always have — but the floor catches you.",
        11,
        "Product",
        ["Floor+", "Trading", "Leverage"],
        "/content/blog/floor-plus-speculation-with-a-safety-net.png",
    ),
    (
        "04-zero-liquidation-lending.md",
        "zero-liquidation-lending",
        "Zero-Liquidation Lending: Why 100% LTV Changes Everything",
        "Borrow the full value of your tokens with no price-based liquidation. Only a timer you control.",
        9,
        "Product",
        ["Lending", "100% LTV", "Loans"],
        "/content/blog/zero-liquidation-lending.png",
    ),
    (
        "09-dynamic-leverage-without-liquidation.md",
        "dynamic-leverage-without-liquidation",
        "Dynamic Leverage Without Liquidation: How ~36x Actually Works",
        "Up to ~36x leverage calculated against a floor that only rises. No liquidation. No margin calls. Just math.",
        11,
        "Product",
        ["Leverage", "Trading", "Risk Management"],
        "/content/blog/dynamic-leverage-without-liquidation.png",
    ),
    (
        "06-the-predict-plus-playbook.md",
        "the-predict-plus-playbook",
        "The Predict+ Playbook: Five Strategies for Smarter Prediction Markets",
        "Binary outcomes are just the beginning. Here are five strategies that turn prediction markets into a real business.",
        10,
        "Strategy",
        ["Predict+", "Prediction Markets", "Strategy"],
        "/content/blog/the-predict-plus-playbook.png",
    ),
    (
        "03-the-agent-business-operating-system.md",
        "the-agent-business-operating-system",
        "The Agent Business Operating System",
        "4 decision trees, 18 strategies, 16 skills. The complete framework for building an autonomous DeFi business on Basis.",
        9,
        "Vision",
        ["AI Agents", "Framework", "Strategy"],
        "/content/blog/the-agent-business-operating-system.png",
    ),
    (
        "10-the-mstr-problem-bitcoin-treasury-without-the-blowup-risk.md",
        "the-mstr-problem-bitcoin-treasury-without-the-blowup-risk",
        "The MSTR Problem: Bitcoin Treasury Without the Blowup Risk",
        "MicroStrategy holds your Bitcoin. BTC+ gives it back. wBTC in, wBTC out. 100% LTV loans — tax-free. The infinite money glitch.",
        12,
        "Analysis",
        ["BTC+", "Bitcoin", "MicroStrategy", "Treasury"],
        "/content/blog/the-mstr-problem-bitcoin-treasury-without-the-blowup-risk.png",
    ),
]

# Publish dates: space them out starting from today, every 2-3 days
DATES = [
    "2026-03-17",  # Article 1
    "2026-03-19",  # Article 2
    "2026-03-21",  # Article 3
    "2026-03-23",  # Article 4
    "2026-03-25",  # Article 5
    "2026-03-27",  # Article 6
    "2026-03-29",  # Article 7
    "2026-03-31",  # Article 8
    "2026-04-02",  # Article 9
    "2026-04-04",  # Article 10
]


def make_frontmatter(title, excerpt, date, readTime, category, tags, coverImage):
    tag_str = ", ".join(f'"{t}"' for t in tags)
    return f'''---
title: "{title}"
excerpt: "{excerpt}"
author: "Basis Team"
date: "{date}"
readTime: {readTime}
category: "{category}"
tags: [{tag_str}]
coverImage: "{coverImage}"
---

'''


for i, (src_file, slug, title, excerpt, readTime, category, tags, coverImage) in enumerate(ARTICLES):
    src_path = SRC / src_file
    if not src_path.exists():
        print(f"  MISSING: {src_file}")
        continue

    content = src_path.read_text(encoding="utf-8")

    # Strip the existing H1 title line and subtitle (first 4-5 lines) since frontmatter has the title
    # Remove leading # Title line and the italic subtitle and --- separator
    lines = content.split("\n")
    # Find where the actual content starts (after the title block)
    start = 0
    for j, line in enumerate(lines):
        if j == 0 and line.startswith("# "):
            continue
        if j <= 4 and (line.strip() == "" or line.strip() == "---" or line.startswith("*")):
            continue
        start = j
        break

    body = "\n".join(lines[start:])

    frontmatter = make_frontmatter(title, excerpt, DATES[i], readTime, category, tags, coverImage)
    out_path = OUT / f"{slug}.md"
    out_path.write_text(frontmatter + body, encoding="utf-8")
    print(f"  [{i+1}/10] {slug}.md ({len(body)} chars)")

print(f"\nDone! Files in: {OUT}")
print(f"\nReminder: Cover images should go in /public/content/blog/ with matching filenames (.png)")
