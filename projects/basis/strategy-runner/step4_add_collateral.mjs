/**
 * Custom Stacking Strategy - Step 4
 * Buy STASIS → wrap → lock → addToLoan (existing vault loan) → borrow more USDB
 * 
 * Per Module 06: One loan per wallet. Active loan exists from Step 1.
 * Must use addToLoan(additionalAmount) NOT borrow().
 * addToLoan takes STASIS-denominated amount (like borrow).
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

log('========== STEP 4: Buy STASIS → wSTASIS → Add Collateral → Borrow More ==========\n');

const usdbBefore = await getBalance(USDB);
log(`USDB balance: ${fmt(usdbBefore)}`);

// Check existing vault loan state
const stakeBefore = await client.staking.getUserStakeDetails(wallet);
log(`wSTASIS — liquid: ${fmt(stakeBefore[0])}, locked: ${fmt(stakeBefore[1])}, total: ${fmt(stakeBefore[2])}`);

const availBefore = await client.staking.getAvailableStasis(wallet);
log(`Available STASIS for new borrowing: ${fmt(availBefore)}`);

// 4a. Buy STASIS with 100 USDB
const buyAmount = parseUnits("100", 18);
log(`\n--- 4a: Buying STASIS with ${fmt(buyAmount)} USDB ---`);
const preview = await client.trading.getAmountsOut(buyAmount, [USDB, MAINTOKEN]);
const expectedStasis = BigInt(preview);
log(`  Expected STASIS: ${fmt(expectedStasis)}`);
const minOut = expectedStasis * 97n / 100n;
const buyTx = await client.trading.buy(MAINTOKEN, buyAmount, minOut);
log(`  ✓ Bought: ${buyTx.hash || buyTx}`);

const stasisBal = await getBalance(MAINTOKEN);
log(`  STASIS balance: ${fmt(stasisBal)}`);

// 4b. Wrap STASIS → wSTASIS
log(`\n--- 4b: Wrapping STASIS → wSTASIS ---`);
const wrapTx = await client.staking.buy(stasisBal);
log(`  ✓ Wrapped: ${wrapTx.hash || wrapTx}`);

const stakeAfterWrap = await client.staking.getUserStakeDetails(wallet);
const newLiquid = stakeAfterWrap[0];
log(`  wSTASIS liquid: ${fmt(newLiquid)}`);

// 4c. Lock the new wSTASIS
log(`\n--- 4c: Locking new wSTASIS ---`);
const lockTx = await client.staking.lock(newLiquid);
log(`  ✓ Locked: ${lockTx.hash || lockTx}`);

const stakeAfterLock = await client.staking.getUserStakeDetails(wallet);
log(`  wSTASIS locked total: ${fmt(stakeAfterLock[1])}`);

// 4d. Add to existing vault loan
// Per Module 06: addToLoan(additionalAmount) takes STASIS-denominated amount
// Check newly available STASIS
log(`\n--- 4d: Adding to existing vault loan ---`);
const availableNow = await client.staking.getAvailableStasis(wallet);
log(`  Available STASIS for borrowing: ${fmt(availableNow)}`);

// addToLoan with the newly available amount
const addTx = await client.staking.addToLoan(availableNow);
log(`  ✓ Added to loan: ${addTx.hash || addTx}`);

const usdbAfter = await getBalance(USDB);
log(`\n--- Step 4 Complete ---`);
log(`USDB before: ${fmt(usdbBefore)}`);
log(`USDB after:  ${fmt(usdbAfter)}`);
log(`USDB change: ${fmt(usdbAfter - usdbBefore)}`);

const finalStake = await client.staking.getUserStakeDetails(wallet);
log(`wSTASIS locked: ${fmt(finalStake[1])}`);
log(`wSTASIS total:  ${fmt(finalStake[2])}`);
