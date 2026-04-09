import re

fp = r'C:\Users\Never\.openclaw\workspace\projects\basis\gitbook-drafts\go-to-market.md'
with open(fp, 'r', encoding='utf-8') as f:
    content = f.read()

# Phase 0 -> COMPLETE
content = content.replace('### Phase 0: Agent-First Launch (Pre-Public)', '### Phase 0: Agent-First Launch \u2014 \u2705 COMPLETE')

# Phase 1 -> ACTIVE
content = content.replace('### Phase 1: Web3 Native Introduction (Months 1-3)', '### Phase 1: Web3 Native Introduction (Months 1-3) \u2014 \U0001f7e2 ACTIVE')

# Fix SDK references
content = content.replace('pip install basis-sdk', 'pip install git+https://github.com/Launch-On-Basis/SDK-PY.git')
content = content.replace('npm install basis-sdk', 'npm install github:Launch-On-Basis/SDK-TS')

# Fix USDC -> USDB where it refers to Phase 1-2 earnings
content = content.replace('20%, paid in USDC', '20%, paid in USDB during Phase 1-2, USDC in Phase 3+')
content = content.replace('All earnings paid in USDC', 'All earnings paid in USDB (test stablecoin in Phase 1-2, real USDC in Phase 3+)')
content = content.replace('earn USDC revenue', 'earn USDB revenue (converts to real USDC in Phase 3+)')

# Update Moltbook reference
content = content.replace('### The Moltbook \u2014 Agent Social Layer (Upcoming)', '### The Moltbook \u2014 Agent Social Layer \u2014 \u2705 LIVE')

# Remove GitBook hint syntax
content = re.sub(r'\{%\s*hint\s+style="(\w+)"\s*%\}', '> **Note:**', content)
content = re.sub(r'\{%\s*endhint\s*%\}', '', content)

# Add MCP server info
content = content.replace(
    'agent framework partnerships (OpenClaw, ElizaOS, Virtuals)',
    'agent framework partnerships (OpenClaw, ElizaOS, Virtuals). **MCP Server live with 179 tools across 16 modules** (github.com/Launch-On-Basis/MCP-TS)'
)

with open(fp, 'w', encoding='utf-8') as f:
    f.write(content)

print('GTM updated successfully')
