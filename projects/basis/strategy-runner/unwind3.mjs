/**
 * Unwind remaining: sell loose STASIS, repay LVTHN loan, close leverage
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
const LVTHN = '0xFf84209eBCCAc7328070E0011e973451c4a045F9';

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}
const fmt = (v) => formatUnits(v, 18);
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

log('========== UNWIND REMAINING ==========\n');

// Step 1: Sell remaining STASIS
const stasisBal = await getBalance(MAINTOKEN);
log(`STASIS balance: ${fmt(stasisBal)}`);
if (stasisBal > 0n) {
  log('Selling all STASIS...');
  const tx = await client.trading.sellPercentage(MAINTOKEN, 100);
  log(`  ✓ Sold: ${tx.hash || tx}`);
}

// Step 2: Claim faucet if available to get more USDB
log('\nChecking faucet...');
const faucet = await client.api.getFaucetStatus();
if (faucet.canClaim) {
  log(`Claiming ${faucet.dailyAmount} USDB...`);
  const claim = await client.claimFaucet();
  log(`  ✓ Claimed: ${JSON.stringify(claim, (k,v) => typeof v === 'bigint' ? v.toString() : v).substring(0, 100)}`);
}

// Check USDB balance
const usdbNow = await getBalance(USDB);
log(`\nUSDB now: ${fmt(usdbNow)}`);

// Step 3: Repay LVTHN loan (hub 2) — needs 425.9 USDB
const LVTHN_REPAY = 425897883566750867239n;
log(`\nLVTHN repay needed: ${fmt(LVTHN_REPAY)}`);
if (usdbNow >= LVTHN_REPAY) {
  log('Repaying LVTHN loan (hub 2)...');
  const tx = await client.loans.repayLoan(2n);
  log(`  ✓ Repaid: ${tx.hash || tx}`);
  
  // Sell returned LVTHN
  const lvthnBal = await getBalance(LVTHN);
  if (lvthnBal > 0n) {
    log(`  Selling ${fmt(lvthnBal)} LVTHN...`);
    const sellTx = await client.trading.sellPercentage(LVTHN, 100);
    log(`  ✓ Sold: ${sellTx.hash || sellTx}`);
  }
} else {
  const shortfall = LVTHN_REPAY - usdbNow;
  log(`NOT ENOUGH USDB — short by ${fmt(shortfall)}`);
  log('Will use hubPartialLoanSell to close what we can...');
  
  // Module 05: hubPartialLoanSell(hubId, percentage, isLeverage, minOut)
  // Sell collateral in 10% increments to repay proportionally
  // Sell 100% to fully close
  log('Attempting hubPartialLoanSell(2, 100, false, 0) to fully liquidate...');
  try {
    const tx = await client.loans.hubPartialLoanSell(2n, 100n, false, 0n);
    log(`  ✓ Partial sell complete: ${tx.hash || tx}`);
  } catch (e) {
    log(`  Error: ${e.message.substring(0, 200)}`);
    // Try smaller chunks
    log('  Trying 50% chunks...');
    try {
      const tx1 = await client.loans.hubPartialLoanSell(2n, 50n, false, 0n);
      log(`  ✓ 50% sold: ${tx1.hash || tx1}`);
      const tx2 = await client.loans.hubPartialLoanSell(2n, 100n, false, 0n);
      log(`  ✓ Remaining sold: ${tx2.hash || tx2}`);
    } catch (e2) {
      log(`  Chunk error: ${e2.message.substring(0, 200)}`);
    }
  }
}

// Step 4: Close leverage position
log('\nClosing leverage position...');
try {
  // Per Module 04: getLeverageCount returns positions on a token
  // The old leverage is on token 0xbb8c... but accessed via MAINTOKEN
  const levCount = await client.trading.getLeverageCount(wallet, MAINTOKEN);
  log(`Leverage positions: ${levCount}`);
  
  for (let i = levCount; i >= 1n; i--) {
    try {
      const pos = await client.trading.getLeveragePosition(wallet, MAINTOKEN, i);
      const active = pos.active ?? pos[12];
      log(`  Position ${i}: active=${active}`);
      if (active) {
        log(`  Closing via hubPartialLoanSell(${i}, 100, true, 0)...`);
        const tx = await client.loans.hubPartialLoanSell(i, 100n, true, 0n);
        log(`  ✓ Closed: ${tx.hash || tx}`);
      }
    } catch (e) {
      log(`  Position ${i} error: ${e.message.substring(0, 150)}`);
    }
  }
} catch (e) {
  log(`Leverage error: ${e.message.substring(0, 200)}`);
}

// Step 5: Final sweep
log('\nFinal sweep...');
for (const [name, addr] of [['STASIS', MAINTOKEN], ['LVTHN', LVTHN], ['0xbb8c', '0xbb8c70bdc0fe13b25753e81af676c23ddcfd6e28']]) {
  const bal = await getBalance(addr);
  if (bal > 0n) {
    log(`  Selling ${fmt(bal)} ${name}...`);
    try {
      const tx = await client.trading.sellPercentage(addr, 100);
      log(`  ✓ Sold: ${tx.hash || tx}`);
    } catch (e) {
      log(`  Error: ${e.message.substring(0, 100)}`);
    }
  }
}

// FINAL STATE
log('\n========== FINAL STATE ==========');
log(`USDB: ${fmt(await getBalance(USDB))}`);
log(`STASIS: ${fmt(await getBalance(MAINTOKEN))}`);
log(`LVTHN: ${fmt(await getBalance(LVTHN))}`);

const apiLoans = await client.api.getLoans();
const active = apiLoans.data?.filter(l => l.active) || [];
log(`Active loans: ${active.length}`);
for (const l of active) {
  log(`  ${l.source} | ${l.token.substring(0,10)}... | repay=${fmt(BigInt(l.fullAmount))}`);
}
