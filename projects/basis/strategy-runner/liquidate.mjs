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
const fmt = (v) => formatUnits(v, 18);

// From the API: leverage loan liquidationTime = 1776115405
const liqTime = 1776115405;
const now = Math.floor(Date.now() / 1000);
console.log(`Now: ${now} (${new Date(now * 1000).toISOString()})`);
console.log(`Liquidation time: ${liqTime} (${new Date(liqTime * 1000).toISOString()})`);
console.log(`Expired: ${now > liqTime}`);
console.log(`Time until expiry: ${((liqTime - now) / 3600).toFixed(1)} hours`);

// Per Module 05: claimLiquidation(hubId) — but this is a leverage loan with hubId: null
// The API shows loanId: 1 for this leverage position
// Module 06 has settleLiquidation() for vault loans
// Let me try both approaches

if (now > liqTime) {
  console.log('\nLoan is expired! Attempting to claim...');
  
  // Try claimLiquidation with various IDs
  for (const id of [1n, 2n, 3n]) {
    try {
      console.log(`  Trying claimLiquidation(${id})...`);
      const tx = await client.loans.claimLiquidation(id);
      console.log(`  ✓ Claimed: ${tx.hash || tx}`);
      break;
    } catch (e) {
      console.log(`  Error: ${e.message.substring(0, 100)}`);
    }
  }
} else {
  console.log('\nLoan not yet expired. Cannot liquidate yet.');
  console.log('Options:');
  console.log('  1. Wait for expiry, then claimLiquidation()');
  console.log('  2. Try repaying the loan directly');
  
  // Try repaying — the loan might accept repayment even if position data is zeroed
  console.log('\nAttempting repayLoan with various IDs...');
  // The leverage loan has no hubId per API. But leverage positions have their own ID system.
  // Let me check if there's a way to repay via the leverage system
  
  // Actually — let me re-check. The API said hubId: null for this leverage loan.
  // Module 04 says leverage uses hubPartialLoanSell, not repayLoan.
  // But the position data is zeroed. Let me try settleLiquidation from staking module
  // in case this is somehow vault-related
  
  console.log('\nTrying staking.settleLiquidation()...');
  try {
    const tx = await client.staking.settleLiquidation();
    console.log(`  ✓ Settled: ${tx.hash || tx}`);
  } catch (e) {
    console.log(`  Error: ${e.message.substring(0, 100)}`);
  }
}

// Check final state
const erc20Abi = [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ name: 'account', type: 'address' }], stateMutability: 'view' }];
const usdb = await client.publicClient.readContract({ address: client.usdbAddress, abi: erc20Abi, functionName: 'balanceOf', args: [wallet] });
console.log(`\nUSDB: ${fmt(usdb)}`);

const loans = await client.api.getLoans();
const active = loans.data?.filter(l => l.active) || [];
console.log(`Active loans: ${active.length}`);
for (const l of active) {
  console.log(`  ${l.source} | ${l.token.substring(0,10)}... | active=${l.active}`);
}
