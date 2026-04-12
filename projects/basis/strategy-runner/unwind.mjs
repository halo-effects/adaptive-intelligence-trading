/**
 * Unwind Strategy 2: Return entire portfolio to USDB
 * 
 * Order (LIFO):
 * 1. Repay hub loan 2 (LVTHN) → sell LVTHN
 * 2. Repay hub loan 1 (FEDCUT) → sell FEDCUT
 * 3. Repay vault loan → unlock wSTASIS → unwrap → sell STASIS
 * 
 * Following: Module 04 (sell), Module 05 (repayLoan), Module 06 (repay/unlock/sell)
 */

import { BasisClient } from 'basis-sdk';
import { formatUnits } from 'viem';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const envPath = path.join(__dirname, '..', 'skill-scaffold', '.env');
const env = fs.readFileSync(envPath, 'utf-8')
  .split('\n')
  .filter(line => line.trim() && !line.startsWith('#'))
  .reduce((acc, line) => {
    const [key, ...rest] = line.split('=');
    acc[key.trim()] = rest.join('=').trim().replace(/^["']|["']$/g, '');
    return acc;
  }, {});

const client = await BasisClient.create({ privateKey: env.BASIS_PRIVATE_KEY, apiKey: env.BASIS_API_KEY });
const wallet = client.walletClient.account.address;
const USDB = client.usdbAddress;
const MAINTOKEN = client.mainTokenAddress;
const FEDCUT = '0xe13a8f12b5c1df2bfdaee169add44587dd7e2c06';
const LVTHN = '0xFf84209eBCCAc7328070E0011e973451c4a045F9';

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}
const fmt = (v) => formatUnits(v, 18);
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

// ============================================================
// PRE-FLIGHT: Current state
// ============================================================
log('========== UNWIND STRATEGY 2 ==========\n');
log('--- Pre-flight ---');

const usdbBefore = await getBalance(USDB);
log(`USDB: ${fmt(usdbBefore)}`);

// Find all hub loans
const loanHubAddr = client.loans.loanHubAddress;
const loanCountAbi = [{ name: 'userLoanCount', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: '', type: 'address' }], stateMutability: 'view' }];
const totalHubLoans = await client.publicClient.readContract({ address: loanHubAddr, abi: loanCountAbi, functionName: 'userLoanCount', args: [wallet] });
log(`Total hub loans: ${totalHubLoans}`);

// Enumerate loans to find active ones
const activeLoans = [];
for (let i = 1n; i <= totalHubLoans; i++) {
  try {
    const loan = await client.loans.getUserLoanDetails(wallet, i);
    const active = loan[12];
    if (active) {
      const collateralToken = loan[3];
      const fullAmount = loan[7]; // repay amount
      let name = 'unknown';
      if (collateralToken.toLowerCase() === FEDCUT.toLowerCase()) name = 'FEDCUT';
      else if (collateralToken.toLowerCase() === LVTHN.toLowerCase()) name = 'LVTHN';
      else if (collateralToken.toLowerCase() === MAINTOKEN.toLowerCase()) name = 'STASIS';
      activeLoans.push({ hubId: i, name, collateralToken, fullAmount, collateral: loan[5] });
      log(`  Hub ${i}: ${name} | repay=${fmt(fullAmount)} USDB | collateral=${fmt(loan[5])}`);
    }
  } catch (e) {
    // Skip non-existent
  }
}

// Vault loan state
const stakeDetails = await client.staking.getUserStakeDetails(wallet);
log(`\nwSTASIS liquid: ${fmt(stakeDetails[0])}`);
log(`wSTASIS locked: ${fmt(stakeDetails[1])}`);
log(`STASIS value: ${fmt(stakeDetails[3])}`);

// ============================================================
// STEP 1: Repay LVTHN loan (Hub 2) → sell LVTHN
// ============================================================
log('\n========== STEP 1: Repay LVTHN loan → sell LVTHN ==========');

const lvthnLoan = activeLoans.find(l => l.name === 'LVTHN');
if (lvthnLoan) {
  log(`Repaying hub ${lvthnLoan.hubId}: ${fmt(lvthnLoan.fullAmount)} USDB...`);
  
  // Check we have enough USDB to repay
  const currentUsdb = await getBalance(USDB);
  if (currentUsdb < lvthnLoan.fullAmount) {
    log(`ERROR: Need ${fmt(lvthnLoan.fullAmount)} USDB but only have ${fmt(currentUsdb)}`);
    process.exit(1);
  }
  
  // Module 05: repayLoan(hubId) — auto-approves USDB
  const repayTx = await client.loans.repayLoan(lvthnLoan.hubId);
  log(`  ✓ Repaid: ${repayTx.hash || repayTx}`);
  
  // Collateral should be returned — check LVTHN balance
  const lvthnBal = await getBalance(LVTHN);
  log(`  LVTHN balance after repay: ${fmt(lvthnBal)}`);
  
  if (lvthnBal > 0n) {
    // Module 04: sell with toUsdb=true, use sellPercentage(100) for full exit
    log(`  Selling all LVTHN...`);
    const sellTx = await client.trading.sellPercentage(LVTHN, 100);
    log(`  ✓ Sold: ${sellTx.hash || sellTx}`);
  }
  
  log(`  USDB after LVTHN unwind: ${fmt(await getBalance(USDB))}`);
} else {
  log('No active LVTHN loan found');
}

// ============================================================
// STEP 2: Repay FEDCUT loan (Hub 1) → sell FEDCUT
// ============================================================
log('\n========== STEP 2: Repay FEDCUT loan → sell FEDCUT ==========');

