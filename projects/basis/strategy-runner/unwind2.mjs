/**
 * Unwind remaining loans: Hub 1 (FEDCUT), Hub 2 (LVTHN), and old leverage position
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
const LEVERAGE_TOKEN = '0xbb8c70bdc0fe13b25753e81af676c23ddcfd6e28';

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}
const fmt = (v) => formatUnits(v, 18);
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

log('========== UNWIND REMAINING POSITIONS ==========\n');

const usdbBefore = await getBalance(USDB);
log(`USDB before: ${fmt(usdbBefore)}`);

// ============================================================
// STEP 1: Repay Hub Loan 1 (FEDCUT) — repay amount: 181.22 USDB
// ============================================================
log('\n--- Repaying Hub 1 (FEDCUT) ---');
log(`  Repay amount: 181.223987905421235742 USDB`);
try {
  const tx = await client.loans.repayLoan(1n);
  log(`  ✓ Repaid: ${tx.hash || tx}`);
} catch (e) {
  log(`  Error: ${e.message.substring(0, 150)}`);
}

// Sell returned FEDCUT
const fedcutBal = await getBalance(FEDCUT);
log(`  FEDCUT returned: ${fmt(fedcutBal)}`);
if (fedcutBal > 0n) {
  log(`  Selling FEDCUT...`);
  const tx = await client.trading.sellPercentage(FEDCUT, 100);
  log(`  ✓ Sold: ${tx.hash || tx}`);
}
log(`  USDB after: ${fmt(await getBalance(USDB))}`);

// ============================================================
// STEP 2: Repay Hub Loan 2 (LVTHN) — repay amount: 425.90 USDB
// ============================================================
log('\n--- Repaying Hub 2 (LVTHN) ---');
log(`  Repay amount: 425.897883566750867239 USDB`);
try {
  const tx = await client.loans.repayLoan(2n);
  log(`  ✓ Repaid: ${tx.hash || tx}`);
} catch (e) {
  log(`  Error: ${e.message.substring(0, 150)}`);
}

// Sell returned LVTHN
const lvthnBal = await getBalance(LVTHN);
log(`  LVTHN returned: ${fmt(lvthnBal)}`);
if (lvthnBal > 0n) {
  log(`  Selling LVTHN...`);
  const tx = await client.trading.sellPercentage(LVTHN, 100);
  log(`  ✓ Sold: ${tx.hash || tx}`);
}
log(`  USDB after: ${fmt(await getBalance(USDB))}`);

// ============================================================
// STEP 3: Close old leverage position
// Per Module 04: hubPartialLoanSell(positionId, 100, true, 0) for full close
// The leverage loan is loanId=1, token=0xbb8c...
// Need to find the leverage position ID via getLeverageCount
// ============================================================
log('\n--- Closing old leverage position ---');
try {
  const levCount = await client.trading.getLeverageCount(wallet, MAINTOKEN);
  log(`  Leverage positions on MAINTOKEN: ${levCount}`);
  
  if (levCount > 0n) {
    for (let i = 1n; i <= levCount; i++) {
      const pos = await client.trading.getLeveragePosition(wallet, MAINTOKEN, i);
      log(`  Position ${i}:`, JSON.stringify(pos, (k,v) => typeof v === 'bigint' ? v.toString() : v));
      
      if (pos.active) {
        log(`  Closing position ${i} (100%)...`);
        const tx = await client.loans.hubPartialLoanSell(i, 100n, true, 0n);
        log(`  ✓ Closed: ${tx.hash || tx}`);
      }
    }
  }
  
  // Also check leverage on the specific token
  const levToken = await client.trading.getLeverageCount(wallet, LEVERAGE_TOKEN);
  log(`  Leverage positions on 0xbb8c...: ${levToken}`);
} catch (e) {
  log(`  Leverage error: ${e.message.substring(0, 200)}`);
}

// ============================================================
// STEP 4: Sweep ALL remaining tokens
// ============================================================
log('\n--- Sweeping remaining tokens ---');
for (const [name, addr] of [['STASIS', MAINTOKEN], ['FEDCUT', FEDCUT], ['LVTHN', LVTHN], ['0xbb8c', LEVERAGE_TOKEN]]) {
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

// ============================================================
// FINAL
// ============================================================
log('\n========== FINAL STATE ==========');
const finalUsdb = await getBalance(USDB);
log(`USDB: ${fmt(finalUsdb)}`);
log(`STASIS: ${fmt(await getBalance(MAINTOKEN))}`);
log(`FEDCUT: ${fmt(await getBalance(FEDCUT))}`);
log(`LVTHN: ${fmt(await getBalance(LVTHN))}`);

const stake = await client.staking.getUserStakeDetails(wallet);
log(`wSTASIS: ${fmt(stake[2])}`);

// Check remaining loans via API
const apiLoans = await client.api.getLoans();
const activeLoans = apiLoans.data?.filter(l => l.active) || [];
log(`\nActive loans remaining: ${activeLoans.length}`);
for (const l of activeLoans) {
  log(`  ${l.source} | token=${l.token.substring(0,10)}... | repay=${fmt(BigInt(l.fullAmount))}`);
}
