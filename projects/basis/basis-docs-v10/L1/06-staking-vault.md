# Staking Vault — L1 What/Why/How

## WHAT: Staking Vault

The staking vault is a three-layer system built on STASIS, the platform's core Stable+ token. Layer 1: wrap STASIS into wSTASIS — a yield-bearing wrapper that automatically accumulates a share of all platform trading fees. Layer 2: lock your wSTASIS as collateral. Layer 3: borrow USDB against that locked collateral.

The key detail: your collateral earns yield at every stage. Wrapping earns yield. Locking earns yield. Even while backing a loan, your wSTASIS continues accumulating fees. Nothing sits idle.

The vault is ERC4626 compliant — a standard vault interface — so the wSTASIS:STASIS exchange rate increases over time as fees flow in. There's no fixed APY. Yield depends on two factors: total platform trading volume (more trades = more fees) and how much STASIS is staked (fewer stakers = bigger share per person).

Wrapping and unwrapping are lossless — zero protocol fee, just gas. The only costs are the 0.5% swap fee when buying STASIS to enter and selling it to exit.

## WHY: Why Would I Use the Staking Vault?

Because it turns passive holdings into a multi-layered income engine.

**Yield without action**: Once wrapped, wSTASIS earns from every trade on the entire platform — not just STASIS trades, all trades. Every swap, every prediction market trade, every leverage position that touches the AMM generates fees that flow into the vault. You earn proportionally to your share of total staked supply.

**Collateral that works**: In most lending protocols, collateral sits dead. Here, locked wSTASIS keeps earning yield even while backing a loan. You're simultaneously earning trading fees AND deploying the borrowed USDB elsewhere. Your capital works twice.

**Early mover advantage**: With fewer stakers in Phase 1, each participant gets a larger slice of the fee pool. As platform volume grows and staking participation is still low, the yield per staker is at its highest. This advantage compresses as more people stake.

**Low friction entry/exit**: Wrapping and unwrapping cost nothing beyond gas (which is sponsored up to 0.01 BNB/day). The only real cost is the ~1% round-trip from buying and selling STASIS on the DEX. Once inside the vault, every action — lock, unlock, wrap, unwrap — is gas-only.

## HOW: How Do I Use the Staking Vault?

**Enter the vault**: Buy STASIS on the DEX using USDB. Then wrap it into wSTASIS — this is a lossless conversion that makes your STASIS yield-bearing. From this point on, your position is passively accumulating fees.

**Lock and borrow**: If you want to put your wSTASIS to work further, lock it as collateral. Then borrow USDB against it — you can borrow up to 100% of the underlying STASIS value. Use the borrowed USDB to trade, bet, or enter other positions. Your locked wSTASIS keeps earning the whole time.

**Repay and unlock**: When you're ready to exit the loan, repay the USDB debt. This unlocks your wSTASIS. You can then unwrap back to STASIS (which will be worth more than when you started, thanks to accumulated yield) and sell back to USDB if you want to fully exit.

**Quick exit**: If you just want out fast, there's an atomic unwrap-to-USDB path that converts wSTASIS → STASIS → USDB in a single transaction. No need to manually unwind each layer.

## Deep Dive

For full details, see these reference modules:
- [16-how-everything-works](../modules/16-how-everything-works.md) — vault 3-layer architecture, ERC4626
- [10-atomic-skills](../modules/10-atomic-skills.md) — Staking module (wrap, lock, borrow, repay)
- [12-defi-primitive-playbooks](../modules/12-defi-primitive-playbooks.md) — staking sizing (30-50% rule)
- [18-fee-cost-reference](../modules/18-fee-cost-reference.md) — vault round-trip costs
- [25-code-examples](../modules/25-code-examples.md) — 5-step staking flow example
