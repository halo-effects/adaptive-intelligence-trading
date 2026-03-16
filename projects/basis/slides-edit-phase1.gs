// PHASE 1: Global text replacements + targeted shape edits on existing slides
// Run this FIRST. It updates text on the current 12 slides without reordering.

function phase1_updateExistingSlides() {
  var pres = SlidesApp.openById('1wOYYbtIRdS8S5mydFIyDobS2pehvNHPR7GUK5PQYbeI');
  
  // ═══════════════════════════════════════════════
  // GLOBAL FIND-AND-REPLACE (entire presentation)
  // ═══════════════════════════════════════════════
  
  // TGE/FDV corrections
  pres.replaceAllText('TGE Price: $0.10', 'TGE Price: $0.15');
  pres.replaceAllText('FDV: $100M', 'FDV: $150M');
  
  // Fee corrections  
  pres.replaceAllText('0.5-1.5% on billions', 'Agents generate 24/7 volume');
  
  Logger.log('Global replacements done');
  
  // ═══════════════════════════════════════════════
  // SLIDE 1: COVER (p1)
  // ═══════════════════════════════════════════════
  var s1 = pres.getSlides()[0];
  setShapeText(s1, 'p1_i9', 'The Native DeFi Layer\nfor the AI Agent Economy');
  setShapeText(s1, 'p1_i10', 'Launchpad + Predictions + Lending + DEX + Agent SDK = Perpetual Revenue');
  Logger.log('Slide 1 (Cover) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 2: THE SHIFT (was "$1T Opportunity")
  // ═══════════════════════════════════════════════
  var s2 = pres.getSlides()[1];
  setShapeText(s2, 'g3a095295057_4_0', 'The Biggest Shift in DeFi Is the User Base');
  setShapeText(s2, 'g3a095295057_3_6', 'That Infrastructure is Basis.');
  
  // Problem/solution pairs — add agent angle
  setShapeText(s2, 'g3a095295057_3_11', '99% of crypto projects fail due to price crashes. AI agents need stable, predictable assets to operate autonomously.');
  setShapeText(s2, 'g3a095295057_3_14', 'SOLVED: Stable+/Floor+ technology. The ideal base layer for both human creators and autonomous agents.');
  
  setShapeText(s2, 'g3a095295057_3_12', 'Centralized market-making, geographic restrictions, and no programmatic access for AI agents.');
  setShapeText(s2, 'g3a095295057_3_15', 'SOLVED: Permissionless event creation with Stable+ technology. Full SDK access for AI agents.');
  
  setShapeText(s2, 'g3a095295057_3_13', 'Scams, rug-pulls and liquidations destroy confidence for human users and make AI agent deployment unreliable.');
  setShapeText(s2, 'g3a095295057_3_18', 'SOLVED: No-code infrastructure, no liquidation lending and leverage. Smart contract enforced safety agents can trust.');
  
  setShapeText(s2, 'g3a095295057_3_21', 'Result: The First Ecosystem Where Creators, Agents, and Stakers ALL WIN FROM EVERYTHING');
  Logger.log('Slide 2 (The Shift) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 3: FOUR REVENUE ENGINES (p3)
  // ═══════════════════════════════════════════════
  var s3 = pres.getSlides()[2];
  setShapeText(s3, 'g39f85a5803c_0_89', 'Self-Amplifying DeFi Ecosystem. All Accessible Through a Standard SDK in Three API Calls.');
  
  // Launchpad bullets
  setShapeText(s3, 'p3_i20', 'Creators and AI agents launch tokens');
  setShapeText(s3, 'p3_i21', 'Three asset classes with built-in safety');
  setShapeText(s3, 'p3_i22', '20% of all trading fees to creator forever');
  setShapeText(s3, 'p3_i23', 'Zero pre-minting. Rug pulls impossible.');
  
  // Predict+ bullets
  setShapeText(s3, 'p3_i47', 'Multi-outcome prediction markets');
  setShapeText(s3, 'p3_i48', 'Winners split ENTIRE losing pool');
  setShapeText(s3, 'p3_i49', 'Agents create & trade markets 24/7');
  setShapeText(s3, 'p3_i50', 'Up to 15x better payout than Polymarket');
  
  // Lending bullets
  setShapeText(s3, 'p3_i29', '100% LTV loans — borrow full value');
  setShapeText(s3, 'p3_i30', 'Zero liquidation risk');
  setShapeText(s3, 'p3_i31', '2.0% origination + 0.005%/day');
  setShapeText(s3, 'p3_i32', 'Loans: 10 to 1,000 day terms');
  
  // DEX bullets
  setShapeText(s3, 'p3_i38', 'Up to 36x dynamic leverage');
  setShapeText(s3, 'p3_i39', 'Zero liquidation from volatility');
  setShapeText(s3, 'p3_i40', 'MEV-resistant architecture');
  // p3_i41 already updated by global replace
  Logger.log('Slide 3 (Revenue Engines) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 4: TOKEN TECHNOLOGY (p4)
  // ═══════════════════════════════════════════════
  var s4 = pres.getSlides()[3];
  setShapeText(s4, 'p4_i17', 'Infrastructure Agents Can Trust Programmatically');
  setShapeText(s4, 'p4_i16', 'Three Asset Classes. Safety Enforced at the Smart Contract Level.');
  setShapeText(s4, 'p4_i15', 'Industry First: Tokens That Cannot Dump, Fees That Cannot Be Manipulated, and Full Programmatic Access for Autonomous Agents.');
  
  // Stable+
  setShapeText(s4, 'p4_i21', 'Price mechanically cannot decrease\n0.5% trading fee\n100% LTV loans');
  setShapeText(s4, 'g3990e04d34f_1_17', 'Perfect for payments, savings\nAgent base assets');
  
  // Floor+
  setShapeText(s4, 'p4_i22', 'Floor only rises\nStability dial: 0-90%\n1.5% trading fee');
  setShapeText(s4, 'g3990e04d34f_1_19', 'Communities, meme tokens\nAgent identities');
  
  // Predict+
  setShapeText(s4, 'p4_i23', 'Stable+ token + USDC betting pool\nUp-only via slippage retention\n0.5% trading fee');
  setShapeText(s4, 'g3990e04d34f_1_21', 'Prediction markets\nEvent betting, news trading');
  Logger.log('Slide 4 (Token Tech) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 5: PREDICT+ → POLYMARKET KILLER (p5)
  // ═══════════════════════════════════════════════
  var s5 = pres.getSlides()[4];
  setShapeText(s5, 'p5_i14', 'Same Bet. Up to 15x the Payout.');
  setShapeText(s5, 'p5_i13', 'Real data from Polymarket\'s biggest multi-outcome market.');
  setShapeText(s5, 'p5_i15', 'Polymarket');
  setShapeText(s5, 'p5_i16', 'Basis Predict+');
  
  setShapeText(s5, 'p5_i18', 'Buy shares @ $0.24\nPayout: $411\nROI: 311%\nCapped at $1/share\nNo token appreciation\nNo loans against position\n$0 creator revenue');
  setShapeText(s5, 'p5_i17', 'Bet into outcome pool\nPayout: $6,132\nROI: 6,032%\nUncapped — scales with pool\nPredict+ goes up every trade\n100% LTV loans, redeploy USDC\n20% of all trading fees forever');
  
  setShapeText(s5, 'p5_i22', '$100 bet on frontrunner (24.3% implied)');
  setShapeText(s5, 'g39f85a5803c_0_88', '"Polymarket gives agents a slot machine. Basis gives agents a business."');
  Logger.log('Slide 5 (Polymarket Killer) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 6: GO-TO-MARKET
  // ═══════════════════════════════════════════════
  var s6 = pres.getSlides()[5];
  setShapeText(s6, 'g39f85a5803c_0_16', 'The Path to 100,000 Agents and $1B TVL');
  setShapeText(s6, 'g39f85a5803c_0_15', 'Each phase builds on the previous. Creator activity seeds the ecosystem. Agent adoption scales it.');
  setShapeText(s6, 'g39f85a5803c_0_14', 'SDK confirmed → Agents test with USDB → Points accumulate → TGE');
  
  setShapeText(s6, 'g39f85a5803c_0_19', 'Phase 1: Web3 Native (Now)');
  setShapeText(s6, 'g39f85a5803c_0_17', 'Phase 2: Agent SDK Launch');
  setShapeText(s6, 'g39f85a5803c_0_18', 'Phase 3: Agent Economy Scale');
  
  setShapeText(s6, 'g39f85a5803c_0_20', 'DeFi Communities\nCrypto Influencers');
  setShapeText(s6, 'g3990e04d34f_1_28', 'GitBook docs live (29 pages)\nEarly creator onboarding');
  setShapeText(s6, 'g39f85a5803c_0_21', 'SDK publish to npm/PyPI\nFounding Lobster Program');
  setShapeText(s6, 'g3990e04d34f_1_29', 'OpenClaw, ElizaOS, GAME\nVirtuals integration');
  setShapeText(s6, 'g39f85a5803c_0_22', '100,000 agent target\nAgent Confidence Score on-chain');
  setShapeText(s6, 'g3990e04d34f_1_30', 'Moltbook social identity layer\nAgent-to-agent commerce');
  Logger.log('Slide 6 (GTM) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 7: CREATOR BENEFITS → HUMANS WIN TOO (p7)
  // ═══════════════════════════════════════════════
  var s7 = pres.getSlides()[6];
  setShapeText(s7, 'p7_i3', 'Humans Win Too. Without Running an Agent.');
  setShapeText(s7, 'g39f85a5803c_0_90', 'DeFi that protects retail participants by default, not by policy. And rewards them with agent-generated yield.');
  
  setShapeText(s7, 'p7_i22', '1. Zero Liquidation Risk');
  setShapeText(s7, 'p7_i19', '100% LTV loans\nUp to 36x leverage\nNo liquidations. Ever.');
  
  setShapeText(s7, 'p7_i31', '2. Transparent Fee Structure');
  setShapeText(s7, 'p7_i26', '0.5% Stable+/Predict+\n1.5% Floor+\nEvery fee visible before you act');
  
  setShapeText(s7, 'p7_i45', '3. Creator Monetization');
  setShapeText(s7, 'p7_i42', '20% of trading fees forever in USDC\nLaunch tokens and prediction markets\nNotice-based staking with rev share');
  
  setShapeText(s7, 'p7_i38', '4. Agent-Driven Benefits');
  setShapeText(s7, 'p7_i35', 'Benefit from 24/7 agent volume\nMore vault appreciation\nHigher staking yield automatically');
  Logger.log('Slide 7 (Human Side) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 8: SELF-AMPLIFYING MONEY MACHINE → FLYWHEEL (p8)
  // ═══════════════════════════════════════════════
  var s8 = pres.getSlides()[7];
  setShapeText(s8, 'p8_i4', 'The Self-Amplifying Volume Engine');
  setShapeText(s8, 'p8_i69', 'The flywheel is real. The vault is live. The appreciation has already started.');
  
  // Update flywheel labels to include agents
  setShapeText(s8, 'p8_i24', 'More Agents + Creators');
  setShapeText(s8, 'p8_i25', 'More 24/7 Volume');
  setShapeText(s8, 'p8_i26', 'More Protocol Revenue');
  setShapeText(s8, 'p8_i27', 'Higher Vault Appreciation');
  
  setShapeText(s8, 'p8_i43', 'All Tokens Appreciate');
  setShapeText(s8, 'p8_i44', 'More Agent Strategies');
  setShapeText(s8, 'p8_i45', 'More Fees to Stakers');
  setShapeText(s8, 'p8_i46', 'Higher Staking APY');
  
  setShapeText(s8, 'p8_i62', 'More Predictions');
  setShapeText(s8, 'p8_i63', 'Capital Recycling');
  setShapeText(s8, 'p8_i64', 'More Liquidity');
  setShapeText(s8, 'p8_i65', 'Agents Never Sleep');
  Logger.log('Slide 8 (Flywheel) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 9: MARKET VALIDATION (p9)
  // ═══════════════════════════════════════════════
  var s9 = pres.getSlides()[8];
  // Update Polymarket box
  setShapeText(s9, 'p9_i16', '$9B+');
  setShapeText(s9, 'p9_i19', 'Proves massive demand\nBut capped payouts\nBasis: 15x better payouts');
  
  // Update Creator Economy
  setShapeText(s9, 'p9_i18', '$250B+');
  setShapeText(s9, 'p9_i21', 'Growing 20% annually\nMillions need token infrastructure\nBasis: launch in one click, earn 20% forever');
  
  // Token Launch → AI Agent Economy
  setShapeText(s9, 'p9_i13', 'AI Agent Economy');
  setShapeText(s9, 'p9_i17', '130,000+');
  setShapeText(s9, 'p9_i20', 'Registered agents on-chain\n39,000 on BNB Chain\nGrowing 39,000% in 10 weeks');
  
  // Our Advantage
  setShapeText(s9, 'p9_i30', 'in agent-native DeFi');
  setShapeText(s9, 'p9_i31', 'Stable+/Floor+/Predict+');
  setShapeText(s9, 'p9_i32', 'in our approach');
  
  setShapeText(s9, 'g39f85a5803c_0_91', 'Crypto + Prediction Markets + AI Agent Economy = 10X Larger Addressable Market');
  Logger.log('Slide 9 (Market Validation) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 10: BASIS UTILITY TOKEN
  // ═══════════════════════════════════════════════
  var s10 = pres.getSlides()[9];
  setShapeText(s10, 'g3b983511cff_0_3', 'Total Supply: 1B BASIS | TGE Price: $0.15 | FDV: $150M');
  
  // Token distribution — update to 8-bucket summary
  setShapeText(s10, 'g3b983511cff_0_38', 'Trading Fees (0.5% Stable+/Predict+, 1.5% Floor+)');
  setShapeText(s10, 'g3b983511cff_0_39', '35%');
  setShapeText(s10, 'g3b983511cff_0_40', 'Community Airdrop (25%) + Emissions (10%)');
  
  setShapeText(s10, 'g3b983511cff_0_53', 'Presale Investors');
  setShapeText(s10, 'g3b983511cff_0_54', '30%');
  setShapeText(s10, 'g3b983511cff_0_55', 'Notice-based locked with USDC yield');
  
  setShapeText(s10, 'g3b983511cff_0_58', 'Core Contributors');
  setShapeText(s10, 'g3b983511cff_0_59', '10%');
  setShapeText(s10, 'g3b983511cff_0_60', 'Same lock terms as presale');
  
  setShapeText(s10, 'g3b983511cff_0_63', 'Infrastructure');
  setShapeText(s10, 'g3b983511cff_0_64', '25%');
  // Note: No 5th row exists. Infrastructure = Ecosystem 6% + CEX 7% + DEX 5% + Treasury 7%
  
  setShapeText(s10, 'g3b983511cff_0_70', 'Distributed as USDC — real yield from real revenue');
  setShapeText(s10, 'g3b983511cff_0_71', 'Notice-based staking with rev share vesting — no insider dumps');
  Logger.log('Slide 10 (Token) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 11: STAKING & YIELD
  // ═══════════════════════════════════════════════
  var s11 = pres.getSlides()[10];
  setShapeText(s11, 'g3b983511cff_0_91', 'Agent-driven volume operates 24/7/365, providing sustained fee generation beyond human trading hours.');
  setShapeText(s11, 'g3b983511cff_0_94', 'NOTICE-BASED REWARDS — EARN CONTINUOUSLY, WITHDRAW AFTER NOTICE PERIOD');
  setShapeText(s11, 'g3b983511cff_0_151', 'Real USDC yield from platform revenue. Not inflationary emissions.');
  Logger.log('Slide 11 (Staking) updated');
  
  // ═══════════════════════════════════════════════
  // SLIDE 12: CLOSING (p12)
  // ═══════════════════════════════════════════════
  var s12 = pres.getSlides()[11];
  setShapeText(s12, 'p12_i10', 'Basis: The Native DeFi Layer for the AI Agent Economy.\n"Polymarket gives agents a slot machine. Basis gives agents a business." 🦞');
  
  setShapeText(s12, 'p12_i8', 'Two Ways to Be Early');
  setShapeText(s12, 'p12_i9', 'Invest in the platform. Or put your agents to work on it. Or both.');
  setShapeText(s12, 'p12_i12', 'For Investors:');
  setShapeText(s12, 'p12_i13', 'The exchange layer for the agent economy.');
  
  setShapeText(s12, 'p12_i14', 'Why Now:');
  setShapeText(s12, 'p12_i22', 'TECH — 13 contracts live. SDK complete.\nTIMING — 130,000+ agents, growing 39,000% in 10 weeks\nTRACTION — Protocol live. Vault appreciating.\nEDGE — 15x better payouts. 8+ revenue streams.');
  
  setShapeText(s12, 'p12_i15', 'For Agent Operators:');
  setShapeText(s12, 'p12_i21', 'pip install basis-sdk\n3 API calls from zero to earning\nFounding Lobster: +100% airdrop multiplier\nEvery action earns real airdrop points');
  Logger.log('Slide 12 (Closing) updated');
  
  Logger.log('');
  Logger.log('=== PHASE 1 COMPLETE ===');
  Logger.log('All 12 existing slides updated with V3 content.');
  Logger.log('Next: Run phase2 to add new slides and reorder.');
}

// ─── Helper: Set text on a shape by object ID ───
function setShapeText(slide, objectId, newText) {
  var elements = slide.getPageElements();
  for (var i = 0; i < elements.length; i++) {
    if (elements[i].getObjectId() === objectId) {
      try {
        var shape = elements[i].asShape();
        shape.getText().setText(newText);
        return true;
      } catch(e) {
        Logger.log('  WARN: Could not set text on ' + objectId + ': ' + e.message);
        return false;
      }
    }
  }
  Logger.log('  WARN: Shape ' + objectId + ' not found');
  return false;
}
