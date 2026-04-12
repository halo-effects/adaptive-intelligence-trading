/**
 * Custom Stacking Strategy - Step 1
 * Buy STASIS → wrap to wSTASIS → lock → borrow USDB
 */
import { BasisClient } from 'basis-sdk';
import { formatUnits, parseUnits } from 'viem';
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
const fmt = (v) => formatUnits(v, 18);

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

log('========== STEP 1: Buy STASIS → wSTASIS → Lock → Borrow ==========\n');

// Pre-state
const usdbBefore = await getBalance(USDB);
log(`USDB balance: ${fmt(usdbBefore)}`);

// Check existing stake details
const stakeDetails = await client.staking.getUserStakeDetails(wallet);
log(`Current wSTASIS — liquid: ${fmt(stakeDetails[0])}, locked: ${fmt(stakeDetails[1])}, total: ${fmt(stakeDetails[2])}`);

// 1a. Buy STASIS with 150 USDB
const buyAmount = parseUnits("150", 18);
log(`\n--- 1a: Buying STASIS with ${fmt(buyAmount)} USDB ---`);

// Pre-flight: check price impact
const preview = await client.trading.getAmountsOut(buyAmount, [USDB, MAINTOKEN]);
log(`  getAmountsOut raw: ${JSON.stringify(preview, (k,v) => typeof v === 'bigint' ? v.toString() : v)}`);
const expectedStasis = Array.isArray(preview) ? (preview[1] ?? preview[preview.length - 1]) : preview;
log(`  Expected STASIS out: ${fmt(expectedStasis)}`);

const minOut = expectedStasis * 97n / 100n; // 3% slippage tolerance
const buyTx = await client.trading.buy(MAINTOKEN, buyAmount, minOut);
log(`  ✓ Bought: ${buyTx.hash || buyTx}`);

const stasisBal = await getBalance(MAINTOKEN);
log(`  STASIS balance: ${fmt(stasisBal)}`);

// 1b. Wrap STASIS → wSTASIS
log(`\n--- 1b: Wrapping STASIS → wSTASIS ---`);
const wrapTx = await client.staking.buy(stasisBal);
log(`  ✓ Wrapped: ${wrapTx.hash || wrapTx}`);

const stakeAfterWrap = await client.staking.getUserStakeDetails(wallet);
log(`  wSTASIS liquid: ${fmt(stakeAfterWrap[0])}`);

// 1c. Lock wSTASIS as collateral
log(`\n--- 1c: Locking wSTASIS ---`);
const liquidShares = stakeAfterWrap[0];
const lockTx = await client.staking.lock(liquidShares);
log(`  ✓ Locked ${fmt(liquidShares)} shares: ${lockTx.hash || lockTx}`);

const stakeAfterLock = await client.staking.getUserStakeDetails(wallet);
log(`  wSTASIS locked: ${fmt(stakeAfterLock[1])}`);

// 1d. Borrow USDB against locked wSTASIS
// borrow() takes STASIS-denominated amount, min 10 days
// Check available collateral first
log(`\n--- 1d: Borrowing USDB ---`);
const availableStasis = await client.staking.getAvailableStasis(wallet);
log(`  Available STASIS for borrowing: ${fmt(availableStasis)}`);

// Borrow up to the available amount, 10 day minimum
const borrowTx = await client.staking.borrow(availableStasis, 10n);
log(`  ✓ Borrowed: ${borrowTx.hash || borrowTx}`);

// Final state
const usdbAfter = await getBalance(USDB);
log(`\n--- Step 1 Complete ---`);
log(`USDB before: ${fmt(usdbBefore)}`);
log(`USDB after:  ${fmt(usdbAfter)}`);
log(`USDB change: ${fmt(usdbAfter - usdbBefore)}`);

const finalStake = await client.staking.getUserStakeDetails(wallet);
log(`wSTASIS locked: ${fmt(finalStake[1])}`);
log(`wSTASIS total:  ${fmt(finalStake[2])}`);
