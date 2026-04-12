/**
 * Custom Stacking Strategy - Step 5
 * Buy Predict+ token → hub loan → USDB
 * 
 * Predict+ = Stable+ subtype, gets 100% LTV at spot price
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

log('========== STEP 5: Buy Predict+ → Loan → USDB ==========\n');

const usdbBefore = await getBalance(USDB);
log(`USDB balance: ${fmt(usdbBefore)}`);

// Find prediction markets — use getMyProjects to find ones I created
// Or search for any active market
log('\nLooking for Predict+ tokens...');

// My projects include prediction markets
const projects = await client.api.getMyProjects();
const markets = projects.markets || [];
log(`My markets: ${markets.length}`);
for (const m of markets) {
  log(`  ${m.symbol} — ${m.name} (${m.address})`);
  // Check if it's a valid ecosystem token
  const isEco = await client.factory.isEcosystemToken(m.address);
  const state = await client.factory.getTokenState(m.address);
  log(`    isEco: ${isEco}, state: ${JSON.stringify(state, (k,v) => typeof v === 'bigint' ? v.toString() : v)}`);
}

// Pick the first market token with activity — TGEQ2 seems like it would have volume
// Let's use "Will BASIS token launch before June 2026?" (TGEQ2)
const PREDICT_TOKEN = '0x22acB59faEBDEf1133016D96752Ab3366aB3bFC1';
log(`\nUsing TGEQ2: ${PREDICT_TOKEN}`);

// 5a. Buy Predict+ token
const buyAmount = parseUnits("75", 18);
log(`\n--- 5a: Buying Predict+ with ${fmt(buyAmount)} USDB ---`);

// Preview via 3-hop path: USDB → STASIS → Predict+
const preview = await client.trading.getAmountsOut(buyAmount, [USDB, MAINTOKEN, PREDICT_TOKEN]);
log(`  Expected tokens: ${preview}`);
const expectedOut = BigInt(preview);
const minOut = expectedOut * 97n / 100n;

const buyTx = await client.trading.buy(PREDICT_TOKEN, buyAmount, minOut);
log(`  ✓ Bought: ${buyTx.hash || buyTx}`);

const predictBal = await getBalance(PREDICT_TOKEN);
log(`  Predict+ balance: ${fmt(predictBal)}`);

// 5b. Take hub loan — Predict+ is Stable+ subtype, gets 100% LTV at spot
log(`\n--- 5b: Taking hub loan against Predict+ ---`);
const loanTx = await client.loans.takeLoan(MAINTOKEN, PREDICT_TOKEN, predictBal, 10n);
log(`  ✓ Loan taken: ${loanTx.hash || loanTx}`);

// Check loan details
const loanCount = await client.loans.getUserLoanCount(wallet);
const hubId = loanCount;
const details = await client.loans.getUserLoanDetails(wallet, hubId);
log(`  Hub ID: ${hubId}`);
log(`  Loan details:`, JSON.stringify(details, (k,v) => typeof v === 'bigint' ? v.toString() : v));

const usdbAfter = await getBalance(USDB);
log(`\n--- Step 5 Complete ---`);
log(`USDB before: ${fmt(usdbBefore)}`);
log(`USDB after:  ${fmt(usdbAfter)}`);
log(`USDB change: ${fmt(usdbAfter - usdbBefore)}`);
log(`Predict+ in wallet: ${fmt(await getBalance(PREDICT_TOKEN))}`);

// FINAL PORTFOLIO STATUS
log('\n========== FINAL PORTFOLIO ==========');
log(`USDB: ${fmt(await getBalance(USDB))}`);

const stake = await client.staking.getUserStakeDetails(wallet);
log(`wSTASIS locked: ${fmt(stake[1])}`);

const loans = await client.api.getLoans();
const active = loans.data?.filter(l => l.active) || [];
log(`Active loans: ${active.length}`);
for (const l of active) {
  log(`  ${l.source} | ${l.token.substring(0,10)}... | repay=${fmt(BigInt(l.fullAmount))}`);
}
