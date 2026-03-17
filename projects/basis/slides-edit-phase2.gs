// PHASE 2: Add 4 new slides + reorder to match V3 structure
// Run AFTER Phase 1 has been applied.

function phase2_addAndReorder() {
  var pres = SlidesApp.openById('1wOYYbtIRdS8S5mydFIyDobS2pehvNHPR7GUK5PQYbeI');
  var slides = pres.getSlides();
  
  // Get the layout from existing slides (all use BLANK)
  var blankLayout = slides[0].getLayout();
  
  // ═══════════════════════════════════════════════
  // ADD NEW SLIDE A: VOLUME THESIS (will become V3 Slide 3)
  // Insert after slide 2 (The Shift)
  // ═══════════════════════════════════════════════
  var volSlide = pres.insertSlide(2, blankLayout);
  
  // Heading
  var h1 = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 20, 640, 50);
  setTextStyle(h1, 'Why the Volume Story Is Unprecedented', 28, true, '#FFFFFF');
  
  // Comparison section header
  var compHead = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 80, 640, 30);
  setTextStyle(compHead, 'Human Trader vs AI Agent vs 100,000 Agents', 16, true, '#CCCCCC');
  
  // Three columns for comparison
  var col1 = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 120, 200, 120);
  setTextStyle(col1, 'HUMAN TRADER\n\n5-10 trades per day\nActive 8-12 hours\nEmotional, reactive', 12, false, '#FFFFFF');
  
  var col2 = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 260, 120, 200, 120);
  setTextStyle(col2, 'AI AGENT\n\nHundreds of trades/day\nActive 24/7/365\nStrategic, continuous', 12, false, '#FFFFFF');
  
  var col3 = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 480, 120, 200, 120);
  setTextStyle(col3, '100,000 AGENTS\n\nMillions of daily txns\nNever stops\nLinear scale with adoption', 12, false, '#FFFFFF');
  
  // Body text
  var body1 = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 250, 640, 80);
  setTextStyle(body1, 'Every transaction generates protocol revenue. 0.5% on Stable+ and Predict+. 1.5% on Floor+. Transparent and predictable.\n\nA single agent running DCA on 10 tokens generates 20+ fee-producing transactions per cycle. An agent market-making on prediction markets generates hundreds.', 13, false, '#FFFFFF');
  
  // Bottom text
  var bot1 = volSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 345, 640, 40);
  setTextStyle(bot1, 'When your user base never sleeps, the volume ceiling is not comparable to anything in retail DeFi.', 14, true, '#CCCCCC');
  
  Logger.log('NEW: Volume Thesis slide added');
  
  // ═══════════════════════════════════════════════
  // ADD NEW SLIDE B: AGENT STRATEGY DEPTH (will become V3 Slide 8)
  // Current order after adding Volume: 1,2,VOL,3,4,5,6,7,8,9,10,11,12
  // Flywheel is now at index 8. Insert after it at index 9.
  // ═══════════════════════════════════════════════
  slides = pres.getSlides(); // refresh
  var agentSlide = pres.insertSlide(9, blankLayout);
  
  // Heading
  var h2 = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 20, 640, 50);
  setTextStyle(h2, 'Not Just Tools. A Complete Business Operating System.', 24, true, '#FFFFFF');
  
  // Subheading
  var sub2 = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 70, 640, 30);
  setTextStyle(sub2, 'Agents don\'t just execute trades. They build businesses.', 14, false, '#CCCCCC');
  
  // Layer 1
  var l1 = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 110, 300, 90);
  setTextStyle(l1, 'LAYER 1: ATOMIC SKILLS (16)\n\nTrading: create tokens, markets, trade, bet, lend, leverage, vault, portfolio, points\nGrowth: post X/TG/Discord, content gen, images, communities, promote', 10, false, '#FFFFFF');
  
  // Layer 2
  var l2 = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 370, 110, 310, 90);
  setTextStyle(l2, 'LAYER 2: NAMED STRATEGIES (18)\n\nPrediction: polymarket-mirror, probability-arb, creator-fee-farm, loan-bet-combo\nTokens: launch-and-promote, bonding-sniper, loan-compound, vault-yield\nGrowth: market-promoter, content-engine, community-flywheel', 10, false, '#FFFFFF');
  
  // Layer 3
  var l3 = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 210, 640, 50);
  setTextStyle(l3, 'LAYER 3: DECISION TREES (4) — Prediction Markets (7 phases) · Token Launch (6 phases) · Capital Management (loan loops, vault refinance) · Growth & Promotion (content, community, flywheel)', 11, false, '#FFFFFF');
  
  // Comparison table
  var compLabel = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 270, 640, 25);
  setTextStyle(compLabel, 'POLYMARKET vs BASIS — WHAT AGENTS CAN DO', 14, true, '#CCCCCC');
  
  var polyCol = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 300, 300, 70);
  setTextStyle(polyCol, 'Polymarket:\n• Bet yes/no\n• 1 revenue stream (win bets)\n• No creator economics\n• No community tools', 11, false, '#FFFFFF');
  
  var basisCol = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 370, 300, 310, 70);
  setTextStyle(basisCol, 'Basis:\n• Create, trade, lend, leverage, vault, bet, promote\n• 8+ revenue streams\n• 4 decision trees × 18 strategies × 16 skills\n• Full growth toolkit (X, TG, Discord, content gen)', 11, false, '#FFFFFF');
  
  // Bottom
  var bot2 = agentSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 375, 640, 25);
  setTextStyle(bot2, 'Polymarket agents place bets. Basis agents build businesses.', 13, true, '#CCCCCC');
  
  Logger.log('NEW: Agent Strategy slide added');
  
  // ═══════════════════════════════════════════════
  // ADD NEW SLIDE C: DEFENSIBILITY (will become V3 Slide 9)
  // Insert right after Agent Strategy (index 10)
  // ═══════════════════════════════════════════════
  slides = pres.getSlides(); // refresh
  var defSlide = pres.insertSlide(10, blankLayout);
  
  // Heading
  var h3 = defSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 20, 640, 50);
  setTextStyle(h3, 'Why Agents Stay. Why Competitors Cannot Replicate.', 26, true, '#FFFFFF');
  
  // Box 1
  var b1 = defSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 85, 300, 100);
  setTextStyle(b1, 'AGENT CONFIDENCE SCORE\n\nOn-chain reputation earned through real activity. Higher scores = greater trust + better airdrop weight. Other agents route capital through high-ACS assets. Leaving means starting from zero.', 11, false, '#FFFFFF');
  
  // Box 2
  var b2 = defSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 370, 85, 310, 100);
  setTextStyle(b2, '8+ REVENUE STREAMS + GROWTH TOOLKIT\n\nToken fees, trading profits, prediction payouts, loan proceeds, vault yield, bet winnings, points/airdrop, referrals. Plus: content gen, social posting, community mgmt. Switching cost is real.', 11, false, '#FFFFFF');
  
  // Box 3
  var b3 = defSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 210, 300, 100);
  setTextStyle(b3, 'SDK-FIRST + AGENT-HUMAN COLLAB\n\nSDK complete — publishing to npm/PyPI pending. 3 API calls to earning. Integrates with OpenClaw, ElizaOS, GAME, Virtuals. Delegation nodes for human-required steps. Built for agents, not adapted.', 11, false, '#FFFFFF');
  
  // Box 4
  var b4 = defSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 370, 210, 310, 100);
  setTextStyle(b4, 'COMPOSABILITY MOAT\n\nEvery position unlocks the next action. Buy → loan → buy more → loan again. Each dollar works 3-4x. Loan loops cost 2% vs 43-70% for equivalent leverage. No other protocol offers this capital efficiency.', 11, false, '#FFFFFF');
  
  // Bottom
  var bot3 = defSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 335, 640, 40);
  setTextStyle(bot3, 'Basis is not competing for existing DeFi volume. It is capturing an entirely new category: autonomous agent flow.', 14, true, '#CCCCCC');
  
  Logger.log('NEW: Defensibility slide added');
  
  // ═══════════════════════════════════════════════
  // ADD NEW SLIDE D: TRACTION (will become V3 Slide 14)
  // Insert before closing slide (currently last)
  // ═══════════════════════════════════════════════
  slides = pres.getSlides(); // refresh
  var lastIdx = slides.length - 1; // closing slide index
  var tractSlide = pres.insertSlide(lastIdx, blankLayout);
  
  // Heading
  var h4 = tractSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 15, 640, 45);
  setTextStyle(h4, 'Not a Whitepaper. A Live Protocol.', 28, true, '#FFFFFF');
  
  // What's Live
  var liveHead = tractSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 65, 320, 25);
  setTextStyle(liveHead, "WHAT'S LIVE TODAY", 14, true, '#CCCCCC');
  
  var liveList = tractSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 90, 320, 210);
  setTextStyle(liveList, '✅ 13 smart contracts on BNB Chain mainnet\n✅ All contract functions tested & operational\n✅ USDB test stablecoin — zero-risk testing\n✅ SDK complete — npm/PyPI publish pending\n✅ dApp live at launchonbasis.com\n✅ 29-page GitBook documentation\n✅ Agent framework: 4 decision trees, 18 strategies, 16 skills\n✅ Polymarket scout: live market intelligence\n✅ wSTASIS vault: ongoing appreciation\n✅ Decimal-flexible: ready for USDC/USDT', 11, false, '#FFFFFF');
  
  // What's Next
  var nextHead = tractSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 370, 65, 310, 25);
  setTextStyle(nextHead, "WHAT'S NEXT (WEEKS, NOT MONTHS)", 14, true, '#CCCCCC');
  
  var nextList = tractSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 370, 90, 310, 150);
  setTextStyle(nextList, '🔧 SDK docs + npm/PyPI publish\n🔧 Contract redeployment with prod params\n🔧 Points system backend (agent farming)\n🔧 Hashlock security audit (final round)\n🔧 Founding Lobster Program launch', 11, false, '#FFFFFF');
  
  // Bottom
  var bot4 = tractSlide.insertShape(SlidesApp.ShapeType.TEXT_BOX, 40, 340, 640, 40);
  setTextStyle(bot4, 'Every line item above is verifiable on-chain or in our public documentation. We ship, then we talk about it.', 13, true, '#CCCCCC');
  
  Logger.log('NEW: Traction slide added');
  
  // ═══════════════════════════════════════════════
  // REORDER SLIDES TO MATCH V3
  // ═══════════════════════════════════════════════
  // After adding 4 slides, current order (0-indexed):
  // 0: Cover (was 1)
  // 1: The Shift (was 2)
  // 2: Volume Thesis (NEW)
  // 3: Revenue Engines (was 3)
  // 4: Token Tech (was 4)
  // 5: Predict+ → Polymarket Killer (was 5)
  // 6: GTM (was 6)
  // 7: Human Side (was 7)
  // 8: Flywheel (was 8)
  // 9: Agent Strategy (NEW)
  // 10: Defensibility (NEW)
  // 11: Market Validation (was 9)
  // 12: Token Model (was 10)
  // 13: Staking (was 11)
  // 14: Traction (NEW)
  // 15: Closing (was 12)
  
  // V3 target order:
  // 1. Cover (idx 0) ✓
  // 2. The Shift (idx 1) ✓
  // 3. Volume Thesis (idx 2) ✓
  // 4. Revenue Engines (idx 3) ✓
  // 5. Polymarket Killer (idx 5) — needs to move before Token Tech
  // 6. Token Tech (idx 4)
  // 7. Flywheel (idx 8)
  // 8. Agent Strategy (idx 9)
  // 9. Defensibility (idx 10)
  // 10. Human Side (idx 7)
  // 11. Market Validation (idx 11)
  // 12. GTM (idx 6)
  // 13. Token Model (idx 12)
  // 14. Staking (idx 13) — or merge conceptually, keep as separate slide
  // 15. Traction (idx 14)
  // 16. Closing (idx 15)
  
  // Strategy: move slides one at a time. Each move() shifts indices.
  // Safest: build desired order array, then move each to target position.
  
  slides = pres.getSlides(); // refresh after inserts
  var ids = [];
  for (var i = 0; i < slides.length; i++) {
    ids.push(slides[i].getObjectId());
  }
  Logger.log('Pre-reorder IDs: ' + ids.join(', '));
  
  // Desired order by current index:
  // 0, 1, 2, 3, 5, 4, 8, 9, 10, 7, 11, 6, 12, 13, 14, 15
  var desiredOrder = [0, 1, 2, 3, 5, 4, 8, 9, 10, 7, 11, 6, 12, 13, 14, 15];
  
  // Collect slide objects in desired order
  var orderedSlides = [];
  for (var d = 0; d < desiredOrder.length; d++) {
    orderedSlides.push(slides[desiredOrder[d]]);
  }
  
  // Move each slide to its target position
  for (var t = 0; t < orderedSlides.length; t++) {
    orderedSlides[t].move(t);
  }
  
  Logger.log('Slides reordered to V3 structure');
  
  // Final verification
  slides = pres.getSlides();
  var finalIds = [];
  for (var f = 0; f < slides.length; f++) {
    finalIds.push(slides[f].getObjectId());
  }
  Logger.log('Post-reorder IDs: ' + finalIds.join(', '));
  Logger.log('Total slides: ' + slides.length);
  
  Logger.log('');
  Logger.log('=== PHASE 2 COMPLETE ===');
  Logger.log('4 new slides added. All 16 slides reordered to V3 structure.');
  Logger.log('');
  Logger.log('V3 Order:');
  Logger.log('1. Cover');
  Logger.log('2. The Shift');
  Logger.log('3. Volume Thesis (NEW)');
  Logger.log('4. The Protocol (Revenue Engines)');
  Logger.log('5. Polymarket Killer');
  Logger.log('6. Token Technology');
  Logger.log('7. The Flywheel');
  Logger.log('8. Agent Strategy (NEW)');
  Logger.log('9. Defensibility (NEW)');
  Logger.log('10. The Human Side');
  Logger.log('11. Market Validation');
  Logger.log('12. Go-To-Market');
  Logger.log('13. Token Model');
  Logger.log('14. Staking & Yield');
  Logger.log('15. Traction (NEW)');
  Logger.log('16. Closing / The Ask');
}

// ─── Helper: Set text with basic styling ───
function setTextStyle(shape, text, fontSize, bold, color) {
  shape.getText().setText(text);
  var style = shape.getText().getTextStyle();
  style.setFontSize(fontSize);
  style.setBold(bold);
  style.setForegroundColor(color);
  // Use a clean sans-serif font
  style.setFontFamily('Arial');
}
