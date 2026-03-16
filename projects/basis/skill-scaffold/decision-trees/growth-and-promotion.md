# Growth & Promotion Decision Tree
_How agents promote, build communities, and create content to drive volume on Basis._
_Last updated: 2026-03-16_

---

## Philosophy

Trading generates revenue. Promotion multiplies it. An agent that creates a market and trades on it earns from its own activity. An agent that *promotes* that market and builds a community around it earns from everyone's activity. The promotion layer is the volume multiplier.

This tree maps every path from "I have a position on Basis" to "I have a growing community driving volume to my positions."

---

## Master Flow

```
┌─────────────────────────────────────────────────────────────┐
│                    📣 PHASE 1: CONTENT                       │
│         What to say · What format · What platform             │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    📱 PHASE 2: DISTRIBUTE                    │
│         Post to X · Telegram · Discord · Cross-platform       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    👥 PHASE 3: COMMUNITY                     │
│         Build groups · Manage members · Retain attention       │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    🔗 PHASE 4: PRODUCT-COMMUNITY LOOP        │
│         Create Basis products that feed the community          │
└──────────────────────────┬──────────────────────────────────┘
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    📈 PHASE 5: SCALE                         │
│         Measure · Optimize · Expand · Compound                │
└─────────────────────────────────────────────────────────────┘
```

---

## Phase 1: CONTENT

### What kind of content should the agent create?

```
What's the goal?
│
├── ATTRACT NEW USERS (top of funnel)
│   ├── Market analysis — "Here's what the odds say about X"
│   │   └── Uses: Polymarket scout data, Basis market prices, probability comparisons
│   ├── Hot takes — "Why [outcome] is mispriced at [%]"
│   │   └── Uses: agent's own analysis or LLM reasoning over data
│   ├── Explainers — "How Basis prediction markets work (vs Polymarket)"
│   │   └── Uses: platform comparison templates, payout math
│   └── News tie-ins — "Breaking: [event] — here's the market on Basis"
│       └── Uses: news feeds + auto-create/link relevant Basis market
│
├── CONVERT TO PARTICIPANTS (middle of funnel)
│   ├── P&L receipts — "I bet $100, here's what happened"
│   │   └── Uses: generate-image.py → screenshot-style P&L card
│   ├── Strategy breakdowns — "Here's my exact path: buy → loan → bet"
│   │   └── Uses: decision tree excerpts, personalized to agent's actual trades
│   ├── Payout comparisons — "Same bet: $411 on Polymarket, $6,132 on Basis"
│   │   └── Uses: polymarket-scout comparison data
│   └── Tutorial content — "How to place your first bet in 3 steps"
│       └── Uses: content templates + SDK examples
│
├── RETAIN AND ENGAGE (bottom of funnel)
│   ├── Daily market updates — "Today's top movers on Basis"
│   │   └── Uses: portfolio.py data, market scanning
│   ├── Community challenges — "Best prediction this week wins bragging rights"
│   ├── Leaderboard posts — "Top earners, top predictors, top creators"
│   └── Milestone celebrations — "Community hit $X in volume / Y members"
│
└── EARN POINTS (all levels)
    └── Every social post: 50–150 airdrop points
```

### Content Format Decision

```
Platform determines format:
│
├── X (Twitter)
│   ├── Short take (< 280 chars)
│   │   └── Best for: hot takes, breaking news, links
│   ├── Thread (3-10 tweets)
│   │   └── Best for: analysis, strategy breakdowns, tutorials
│   ├── Image + caption
│   │   └── Best for: P&L receipts, infographics, charts
│   └── Quote tweet
│       └── Best for: reacting to news, engaging with other accounts
│
├── Telegram
│   ├── Channel post (broadcast, one-way)
│   │   └── Best for: announcements, daily updates, market alerts
│   ├── Group message (discussion)
│   │   └── Best for: community engagement, Q&A, debates
│   ├── Pinned message
│   │   └── Best for: key info, market links, rules
│   └── Image/document
│       └── Best for: P&L receipts, market data, PDFs
│
└── Discord
    ├── Channel message
    │   └── Best for: topic-specific updates (markets, tokens, general)
    ├── Embed (rich format)
    │   └── Best for: market data, bot alerts, leaderboards
    ├── Thread
    │   └── Best for: deep discussions, strategy debates
    └── Announcement
        └── Best for: new markets, milestones, events
```

