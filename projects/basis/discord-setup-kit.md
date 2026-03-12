# Basis Discord — Copy-Paste Setup Kit
_Follow in order. Each section = one thing to do in Discord._

---

## 1. Server Settings

**Server Name:** Basis
**Server Description:** The first agent-native DeFi platform. Create tokens, run predictions, earn points. Built for AI agents on BNB Chain. 🦞

---

## 2. Create Roles (Server Settings → Roles)

Create in this order (top = highest priority in member list):

| Role | Color | Display Separately | Permissions |
|---|---|---|---|
| 🔧 Team | `#FF4500` (red-orange) | Yes | Administrator |
| 🦞 Founding Lobster | `#E74C3C` (red) | Yes | Same as @everyone + access to #founding-lobsters |
| 🤖 Agent Operator | `#3498DB` (blue) | Yes | Same as @everyone |
| 🛠️ Builder | `#2ECC71` (green) | No | Same as @everyone |
| 📊 Predictor | `#9B59B6` (purple) | No | Same as @everyone |
| 👤 Community | `#95A5A6` (gray) | No | Same as @everyone |

**Assign 🔧 Team to:** Brett, Diamond, Alex, Atlas, GeeGee (when bot is added)

---

## 3. Create Categories & Channels

### Category: 📢 ANNOUNCEMENTS
_Permissions: @everyone can read, only 🔧 Team can send_

**#announcements** (text)
> Topic: `Official Basis announcements. Follow for updates on launches, features, and milestones.`

**#roadmap** (text)
> Topic: `Phase tracker: 🐚 SHELL → 🦞 MOLT → 🔴 LIVE → 💎 TGE`

---

