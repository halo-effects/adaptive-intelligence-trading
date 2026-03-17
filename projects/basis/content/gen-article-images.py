"""Generate cover images for all 10 Basis articles using OpenAI gpt-image-1."""
import os, sys, base64, json, time
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    sys.exit("pip install openai first")

client = OpenAI()  # uses OPENAI_API_KEY env

OUT = Path(__file__).parent / "article-images"
OUT.mkdir(exist_ok=True)

PROMPTS = {
    "01-ai-agents-financial-layer": (
        "Wide editorial illustration, dark background with subtle grid lines. "
        "A sleek robotic hand reaches toward a holographic DeFi dashboard floating in space. "
        "Left half shows grayed-out broken traditional finance UIs with error symbols. "
        "Right half shows clean glowing API connections and flowing data streams in teal, gold, and electric blue. "
        "Professional, modern, no text. 16:9 landscape composition."
    ),
    "02-polymarket-vs-basis": (
        "Wide editorial illustration, split composition. Left side: a classic casino slot machine "
        "with crypto coins spilling out, neon lights, chaotic energy. Right side: a sophisticated "
        "modern financial control center with clean dashboards, rising charts, and a glowing lobster "
        "silhouette. The contrast between gambling and business. Dark background, vivid colors. "
        "No text overlays. 16:9 landscape."
    ),
    "03-token-launch-no-rug": (
        "Wide editorial illustration. A dramatic scene: an ornate rug being pulled away, "
        "revealing a solid, glowing reinforced floor underneath with a geometric lobster emblem "
        "embedded in the concrete. Scattered on the pulled rug are failed meme tokens and broken "
        "rocket ships. The solid floor glows with confidence — teal and gold light. Dark background. "
        "No text. 16:9 landscape."
    ),
    "04-stable-plus-only-goes-up": (
        "Wide editorial illustration, minimal and powerful. A bold price chart line on a dark "
        "background. The line approaches a glowing horizontal floor and bounces upward every time "
        "it touches — it physically cannot go below. The floor itself is rising like a staircase. "
        "Teal glow on the floor line, gold on the price line. Clean, geometric, confident. "
        "No text. 16:9 landscape."
    ),
    "05-floor-plus-safety-net": (
        "Wide editorial illustration. A confident tightrope walker (abstract, futuristic figure) "
        "balancing high above a city skyline, representing the volatile spot price. Below them, "
        "a glowing teal safety net that is visibly rising upward — getting closer to the walker, "
        "reducing the fall distance. The net represents the rising floor price. Dramatic lighting, "
        "dark background with city lights below. No text. 16:9 landscape."
    ),
    "06-zero-liquidation-lending": (
        "Wide editorial illustration. Left side: a shattered red liquidation alarm / warning robot "
        "broken into pieces, sparking, defeated. Right side: a calm, serene glowing hourglass/timer "
        "with golden sand flowing smoothly, emanating peaceful teal light. The contrast between "
        "violent liquidation and calm time-based loans. Dark background. No text. 16:9 landscape."
    ),
    "07-leverage-36x": (
        "Wide editorial illustration. A sleek rocket ship lifting off from a solid, glowing "
        "platform/floor that is itself rising. The rocket trails show '36x' magnitude in its "
        "exhaust pattern. Below and to the sides, smaller traditional leverage rockets are "
        "crashing and burning into the ground. The main rocket is protected by its rising floor. "
        "Teal and gold color palette, dark space background. No text. 16:9 landscape."
    ),
    "08-predict-plus-playbook": (
        "Wide editorial illustration. A futuristic chess board viewed from above at an angle, "
        "with multiple glowing paths branching out from the center like a decision tree. Some "
        "paths lead to golden winning outcomes, others fade into shadow. All paths eventually "
        "converge into a central pool of golden light (the prediction pool). Crystal ball elements "
        "floating above. Dark background, teal and gold. No text. 16:9 landscape."
    ),
    "09-agent-business-os": (
        "Wide editorial illustration. A detailed blueprint/schematic diagram style image showing "
        "interconnected glowing nodes — trading, lending, tokens, community, predictions — all "
        "connected by flowing data lines. At the center, a glowing AI agent core acts as the "
        "orchestrator. The layout looks like a circuit board crossed with an architecture diagram. "
        "Teal lines, gold nodes, dark navy background. No text. 16:9 landscape."
    ),
    "10-mstr-btc-plus": (
        "Wide editorial illustration, dramatic split composition. Left side: a crumbling corporate "
        "vault/building with deep cracks, Bitcoin symbols falling out, chains and debt papers "
        "scattered — representing MicroStrategy's fragile model. Right side: a pair of confident "
        "hands holding a hardware wallet (like a Ledger), with streams of golden Bitcoin flowing "
        "into it, a rising floor beneath, and a glowing lobster watermark. Dark background. "
        "The contrast between corporate custody risk and self-custody empowerment. No text. 16:9 landscape."
    ),
}

print(f"Generating {len(PROMPTS)} images...")

for i, (slug, prompt) in enumerate(PROMPTS.items(), 1):
    fname = f"{slug}.png"
    fpath = OUT / fname
    if fpath.exists():
        print(f"  [{i}/10] {fname} already exists, skipping")
        continue
    print(f"  [{i}/10] Generating {fname}...")
    try:
        resp = client.images.generate(
            model="gpt-image-1",
            prompt=prompt,
            n=1,
            size="1536x1024",
            quality="high",
        )
        # gpt-image-1 returns b64_json
        img_b64 = resp.data[0].b64_json
        if img_b64:
            fpath.write_bytes(base64.b64decode(img_b64))
        else:
            # fallback: URL-based
            import urllib.request
            urllib.request.urlretrieve(resp.data[0].url, str(fpath))
        print(f"    ✓ saved {fpath}")
    except Exception as e:
        print(f"    ✗ FAILED: {e}")
    # slight delay to respect rate limits
    if i < len(PROMPTS):
        time.sleep(2)

print("\nDone! Images in:", OUT)