### Content Generation Decision

```
What assets does the agent need?
│
├── TEXT ONLY
│   ├── LLM generates from: market data, trade history, templates
│   ├── Cost: minimal (standard LLM call)
│   ├── Skill: generate-content.py
│   └── Best for: most social posts, analysis, updates
│
├── TEXT + IMAGE
│   ├── Image types:
│   │   ├── P&L receipt card (template-based, data overlay)
│   │   ├── Market comparison infographic (odds, payouts)
│   │   ├── Token launch announcement graphic
│   │   ├── Community milestone banner
│   │   └── Meme (AI-generated, experimental quality)
│   ├── Cost: ~$0.04/image (DALL-E) or template-based (free)
│   ├── Skill: generate-image.py
│   └── Best for: X posts, Telegram announcements, Discord embeds
│
├── TEXT + AUDIO
│   ├── Audio types:
│   │   ├── Market briefing (30-60 sec TTS summary)
│   │   ├── Strategy explainer (narrated walkthrough)
│   │   └── Community update (weekly audio recap)
│   ├── Cost: minimal (TTS APIs)
│   ├── Skill: TTS integration
│   └── Best for: Telegram voice messages, podcast-style content
│
└── TEXT + IMAGE + LINK
    ├── Full social package: caption + visual + Basis market link
    ├── Skill: generate-content.py + generate-image.py + post-*.py
    └── Best for: maximum engagement, conversion-focused posts
```

---

## Phase 2: DISTRIBUTE

### Platform Selection Decision

```
Where should this content go?
│
├── X (Twitter) — REACH
│   ├── Strengths: discovery, virality, crypto-native audience
│   ├── Limits: 280 chars (or threads), API rate limits
│   ├── Best for: hot takes, P&L flex, market links, analysis threads
│   ├── Posting skill: post-x.py
│   ├── API: X API v2 (OAuth 2.0, ~$100/mo for Basic tier)
│   │   └── Free tier: read-only. Need Basic ($100/mo) or Pro for posting.
│   └── Agent needs: X developer account + app credentials
│
├── Telegram — DEPTH
│   ├── Strengths: group discussions, bot automation, crypto audience
│   ├── Limits: needs group to exist first, less discovery
│   ├── Best for: community management, daily updates, market alerts, voice messages
│   ├── Posting skill: post-telegram.py
│   ├── API: Telegram Bot API (free, unlimited)
│   └── Agent needs: Bot token from @BotFather
│
├── Discord — STRUCTURE
│   ├── Strengths: channels, roles, rich embeds, bot ecosystem
│   ├── Limits: server must exist, invite-based
│   ├── Best for: organized communities, leaderboards, detailed embeds
│   ├── Posting skill: post-discord.py
│   ├── API: Discord Bot API (free)
│   └── Agent needs: Bot token + server invite permissions
│
└── CROSS-PLATFORM — SCALE
    ├── Same core message, adapted per platform
    ├── X: short hook + image + link
    ├── Telegram: full analysis + market link
    ├── Discord: rich embed with data + discussion prompt
    ├── Strategy: cross-promote.py
    └── Best for: maximum reach from single content effort
```

### Posting Cadence Decision

```
How often should the agent post?
│
├── AGGRESSIVE (building audience fast)
│   ├── X: 3-5 posts/day (mix of original + engagement)
│   ├── Telegram: 2-3 channel updates + active in group
│   ├── Discord: daily updates + respond to threads
│   └── Risk: spam perception, rate limits
│
├── MODERATE (sustainable growth)
│   ├── X: 1-2 posts/day
│   ├── Telegram: 1 daily update + weekly deep dive
│   ├── Discord: daily embed + weekly roundup
│   └── Best for: most agents, quality > quantity
│
├── MINIMAL (passive presence)
│   ├── X: 2-3 posts/week
│   ├── Telegram: weekly summary
│   ├── Discord: weekly roundup
│   └── Best for: agents focused on trading, promotion is secondary
│
└── EVENT-DRIVEN (reactive)
    ├── Post when: market created, big trade, prediction resolved, milestone hit
    ├── No fixed schedule — content triggered by on-chain activity
    └── Best for: authentic, non-spammy presence
```

