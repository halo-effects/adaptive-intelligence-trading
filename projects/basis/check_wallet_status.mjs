import { BasisClient } from './dist/index.mjs';
import * as fs from 'fs';
import * as path from 'path';
import { fileURLToPath } from 'url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));

// Load env
const envPath = path.join(__dirname, 'skill-scaffold', '.env');
const env = fs.readFileSync(envPath, 'utf-8')
  .split('\n')
  .filter(line => line.trim() && !line.startsWith('#'))
  .reduce((acc, line) => {
    const [key, ...rest] = line.split('=');
    acc[key.trim()] = rest.join('=').trim().replace(/^["']|["']$/g, '');
    return acc;
  }, {});

const PRIVATE_KEY = env.BASIS_PRIVATE_KEY;
const API_KEY = env.BASIS_API_KEY;

if (!PRIVATE_KEY) {
  console.error('BASIS_PRIVATE_KEY not found in .env');
  process.exit(1);
}

console.log('=== Initializing Basis Client ===');
const client = await BasisClient.create({
  privateKey: PRIVATE_KEY,
  apiKey: API_KEY,
});

const wallet = client.walletClient.account.address;
console.log(`Wallet: ${wallet}`);

console.log('\n=== On-Chain: Balances ===');
try {
  const usdbBal = await client.publicClient.readContract({
    address: client.usdbAddress,
    abi: [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ type: 'address' }], stateMutability: 'view' }],
    functionName: 'balanceOf',
    args: [wallet],
  });
  console.log(`USDB: ${Number(usdbBal) / 10**18} (wei: ${usdbBal})`);
} catch (e) { console.log(`USDB error: ${e.message}`); }

try {
  const stasisBal = await client.publicClient.readContract({
    address: client.mainTokenAddress,
    abi: [{ name: 'balanceOf', type: 'function', outputs: [{ type: 'uint256' }], inputs: [{ type: 'address' }], stateMutability: 'view' }],
    functionName: 'balanceOf',
    args: [wallet],
  });
  console.log(`STASIS: ${Number(stasisBal) / 10**18}`);
} catch (e) { console.log(`STASIS error: ${e.message}`); }

try {
  const bnb = await client.publicClient.getBalance({ account: wallet });
  console.log(`BNB: ${Number(bnb) / 10**18}`);
} catch (e) { console.log(`BNB error: ${e.message}`); }

console.log('\n=== On-Chain: wSTASIS Staking ===');
try {
  const details = await client.staking.getUserStakeDetails(wallet);
  console.log(`Locked wSTASIS: ${details.locked / 10**18}`);
  console.log(`Total value (STASIS): ${details.totalValue / 10**18}`);
} catch (e) { console.log(`Staking error: ${e.message}`); }

console.log('\n=== On-Chain: Loans ===');
try {
  const count = await client.loans.getUserLoanCount(wallet);
  console.log(`Total loans: ${count}`);
  for (let i = 1; i <= count; i++) {
    const loan = await client.loans.getUserLoanDetails(wallet, i);
    console.log(`  Loan ${i}: collateral=${loan.collateralAmount/10**18}, borrowed=${loan.borrowedAmount/10**18}, active=${loan.active}`);
  }
} catch (e) { console.log(`Loans error: ${e.message}`); }

console.log('\n=== API: Authenticate & Session ===');
try {
  await client.authenticate();
  console.log('✓ SIWE authentication successful');
  console.log(`Session cookie: ${client._sessionCookie ? '✓ set' : '✗ not set'}`);
} catch (e) { console.log(`Auth error: ${e.message}`); }

console.log('\n=== API: Profile ===');
try {
  const profile = await client.api.getProfile();
  console.log(JSON.stringify(profile, null, 2));
} catch (e) { console.log(`Profile error: ${e.message}`); }

console.log('\n=== API: Moltbook Status ===');
try {
  const mb = await client.api.getMoltbookStatus();
  console.log(JSON.stringify(mb, null, 2));
} catch (e) { console.log(`Moltbook error: ${e.message}`); }

console.log('\n=== API: Faucet Status ===');
try {
  const faucet = await client.api.getFaucetStatus();
  console.log(JSON.stringify(faucet, null, 2));
} catch (e) { console.log(`Faucet error: ${e.message}`); }

console.log('\n=== API: Tokens (Prediction) ===');
try {
  const tokens = await client.api.getTokens({ isPrediction: true, limit: 10, sort: 'newest' });
  if (tokens.data && tokens.data.length > 0) {
    console.log(`Found ${tokens.data.length} prediction markets:`);
    for (const t of tokens.data.slice(0, 5)) {
      console.log(`  ${t.symbol} | ${t.name} | addr: ${t.address}`);
    }
  } else {
    console.log('No prediction markets found');
  }
} catch (e) { console.log(`Tokens error: ${e.message}`); }

console.log('\n=== API: Tokens (All, newest) ===');
try {
  const tokens = await client.api.getTokens({ limit: 50, sort: 'newest' });
  if (tokens.data) {
    console.log(`Found ${tokens.data.length} total tokens:`);
    const predicted = tokens.data.filter(t => t.isPrediction);
    const floor = tokens.data.filter(t => t.multiplier && t.multiplier < 100);
    const stable = tokens.data.filter(t => t.multiplier === 100);
    console.log(`  Predict+: ${predicted.length}, Floor+: ${floor.length}, Stable+: ${stable.length}`);
    
    console.log('\n  Top 10 by creation:');
    for (const t of tokens.data.slice(0, 10)) {
      const type = t.isPrediction ? 'Predict+' : t.multiplier === 100 ? 'Stable+' : 'Floor+';
      console.log(`    ${t.symbol} (${type}) | mult=${t.multiplier} | liq=$${t.liquidityUSD} | ${t.address}`);
    }

    // Find best Floor+ for stacking
    const floorTokens = tokens.data.filter(t => t.multiplier && t.multiplier < 100 && t.multiplier > 0).sort((a, b) => b.liquidityUSD - a.liquidityUSD);
    if (floorTokens.length > 0) {
      console.log('\n  Floor+ by liquidity:');
      for (const t of floorTokens.slice(0, 5)) {
        console.log(`    ${t.symbol} | mult=${t.multiplier} | liq=$${t.liquidityUSD} | ${t.address}`);
      }
    }
  }
} catch (e) { console.log(`All tokens error: ${e.message}`); }

console.log('\n=== Done ===');
