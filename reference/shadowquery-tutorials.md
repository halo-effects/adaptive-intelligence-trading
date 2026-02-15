# ShadowQuery Tutorial Notes
*Captured from Pete's YouTube tutorials — 2026-02-12*

## What is ShadowQuery?
A Windows tool that captures the hidden "shadow queries" ChatGPT performs when it searches the web to answer user questions. These long-tail search terms have zero competition and can be targeted with optimized pages to get your business recommended by AI.

---

## Tutorial 1: Keyword Discovery (XZlw2Gz90tg)

**Key concept:** When ChatGPT can't answer from its parameters alone, it searches the web (Bing) using internal "shadow queries" — invisible to users.

**How it works:**
1. ShadowQuery runs a Windows app + browser that captures ChatGPT's hidden search terms
2. Enter a seed query (e.g. "pest control near me Gold Coast")
3. ChatGPT triggers 2-10 shadow queries per search
4. ShadowQuery captures those exact long-tail terms
5. Checks Bing competition — typically **zero competition**

**Important:**
- Use a fresh Google account (not personal) to avoid bias in ChatGPT results
- Only works for queries that trigger web search (not simple knowledge questions)
- Also captures auto-suggested terms and AI-generated "simulated" terms

---

## Tutorial 2: Finding High-Volume Keywords (ZUyJLGvaQdU)

**Method:**
1. Start with your base term (e.g. "pest control")
2. Screenshot ShadowQuery's example terms page
3. Paste screenshot into ChatGPT/Grok/Gemini: "Revise this to suit my base term which is [your niche]"
4. Get high-volume variations (e.g. "pest control near me" = 300K/month)

**For each high-volume term:**
1. Run through ShadowQuery
2. Right-click → "Copy all" to save shadow queries, auto-suggested, and simulated results
3. Competition is typically zero

**Pro tips:**
- ChatGPT geo-targets via IP — swap locations as needed
- Take all terms → Google Deep Research → ask for search volume summary (discovers even more terms)

---

## Tutorial 3: Multiple Runs & Simulated Results (ZExDvcQD1Ic)

**Key insight:** Run the same term multiple times — get different shadow queries each time, up to 4-6 unique sets before repeating.

**Simulated Results:**
- When real shadow queries can't be captured, AI generates simulated ones
- Improve over time — all users' real results feed into a shared database
- Currently scoring 7.5-9/10 accuracy vs real shadow queries

**Cross-LLM coverage:**
- ChatGPT: 2-10 shadow queries per search
- Grok: 15-20 shadow queries
- Gemini Deep Research: up to 500 shadow queries

---

## Tutorial 4: Page Prompt Builder (KQ_agTAKmHI)

**Workflow:**
1. Go to Shadow Query Page Prompt Builder
2. Answer questions: long-tail term, full business info, logo image URL
3. Click "Generate Gemini Prompt"
4. Copy prompt → **Gemini Canvas** → paste
5. Gemini creates fully optimized HTML page with structured data, schema, JSON-LD, Open Graph
6. Copy code → save as HTML (filename = search term, no spaces)
7. Repeat for each shadow query term

**Hosting & Indexing:**
- Host on your domain or AWS bucket
- **Submit to Bing Webmaster Tools** (critical for ChatGPT)
- Use "Index Me Now" service for fast indexing
- Google: 8-12 hours to index
- Bing: up to 1 week

**Scale options:**
- DIY via Gemini Canvas
- Listicles.tech (upcoming tool with internal linking)
- Done-for-you service: shadowquery.tech/dfy

---

## Tutorial 5: AIM Builder — Web Tool (cZhFze2uVhE)

**Two-part process on shadowquery.tech/AIM:**

**Part 1: Individual Pages**
1. Enter email, shadow query term, business info, hero image URL
2. "Generate Gemini Prompt" (~2 min)
3. Copy → Gemini Canvas → save as HTML
4. Repeat for 10-15 pages per mini site

**Part 2: Index + Site Structure**
1. Switch to "Atomic Intent Mesh Builder" tab
2. Paste file names → enter main URL + image URL → Generate
3. Pick longest-tail folder name (captures Google traffic too)
4. Download: index.html, sitemap.xml, llms.txt

**Hosting:**
- Upload folder to domain or register new keyword-rich domain
- Long-tail terms don't need domain authority to rank
- Send backlinks to folder for higher-volume term ranking

---

## Tutorial 6: AIM Builder — Custom GPT Version (9h2_zc-iHgQ)

**Same output, different interface (ChatGPT GPT):**

1. Click "Go" in the Atomic Intent Mesh Builder GPT
2. Screenshot your folder of HTML files → paste (reads filenames via vision)
3. Provide main URL + logo URL
4. GPT suggests folder name based on intent analysis
5. Generates Gemini prompt → paste into Gemini Canvas

**Outputs (say "yes" to each):**
1. index.html — listicle hub linking all internal pages
2. sitemap.xml — for Bing Webmaster Tools submission
3. llms.txt — tells AI crawlers about content structure

---

## Complete Pipeline Summary

```
1. Pick niche base term
2. Generate high-volume variations (ChatGPT/Grok/Gemini)
3. Run each through ShadowQuery (multiple times per term)
4. Collect: shadow queries + auto-suggested + simulated results
5. For each shadow query:
   a. AIM Builder → generate Gemini prompt
   b. Gemini Canvas → create optimized HTML page
   c. Save as HTML
6. Build index page + sitemap.xml + llms.txt via AIM Builder
7. Upload folder to domain
8. Submit to Bing Webmaster Tools
9. Index via "Index Me Now" or similar
10. Verify in ChatGPT once Bing indexes (~1 week)
```

**Goal:** Build multiple mini sites of 10-21 pages each, covering every possible shadow query in your niche. Complete niche domination in AI recommendations.