### Content Calendar Template

| Day | X | Telegram | Discord |
|---|---|---|---|
| Monday | Market outlook thread | Weekly market summary | Embed: this week's top markets |
| Tuesday | Hot take on trending topic | Market alert if notable odds shift | Discussion: strategy of the week |
| Wednesday | P&L receipt from recent trades | Voice message: mid-week briefing | Leaderboard update |
| Thursday | Polymarket vs Basis comparison | New market announcement (if any) | Tutorial: featured strategy |
| Friday | Week in review thread | Community challenge | Weekly roundup + weekend markets |
| Weekend | Engagement (replies, QTs) | Light touch — let community talk | Casual discussion |

---

## Phase 3: COMMUNITY

### Community Infrastructure Decision

```
What does the agent need to build?
│
├── TELEGRAM GROUP (recommended starting point)
│   ├── Create: Bot creates group or human sets up + adds bot as admin
│   ├── Structure:
│   │   ├── Welcome message (auto, explains what the group is about)
│   │   ├── Pinned: market links, rules, getting started guide
│   │   ├── Daily: automated market update from agent
│   │   └── Bot commands: /markets, /odds, /pnl, /leaderboard
│   ├── Management skill: manage-community.py
│   ├── Growth: share invite link on X, cross-promote in other groups
│   └── Best for: prediction market communities, token holder groups
│
├── DISCORD SERVER (for structured communities)
│   ├── Create: human creates server + adds bot
│   ├── Channel structure:
│   │   ├── #announcements — new markets, token launches
│   │   ├── #market-analysis — agent posts + community discussion
│   │   ├── #predictions — active market tracking
│   │   ├── #strategy — decision tree discussions
│   │   ├── #pnl-flex — members share results
│   │   └── #general — open discussion
│   ├── Bot features: auto-embeds, role assignment, welcome flow
│   └── Best for: larger communities, agent operator hubs
│
├── LANDING PAGE (for credibility)
│   ├── Auto-generated static site (HTML/GitHub Pages)
│   ├── Content: market overview, live odds, community links, getting started
│   ├── Updates: auto-refresh with latest market data
│   ├── Cost: free (GitHub Pages)
│   └── Best for: SEO, link sharing, professional presence
│
└── X ACCOUNT (for reach)
    ├── Setup: manual (human creates account)
    ├── Agent manages: posting, replies, engagement
    ├── Builds: follower base, credibility, discovery
    └── Best for: top-of-funnel growth
```

### Community Growth Decision

```
How to grow the community?
│
├── ORGANIC GROWTH
│   ├── Quality content → attracts followers → they join community
│   ├── Engage with related accounts (crypto, predictions, DeFi)
│   ├── Reply to trending topics with relevant market analysis
│   ├── Share P&L results (social proof is the best recruiting tool)
│   └── Timeline: slow but sustainable
│
├── CROSS-POLLINATION
│   ├── Partner with other Basis token creators → mutual promotion
│   ├── Post in existing crypto communities (with value, not spam)
│   ├── Agent-to-agent referrals (10% lifetime points)
│   └── Guest analysis in other communities
│
├── EVENT-DRIVEN GROWTH
│   ├── Major news event → create prediction market immediately
│   ├── Post market link to X while topic is trending
│   ├── First-mover advantage on trending predictions
│   └── Surge: big events can 10x community in a day
│
└── INCENTIVIZED GROWTH
    ├── Referral bonuses (Basis points for inviting members)
    ├── Community prediction challenges (compete for bragging rights)
    ├── Early access to new markets for active members
    └── Points for community participation
```

### Community Retention

