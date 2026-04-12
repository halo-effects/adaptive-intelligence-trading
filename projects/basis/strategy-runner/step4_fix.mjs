/**
 * Step 4 fix: extend vault loan first, then addToLoan
 * Error was "Duration too short" — need to extend before adding collateral
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
const fmt = (v) => formatUnits(v, 18);

const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
async function getBalance(addr) {
  return client.publicClient.readContract({ address: addr, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
}
function log(msg) { console.log(`[${new Date().toISOString()}] ${msg}`); }

log('========== STEP 4 (continued): Extend + AddToLoan ==========\n');

const usdbBefore = await getBalance(USDB);
log(`USDB balance: ${fmt(usdbBefore)}`);

// Steps 4a-4c already completed: STASIS bought, wrapped, locked
// wSTASIS locked should include both Step 1 and Step 4 amounts
const stake = await client.staking.getUserStakeDetails(wallet);
log(`wSTASIS locked: ${fmt(stake[1])}`);

const available = await client.staking.getAvailableStasis(wallet);
log(`Available STASIS for new borrowing: ${fmt(available)}`);

// Extend the existing loan by 10 more days (cheap: 0.005%/day)
log(`\n--- Extending vault loan by 10 days ---`);
const extendTx = await client.staking.extendLoan(10n, true, false);
log(`  ✓ Extended: ${extendTx.hash || extendTx}`);

// Now try addToLoan with the available amount
log(`\n--- Adding to vault loan ---`);
const availableNow = await client.staking.getAvailableStasis(wallet);
log(`  Available STASIS: ${fmt(availableNow)}`);

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

const finalAvail = await client.staking.getAvailableStasis(wallet);
log(`Available STASIS remaining: ${fmt(finalAvail)}`);