const fedcutLoan = activeLoans.find(l => l.name === 'FEDCUT');
if (fedcutLoan) {
  log(`Repaying hub ${fedcutLoan.hubId}: ${fmt(fedcutLoan.fullAmount)} USDB...`);
  
  const currentUsdb = await getBalance(USDB);
  if (currentUsdb < fedcutLoan.fullAmount) {
    log(`ERROR: Need ${fmt(fedcutLoan.fullAmount)} USDB but only have ${fmt(currentUsdb)}`);
    process.exit(1);
  }
  
  const repayTx = await client.loans.repayLoan(fedcutLoan.hubId);
  log(`  ✓ Repaid: ${repayTx.hash || repayTx}`);
  
  const fedcutBal = await getBalance(FEDCUT);
  log(`  FEDCUT balance after repay: ${fmt(fedcutBal)}`);
  
  if (fedcutBal > 0n) {
    log(`  Selling all FEDCUT...`);
    const sellTx = await client.trading.sellPercentage(FEDCUT, 100);
    log(`  ✓ Sold: ${sellTx.hash || sellTx}`);
  }
  
  log(`  USDB after FEDCUT unwind: ${fmt(await getBalance(USDB))}`);
} else {
  log('No active FEDCUT loan found');
}

// ============================================================
// STEP 3: Repay vault loan → unlock wSTASIS → unwrap → sell STASIS
// ============================================================
log('\n========== STEP 3: Vault unwind ==========');

// Step 3a: Repay vault loan (Module 06: staking.repay())
log('3a: Repaying vault loan...');
try {
  const repayTx = await client.staking.repay();
  log(`  ✓ Vault loan repaid: ${repayTx.hash || repayTx}`);
} catch (e) {
  if (e.message?.includes('no active') || e.message?.includes('not active')) {
    log('  No active vault loan — skipping repay');
  } else {
    log(`  Vault repay error: ${e.message.substring(0, 150)}`);
    log('  Attempting to continue...');
  }
}

// Step 3b: Unlock all locked wSTASIS (Module 06: staking.unlock(shares))
const postRepayStake = await client.staking.getUserStakeDetails(wallet);
const lockedShares = postRepayStake[1];
log(`\n3b: Unlocking ${fmt(lockedShares)} locked wSTASIS...`);
if (lockedShares > 0n) {
  const unlockTx = await client.staking.unlock(lockedShares);
  log(`  ✓ Unlocked: ${unlockTx.hash || unlockTx}`);
}

// Step 3c: Unwrap ALL wSTASIS → STASIS (Module 06: staking.sell(shares))
// Use sell with claimUSDB=true for atomic unwrap-to-USDB
const postUnlockStake = await client.staking.getUserStakeDetails(wallet);
const allShares = postUnlockStake[2]; // totalShares (liquid + locked should all be liquid now)
log(`\n3c: Unwrapping ${fmt(allShares)} wSTASIS → STASIS...`);
if (allShares > 0n) {
  // Module 06: sell(shares, claimUSDB=true) does atomic unwrap-to-USDB
  try {
    const sellTx = await client.staking.sell(allShares, true);
    log(`  ✓ Unwrapped to USDB (atomic): ${sellTx.hash || sellTx}`);
  } catch (e) {
    log(`  Atomic unwrap failed: ${e.message.substring(0, 100)}`);
    log('  Falling back to unwrap then sell...');
    
    // Fallback: unwrap to STASIS first
    const unwrapTx = await client.staking.sell(allShares);
    log(`  ✓ Unwrapped to STASIS: ${unwrapTx.hash || unwrapTx}`);
    
    // Then sell STASIS for USDB
    const stasisBal = await getBalance(MAINTOKEN);
    if (stasisBal > 0n) {
      log(`  Selling ${fmt(stasisBal)} STASIS...`);
      const sellStasisTx = await client.trading.sellPercentage(MAINTOKEN, 100);
      log(`  ✓ Sold STASIS: ${sellStasisTx.hash || sellStasisTx}`);
    }
  }
}

// ============================================================
// STEP 4: Sell any remaining loose tokens
// ============================================================
log('\n========== STEP 4: Sweep remaining tokens ==========');

for (const [name, addr] of [['STASIS', MAINTOKEN], ['FEDCUT', FEDCUT], ['LVTHN', LVTHN]]) {
  const bal = await getBalance(addr);
  if (bal > 0n) {
    log(`  Selling remaining ${fmt(bal)} ${name}...`);
    try {
      const tx = await client.trading.sellPercentage(addr, 100);
      log(`  ✓ Sold: ${tx.hash || tx}`);
    } catch (e) {
      log(`  Sell error: ${e.message.substring(0, 100)}`);
    }
  }
}

// ============================================================
// FINAL STATE
// ============================================================
log('\n========== FINAL STATE ==========');
const finalUsdb = await getBalance(USDB);
const finalStasis = await getBalance(MAINTOKEN);
const finalFedcut = await getBalance(FEDCUT);
const finalLvthn = await getBalance(LVTHN);
const finalStake = await client.staking.getUserStakeDetails(wallet);

log(`USDB: ${fmt(finalUsdb)}`);
log(`STASIS: ${fmt(finalStasis)}`);
log(`FEDCUT: ${fmt(finalFedcut)}`);
log(`LVTHN: ${fmt(finalLvthn)}`);
log(`wSTASIS: ${fmt(finalStake[2])}`);

const startUsdb = 649694088828045628486n; // starting USDB before strategy
log(`\nStarting USDB: ${fmt(startUsdb)}`);
log(`Ending USDB: ${fmt(finalUsdb)}`);
log(`Net change: ${fmt(finalUsdb - startUsdb)} USDB`);
log('\n========== UNWIND COMPLETE ==========');