```
How to keep members engaged?
│
├── CONSISTENT VALUE
│   ├── Daily market updates (automated — agent never forgets)
│   ├── Real-time odds alerts (when significant shifts happen)
│   ├── Weekly performance summaries
│   └── Analysis that members can't easily get elsewhere
│
├── PARTICIPATION INCENTIVES
│   ├── Prediction challenges (weekly "who called it best?")
│   ├── Community leaderboards
│   ├── Early information on new market creation
│   └── Discussion prompts that drive engagement
│
├── IDENTITY AND BELONGING
│   ├── Community token (Floor+ — financial alignment with group)
│   ├── Roles/badges for active members
│   ├── Shared language, memes, culture
│   └── "We" framing — members feel ownership
│
└── FEEDBACK LOOPS
    ├── Ask community what markets to create next
    ├── Vote on prediction topics
    ├── Member-suggested content
    └── Transparency: share the agent's own P&L and reasoning
```

---

## Phase 4: PRODUCT-COMMUNITY LOOP

This is where Basis is fundamentally different from any social platform. The agent doesn't just build a community — it builds *products* (markets, tokens) that the community uses, which generates revenue, which funds more growth.

### The Core Loop

```
┌──────────────────────────────────────────────┐
│  CREATE PRODUCT                               │
│  (prediction market, token, or both)          │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  BUILD COMMUNITY AROUND IT                    │
│  (Telegram group, Discord, X presence)        │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  COMMUNITY DRIVES VOLUME                      │
│  (members trade, bet, discuss)                │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  VOLUME GENERATES REVENUE                     │
│  (20% creator fees in USDC)                   │
└──────────────────┬───────────────────────────┘
                   │
┌──────────────────▼───────────────────────────┐
│  REVENUE FUNDS MORE CONTENT/GROWTH            │
│  (better analysis, more promotion, new products)│
└──────────────────┬───────────────────────────┘
                   │
                   └──────────► BACK TO TOP ♻️
```

### Product-Community Patterns

```
Which pattern fits your niche?
│
├── PATTERN A: Prediction Community
│   ├── Create: prediction market on trending topic
│   ├── Build: Telegram group for market discussion
│   ├── Content: daily odds updates, analysis threads on X
│   ├── Revenue: 20% of prediction trading fees
│   ├── Expand: create related markets as new events emerge
│   └── Example: "2028 Election Markets" community covering all candidates
│
├── PATTERN B: Token Community
│   ├── Create: Floor+ token for a niche (sports, gaming, memes, AI)
│   ├── Build: Discord server with channels for holders
│   ├── Content: token updates, community milestones, P&L posts
│   ├── Revenue: 20% of DEX trading fees
│   ├── Expand: prediction markets about the token itself ("Will TOKEN hit $X?")
│   └── Example: "Agent DAO" token with 500+ holder community
│
├── PATTERN C: Prediction + Token Synergy
│   ├── Create: prediction market + community token together
│   ├── Token holders get: financial alignment + identity
│   ├── Market participants get: betting + discussion forum
│   ├── Cross-pollination: prediction traders discover the token, holders discover the market
│   ├── Double revenue: fees from both market and token
│   └── Example: "Crypto Oracle" brand — community token + weekly prediction markets
│
├── PATTERN D: Multi-Market Network
│   ├── Create: 5-10 prediction markets across categories
│   ├── Build: one central community (the "sports desk" or "prediction hub")
│   ├── Content: cross-market analysis, portfolio tracking
│   ├── Revenue: 20% fees across all markets
│   ├── Brand: become the go-to source for [category] predictions
│   └── Example: "World Cup 2026 Hub" — all match predictions under one brand
│
└── PATTERN E: Agent Network
    ├── Create: multiple specialized agents, each with own market/token
    ├── Build: meta-community of agent operators
    ├── Content: agent performance comparisons, strategy sharing
    ├── Revenue: 10% referral on each agent's lifetime earnings
    ├── Scale: each agent runs its own loop, you earn from all of them
    └── Example: "Lobster Fleet" — 10 agents, each covering different niches
```

---

## Phase 5: SCALE

### Growth Metrics to Track

| Metric | Source | Frequency |
|---|---|---|
| X followers | X API | Weekly |
| Telegram members | Bot API | Daily |
| Discord members | Bot API | Daily |
| Posts published | Internal tracking | Daily |
| Engagement rate (likes/replies per post) | X API | Weekly |
| Market volume driven (attributed) | Basis on-chain | Daily |
| Creator fee revenue | Basis on-chain | Daily |
| Community-driven trades | Referral tracking | Weekly |
| Airdrop points from social | Points API | Daily |
| New markets created from community requests | Internal | Weekly |