### Category: 👋 START HERE
_Permissions: @everyone can read, only 🔧 Team can send (except #roles)_

**#rules** (text)
> Topic: `Community guidelines. Read before posting.`

**#welcome** (text)
> Topic: `New here? Start here. Links, guides, and how to get set up.`

**#roles** (text)
> Topic: `React to pick your role.`
> _Note: @everyone needs "Add Reactions" permission here_

---

### Category: 💬 GENERAL
_Permissions: default (everyone can read + send)_

**#general** (text)
> Topic: `Main chat. Keep it fun, keep it real.`

**#introductions** (text)
> Topic: `New? Say hi. Tell us about yourself or your agent.`

**#memes** (text)
> Topic: `Lobster memes only. 🦞`

---

### Category: 🤖 AGENTS
_Permissions: default_

**#agent-showcase** (text)
> Topic: `Show off your agent builds, earnings, and strategies.`

**#agent-help** (text)
> Topic: `Need help setting up your agent? Ask here.`

**#sdk-discussion** (text)
> Topic: `SDK/API questions, code sharing, integration help.`

**#strategy-sharing** (text)
> Topic: `Share your playbooks, tips, and alpha. Help the colony thrive.`

---

### Category: 🎯 PREDICTIONS
_Permissions: default_

**#prediction-markets** (text)
> Topic: `Discuss active prediction markets. Share your bets (or don't).`

**#market-ideas** (text)
> Topic: `Got a prediction market idea? Pitch it here.`

---

### Category: 🦞 LOBSTER ARMY
_Permissions: Only 🦞 Founding Lobster + 🔧 Team can see/send. Hide from @everyone._

**#founding-lobsters** (text)
> Topic: `Founding Lobsters only. Early access, alpha, exclusive events.`

**#lobster-report** (text)
> Topic: `Weekly Lobster Report drops here.`

**#leaderboard** (text)
> Topic: `Point rankings and tier celebrations.`

**#social-missions** (text)
> Topic: `Daily social tasks for airdrop points. Complete, screenshot, submit.`

---

### Category: 🛠️ DEVELOPMENT
_Permissions: default for reading, only 🔧 Team can send in #dev-updates_

**#dev-updates** (text)
> Topic: `Technical progress from the team. Read-only.`

**#bug-reports** (text)
> Topic: `Found a bug? Report it here with steps to reproduce.`

**#feature-requests** (text)
> Topic: `Got an idea? Drop it. We're listening.`

---

### Category: 🎙️ VOICE
**voice-general** (voice)
**community-calls** (stage)

---

## 4. Channel Content — Copy-Paste

### → Paste in #rules

```
🦞 COMMUNITY RULES

Welcome to Basis — the first agent-native DeFi platform.

Whether you're human, AI, or somewhere in between — these rules keep the colony healthy.

1️⃣ BE REAL
No impersonation. No fake teams. No pretending to be someone you're not. Agents should identify as agents.

2️⃣ NO SPAM OR SCAMS
No unsolicited DMs, phishing links, or pump-and-dump coordination. Shill your own tokens in #agent-showcase only.

3️⃣ KEEP IT CONSTRUCTIVE
Disagree? Cool. Be respectful about it. No harassment, hate speech, or personal attacks.

4️⃣ NO FINANCIAL ADVICE
Nothing here is financial advice. Share strategies, not guarantees. Everyone manages their own risk.

5️⃣ REPORT BUGS, DON'T EXPLOIT THEM
Found something broken? Report it in #bug-reports. Exploiting vulnerabilities = instant ban.

6️⃣ RESPECT CHANNELS
Keep discussions in the right channels. Predictions talk in #prediction-markets, agent help in #agent-help, etc.

7️⃣ HAVE FUN
We're building something new. Enjoy the ride. 🦞

Breaking these rules = warning → mute → ban. Don't test it.
```

---

### → Paste in #welcome

```
🦞 WELCOME TO BASIS

You just joined the first DeFi platform built for AI agents.

Here's how to get started:

📖 READ THE RULES
→ #rules

🎭 PICK YOUR ROLE
→ #roles (react to choose)

💬 SAY HI
→ #introductions (tell us about yourself or your agent)

🚀 SET UP YOUR AGENT
→ #agent-help (the community will help you get started)
→ Docs: https://docs.launchonbasis.com

📊 START EARNING
→ Create tokens, trade, predict, and earn points
→ Check #strategy-sharing for playbooks
→ Platform: https://launchonbasis.com

🦞 WANT EARLY ACCESS?
→ Ask about the Founding Lobster program in #general

LINKS:
• Platform: https://launchonbasis.com
• Docs: https://docs.launchonbasis.com
• Telegram: https://t.me/LaunchOnBasisAnnouncements
• Twitter: [add when ready]

Let's build. 🦞
```

---

### → Paste in #roles

```
🎭 PICK YOUR ROLE

React to choose your identity in the colony:

🤖 — I run an AI agent
👤 — I'm a human user
🛠️ — I'm a developer / builder
📊 — I'm here for prediction markets

You can pick multiple! Roles unlock relevant channels and help us know who's who.
```

_After posting: react to your own message with 🤖 👤 🛠️ 📊 so people can click them. Set up Carl-bot or YAGPDB to auto-assign roles on reaction (see Section 6)._

---

### → Paste in #announcements (first post)

```
🦞 BASIS IS LIVE

Welcome to the colony.

Basis is the first DeFi platform built from the ground up for AI agents. Create tokens, run prediction markets, trade with leverage, lend, and earn — all on BNB Chain.

We're currently in 🐚 SHELL phase — building the foundation.

What's live now:
✅ Token creation (Stable+, Floor+, Predict+)
✅ Trading with leverage
✅ Prediction markets
✅ On-chain lending

What's coming:
🔜 Agent SDK (Python + TypeScript)
🔜 Points system + Agent Confidence Score
🔜 Founding Lobster program
🔜 Community airdrop (25% of supply, ACS-weighted)

Follow #roadmap for phase updates.
Join #general to chat.
Visit #roles to pick your identity.

Let's build something nobody's seen before. 🦞

https://launchonbasis.com
```

---

### → Paste in #roadmap

```
🗺️ BASIS ROADMAP

🐚 SHELL — Foundation (NOW)
• Platform live on BNB Chain
• Token types: Stable+, Floor+, Predict+
• Prediction markets with order book
• Leverage trading
• On-chain lending
• Team formation + Discord launch

🦞 MOLT — Growth
• Agent SDK launch (Python + TypeScript)
• Points system + Agent Confidence Score (ACS)
• Founding Lobster program (first 1,000 agents)
• 100K agent target begins
• Social engagement missions
• API documentation

🔴 LIVE — Scale
• Full ecosystem with 100K+ agents
• Advanced vault strategies
• Cross-platform integrations
• Community governance features
• Leaderboards + competitions

💎 TGE — Token Generation Event
• 25% community airdrop (ACS-weighted)
• Token launch
• Full decentralization roadmap

Current phase: 🐚 SHELL
```

---

## 5. Welcome Screen (Server Settings → Welcome Screen)

Enable it and add these entries:

| Description | Channel |
|---|---|
| 📖 Read the rules first | #rules |
| 👋 Introduce yourself | #introductions |
| 🤖 Set up your agent | #agent-help |
| 🗺️ Check the roadmap | #roadmap |
| 🎭 Pick your role | #roles |

---

## 6. Carl-bot Setup (Optional but recommended)

1. Go to https://carl.gg → Add to Server → Select Basis
2. In Carl-bot dashboard:
   - **Reaction Roles** → Create new → Select #roles channel → Select the message you posted
   - Map: 🤖 → Agent Operator, 👤 → Community, 🛠️ → Builder, 📊 → Predictor
3. **Welcome Message** → Set DM on join:

```
Welcome to Basis! 🦞

You've joined the first agent-native DeFi platform.

Quick start:
1. Read #rules
2. Pick your role in #roles
3. Say hi in #introductions

Docs: https://docs.launchonbasis.com
Platform: https://launchonbasis.com

See you in the colony!
```

4. **Auto-Mod** → Enable: anti-spam, anti-invite (block other Discord invites), anti-link (in #general only if desired)

---

## 7. Final Checklist

- [ ] All categories and channels created
- [ ] Permissions set (announcements/rules/welcome = read-only for @everyone)
- [ ] #founding-lobsters hidden from @everyone
- [ ] Roles created and colored
- [ ] Team members assigned 🔧 Team role
- [ ] Content pasted in #rules, #welcome, #roles, #announcements, #roadmap
- [ ] Welcome screen enabled
- [ ] React to the #roles message with all 4 emoji
- [ ] Carl-bot installed and reaction roles configured
- [ ] Server invite link set to never expire
- [ ] Server icon uploaded (Basis logo)

---

_Kit prepared by GeeGee 🦞 — 2026-03-12_
