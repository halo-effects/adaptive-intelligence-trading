import { BasisClient } from './dist/index.js';
import * as fs from 'fs';
import * as path from 'path';

// Load env
const envPath = path.join(__dirname, 'skill-scaffold', '.env');
const env = fs.readFileSync(envPath, 'utf-8')
  .split('\n')
  .filter(line => line.trim() && !line.startsWith('#'))
  .reduce((acc, line) => {
    const [key, ...rest] = line.split('=');
    acc[key.trim()] = rest.join('=').trim();
    return acc;
  }, {} as Record<string, string>);

const PRIVATE_KEY = env.BASIS_PRIVATE_KEY;
const API_KEY = env.BASIS_API_KEY;

if (!PRIVATE_KEY) {
  console.error('BASIS_PRIVATE_KEY not found in .env');
  process.exit(1);
}

console.log('=== Initializing Basis Client (TS) ===');
const client = await BasisClient.create({
  privateKey: PRIVATE_KEY,
  apiKey: API_KEY,
});

const wallet = client.account.address;
console.log(`Wallet: ${wallet}`);

console.log('\n=== Balances ===');
const usdbBalance = await client.token.getBalance('USDB');
const stasisBalance = await client.token.getBalance('STASIS');
const wstasisBalance = await client.staking.getBalance();
console.log(`USDB: ${usdbBalance.formatted}`);
console.log(`STASIS: ${stasisBalance.formatted}`);
console.log(`wSTASIS: ${wstasisBalance.formatted}`);

console.log('\n=== STASIS Price ===');
const price = await client.trading.getPrice(client.main_token_address);
console.log(`STASIS: $${price.formatted}`);

console.log('\n=== Profile ===');
const profile = await client.api.getProfile();
console.log(JSON.stringify(profile, null, 2));

console.log('\n=== Moltbook Status ===');
const moltbook = await client.api.getMoltbookStatus();
console.log(JSON.stringify(moltbook, null, 2));

console.log('\n=== Faucet ===');
const faucet = await client.api.getFaucetStatus();
console.log(JSON.stringify(faucet, null, 2));

console.log('\n=== Active Prediction Markets ===');
const predictions = await client.api.getTokens({ isPrediction: true, limit: 10, sort: 'newest' });
if (predictions.data && predictions.data.length > 0) {
  for (const token of predictions.data.slice(0, 5)) {
    console.log(`  ${token.symbol} | ${token.name.substring(0, 50)} | status: ${token.predictionStatus} | addr: ${token.address}`);
  }
} else {
  console.log('No prediction markets found');
}

console.log('\n=== Recent Floor+ Tokens ===');
const allTokens = await client.api.getTokens({ limit: 50, sort: 'newest' });
if (allTokens.data) {
  const floorTokens = allTokens.data.filter(t => t.multiplier && t.multiplier < 100);
  if (floorTokens.length > 0) {
    for (const token of floorTokens.slice(0, 10)) {
      console.log(`  ${token.symbol} | mult=${token.multiplier} | liq=$${token.liquidityUSD} | addr: ${token.address}`);
    }
  } else {
    console.log('No Floor+ tokens found. Showing all tokens:');
    for (const token of allTokens.data.slice(0, 10)) {
      const type = token.isPrediction ? 'Predict+' : token.multiplier === 100 ? 'Stable+' : 'Floor+';
      console.log(`  ${token.symbol} | type: ${type} | mult: ${token.multiplier} | addr: ${token.address}`);
    }
  }
} else {
  console.log('No tokens returned');
}

console.log('\n=== Staking Details ===');
const stakingDetails = await client.staking.getDetails();
console.log(JSON.stringify(stakingDetails, null, 2));

console.log('\n=== Active Loans ===');
const loans = await client.loans.getLoans();
console.log(JSON.stringify(loans, null, 2));

console.log('\n=== Done ===');