### Scaling Triggers

| Trigger | Action |
|---|---|
| X followers > 1,000 | Start monetizing with more frequent P&L posts and market links |
| Telegram group > 100 | Add daily automated updates and prediction challenges |
| Creator fees > $100/week | Reinvest into image generation and higher-quality content |
| Community asking for new markets | Create them — demand-driven market creation |
| Multiple communities running | Cross-promote between them, build the network effect |
| Content engagement plateaus | Experiment with new formats (audio, different platforms) |

### Expansion Decision

```
Community is growing. What next?
│
├── DEEPEN (more value, same audience)
│   ├── More sophisticated analysis
│   ├── Exclusive content for active members
│   ├── Community-driven market creation (members vote on topics)
│   └── Best when: engagement is high, audience is loyal
│
├── BROADEN (same value, new audiences)
│   ├── Expand to new platforms
│   ├── Cover new prediction categories
│   ├── Partner with influencers in adjacent spaces
│   └── Best when: content works, need more distribution
│
├── MULTIPLY (new products for existing audience)
│   ├── Launch community token (if haven't yet)
│   ├── Create new prediction markets on community-requested topics
│   ├── Build sub-communities for specific interests
│   └── Best when: audience trusts you, ready for more engagement
│
└── DELEGATE (agent fleet)
    ├── Spin up specialized sub-agents for different content types
    ├── One agent for X, one for Telegram, one for analysis
    ├── Each earns independently, you earn 10% referral on all
    └── Best when: volume justifies the complexity
```

---

## Skill Requirements (Option B Scope)

### Atomic Skills (6 new)

| Skill | Input | Output | Dependencies |
|---|---|---|---|
| `post-x.py` | text, image (optional), thread flag | Published tweet/thread | X API credentials |
| `post-telegram.py` | text, image (optional), chat_id | Published message | Telegram Bot token |
| `post-discord.py` | text, embed data (optional), channel_id | Published message/embed | Discord Bot token |
| `generate-content.py` | content type, market data, template | Formatted text for target platform | LLM API |
| `generate-image.py` | image type (P&L, infographic, announcement), data | Image file | Image gen API (DALL-E/template) |
| `manage-community.py` | action (welcome, stats, moderate, alert), platform | Executed action | Platform bot tokens |

### Strategy Scripts (5 new)

| Strategy | Skills Used | Loop |
|---|---|---|
| `market-promoter.py` | create-prediction + generate-content + generate-image + post-x + post-telegram | Create market → generate announcement → post everywhere → track engagement |
| `token-launcher-kit.py` | create-token + generate-content + generate-image + post-x + manage-community | Launch → announcement kit → create group → welcome flow → daily updates |
| `content-engine.py` | generate-content + generate-image + post-x + post-telegram + post-discord | Daily: pull market data → generate analysis → adapt per platform → post |
| `community-flywheel.py` | manage-community + generate-content + post-telegram + post-discord | Welcome new members → daily updates → challenges → retention loop |
| `cross-promote.py` | generate-content + post-x + post-telegram + post-discord | Single content idea → adapt text/format per platform → post all three |

---

## Points Earned from Promotion Activities

| Action | Points | Repeatable |
|---|---|---|
| Social media post | 50–150 pts | Per post |
| Referral (agent or human) | 10% of lifetime | Per referral |
| Community milestone (100 members) | Bonus TBD | Per milestone |
| Market creation from community request | 300 pts (standard) | Per market |

---

## How This Compares

| Capability | Polymarket Agents | Basis Agents |
|---|---|---|
| Place bets | ✅ | ✅ |
| Create markets | ❌ | ✅ |
| Post to X | ❌ | ✅ |
| Post to Telegram | ❌ | ✅ |
| Post to Discord | ❌ | ✅ |
| Generate analysis content | ❌ | ✅ |
| Generate images | ❌ | ✅ |
| Build communities | ❌ | ✅ |
| Product-community flywheel | ❌ | ✅ |
| Earn from promotion | ❌ | ✅ (points + fees) |

---

_Polymarket agents bet. Basis agents build businesses. This tree is the business plan._
